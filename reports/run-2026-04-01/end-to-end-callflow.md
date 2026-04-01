# End-To-End Call Flow

## Goal

Produce a single code-anchored request path that crosses entry surfaces, orchestration, provider/tool execution, persistence, and final rendering.

## Summary

The dominant path is not “CLI directly calls model.” It is:

1. client shell,
2. control-plane/API boundary,
3. session orchestrator,
4. stream processor,
5. provider/tool execution,
6. sync-backed persistence,
7. client rendering.

## Canonical Path

### 1. User input enters a shell

The request starts in:

- plain CLI `run`, or
- TUI prompt submission.

These differ in UX, but both become SDK/session mutations quickly.

### 2. The client becomes a backend client

In local mode, both CLI and TUI commonly talk to the in-process backend through:

- `Server.Default().fetch(...)`

Interpretation:

- there is a real internal client/server boundary even without a remote network hop.

### 3. The server binds workspace context

`WorkspaceRouterMiddleware` activates the correct instance via `Instance.provide(...)`.

Interpretation:

- runtime execution is always scoped to a concrete directory/worktree context before session orchestration begins.

### 4. SessionPrompt takes ownership

`SessionRoutes` hands the request to `SessionPrompt.*`.

`SessionPrompt`:

- creates the user message,
- enters the per-session runner,
- loads history,
- selects model/agent,
- resolves tools and prompts,
- delegates one execution step.

Interpretation:

- this is the main control owner in the backend.

### 5. SessionProcessor runs one streamed step

`SessionProcessor.process(...)` consumes the provider stream and updates:

- text parts,
- reasoning parts,
- tool parts,
- errors/retries.

Interpretation:

- orchestration and stream execution are separate layers.

### 6. Provider and tools execute beneath that layer

`LLM.stream(...)` resolves provider/model execution and active tools.

If the model requests a tool:

- the tool map created in `SessionPrompt.resolveTools(...)` executes it,
- tool results re-enter the stream/event flow,
- session parts are updated accordingly.

### 7. Durable state is written through sync/projectors

Session/message/part writes flow through:

- `Session.*`
- `SyncEvent.run(...)`
- session projectors
- SQLite tables

Interpretation:

- final output is always also a persistence event path.

### 8. The client renders from events/state

Plain CLI renders directly from subscribed events.

TUI:

- ingests events and snapshot reads through the SDK,
- updates `SyncProvider`,
- renders from synchronized local state.

Interpretation:

- “final response” exists simultaneously as rendered UI output and stored transcript state.

## Key Conclusions

- The end-to-end flow is centered on `SessionPrompt`, not on the CLI parser or event bus.
- The internal control-plane API is a major architectural boundary even for local usage.
- Persistence is part of the hot path, not an afterthought.
- Tool execution is embedded in the same loop rather than handled by a separate job system.

## Open Questions

- Whether alternative surfaces such as ACP introduce a materially different front-half of the flow.
- Which provider-specific quirks can change the exact event ordering without changing the high-level spine.
