# SessionPrompt / `prompt.ts`

## Why This File Name Is Misleading

At first glance, `workspace/source/opencode/packages/opencode/src/session/prompt.ts` sounds like a prompt-template file. That reading is understandable but wrong.

The repository does contain textual prompt assets under `workspace/source/opencode/packages/opencode/src/session/prompt/`, but `prompt.ts` itself is not a bag of prompt strings. It is the runtime orchestration core for interactive session execution.

That distinction matters because readers who skip this file often misunderstand where the system's control ownership actually lives.

## What This File Really Is

`prompt.ts` is the main control layer that takes a session-scoped request and turns it into a live execution loop.

In practical terms, it owns:

- accepting prompt / command / shell entrypoints,
- creating the new user message,
- deciding whether the session loop should start,
- serializing work per session through `Runner`,
- selecting models and agents,
- resolving bound tools and MCP tools,
- coordinating subtask, compaction, command, and shell branches,
- and deciding when the loop should continue, stop, or hand off.

This makes `SessionPrompt` the runtime orchestrator, not a content-definition helper.

## Control Ownership

The most important way to read this file is as a control-ownership map.

`SessionPrompt` owns:

1. transport handoff after CLI / SDK / server routing,
2. session-loop ownership through `loop(...)` and `runLoop(...)`,
3. concurrency and cancellation boundaries through per-session `Runner` instances,
4. model/tool/system prompt preparation before a model call,
5. high-level runtime branch policy:
   - normal assistant turn
   - subtask execution
   - compaction
   - command expansion
   - shell execution
   - structured-output enforcement

It does not own the whole runtime alone, but it is the place where those concerns are coordinated.

## What It Delegates

The file is powerful because it coordinates many things, but it still delegates key responsibilities outward.

### Delegated To `Session`

- create/update/touch session state
- persist messages and parts
- manage session metadata such as permissions or revert state

`SessionPrompt` does not write database rows directly. It calls `Session.*`.

### Delegated To `SessionProcessor`

- consume streamed model/tool events
- update assistant parts as output arrives
- convert low-level stream activity into `continue` / `stop` / `compact`

This means `SessionPrompt` decides the loop, but `SessionProcessor` handles one model run.

### Delegated To `LLM`

- provider-facing model execution
- actual `stream(...)` call into the selected language model

### Delegated To `ToolRegistry` And Tool Definitions

- discover the available tool surface
- initialize built-in, config, plugin, and MCP tools
- execute the concrete tool logic

`prompt.ts` binds tools into session context, but it is not where most tool business logic lives.

### Delegated To `SessionStatus`

- publish busy / retry / idle status

The file owns when status changes, but not the status-store abstraction itself.

### Delegated To `SessionCompaction`

- detect and execute summary compaction branches

## Relationship To `Session`

`Session` and `SessionPrompt` are not sibling orchestrators.

Their relationship is:

- `Session` is the durable state boundary,
- `SessionPrompt` is the live execution coordinator built on top of that state.

In other words:

1. `SessionPrompt` reads session history and metadata from `Session`,
2. uses that state to drive the next runtime step,
3. then writes the resulting state back through `Session`.

This is why `SessionPrompt` feels central without replacing the session module itself.

## Main Entrypoints

The exported API surface makes the file's real role visible.

### `prompt(input)`

This is the main interactive entrypoint.

It:

1. loads the target session,
2. cleans revert state,
3. creates the user message,
4. applies per-request permission overrides,
5. and enters `loop(...)` unless `noReply` is set.

### `loop({ sessionID })`

This is the serialization wrapper.

It does not implement the loop body itself. Instead, it:

- gets or creates the session runner,
- ensures only one active loop owns the session,
- and forwards control into `runLoop(sessionID)`.

### `runLoop(sessionID)`

This is the true orchestration core.

On each pass it:

1. loads filtered session history,
2. discovers the latest user/assistant state,
3. handles pending subtask or compaction work,
4. resolves agent/model/tools,
5. creates the next assistant message,
6. creates a `SessionProcessor`,
7. delegates one streamed run,
8. interprets the outcome,
9. repeats or exits.

