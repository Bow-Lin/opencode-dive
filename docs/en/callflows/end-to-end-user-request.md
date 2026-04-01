# End-To-End User Request Flow

## Trigger

Canonical analyzed trigger: a local user submits a request through Opencode's CLI or TUI, which then reaches the shared backend runtime and produces assistant output, tool actions, and persisted session state.

The exact front end can differ:

- plain CLI `run`
- local TUI
- attached/remote server-backed UI

But the backend control path converges quickly.

## Start File / Symbol

Primary entry files/symbols:

- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts`
- `workspace/source/opencode/packages/opencode/src/server/router.ts`
- `workspace/source/opencode/packages/opencode/src/server/routes/session.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`

## Ordered Execution Steps

1. The user enters a message in a CLI/TUI surface.
2. The client shell normalizes input:
   - yargs command handler for CLI,
   - prompt component + SDK mutation for TUI.
3. In local mode, the client usually targets the in-process control-plane app via `Server.Default().fetch(...)`; in remote/attach mode it targets a real server URL.
4. `WorkspaceRouterMiddleware` establishes the correct directory/workspace instance through `Instance.provide(..., init: InstanceBootstrap)`.
5. `SessionRoutes` receives the session mutation request and calls `SessionPrompt.prompt(...)`, `command(...)`, or `shell(...)`.
6. `SessionPrompt.prompt(...)` creates/touches the user message, applies request-level tool permissions, and enters the per-session runner.
7. `SessionPrompt.runLoop(...)` loads current session history, selects the agent/model path, branches for compaction/subtasks if needed, creates the next assistant message, resolves tools/system prompt/messages, and delegates one execution step to `SessionProcessor.process(...)`.
8. `SessionProcessor.process(...)` calls `LLM.stream(...)`, consumes streamed model events, and updates message parts for text, reasoning, tool calls, tool results, errors, and retries.
9. `LLM.stream(...)` resolves provider/model config, filters active tools, and calls AI SDK `streamText(...)`; if the model requests tools, execution flows through the session-bound tool map created by `SessionPrompt.resolveTools(...)`.
10. Tool execution updates session state through `Session.updatePart(...)` and related APIs, while persistent session/message/part mutations flow through `SyncEvent.run(...)` into SQLite projectors.
11. When the model/tool loop finishes or stops, `SessionStatus` returns to `idle`; client shells observe streamed events and final stored transcript updates.
12. The final user-visible output is:
    - rendered directly in CLI/TUI,
    - persisted in session/message/part storage,
    - and available for later replay through session history APIs.

## State Transitions

- transport state:
  - raw input becomes SDK/server session mutation request
- runtime state:
  - user message created
  - assistant message created
  - runner busy/idle transitions
- model/tool state:
  - text/reasoning/tool parts move through pending/running/completed/error
- persistence state:
  - session/message/part sync events projected into DB
- client state:
  - UI/CLI reacts to streamed events and/or synchronized store updates

## External Boundaries

- shell/UI boundary at CLI/TUI input
- control-plane HTTP/fetch boundary at `Server.Default().fetch(...)` or remote server
- workspace-instance boundary at `Instance.provide(...)`
- provider SDK/network boundary inside `LLM.stream(...)`
- SQLite/sync-event persistence boundary for session state

## Failure / Branching Behavior

- CLI/TUI argument validation can fail before runtime entry.
- Missing session/agent/model errors are surfaced through session error events and client rendering.
- Compaction and subtask handling are explicit branches inside `SessionPrompt.runLoop(...)`.
- Tool permission rejection or question rejection can block the current step and stop the loop.
- Providers may trigger retries or compatibility shims such as `_noop` tools for LiteLLM-like proxies.
- Final output can be plain assistant text, structured output, tool side effects, or an error state persisted into the session.

## Evidence Table

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 1-2 | `workspace/source/opencode/packages/opencode/src/index.ts` | yargs CLI + command dispatch | raw shell input becomes command handler invocation |
| 2-3 | `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts` | `execute(sdk)` / local `fetchFn` | local CLI becomes SDK client over in-process server |
| 3-4 | `workspace/source/opencode/packages/opencode/src/server/router.ts` | `WorkspaceRouterMiddleware` | binds request to project/workspace instance |
| 5 | `workspace/source/opencode/packages/opencode/src/server/routes/session.ts` | `session.prompt` / `session.command` routes | transport handoff into session runtime |
| 6-7 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `prompt`, `loop`, `runLoop` | main orchestration core |
| 8 | `workspace/source/opencode/packages/opencode/src/session/processor.ts` | `process(...)` | consumes stream events into transcript state |
| 9 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | `LLM.stream(...)` | provider + tool handoff into AI SDK |
| 9 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | internal `resolveTools(...)` | builds session-bound tool executors |
| 10 | `workspace/source/opencode/packages/opencode/src/session/index.ts` | `updateMessage/updatePart/...` | durable session mutation API |
| 10 | `workspace/source/opencode/packages/opencode/src/sync/index.ts` | `SyncEvent.run(...)` | persistence/event projection boundary |
| 10 | `workspace/source/opencode/packages/opencode/src/session/projectors.ts` | session/message/part projectors | SQLite writes |
| 11-12 | `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts` | event subscription loop | CLI rendering of final events/output |
| 11-12 | `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/context/sync.tsx` | `SyncProvider` | TUI synchronized state/render path |

## Pending Verification

- Exact differences between plain CLI and TUI event ordering under heavy tool usage.
- Which rare commands bypass the standard session mutation route and therefore alter the front half of this chain.
