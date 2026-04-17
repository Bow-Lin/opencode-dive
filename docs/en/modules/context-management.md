# Context Management Module

## Module Responsibility

Context management controls how Opencode keeps long sessions usable when message history, tool output, media attachments, or provider context limits grow too large.

In the pinned version, it is a layered mechanism rather than one pass:

- local token-window overflow detection,
- provider context-overflow error parsing,
- summary compaction through a hidden `compaction` agent,
- replay trimming through `MessageV2.filterCompacted(...)`,
- old completed tool-output pruning,
- and pre-transcript truncation of long textual tool output.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/session/overflow.ts` | local token-window overflow calculation | `isOverflow(...)` |
| `workspace/source/opencode/packages/opencode/src/session/processor.ts` | turns stream usage/errors into `compact` / `stop` / `continue` control results | `finish-step`, `halt(...)`, `process(...)` |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | main loop branch that creates and consumes compaction tasks | `runLoop(...)`, `compaction.create(...)`, `MessageV2.filterCompacted(...)` |
| `workspace/source/opencode/packages/opencode/src/session/compaction.ts` | summary compaction and old tool-output pruning | `SessionCompaction.process(...)`, `create(...)`, `prune(...)` |
| `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | model-message projection and compaction replay filter | `toModelMessages(...)`, `filterCompacted(...)`, `fromError(...)` |
| `workspace/source/opencode/packages/opencode/src/provider/error.ts` | provider context-overflow classification | `ProviderError.parseAPICallError(...)`, `parseStreamError(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/truncate.ts` | long textual tool-output truncation | `Truncate.output(...)`, `MAX_LINES`, `MAX_BYTES` |
| `workspace/source/opencode/packages/opencode/src/tool/tool.ts` | common tool wrapper that applies output truncation | `Tool.define(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/registry.ts` | plugin tool adapter that applies output truncation | local `fromPlugin(...)` |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `isOverflow(...)` | predicate | `session/overflow.ts` | compares observed usage against model context/input limits with a reserved buffer |
| `SessionProcessor.process(...)` | stream processor | `session/processor.ts` | returns `compact` when overflow is detected |
| `SessionCompaction.create(...)` | task creator | `session/compaction.ts` | writes a user `compaction` part that the next loop iteration will process |
| `SessionCompaction.process(...)` | compaction runner | `session/compaction.ts` | summarizes prior history through the hidden compaction agent |
| `SessionCompaction.prune(...)` | cleanup pass | `session/compaction.ts` | marks older completed tool outputs as compacted |
| `MessageV2.filterCompacted(...)` | replay filter | `session/message-v2.ts` | trims runtime history around completed compaction summaries |
| `MessageV2.toModelMessages(...)` | projection | `session/message-v2.ts` | replaces compacted tool output and optionally strips media |
| `Truncate.output(...)` | output limiter | `tool/truncate.ts` | stores full long tool output externally and returns a bounded preview |

## Initialization / Entry

There is no standalone context manager process. Context handling is reached from the session runtime:

1. `SessionPrompt.runLoop(...)` loads compacted history with `MessageV2.filterCompacted(...)`.
2. `SessionProcessor.process(...)` consumes one model stream and tracks token usage or provider errors.
3. Overflow returns `compact` to `runLoop(...)`.
4. `runLoop(...)` writes a compaction task through `SessionCompaction.create(...)`.
5. A later loop iteration sees the compaction part and runs `SessionCompaction.process(...)`.
6. After the loop returns, `runLoop(...)` starts `SessionCompaction.prune(...)` in the background.

Tool output truncation is reached earlier, inside tool execution wrappers, before oversized text becomes a normal tool result.

## Main Control Flow

### 1. Detect Overflow

Local overflow detection is based on completed assistant-step usage.

`session/overflow.ts` computes:

- `count = tokens.total` when present,
- otherwise `input + output + cache.read + cache.write`,
- `reserved = cfg.compaction.reserved ?? min(20_000, maxOutputTokens(model))`,
- and a usable input window derived from `model.limit.input` or `model.limit.context`.