If you want to understand where "the runtime loop" actually lives, this is the function.

### `shell(input)`

This is not a side utility. It is a sibling orchestration entrypoint that uses the same runner model but starts shell execution through `runner.startShell(...)`.

### `command(input)`

This expands a named command template, resolves arguments, shell substitutions, target agent/model, and then funnels the final result back into `prompt(...)`.

That is an important design clue: commands are not a separate execution system. They are another path into the same session-oriented orchestration core.

## Internal File Structure

The file is large, but it is not random. It has a recognizable structure.

### 1. Service Wiring And Dependency Assembly

Near the top of the `Layer.effect(...)`, the file pulls in its core collaborators:

- `Session`
- `Agent`
- `Provider`
- `SessionProcessor`
- `SessionCompaction`
- `Plugin`
- `Command`
- `Permission`
- `MCP`
- `LSP`
- `ToolRegistry`
- `SessionStatus`

This section is the strongest evidence that the file is acting as an orchestration hub.

### 2. Runner Cache And Concurrency Control

The `InstanceState` cache stores `Map<sessionID, Runner<...>>`.

This is where the file establishes:

- one active runner per session,
- cancellation routing,
- idle/busy transitions,
- and cleanup on scope finalization.

### 3. Prompt-Preparation Helpers

Functions such as `resolvePromptParts(...)`, title generation, reminder insertion, and command-template expansion live here.

These are not the core loop, but they prepare the state that the loop depends on.

### 4. Tool Resolution

`resolveTools(...)` is one of the file's most revealing helpers.

It takes registry-level tool definitions and binds them to a live session context:

- `sessionID`
- `messageID`
- `callID`
- active model metadata
- permission requests
- metadata updates into matching tool parts

This is why `prompt.ts` sits above `ToolRegistry`: it turns static tool definitions into runtime-bound executable capabilities.

### 5. Branch Helpers

Helpers such as `handleSubtask(...)` and `shellImpl(...)` support specialized branches that still participate in the same overall orchestration model.

### 6. Core Entrypoints

The file then defines:

- `prompt`
- `runLoop`
- `loop`
- `shell`
- `command`

This is the real spine of the file.

### 7. Exported Input Schemas And Wrappers

At the bottom, `PromptInput`, `LoopInput`, `ShellInput`, and `CommandInput` define the public shape of the orchestration API. The exported async wrappers call `runPromise(...)` and expose the service outside the Effect layer.

## Why The Name Still Exists

A likely reason the file is still named `prompt.ts` is historical layering:

- the file probably began closer to "handle a prompt",
- then absorbed more and more runtime coordination responsibilities,
- until it became the effective session orchestration core.

So the name now reflects its original entrypoint more than its current architectural weight.

## Design Tradeoffs And Risks

The design has one strong advantage: control ownership becomes easier to locate once you know this file matters.

But the tradeoffs are real:

- the file concentrates a large amount of policy,
- transport concerns and runtime policy meet here,
- branch logic for subtasks, compaction, commands, and shell mode all accumulate in one place,
- and bugs here can affect both CLI and server flows at once.

This is why the file is both the best place to understand the runtime and the riskiest place for architectural complexity to pool.

## Reading Advice

If you want to understand this file efficiently, use this order:

1. `prompt(...)`
2. `loop(...)`
3. `runLoop(...)`
4. `resolveTools(...)`
5. `command(...)`
6. `shell(...)`

Then cross-reference:

- `runtime.md`
- `session.md`
- `callflows/prompt-to-model.md`
- `callflows/tool-call-execution.md`

## Primary Code Anchors

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/index.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`
- `workspace/source/opencode/packages/opencode/src/session/compaction.ts`
- `workspace/source/opencode/packages/opencode/src/session/status.ts`
- `workspace/source/opencode/packages/opencode/src/tool/registry.ts`
- `workspace/source/opencode/packages/opencode/src/session/llm.ts`
