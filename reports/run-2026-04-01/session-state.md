# Session State

## Goal

Explain how Opencode creates session state, persists transcript mutations, and restores usable conversation history for later runtime steps.

## Summary

The session state system has three distinct layers:

1. `Session.Service` owns lifecycle and mutation APIs.
2. `SyncEvent` plus session projectors turn those mutations into durable SQLite writes.
3. `MessageV2` reconstructs stored rows back into hydrated transcript objects and model-facing messages.

## Findings

### 1. `Session.Service` is the state owner

The main owner of persisted conversation state is `Session.Service` in `session/index.ts`.

It exposes:

- lifecycle APIs such as `create`, `fork`, `get`, `remove`, `setTitle`, `setPermission`;
- transcript mutation APIs such as `updateMessage`, `updatePart`, `removeMessage`, `removePart`;
- transcript read APIs such as `messages`.

Interpretation:

- runtime modules should not write SQL directly;
- session state is intentionally centralized behind service methods.

### 2. Persistence is event-driven, not repository-style

Writes flow through `SyncEvent.run(...)`, not direct table updates from runtime code.

Examples:

- `Session.Event.Created`
- `Session.Event.Updated`
- `MessageV2.Event.Updated`
- `MessageV2.Event.PartUpdated`

Interpretation:

- the persistence model is closer to event projection than CRUD repositories;
- replay/order semantics are part of the design.

### 3. Durable storage is split across session, message, and part tables

Observed durable tables:

- `SessionTable`
- `MessageTable`
- `PartTable`

Notable shape:

- IDs, session linkage, and timestamps are explicit indexed columns;
- most payload is stored in JSON `data` columns.

Interpretation:

- the schema keeps transcript structure flexible;
- hydration code becomes essential because rows are intentionally normalized only partially.

### 4. Projectors are the real SQL writers

`session/projectors.ts` handles inserts/updates/deletes for session/message/part events.

Notable behavior:

- message and part writes use upsert semantics;
- some late foreign-key failures are tolerated and logged rather than throwing hard.

Interpretation:

- the projector layer is the true persistence adapter;
- it absorbs some race/ordering tolerance that runtime callers do not handle directly.

### 5. Read restoration is centered on `MessageV2`

`Session.messages(...)` does not query message/part joins itself. It delegates to `MessageV2.stream(sessionID)`.

Observed read chain:

- `page(...)` fetches a reverse-chronological slice from `MessageTable`;
- `hydrate(...)` loads matching part rows from `PartTable`;
- `stream(...)` yields chronological `WithParts` items;
- `Session.messages(...)` collects them.

Interpretation:

- `MessageV2` is effectively the transcript read model.

### 6. Runtime replay is filtered and projected, not raw

Before a model call, stored history is transformed by:

- `filterCompacted(...)`
- `toModelMessages(...)`

This means:

- the runtime may deliberately ignore older pre-compaction history;
- provider-facing messages are reconstructed from persisted transcript state with provider/media/tool-specific logic.

### 7. Live deltas are not the persistence format

`Session.updatePartDelta(...)` only publishes `message.part.delta` on `Bus`.

Interpretation:

- streaming UIs can observe incremental text/tool output;
- durable history is only guaranteed once a full part update is written.

### 8. Some session state lives outside the main transcript tables

Observed side channels:

- `session_diff/<sessionID>` in `Storage` for diffs,
- share URL integration through `ShareNext`,
- summary/revert metadata embedded in `SessionTable`,
- TODO state in `TodoTable`.

Interpretation:

- "session state" is broader than transcript rows, but the core memory path still revolves around session/message/part persistence.

## Key Conclusions

- `Session.Service` is the authoritative API boundary for session state.
- `SyncEvent + projectors + SQLite` is the durable write path.
- `MessageV2` is the read/hydration/projection bridge back into runtime form.
- Incremental bus deltas are observability/live UX features, not durable memory.

## Open Questions

- Whether TODO state should be treated as part of the main conversation memory model or as an adjacent per-session subsystem.
- How often sync-event replay is exercised in ordinary product flows versus migration/recovery scenarios.
