# Session 模块

## 模块职责

session 模块是会话的持久化状态边界。在当前固定版本中，它负责：

- 创建和管理 session 记录，
- 持久化 message 与 part 的变更，
- 把会话历史重新加载成运行时可用的形态，
- 支持 fork / share / archive / revert 相关元数据，
- 并以适合 UI / API 读取以及 provider model 调用的形态暴露 transcript。

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/session/index.ts` | session service、生命周期 API 和 mutation 入口 | `Session.Service`, `create`, `get`, `messages`, `updateMessage`, `updatePart` |
| `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | message / part schema、读取 API，以及 model-message 重建逻辑 | `MessageV2.Event.*`, `stream`, `parts`, `get`, `filterCompacted`, `toModelMessages` |
| `workspace/source/opencode/packages/opencode/src/session/projectors.ts` | 把 sync event 写入 session / message / part 行的 projector | `SyncEvent.project(...)` handlers |
| `workspace/source/opencode/packages/opencode/src/session/session.sql.ts` | session 状态对应的 SQLite 表定义 | `SessionTable`, `MessageTable`, `PartTable`, `TodoTable` |
| `workspace/source/opencode/packages/opencode/src/server/projectors.ts` | sync 系统初始化，以及用于发布更新的事件转换 | `initProjectors()` |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Session.Info` | schema/type | `index.ts` | 规范的持久化 session 记录 |
| `Session.Service` | service | `index.ts` | session 生命周期和 mutation 的主 API |
| `Session.create(...)` | creator | `index.ts` | 创建新 session，并持久化 `session.created` |
| `Session.messages(...)` | read API | `index.ts` | 为某个 session 加载 hydration 之后的消息历史 |
| `Session.updateMessage(...)` | mutation | `index.ts` | 通过 `message.updated` 持久化 message 信息 |
| `Session.updatePart(...)` | mutation | `index.ts` | 通过 `message.part.updated` 持久化 part 状态 |
| `Session.updatePartDelta(...)` | transient update | `index.ts` | 发布增量 text / tool delta，而不写数据库 |
| `MessageV2.stream(...)` | history stream | `message-v2.ts` | 分页读取 hydration 后的 messages + parts |
| `MessageV2.filterCompacted(...)` | history filter | `message-v2.ts` | 围绕已完成 compaction summary 裁剪 replay window |
| `MessageV2.toModelMessages(...)` | projection | `message-v2.ts` | 把已存储 transcript 转回 provider-facing message 结构 |

## 初始化 / 入口

session 模块由 `Session.defaultLayer` 初始化，但它的持久化行为依赖 `server/projectors.ts` 中的 sync projector 设置，该文件会调用 `SyncEvent.init({ projectors: sessionProjectors, ... })`。

在实际运行中，这个模块会通过下列入口被触达：

- 交互执行期间的 `SessionPrompt`，
- 处理 session CRUD 和 transcript 查询的 server routes，
- 通过 SDK-backed session endpoint 访问的 CLI / TUI client。

## 主控制流

### 1. Create Session Record

`Session.create(...)` 会构造一个 `Session.Info` 对象，并通过以下路径持久化：

1. `SyncEvent.run(Session.Event.Created, ...)`
2. `session/projectors.ts` 把数据插入 `SessionTable`

附带的副作用还可能包括自动 share 和兼容旧逻辑的 bus 发布。

### 2. Persist Message And Part Mutations

运行期间，`SessionPrompt` 和 `SessionProcessor` 会通过下列 API 写入 transcript 状态：

- `Session.updateMessage(...)`
- `Session.updatePart(...)`
- `Session.removeMessage(...)`
- `Session.removePart(...)`

这些 API 不会直接写 SQL。它们会为下面这些事件调用 `SyncEvent.run(...)`：

- `message.updated`
- `message.part.updated`
- `message.removed`
- `message.part.removed`

随后 session projector 会对 `MessageTable` 和 `PartTable` 执行 upsert / delete。

### 3. Publish Incremental Deltas

`Session.updatePartDelta(...)` 是有意设计成不同路径的。

它只会在 `Bus` 上发布 `MessageV2.Event.PartDelta`，这意味着：

- delta 对实时流式 UI / subscriber 很有用；
- 它们不是耐久化的持久化格式；
- 真正的持久化状态仍然依赖后续完整的 `updatePart(...)` 写入。

### 4. Restore Session History

`Session.messages({ sessionID })` 会通过遍历 `MessageV2.stream(sessionID)` 来恢复 transcript 状态。

这条读取路径的具体过程是：

1. `MessageV2.page(...)` 按时间逆序查询 `MessageTable`；
2. `hydrate(...)` 取出对应的 `PartTable` 行并挂到每条 message 上；
3. `stream(...)` 再按正向时间顺序产出整个会话；
4. `Session.messages(...)` 收集这些数据并返回 hydration 后的列表。

### 5. Reconstruct Runtime Conversation State

在模型调用之前，`SessionPrompt` 通常会用到：

- `MessageV2.filterCompacted(...)`，用于围绕已完成的 compaction summary 裁剪历史；
- `MessageV2.toModelMessages(...)`，用于把已持久化的行重建成 provider-facing 的 message / tool / media 结构。

这说明 session 模块负责以数据库形态保存规范状态，而 `MessageV2` 负责把这份状态重新投影回 runtime / model 形态。

## 上下游依赖

Upstream:

- `SessionPrompt` / `SessionProcessor`
- server session routes
- CLI / TUI SDK 调用方

Downstream:

- 用于耐久 mutation 执行的 `SyncEvent`
- 用于落库的 `session/projectors.ts`
- `session.sql.ts` 中的 SQLite / Drizzle 表
- 用于瞬时 delta 及错误 / 状态相关通知的 `Bus`
- 通过 `MessageV2.toModelMessages(...)` 与 provider / runtime 层衔接

## 实现细节

- session 持久化被拆分为三类耐久行：
  - `SessionTable` 中的 session metadata
  - `MessageTable` 中的 message info
  - `PartTable` 中的 part payload
- message 和 part 的大部分 payload 都存放在 JSON `data` 列中，而 ID / session / time 则单独拆成可索引列。
- `server/projectors.ts` 会在重新发布 `session.updated` 事件之前回读完整行并做规范化，这样 bus consumer 就能看到完整的 session 形态。
- `Session.fork(...)` 会把已存储的 message / part 记录回放到一个带有新 ID 的新 session 中，从而复制历史。
- `Session.diff(...)` 不存放在主 session 表里，而是从 `Storage` 的 `session_diff/<sessionID>` 路径读取。
- `filterCompacted(...)` 表明运行时重放并不总是使用原始的完整 transcript。

## 设计取舍 / 风险

- 持久化采用 event / projector 驱动，而不是直接 repository 写入；这提高了 replay 能力，但也增加了间接层。
- 实时 delta 流和耐久化 part 持久化是两套不同机制，消费方必须清楚自己读取的是哪一种。
- 把大部分 message / part payload 存在 JSON 列里提升了 schema 灵活性，但也让部分查询模式不那么关系型直观。
- `MessageV2.toModelMessages(...)` 在历史重建里包含 provider-specific projection 逻辑，因此持久化层与模型兼容层存在一定耦合。

## 待验证

- 除了 `SessionTable` / `Storage(session_diff)` 之外，是否还有其他辅助 session 状态会显著影响普通 prompt continuation。
- `TodoTable` 以及其他按 session 组织的侧表，在主交互记忆路径里到底参与到了多大程度。