Overflow is disabled if `cfg.compaction.auto === false`.

Provider-side overflow is detected separately. `provider/error.ts` maps context-window phrases, `context_length_exceeded`, and HTTP `413`-style errors to `context_overflow`; `MessageV2.fromError(...)` turns those into `ContextOverflowError`.

### 2. Signal Compaction To The Loop

When `SessionProcessor` sees local overflow in `finish-step`, it sets `ctx.needsCompaction = true`.

When `halt(...)` sees `MessageV2.ContextOverflowError`, it also sets `ctx.needsCompaction = true` instead of treating the error as retryable.

`SessionProcessor.process(...)` then returns `compact` before `stop` / `continue`.

### 3. Create And Consume A Compaction Task

`SessionPrompt.runLoop(...)` handles `compact` by writing a synthetic user message with a `type: "compaction"` part. On the next iteration, pending compaction parts are pulled from recent history and routed into `SessionCompaction.process(...)`.

The compaction process:

1. validates that the parent is a user message;
2. optionally identifies a replay user message when the compaction was caused by provider overflow;
3. selects the hidden `compaction` agent;
4. lets plugins modify the compaction prompt through `experimental.session.compacting`;
5. converts history to model messages with `stripMedia: true`;
6. creates a `summary: true` assistant message;
7. calls `SessionProcessor.process(...)` with `tools: {}`;
8. appends a continuation user message when auto-compaction succeeds.

If compaction itself returns `compact`, Opencode records `ContextOverflowError` and returns `stop`.

Detailed algorithm:

1. `SessionPrompt.runLoop(...)` first records a compaction request instead of compacting inline. Local token overflow after a finished assistant step calls `SessionCompaction.create({ auto: true })`; provider-side overflow from an unfinished assistant message calls `create({ auto: true, overflow: true })`.
2. `SessionCompaction.create(...)` writes a new user message with the original agent/model and attaches a `type: "compaction"` part carrying `auto` and optional `overflow`. This makes compaction a normal transcript task that the next loop iteration can pick up.
3. On the next iteration, `runLoop(...)` finds recent pending `compaction` parts before starting another normal model request. It calls `SessionCompaction.process(...)` with the current compacted message list, `parentID` set to the compaction user message, and the part's `auto` / `overflow` flags.
4. `process(...)` validates that the parent message exists and is a user message. If the compaction was provider-overflow-triggered, it scans backward from the compaction marker for the nearest earlier non-compaction user message. When found and there is still other user content before it, that earlier user message becomes `replay`, and the summarization input is truncated to messages before that replay point.
5. The compaction model is chosen from the hidden `compaction` agent if that agent has an explicit model; otherwise it reuses the triggering user message's model. Plugins can replace or extend the compaction prompt through `experimental.session.compacting`.
6. The summarization input is cloned, passed through `experimental.chat.messages.transform`, and projected with `MessageV2.toModelMessages(..., { stripMedia: true })`. This means compaction summarizes the transcript without media attachments.
7. `process(...)` creates a new assistant message with `agent: "compaction"` and `summary: true`, then runs `SessionProcessor.process(...)` against the model with `tools: {}`, `system: []`, the projected transcript, and a final user prompt asking for a continuation summary.
8. If the summary run itself returns `compact`, Opencode marks the summary assistant message with a `ContextOverflowError`, sets `finish = "error"`, persists it, and returns `stop`.
9. If the summary run returns `continue` and the compaction was automatic, Opencode appends a synthetic continuation user message. For provider-overflow replay, it recreates the earlier replay user message and copies its non-compaction parts; media file parts are replaced by text placeholders like `[Attached image/png: file]`. Without replay, it creates a synthetic text prompt telling the next loop to continue or ask for clarification, with an extra media-overflow warning when relevant.
10. If the summary assistant has an error, `process(...)` returns `stop`; otherwise a successful `continue` publishes `session.compacted` and returns `continue` to the loop.

