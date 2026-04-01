# Session Persistence Flow

## Trigger

Either:

- a runtime path creates or mutates session/message/part state,
- or a reader loads prior conversation state back into the runtime.

## Start File / Symbol

- `workspace/source/opencode/packages/opencode/src/session/index.ts`
- key symbols:
  - `Session.create(...)`
  - `Session.updateMessage(...)`
  - `Session.updatePart(...)`
  - `Session.messages(...)`

## Ordered Execution Steps

1. Runtime code such as `SessionPrompt` or `SessionProcessor` calls a `Session.*` mutation API.
2. `Session.*` converts that mutation into a `SyncEvent.run(...)` call using `Session.Event.*` or `MessageV2.Event.*`.
3. The sync layer executes the matching projector inside a DB transaction.
4. `session/projectors.ts` inserts, updates, or deletes rows in `SessionTable`, `MessageTable`, or `PartTable`.
5. The sync layer records ordered event metadata and may republish an event onto the `Bus`.
6. Later, readers call `Session.get(...)`, `Session.messages(...)`, `MessageV2.get(...)`, or `MessageV2.stream(...)`.
7. `MessageV2.page(...)` queries message rows, `hydrate(...)` joins part rows, and the result is reconstructed into `MessageV2.WithParts`.
8. Before model execution, `MessageV2.filterCompacted(...)` and `toModelMessages(...)` reshape the stored transcript into the runtime/model-facing conversation window.

## State Transitions

- session lifecycle:
  - `session.created`
  - `session.updated`
  - `session.deleted`
- transcript lifecycle:
  - `message.updated`
  - `message.removed`
  - `message.part.updated`
  - `message.part.removed`
- transient live updates:
  - `message.part.delta` over `Bus` only

## External Boundaries

- SQLite/Drizzle boundary through `SessionTable`, `MessageTable`, and `PartTable`
- sync/event-sourcing boundary at `SyncEvent.run(...)`
- bus publication boundary for transient deltas and republished sync events
- provider/model boundary when stored transcript is converted by `toModelMessages(...)`

## Failure / Branching Behavior

- Missing rows raise `NotFoundError` in `Session.get(...)` and `MessageV2.get(...)`.
- Projectors tolerate some late message/part updates by catching foreign-key failures and logging warnings instead of crashing.
- `filterCompacted(...)` intentionally truncates replay around completed compaction summaries, so restored runtime history may be smaller than raw storage history.
- `Session.updatePartDelta(...)` does not persist anything, so consumers relying only on DB reads will miss in-flight incremental deltas.

## Evidence Table

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 1 | `workspace/source/opencode/packages/opencode/src/session/index.ts` | `Session.updateMessage/updatePart/...` | mutation entrypoints used by runtime code |
| 2 | `workspace/source/opencode/packages/opencode/src/session/index.ts` | `SyncEvent.run(...)` call sites | converts state changes into durable events |
| 3 | `workspace/source/opencode/packages/opencode/src/sync/index.ts` | `SyncEvent.run/process(...)` | transaction + event sequencing layer |
| 4 | `workspace/source/opencode/packages/opencode/src/session/projectors.ts` | projector handlers | writes `session`, `message`, `part` tables |
| 6 | `workspace/source/opencode/packages/opencode/src/session/index.ts` | `messages(...)`, `get(...)` | main read APIs |
| 7 | `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | `page`, `hydrate`, `stream`, `parts` | reconstructs `WithParts` history |
| 8 | `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | `filterCompacted`, `toModelMessages` | rebuilds runtime/model conversation state |

## Pending Verification

- Whether any consumers depend on raw sync-event replay rather than normal `Session`/`MessageV2` read APIs.
- How frequently archived/forked/shared session metadata changes are read on the hot interactive path.
