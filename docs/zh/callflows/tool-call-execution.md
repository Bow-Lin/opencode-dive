# 工具调用执行流程

## 触发条件

在某个 `SessionPrompt` 生成步骤中，模型决定调用一个工具，而 Opencode 已经为这次请求构建好了 session 级的工具映射。

## 起始文件 / 符号

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- 关键符号：
  - internal `resolveTools(...)`
  - `handle.process(...)`

## 顺序执行步骤

1. `SessionPrompt` 向 `ToolRegistry.tools(...)` 请求当前 model 和 agent 可用的工具定义。
2. `SessionPrompt.resolveTools(...)` 把每个返回的定义都包装成一个 AI SDK `tool({...})`，并构建带有 session/message/permission 回调的 `Tool.Context`。
3. `LLM.stream(...)` 接收这份工具映射，移除被用户禁用或被权限禁用的工具，然后把过滤后的集合以 `tools` 和 `activeTools` 传给 `streamText(...)`。
4. 当模型开始一次工具调用时，`tool-input-start` 和 `tool-call` 这类流式事件会到达 `SessionProcessor`，后者会创建或更新一个处于 `pending` 再到 `running` 状态的 `MessageV2.ToolPart`。
5. AI SDK 调用包装后的工具 `execute(...)` 函数。
6. Opencode 运行 `tool.execute.before` hook，执行具体工具，规范化 attachments 和 metadata，然后运行 `tool.execute.after` hook。
7. 最终的结构化载荷会以 `tool-result` 或 `tool-error` 的形式回到流中。
8. `SessionProcessor` 把同一个 `MessageV2.ToolPart` 更新为 `completed` 或 `error`，并写入 input、output、metadata、timing 与 attachments。
9. 现在工具结果已经进入会话状态，模型循环会继续向下执行。

## 状态转换

- registry 中的定义被转换成绑定到 session 的 AI SDK 工具
- 具备资格的工具在权限和用户覆盖过滤后成为 `activeTools`
- tool part 状态按顺序推进：
  - `pending`
  - `running`
  - `completed` 或 `error`
- 执行元数据可以在运行过程中通过 `ctx.metadata(...)` 被更新

## 外部边界

- `tool({...})` / `streamText(...)` 处的 AI SDK 工具边界
- `Permission.ask(...)` 对应的权限边界
- `tool.execute.before` 和 `tool.execute.after` 对应的 plugin hook 边界
- 外部提供工具时可能出现的 MCP 边界

## 失败 / 分支行为

- 无效工具参数会在 `Tool.define(...)` 包装层失败，底层工具逻辑不会执行。
- `LLM.experimental_repairToolCall(...)` 可以把名称不匹配的工具名转成小写，或把损坏调用重定向到 `invalid` 工具。
- 重复的相同工具调用会触发 `SessionProcessor` 中的 doom-loop 权限检查。
- 权限拒绝或问题拒绝会把 processor 标记为 blocked，并以不同于普通工具失败的方式结束当前步骤。
- LiteLLM 风格代理在历史里已经存在工具调用、但当前没有真实活跃工具时，可能收到一个合成的 `_noop` 工具。
- GitLab workflow 模型使用自定义的 `toolExecutor` 路径，但最终仍然指向同一份 session tool map。

## 证据表

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 1 | `workspace/source/opencode/packages/opencode/src/tool/registry.ts` | `ToolRegistry.tools(...)` | 为 model + agent 构建已初始化工具定义 |
| 2 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | internal `resolveTools(...)` | 把定义绑定成感知 session 的 AI SDK 工具 |
| 3 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | local `resolveTools(...)` | 在 provider 调用前移除禁用工具 |
| 4 | `workspace/source/opencode/packages/opencode/src/session/processor.ts` | `handleEvent(...)` | 记录 `tool-input-start` 和 `tool-call` |
| 5 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | wrapped `execute(args, options)` | 进入具体工具逻辑的执行适配层 |
| 6 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `plugin.trigger("tool.execute.before/after", ...)` | 可插 hook 的执行生命周期 |
| 7 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | `streamText(...)` | 工具结果通过模型流返回 |
| 8 | `workspace/source/opencode/packages/opencode/src/session/processor.ts` | `tool-result` / `tool-error` cases | 最终消息 part 状态回写 |

## 待验证

- 在真实流量下，普通 AI SDK 工具流与 GitLab workflow `toolExecutor` 路径之间的精确差异。
- 是否有 provider 会实质性改变 `tool-result` 事件顺序。
