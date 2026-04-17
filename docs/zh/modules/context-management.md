# 上下文管理模块

## 模块职责

上下文管理负责在 message history、tool output、media attachments 或 provider context limit 变大时，让 Opencode 的长会话仍然可以继续运行。

在当前固定版本中，它不是单次截断，而是一组分层机制：

- 基于本地 token window 的 overflow 检测，
- provider context-overflow 错误解析，
- 通过隐藏 `compaction` agent 执行的摘要式 compaction，
- 通过 `MessageV2.filterCompacted(...)` 执行的 replay 裁剪，
- 旧 completed tool output 的 prune，
- 以及长文本 tool output 入 transcript 前的截断。

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/session/overflow.ts` | 本地 token window overflow 计算 | `isOverflow(...)` |
| `workspace/source/opencode/packages/opencode/src/session/processor.ts` | 把 stream usage / errors 转成 `compact` / `stop` / `continue` 控制结果 | `finish-step`, `halt(...)`, `process(...)` |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | 创建并消费 compaction task 的主 loop 分支 | `runLoop(...)`, `compaction.create(...)`, `MessageV2.filterCompacted(...)` |
| `workspace/source/opencode/packages/opencode/src/session/compaction.ts` | 摘要式 compaction 与旧 tool output prune | `SessionCompaction.process(...)`, `create(...)`, `prune(...)` |
| `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | model-message projection 与 compaction replay filter | `toModelMessages(...)`, `filterCompacted(...)`, `fromError(...)` |
| `workspace/source/opencode/packages/opencode/src/provider/error.ts` | provider context-overflow 分类 | `ProviderError.parseAPICallError(...)`, `parseStreamError(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/truncate.ts` | 长文本 tool output 截断 | `Truncate.output(...)`, `MAX_LINES`, `MAX_BYTES` |
| `workspace/source/opencode/packages/opencode/src/tool/tool.ts` | 应用输出截断的通用 tool wrapper | `Tool.define(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/registry.ts` | 应用输出截断的 plugin tool adapter | local `fromPlugin(...)` |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `isOverflow(...)` | predicate | `session/overflow.ts` | 用 reserved buffer 比较 usage 与 model context/input limits |
| `SessionProcessor.process(...)` | stream processor | `session/processor.ts` | 检测到 overflow 时返回 `compact` |
| `SessionCompaction.create(...)` | task creator | `session/compaction.ts` | 写入下一轮 loop 会处理的 user `compaction` part |
| `SessionCompaction.process(...)` | compaction runner | `session/compaction.ts` | 通过隐藏 compaction agent 总结旧历史 |
| `SessionCompaction.prune(...)` | cleanup pass | `session/compaction.ts` | 把更旧的 completed tool output 标记为 compacted |
| `MessageV2.filterCompacted(...)` | replay filter | `session/message-v2.ts` | 围绕已完成 compaction summary 裁剪运行时历史 |
| `MessageV2.toModelMessages(...)` | projection | `session/message-v2.ts` | 替换 compacted tool output，并可选择剥离 media |
| `Truncate.output(...)` | output limiter | `tool/truncate.ts` | 把完整长 tool output 外存，只返回有界预览 |

## 初始化 / 入口

没有独立的 context manager 进程。上下文处理是从 session runtime 进入的：

1. `SessionPrompt.runLoop(...)` 用 `MessageV2.filterCompacted(...)` 加载已压缩过的历史。
2. `SessionProcessor.process(...)` 消费一次 model stream，并跟踪 token usage 或 provider errors。
3. overflow 会向 `runLoop(...)` 返回 `compact`。
4. `runLoop(...)` 通过 `SessionCompaction.create(...)` 写入 compaction task。
5. 后续 loop iteration 看到 compaction part 后调用 `SessionCompaction.process(...)`。
6. loop 返回后，`runLoop(...)` 会在后台启动 `SessionCompaction.prune(...)`。

Tool output truncation 更早发生在工具执行 wrapper 内部，也就是过长文本变成普通 tool result 之前。

## 主控制流程

### 1. 检测 Overflow

本地 overflow 检测基于已完成 assistant step 的 usage。

`session/overflow.ts` 会计算：

- 优先使用 `tokens.total`，
- 否则使用 `input + output + cache.read + cache.write`，
- `reserved = cfg.compaction.reserved ?? min(20_000, maxOutputTokens(model))`，
- usable window 来自 `model.limit.input` 或 `model.limit.context`。

如果 `cfg.compaction.auto === false`，本地自动 overflow 触发会被禁用。

