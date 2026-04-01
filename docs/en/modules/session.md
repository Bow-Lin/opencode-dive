# Session Module

## Module Responsibility

The session module is the durable state boundary for conversations. In the pinned version it is responsible for:

- creating and managing session records,
- persisting message and part mutations,
- loading conversation history back into runtime form,
- supporting fork/share/archive/revert-related metadata,
- and exposing the transcript in shapes suitable for both UI/API reads and provider model calls.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/session/index.ts` | session service, lifecycle APIs, mutation entrypoints | `Session.Service`, `create`, `get`, `messages`, `updateMessage`, `updatePart` |
| `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | message/part schemas, read APIs, model-message reconstruction | `MessageV2.Event.*`, `stream`, `parts`, `get`, `filterCompacted`, `toModelMessages` |
| `workspace/source/opencode/packages/opencode/src/session/projectors.ts` | sync-event projectors that write session/message/part rows | `SyncEvent.project(...)` handlers |
| `workspace/source/opencode/packages/opencode/src/session/session.sql.ts` | SQLite table definitions for session state | `SessionTable`, `MessageTable`, `PartTable`, `TodoTable` |
| `workspace/source/opencode/packages/opencode/src/server/projectors.ts` | sync-system initialization and event conversion for published updates | `initProjectors()` |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Session.Info` | schema/type | `index.ts` | canonical persisted session record |
| `Session.Service` | service | `index.ts` | main session lifecycle and mutation API |
| `Session.create(...)` | creator | `index.ts` | creates a new session and persists `session.created` |
| `Session.messages(...)` | read API | `index.ts` | loads hydrated message history for a session |
| `Session.updateMessage(...)` | mutation | `index.ts` | persists message info via `message.updated` |
| `Session.updatePart(...)` | mutation | `index.ts` | persists part state via `message.part.updated` |
| `Session.updatePartDelta(...)` | transient update | `index.ts` | publishes incremental text/tool deltas without DB write |
| `MessageV2.stream(...)` | history stream | `message-v2.ts` | paged read of hydrated messages + parts |
| `MessageV2.filterCompacted(...)` | history filter | `message-v2.ts` | trims replay window around completed compaction summaries |
| `MessageV2.toModelMessages(...)` | projection | `message-v2.ts` | converts stored transcript into provider-facing messages |

## Initialization / Entry

The session module is initialized by `Session.defaultLayer`, but its persistent behavior depends on the sync projector setup in `server/projectors.ts`, which calls `SyncEvent.init({ projectors: sessionProjectors, ... })`.

Operationally, the module is reached from:

- `SessionPrompt` during interactive execution,
- server routes for session CRUD and transcript queries,
- CLI/TUI clients through the SDK-backed session endpoints.

## Main Control Flow

### 1. Create Session Record

`Session.create(...)` builds a `Session.Info` object and persists it through:

1. `SyncEvent.run(Session.Event.Created, ...)`
2. `session/projectors.ts` inserting into `SessionTable`

Optional side effects include auto-share and backward-compatibility bus publication.

### 2. Persist Message And Part Mutations

During runtime, `SessionPrompt` and `SessionProcessor` write transcript state through:

- `Session.updateMessage(...)`
- `Session.updatePart(...)`
- `Session.removeMessage(...)`
- `Session.removePart(...)`

Those APIs do not write SQL directly. They emit `SyncEvent.run(...)` for:

- `message.updated`
- `message.part.updated`
- `message.removed`
- `message.part.removed`

The session projectors then upsert/delete rows in `MessageTable` and `PartTable`.

### 3. Publish Incremental Deltas

`Session.updatePartDelta(...)` is intentionally different.

It only publishes `MessageV2.Event.PartDelta` on the `Bus`, which means:

- deltas are useful for live streaming UIs/subscribers;
- they are not the durable persistence format;
- durable state still comes from later full `updatePart(...)` writes.

### 4. Restore Session History

`Session.messages({ sessionID })` restores transcript state by iterating `MessageV2.stream(sessionID)`.

That read path works as:

1. `MessageV2.page(...)` queries `MessageTable` in reverse chronological order;
2. `hydrate(...)` fetches matching `PartTable` rows and attaches them to each message;
3. `stream(...)` yields the conversation in chronological order;
4. `Session.messages(...)` collects and returns the hydrated list.

### 5. Reconstruct Runtime Conversation State

Before a model call, `SessionPrompt` typically uses:

- `MessageV2.filterCompacted(...)` to trim history around finished compaction summaries,
- `MessageV2.toModelMessages(...)` to rebuild provider-facing message/tool/media structures from persisted rows.

This means the session module stores canonical state in DB form, while `MessageV2` is responsible for projecting that state back into runtime/model form.

## Upstream And Downstream Dependencies

Upstream:

- `SessionPrompt` / `SessionProcessor`
- server session routes
- CLI/TUI SDK callers

Downstream:

- `SyncEvent` for durable mutation execution
- `session/projectors.ts` for DB writes
- SQLite/Drizzle tables in `session.sql.ts`
- `Bus` for transient deltas and error/status-adjacent notifications
- provider/runtime layers via `MessageV2.toModelMessages(...)`

## Implementation Details

- Session persistence is split across three durable row types:
  - session metadata in `SessionTable`
  - message info in `MessageTable`
  - part payloads in `PartTable`
- Message and part rows store most payload in JSON `data` columns, with IDs/session/time broken out as indexed columns.
- `server/projectors.ts` normalizes published `session.updated` events by reloading the full row before republishing, so bus consumers can see a complete session shape.
- `Session.fork(...)` clones history by replaying stored message/part records into a new session with fresh IDs.
- `Session.diff(...)` is not stored in the main session tables; it reads from `Storage` under `session_diff/<sessionID>`.
- `filterCompacted(...)` means runtime replay is intentionally not always the full raw transcript.

## Design Tradeoffs / Risks

- Persistence is event/projector-driven rather than direct-repository writes, which improves replayability but adds indirection.
- Live delta streaming and durable part persistence are separate mechanisms; consumers need to know which one they are reading.
- Storing most message/part payload in JSON columns keeps schemas flexible but makes some query patterns less relationally explicit.
- History reconstruction includes provider-specific projection logic in `MessageV2.toModelMessages(...)`, so persistence and model compatibility are somewhat coupled.

## Pending Verification

- Whether any auxiliary session state outside `SessionTable` / `Storage(session_diff)` materially affects ordinary prompt continuation.
- How widely `TodoTable` and other per-session side tables participate in the main interactive memory path.
