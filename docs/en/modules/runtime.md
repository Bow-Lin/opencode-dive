# Runtime Module

## Module Responsibility

The runtime orchestration layer coordinates the interactive session loop after a request has already entered the core backend. In the pinned version, its responsibilities are:

- serializing work per session,
- turning a user message into one or more model/tool/compaction steps,
- managing cancellation and busy state,
- delegating stream execution to the LLM and processor layers,
- and deciding when the loop should continue, compact, stop, or switch into subtask/shell flows.

Detailed file-level analysis of the orchestration core lives in `session-prompt.md`. That page explains why `session/prompt.ts` is not just a prompt-template file and why it owns so much runtime control.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | main runtime orchestrator and per-session loop owner | `SessionPrompt.prompt`, `runLoop`, `loop`, `shell`, `command` |
| `workspace/source/opencode/packages/opencode/src/effect/runner.ts` | per-session single-flight runner with cancel/shell sequencing | `Runner.make`, `ensureRunning`, `startShell`, `cancel` |
| `workspace/source/opencode/packages/opencode/src/session/processor.ts` | streamed model/tool event consumer used by the orchestrator | `SessionProcessor.create`, `process(...)`, `abort(...)` |
| `workspace/source/opencode/packages/opencode/src/session/compaction.ts` | compaction side-loop invoked by the main session loop | `SessionCompaction.process`, `create`, `prune` |
| `workspace/source/opencode/packages/opencode/src/session/status.ts` | session busy/retry/idle state publication | `SessionStatus.set(...)` |
| `workspace/source/opencode/packages/opencode/src/server/routes/session.ts` | request boundary that hands control to `SessionPrompt` | `session.prompt`, `session.command`, `session.shell` routes |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `SessionPrompt.prompt(...)` | entrypoint | `prompt.ts` | creates the user message and enters the session loop |
| `runLoop(sessionID)` | orchestrator loop | `prompt.ts` | owns step-by-step control of a live session |
| `loop({ sessionID })` | serialization wrapper | `prompt.ts` | ensures only one runner owns a session loop at a time |
| `Runner.make(...)` | concurrency primitive | `runner.ts` | creates the single-flight runner used per session |
| `SessionProcessor.create(...)` | processor factory | `processor.ts` | binds a new assistant message to a stream event handler |
| `SessionProcessor.process(...)` | delegated execution | `processor.ts` | consumes LLM stream events and returns `continue` / `stop` / `compact` |
| `SessionCompaction.process(...)` | branch handler | `compaction.ts` | performs summary compaction when the loop switches modes |
| `SessionStatus.set(...)` | signaling helper | `status.ts` | publishes busy/retry/idle status out to observers |

## Initialization / Entry

The runtime layer is reached from two main front doors:

1. CLI flow:
   - `cli/cmd/run.ts` builds an SDK client,
   - often pointing at `Server.Default().fetch(...)`,
   - then calls `sdk.session.prompt(...)` or `sdk.session.command(...)`.
2. Server flow:
   - `server/routes/session.ts` validates the request,
   - then directly calls `SessionPrompt.prompt(...)`, `SessionPrompt.command(...)`, or `SessionPrompt.shell(...)`.

The concrete runtime handoff happens when those exported `SessionPrompt.*` wrappers call `runPromise(...)` from `makeRuntime(...)`. At that point control ownership moves out of the transport layer and into the Effect-backed orchestration service.

## Main Control Flow

### 1. Enter SessionPrompt

`SessionPrompt.prompt(...)`:

1. loads the target session,
2. cleans revert state,
3. creates the new user message,
4. applies explicit per-request tool permission overrides,
5. and, unless `noReply` is set, enters `loop({ sessionID })`.

### 2. Serialize Per Session

`loop(...)` looks up a runner from an instance-scoped `Map<sessionID, Runner<...>>`.

This means:

- only one interactive loop can own a session at a time;
- repeated prompt attempts reuse the in-flight runner;
- shell execution has its own runner path via `startShell(...)`;
- cancellation is centralized through the runner rather than spread across modules.

### 3. Run The Main Orchestration Loop

`runLoop(sessionID)` is the core orchestrator.

On each iteration it:

1. loads compacted message history,
2. finds the latest user/assistant state,
3. selects the model,
4. branches into subtask handling, compaction handling, or normal assistant generation,
5. creates the next assistant message record,
6. creates a `SessionProcessor` for that message,
7. resolves tools, system prompts, instructions, and model messages,
8. delegates execution to `handle.process(...)`,
9. interprets the result as `break`, `continue`, or `compact`.

### 4. Delegate Streaming Work

The orchestrator does not directly consume provider events itself. It hands that responsibility to `SessionProcessor.process(...)`, which:

- calls `LLM.stream(...)`,
- updates text/reasoning/tool parts,
- manages retries,
- records errors,
- and returns a control signal back to the loop.

This is the boundary between "control-plane orchestration" and "stream event consumption."

### 5. Handle Side Branches

The loop explicitly branches for:

- subtask execution,
- overflow or auto compaction,
- shell mode,
- command-template expansion,
- structured-output enforcement,
- cancellation and abort cleanup.

This makes `SessionPrompt` the place where high-level runtime policy lives, even though actual provider/tool/state work is delegated outward.

## Upstream And Downstream Dependencies

Upstream:

- `server/routes/session.ts` and CLI SDK callers
- `Instance.provide(..., init: InstanceBootstrap)` for workspace-scoped context
- `Agent`, `Provider`, `Command`, `Permission`, `Plugin`, `Config`

Downstream:

- `SessionProcessor` for event handling
- `LLM` / `Provider` for model execution
- `ToolRegistry` and MCP/LSP for executable capabilities
- `Session` / `MessageV2` for durable message-state updates
- `SyncEvent`-backed session/message projectors for persistence writes
- `SessionCompaction` for summary fallback
- `SessionStatus` / `Bus` for published state

## Implementation Details

- Runtime serialization is instance-scoped and keyed by session ID, not purely global.
- `Runner.onIdle` and `Runner.onBusy` are wired into `SessionStatus.set(...)`, so session status is a projection of orchestrator state rather than a separate scheduler.
- `SessionPrompt.command(...)` and `SessionPrompt.shell(...)` are sibling orchestration entrypoints that still reuse the same runner model.
- The loop uses concrete branch conditions on message history and finish reasons instead of a generic reducer or explicit state machine object.
- `SessionCompaction` is not background-only; it is a first-class branch inside the main loop and can recursively cause the next loop step.
- Session/message mutations performed during orchestration eventually flow through `Session.*` APIs backed by `SyncEvent.run(...)`, so persistence is on the hot path even though sync is not the loop driver.

## Design Tradeoffs / Risks

- The main orchestration logic is concentrated in a very large `session/prompt.ts`, which makes control ownership clear but increases local complexity.
- Session serialization through `Runner` avoids overlapping execution but also means long-running operations directly affect responsiveness for that session.
- High-level policy and low-level branching live in the same module, so `SessionPrompt` risks becoming a god object for runtime behavior.
- Because transport entrypoints funnel into the same orchestration core, bugs in `SessionPrompt` can affect both CLI and server surfaces simultaneously.

## Pending Verification

- Whether any non-session interactive flows bypass `SessionPrompt` for provider execution.
- How much of TUI-specific behavior is runtime orchestration versus pure client-side subscription/rendering.