Provider 侧 overflow 是另一条路径。`provider/error.ts` 会把 context-window 相关文本、`context_length_exceeded`、HTTP `413` 类错误映射成 `context_overflow`；`MessageV2.fromError(...)` 再把它转换成 `ContextOverflowError`。

### 2. 把 Compaction 信号交给 Loop

`SessionProcessor` 在 `finish-step` 里检测到本地 overflow 时，会设置 `ctx.needsCompaction = true`。

`halt(...)` 如果看到 `MessageV2.ContextOverflowError`，也会设置 `ctx.needsCompaction = true`，而不是把这个错误当成可重试错误。

随后 `SessionProcessor.process(...)` 会优先返回 `compact`，再考虑 `stop` / `continue`。

### 3. 创建并消费 Compaction Task

`SessionPrompt.runLoop(...)` 处理 `compact` 的方式是写入一个 synthetic user message，里面带 `type: "compaction"` part。下一轮 iteration 会从最近历史里拿到这个 compaction part，并交给 `SessionCompaction.process(...)`。

Compaction 过程会：

1. 校验 parent 是 user message；
2. 如果是 provider overflow 导致的 compaction，尝试找一个 replay user message；
3. 选择隐藏的 `compaction` agent；
4. 允许 plugin 通过 `experimental.session.compacting` 修改 compaction prompt；
5. 用 `stripMedia: true` 把历史转成 model messages；
6. 创建一条 `summary: true` 的 assistant message；
7. 用 `tools: {}` 调 `SessionProcessor.process(...)`；
8. 自动 compaction 成功后追加一条 continuation user message。

如果 compaction 自己也返回 `compact`，Opencode 会记录 `ContextOverflowError` 并返回 `stop`。

更细的算法如下：

1. `SessionPrompt.runLoop(...)` 先记录 compaction request，而不是在当前分支里直接压缩。已完成 assistant step 之后的本地 token overflow 会调用 `SessionCompaction.create({ auto: true })`；来自未完成 assistant message 的 provider-side overflow 会调用 `create({ auto: true, overflow: true })`。
2. `SessionCompaction.create(...)` 写入一条新的 user message，沿用原 agent/model，并挂一个 `type: "compaction"` part，part 里带 `auto` 和可选 `overflow`。这让 compaction 变成 transcript 里的普通 task，下一轮 loop 才会消费它。
3. 下一轮 iteration 中，`runLoop(...)` 会在启动普通模型请求前找到最近的 pending `compaction` part，然后用当前 compacted message list、指向 compaction user message 的 `parentID`、以及 part 上的 `auto` / `overflow` 调 `SessionCompaction.process(...)`。
4. `process(...)` 先校验 parent message 存在且是 user message。如果这是 provider-overflow-triggered compaction，它会从 compaction marker 往前找最近一个非 compaction user message。找到后，如果该 replay 点之前仍然有其他 user 内容，这条较早 user message 会成为 `replay`，用于摘要的输入历史会被截断为 replay 点之前的 messages。
5. compaction model 优先取隐藏 `compaction` agent 的显式 model；如果该 agent 没有配置 model，就复用触发 compaction 的 user message model。plugin 可以通过 `experimental.session.compacting` 替换或扩展 compaction prompt。
6. 摘要输入会先 structured clone，再经过 `experimental.chat.messages.transform`，最后用 `MessageV2.toModelMessages(..., { stripMedia: true })` 投影成 model messages。因此 compaction 总结的是去掉 media attachments 后的 transcript。
7. `process(...)` 创建一条新的 assistant message，字段包含 `agent: "compaction"` 和 `summary: true`，然后用 `SessionProcessor.process(...)` 调模型；这次调用传 `tools: {}`、`system: []`、投影后的 transcript，以及最后一条要求生成 continuation summary 的 user prompt。
8. 如果 summary run 自己返回 `compact`，Opencode 会把这条 summary assistant message 标记为 `ContextOverflowError`，设置 `finish = "error"`，持久化后返回 `stop`。
9. 如果 summary run 返回 `continue` 且这是自动 compaction，Opencode 会追加一条 synthetic continuation user message。provider-overflow replay 场景下，它会重建之前找到的 replay user message，并复制其中非 compaction parts；media file parts 会被替换成类似 `[Attached image/png: file]` 的文本占位。没有 replay 时，它会创建一条 synthetic text prompt，让下一轮继续或在不确定时请求澄清；如果是 media overflow，还会额外提示附件过大。
10. 如果 summary assistant 有 error，`process(...)` 返回 `stop`；否则成功的 `continue` 会发布 `session.compacted` 并把 `continue` 返回给 loop。

