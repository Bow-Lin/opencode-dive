# UI Module

## Module Responsibility

The UI layer is the interactive shell beyond raw CLI parsing. In the pinned version, the main analyzed UI surface is the terminal UI (TUI), which is responsible for:

- rendering interactive session and workspace views,
- collecting user input and command actions,
- maintaining a synchronized local view-model of runtime state,
- and bridging UI mutations back into the backend through the SDK.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/app.tsx` | TUI composition root and top-level event reactions | `tui(...)`, `App`, `SDKProvider`, `SyncProvider` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/context/sdk.tsx` | SDK client + event stream provider for UI components | `SDKProvider`, `createOpencodeClient(...)`, `sdk.event.subscribe(...)` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/context/sync.tsx` | local synchronized store fed by snapshots and event streams | `SyncProvider`, `bootstrap()`, `sdk.event.listen(...)` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/thread.ts` | worker-thread launcher and transport selection for local TUI mode | `TuiThreadCommand`, `createWorkerFetch`, `createEventSource` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/worker.ts` | worker-side RPC bridge to in-process server and event bus | `rpc.fetch`, `Bus.subscribeAll(...)`, `startEventStream(...)` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/routes/session/index.tsx` | main session screen consuming sync state and issuing SDK mutations | `useSync()`, `useSDK()` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/component/prompt/index.tsx` | prompt input surface and prompt/command/shell submission | `sdk.client.session.create/prompt/command/shell(...)` |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `tui(input)` | entrypoint | `app.tsx` | starts the TUI renderer and provider tree |
| `SDKProvider` | context/provider | `context/sdk.tsx` | owns SDK client and inbound event stream |
| `SyncProvider` | context/provider | `context/sync.tsx` | owns locally synchronized UI store |
| `EventSource` | transport type | `context/sdk.tsx` | abstracts custom worker-provided event feeds |
| `TuiThreadCommand` | launcher | `thread.ts` | starts worker-backed local TUI or network mode |
| `rpc.fetch(...)` | bridge | `worker.ts` | forwards SDK HTTP calls into `Server.Default().fetch(...)` |

## Initialization / Entry

The main local TUI path starts at `TuiThreadCommand`:

1. resolve target directory and config,
2. start a worker thread,
3. choose transport mode,
4. call `tui(...)`.

Transport modes:

- internal/local mode:
  - worker RPC provides `fetch` and event bridge
  - backend requests stay in-process
- external/server mode:
  - TUI points directly at a real server URL
- attach mode:
  - `AttachCommand` skips the worker and connects to an existing server

## Main Control Flow

### 1. Build UI Runtime Context

`tui(...)` composes the UI around a provider stack including:

- `SDKProvider`
- `SyncProvider`
- theme/dialog/keybind/local-state providers

This establishes a clean split between backend access, synchronized runtime state, and purely local UI state.

### 2. Receive Runtime State

`SDKProvider` creates the `@opencode-ai/sdk/v2` client and manages event intake:

- direct SSE through `sdk.event.subscribe(...)` when no custom event source is supplied,
- or custom events forwarded from the worker bridge.

Events are batched before emission to reduce render churn.

### 3. Maintain Local Sync Store

`SyncProvider` is the actual UI-facing state cache.

It does two jobs:

1. bootstrap initial snapshots through SDK queries such as:
   - `session.list`
   - `config.get`
   - `app.agents`
   - `command.list`
   - `session.get/messages/todo/diff`
2. update that local store incrementally from streamed events such as:
   - `session.updated`
   - `message.updated`
   - `message.part.updated`
   - `session.status`
   - permission/question events

### 4. Render From Synced State

UI routes and components generally render from `useSync()` data rather than directly reading runtime services.

Examples:

- session route reads synchronized session/message/part state;
- prompt component derives session status and transcript context from the sync store;
- plugin API exposes the same synchronized data to UI plugins.

### 5. Send Mutations Back Through SDK

When the user acts, components call `sdk.client.*` methods for mutations and one-off queries:

- `session.create`
- `session.prompt`
- `session.command`
- `session.shell`
- `session.abort`
- `session.fork`

This keeps the UI in client mode even in local execution.

## Upstream And Downstream Dependencies

Upstream:

- CLI thread/attach commands
- terminal renderer/input system

Downstream:

- `@opencode-ai/sdk/v2`
- worker RPC bridge in local mode
- `Server.Default().fetch(...)` through worker fetch
- `Bus.subscribeAll(...)` through worker event forwarding
- local Solid store consumers across routes/components/plugins

## Implementation Details

- The TUI is built with Solid plus `@opentui/*`, not a simple readline loop.
- Local mode uses a worker thread so the UI thread stays isolated from backend/server work.
- The UI's main render source is synchronized local state, not direct backend service calls.
- Workspace switching rebuilds the SDK client with `experimental_workspaceID` and refreshes the event stream.
- `App` still listens to some events directly for toasts/navigation, but those are UI reactions layered on top of the broader sync store.

## Design Tradeoffs / Risks

- The TUI architecture is cleanly layered, but it introduces multiple caches and transports: SDK snapshots, event streams, sync store, and local UI state.
- Local worker mode improves responsiveness and isolation, but adds RPC/event-bridge complexity.
- Because rendering is sync-store driven, missing or misordered events can create stale UI even when the backend state is correct.

## Pending Verification

- How much of the web/app/desktop packages reuse the same backend interaction model versus adding distinct UI-specific state layers.
- Whether any TUI screens still depend heavily on direct ad hoc SDK fetches instead of the shared sync store.
