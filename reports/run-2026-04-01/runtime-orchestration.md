# Runtime Orchestration

## Goal

Identify the layer that actually coordinates the interactive runtime after a request enters Opencode, and explain its boundaries to transport, provider, tool, and state subsystems.

## Summary

The main runtime orchestrator is `SessionPrompt`, especially its internal `runLoop(sessionID)` path. It is not the CLI command handler, the Hono server, or the event bus.

The orchestration stack is best understood as:

1. transport entrypoint,
2. instance/workspace binding,
3. session orchestrator,
4. stream processor,
5. delegated subsystems,
6. outward status/events.

## Findings

### 1. The server and CLI are transport shells around the same backend core

Observed path:

- `cli/cmd/run.ts` builds an SDK client;
- local mode points that SDK client at `Server.Default().fetch(...)`;
- `server/routes/session.ts` calls `SessionPrompt.prompt(...)` / `command(...)` / `shell(...)`.

Interpretation:

- even local CLI usage is often routed through the same internal API boundary used by server mode;
- transport handling and runtime orchestration are intentionally separated.

### 2. `WorkspaceRouterMiddleware` and `InstanceBootstrap` establish execution context, not business orchestration

`WorkspaceRouterMiddleware` selects the correct directory/workspace and wraps request handling in:

- `Instance.provide({ directory, init: InstanceBootstrap, ... })`

`InstanceBootstrap()` initializes project-scoped services such as plugins, formatting, LSP, file services, snapshots, and a bus subscription.

Interpretation:

- this layer prepares the environment for orchestration;
- it does not itself own the prompt/tool/model loop.

### 3. `SessionPrompt.runLoop` is the real control owner

The loop in `session/prompt.ts` decides:

- whether the session should continue at all,
- whether to branch into subtask handling,
- whether to trigger compaction,
- which model and agent to use,
- when to create an assistant message,
- when to delegate execution to the processor,
- and whether the result means `break`, `continue`, or `compact`.

This is the clearest runtime ownership point found so far.

Related boundary:

- transport code crosses into this layer through exported `SessionPrompt.*` wrappers that call `runPromise(...)`;
- after that, orchestration runs inside the service runtime rather than in route-handler code.

### 4. `Runner` provides per-session serialization and cancel semantics

`SessionPrompt.loop(...)` uses a `Runner` stored in an instance-scoped `Map`.

Observed behaviors:

- one active loop per session;
- later prompt attempts reuse or wait on the active run;
- shell execution is a specialized path;
- cancellation is centralized.

Interpretation:

- orchestration is not merely a recursive function; it is protected by an explicit concurrency primitive.

### 5. `SessionProcessor` is the execution delegate, not the top-level orchestrator

`SessionPrompt` creates a processor per assistant message, then calls `handle.process(...)`.

`SessionProcessor` handles:

- streaming events,
- retries,
- text/reasoning/tool part updates,
- errors,
- stop/compact/continue signaling.

Interpretation:

- `SessionPrompt` owns session policy;
- `SessionProcessor` owns one streamed execution attempt inside that policy.

### 6. Bus/status infrastructure is adjacent, not central, to the control loop

Observed uses:

- `SessionStatus.set(...)` publishes `busy`, `retry`, and `idle`;
- `SessionPrompt` and `SessionProcessor` publish `Session.Event.Error` on failure paths;
- `Bus` is a publish/subscribe surface for observers and integrations.

Interpretation:

- `Bus` is a signaling layer, not the dispatcher driving orchestration steps.

### 7. Sync is mainly for persistent domain-event projection

`SyncEvent`:

- defines versioned domain events,
- applies projectors inside DB transactions,
- supports replay and aggregate sequences,
- can republish to the bus.

Interpretation:

- sync is about durable state projection/replay;
- it is architecturally important, but it does not appear to drive the hot prompt loop directly.

## Key Conclusions

- `SessionPrompt` is the runtime orchestration core.
- `Runner` is the mechanism that makes session orchestration single-flight and cancelable.
- `SessionProcessor` is a subordinate execution layer that consumes one model/tool stream.
- `Bus` and `SyncEvent` matter for visibility and persistence, but they are not the main interactive dispatcher.

## Open Questions

- Whether any ACP or non-session flows implement a parallel orchestration path outside `SessionPrompt`.
- How much TUI behavior depends on live bus/event subscriptions versus polling session state APIs.