`summary: true` 的模型调用有两层 prompt。隐藏的 `compaction` agent 会先提供来自 `agent/prompt/compaction.txt` 的 agent prompt，要求模型为后续继续对话总结上下文，并且不要回答原对话中的问题。随后 `SessionCompaction.process(...)` 会追加最后一条 user prompt。默认情况下，这条 prompt 要求生成“用于继续上面对话的详细 prompt”，要求不要调用工具、只输出 summary text，并建议使用 `Goal`、`Instructions`、`Discoveries`、`Accomplished`、`Relevant files / directories` 这些章节。plugin 可以通过 `experimental.session.compacting` 返回 `prompt` 来整体替换这条 final user prompt；如果没有替换，Opencode 会使用默认 prompt，并把 plugin 提供的 `context` entries 接在后面。

### 4. 重放更小的 Runtime Window

Compaction 不会删除原始 transcript。

`MessageV2.filterCompacted(...)` 会改变 runtime replay 的窗口：它记录成功的 `summary: true` assistant message 的 parent ID，找到匹配的 user compaction marker 后停止，然后反转已收集的 message list。这样后续模型调用会看到 summary 和较新的消息，而不是完整的 compaction 前历史。

### 5. 剪枝旧 Tool Output

普通 loop 返回后，`runLoop(...)` 会 fork `SessionCompaction.prune(...)`。

`prune(...)` 从存储消息里倒序扫描，并在满足这些条件时把旧 completed tool output 标记为 compacted：

- `cfg.compaction.prune !== false`；
- 扫描范围已经早于最新两个 user turns；
- tool 不是受保护工具，目前是 `skill`；
- tool output 是 completed 且未 compacted；
- 在保护约 `40_000` 个最近 tool-output tokens 后，可剪内容超过 `20_000` tokens。

后续投影成 model messages 时，compacted tool output 会被替换成 `[Old tool result content cleared]`，attachments 也会被移除。

### 6. Tool Output 入库前截断

`Truncate.output(...)` 会把文本输出限制到：

- `2000` 行，
- 或 `50 * 1024` bytes。

如果超过任一阈值，完整文本会写到 truncation 目录，模型只收到有界预览和如何读取保存文件的提示。

覆盖路径包括：

- 通过 `Tool.define(...)` 包装的内置工具，除非工具显式设置 `metadata.truncated`；
- `ToolRegistry` 适配的 plugin-defined tools；
- `SessionPrompt.resolveTools(...)` 里适配的 MCP textual output。

## 上下游依赖

上游：

- AI SDK stream event 中报告的 model usage，
- provider 错误消息与状态码，
- `Config.compaction` 中的 `auto`、`prune`、`reserved`，
- 把文本传给 `Truncate.output(...)` 的 tool execution wrappers。

下游：

- 负责 compaction 分支的 `SessionPrompt.runLoop(...)`，
- 负责 summarization run 与 overflow signaling 的 `SessionProcessor`，
- 持久化 compaction messages、summaries 和 compacted tool flags 的 `Session`，
- 负责最终 provider-facing context window 的 `MessageV2.toModelMessages(...)`。

## 实现细节

- 摘要式 compaction 会生成普通 assistant message，只是这条 message 带 `summary: true`，而不是原地改写旧 messages。
- 原始历史行仍保存在数据库中；compaction 通过 `filterCompacted(...)` 改变 model-facing replay。
- compaction 会剥离 media，overflow replay 会把 media attachments 替换成文本占位。
- tool-output pruning 标记的是 `part.state.time.compacted`；它不删除 part row。
- `ContextOverflowError` 在 `SessionRetry.retryable(...)` 中被显式视为不可重试。
- tool truncation 会保存完整文本供后续检查，并只把短预览返回给模型。

## 设计取舍 / 风险

- 保留原始历史并投影出更小的 model context 有利于审计，但也意味着“存储中的 transcript”和“模型可见 transcript”不是同一个东西。
- 摘要式 compaction 会丢失细节，因为后续模型看到的是生成摘要，而不是完整旧对话。
- 本地 token 检测依赖 provider usage 和 model limits；当这些限制不完整或不准确时，仍需要 provider-side overflow 处理兜底。
- tool truncation 能保护文本上下文，但大型 media attachments 更多依赖 compaction-time stripping 和 projection 规则，而不是同一套 byte/line truncation。

## 待验证

- 是否有内置工具绕过 `Tool.define(...)`，因此跳过标准 truncation wrapper。
- media attachments 除了 `stripMedia` 和 compacted-output attachment removal 之外，是否还有额外 hard byte limit。