The `summary: true` model call has two prompt layers. The hidden `compaction` agent contributes its own agent prompt from `agent/prompt/compaction.txt`, which tells the model to summarize the conversation for continuation and not answer questions from the original conversation. `SessionCompaction.process(...)` then appends a final user prompt. By default, that prompt asks for "a detailed prompt for continuing our conversation above", instructs the model not to call tools and to respond only with summary text, and suggests sections for `Goal`, `Instructions`, `Discoveries`, `Accomplished`, and `Relevant files / directories`. Plugins can override the whole final user prompt by returning `prompt` from `experimental.session.compacting`; otherwise Opencode uses the default prompt plus any plugin-provided `context` entries joined after it.

### 4. Replay A Smaller Runtime Window

Compaction does not delete the raw transcript.

Instead, `MessageV2.filterCompacted(...)` changes what the runtime replays. It tracks successful `summary: true` assistant messages, finds the matching user compaction marker, stops there, then reverses the collected message list. That makes future model calls use the summary and newer messages instead of the full pre-compaction history.

### 5. Prune Older Tool Output

After a normal loop returns, `runLoop(...)` forks `SessionCompaction.prune(...)`.

`prune(...)` scans backward through stored messages and marks old completed tool outputs as compacted when all of these hold:

- `cfg.compaction.prune !== false`;
- the scan is older than the two newest user turns;
- the tool is not protected, currently `skill`;
- the tool output is completed and not already compacted;
- the prunable estimate exceeds `20_000` tokens after protecting about `40_000` recent tool-output tokens.

When projected to model messages, a compacted tool output is replaced with `[Old tool result content cleared]`, and its attachments are removed.

### 6. Truncate Tool Output Before Storage

`Truncate.output(...)` limits text output to:

- `2000` lines,
- or `50 * 1024` bytes.

If the output exceeds either limit, the full text is written to the truncation directory and the model receives a bounded preview plus instructions for reading the saved file.

This path covers:

- built-in tools wrapped by `Tool.define(...)`, unless the tool explicitly marks `metadata.truncated`;
- plugin-defined tools adapted by `ToolRegistry`;
- MCP textual output adapted in `SessionPrompt.resolveTools(...)`.

## Upstream And Downstream Dependencies

Upstream:

- model usage reported through AI SDK stream events,
- provider error messages and status codes,
- `Config.compaction` for `auto`, `prune`, and `reserved`,
- tool execution wrappers that pass text through `Truncate.output(...)`.

Downstream:

- `SessionPrompt.runLoop(...)` for compaction branching,
- `SessionProcessor` for summarization runs and overflow signaling,
- `Session` persistence for compaction messages, summaries, and compacted tool flags,
- `MessageV2.toModelMessages(...)` for the final provider-facing context window.

## Implementation Details

- Summary compaction is performed by a normal assistant message marked `summary: true`, not by mutating the old messages in place.
- Old raw transcript rows remain stored; compaction changes model-facing replay through `filterCompacted(...)`.
- Compaction strips media, and overflow replay replaces media attachments with textual placeholders.
- Tool-output pruning marks `part.state.time.compacted`; it does not remove the part row.
- `ContextOverflowError` is explicitly non-retryable in `SessionRetry.retryable(...)`.
- Tool truncation saves full text for later inspection and only returns a short preview to the model.

## Design Tradeoffs / Risks

- Keeping raw history while projecting a smaller model context preserves auditability, but makes "stored transcript" and "model-visible transcript" different objects.
- Summary compaction can lose detail because the future model sees a generated summary, not the complete older conversation.
- The local token check depends on provider usage and model limits; provider-side overflow handling remains necessary when those limits are incomplete or inaccurate.
- Tool truncation protects context, but large media attachments rely more on compaction-time stripping and projection rules than on the same byte/line truncation path.

## Pending Verification

- Whether any built-in tools bypass `Tool.define(...)` and therefore skip the standard truncation wrapper.
- Whether media attachments have an additional hard byte limit outside `stripMedia` and compacted-output attachment removal.
