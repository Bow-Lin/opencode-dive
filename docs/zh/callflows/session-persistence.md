# 会话持久化流程

## 触发条件

满足以下任一情况：

- 某条运行时路径创建或修改 session/message/part 状态，
- 或某个读取路径把先前的会话状态重新加载回运行时。

## 起始文件 / 符号

- `workspace/source/opencode/packages/opencode/src/session/index.ts`
- 关键符号：
  - `Session.create(...)`
  - `Session.updateMessage(...)`
  - `Session.updatePart(...)`
  - `Session.messages(...)`

## 顺序执行步骤

1. `SessionPrompt` 或 `SessionProcessor` 这类运行时代码调用某个 `Session.*` 变更 API。
2. `Session.*` 使用 `Session.Event.*` 或 `MessageV2.Event.*`，把这次变更转换成一次 `SyncEvent.run(...)` 调用。
3. sync 层在数据库事务内执行对应的 projector。
4. `session/projectors.ts` 向 `SessionTable`、`MessageTable` 或 `PartTable` 插入、更新或删除行。
5. sync 层记录有序事件元数据，并可能把事件重新发布到 `Bus` 上。
6. 之后，读取方会调用 `Session.get(...)`、`Session.messages(...)`、`MessageV2.get(...)` 或 `MessageV2.stream(...)`。
7. `MessageV2.page(...)` 查询消息行，`hydrate(...)` 关联加载 part 行，再把结果重建成 `MessageV2.WithParts`。
8. 在模型执行前，`MessageV2.filterCompacted(...)` 与 `toModelMessages(...)` 会把存储中的转录重塑成运行时/模型可消费的会话窗口。

## 状态转换

- session 生命周期：
  - `session.created`
  - `session.updated`
  - `session.deleted`
- transcript 生命周期：
  - `message.updated`
  - `message.removed`
  - `message.part.updated`
  - `message.part.removed`
- 短暂的实时更新：
  - `message.part.delta` 只经过 `Bus`

## 外部边界

- 通过 `SessionTable`、`MessageTable`、`PartTable` 形成的 SQLite/Drizzle 边界
- `SyncEvent.run(...)` 处的 sync/event-sourcing 边界
- 针对临时 delta 和重发布 sync event 的 bus 发布边界
- 存储转录经 `toModelMessages(...)` 变成模型输入时的 provider/model 边界

## 失败 / 分支行为

- `Session.get(...)` 和 `MessageV2.get(...)` 在缺少行时会抛出 `NotFoundError`。
- projector 通过捕获外键失败并记录 warning，而不是直接崩溃，以容忍部分延迟到达的 message/part 更新。
- `filterCompacted(...)` 会有意在已完成的 compaction summary 处截断重放，因此恢复后的运行时历史可能比原始存储历史更短。
- `Session.updatePartDelta(...)` 不会持久化任何内容，所以只依赖 DB 读取的消费者会错过飞行中的增量 delta。

## 证据表

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 1 | `workspace/source/opencode/packages/opencode/src/session/index.ts` | `Session.updateMessage/updatePart/...` | 运行时代码使用的变更入口 |
| 2 | `workspace/source/opencode/packages/opencode/src/session/index.ts` | `SyncEvent.run(...)` call sites | 将状态变化转换成持久化事件 |
| 3 | `workspace/source/opencode/packages/opencode/src/sync/index.ts` | `SyncEvent.run/process(...)` | 事务 + 事件排序层 |
| 4 | `workspace/source/opencode/packages/opencode/src/session/projectors.ts` | projector handlers | 写入 `session`、`message`、`part` 表 |
| 6 | `workspace/source/opencode/packages/opencode/src/session/index.ts` | `messages(...)`, `get(...)` | 主要读取 API |
| 7 | `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | `page`, `hydrate`, `stream`, `parts` | 重建 `WithParts` 历史 |
| 8 | `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | `filterCompacted`, `toModelMessages` | 重建运行时/模型会话状态 |

## 待验证

- 是否有消费者依赖原始 sync-event 重放，而不是常规的 `Session`/`MessageV2` 读取 API。
- archived/forked/shared 会话元数据变化在高频交互路径上被读取的频率有多高。
