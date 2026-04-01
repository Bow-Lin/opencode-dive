# 端到端用户请求流程

## 触发条件

规范化分析的触发场景是：本地用户通过 Opencode 的 CLI 或 TUI 提交一个请求，随后请求进入共享后端运行时，并产出助手输出、工具动作以及持久化的会话状态。

具体前端入口可以不同：

- 普通 CLI `run`
- 本地 TUI
- attach/remote 模式下由服务器支撑的 UI

但后端控制路径会很快收敛。

## 起始文件 / 符号

主要入口文件/符号：

- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts`
- `workspace/source/opencode/packages/opencode/src/server/router.ts`
- `workspace/source/opencode/packages/opencode/src/server/routes/session.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`

## 顺序执行步骤

1. 用户在 CLI/TUI 界面中输入一条消息。
2. 客户端壳层对输入做规范化：
   - CLI 走 yargs 命令处理器，
   - TUI 走 prompt 组件和 SDK mutation。
3. 在本地模式下，客户端通常通过 `Server.Default().fetch(...)` 调用进程内控制平面应用；在 remote/attach 模式下，则会命中真实的服务器 URL。
4. `WorkspaceRouterMiddleware` 通过 `Instance.provide(..., init: InstanceBootstrap)` 建立正确的目录/工作区实例。
5. `SessionRoutes` 接收会话 mutation 请求，并调用 `SessionPrompt.prompt(...)`、`command(...)` 或 `shell(...)`。
6. `SessionPrompt.prompt(...)` 创建或触达用户消息，应用请求级工具权限，然后进入该会话对应的 runner。
7. `SessionPrompt.runLoop(...)` 加载当前会话历史，选择 agent/model 路径，在需要时分支进入 compact/subtask 逻辑，创建下一条助手消息，解析 tools/system prompt/messages，并把一个执行步委托给 `SessionProcessor.process(...)`。
8. `SessionProcessor.process(...)` 调用 `LLM.stream(...)`，消费模型流式事件，并为文本、reasoning、tool call、tool result、error 与 retry 更新消息 part。
9. `LLM.stream(...)` 解析 provider/model 配置，过滤活跃工具，并调用 AI SDK 的 `streamText(...)`；如果模型请求工具，则执行路径会流向 `SessionPrompt.resolveTools(...)` 创建的、绑定会话上下文的工具映射。
10. 工具执行会通过 `Session.updatePart(...)` 及相关 API 更新会话状态，而持久化的 session/message/part 变更则通过 `SyncEvent.run(...)` 进入 SQLite projector。
11. 当模型/工具循环结束或停止时，`SessionStatus` 会回到 `idle`；客户端壳层会观察流式事件以及最终存储下来的转录更新。
12. 最终对用户可见的输出会：
    - 直接渲染在 CLI/TUI 中，
    - 持久化到 session/message/part 存储中，
    - 并可通过会话历史 API 在之后重放。

## 状态转换

- 传输状态：
  - 原始输入被转换成 SDK/server 的 session mutation 请求
- 运行时状态：
  - 创建用户消息
  - 创建助手消息
  - runner 在 busy/idle 间切换
- 模型/工具状态：
  - text/reasoning/tool part 在 pending/running/completed/error 间流转
- 持久化状态：
  - session/message/part sync event 被投影进数据库
- 客户端状态：
  - UI/CLI 对流式事件和/或同步存储更新作出响应

## 外部边界

- CLI/TUI 输入处的 shell/UI 边界
- `Server.Default().fetch(...)` 或远程服务器处的控制平面 HTTP/fetch 边界
- `Instance.provide(...)` 处的 workspace-instance 边界
- `LLM.stream(...)` 内部的 provider SDK/网络边界
- 会话状态对应的 SQLite/sync-event 持久化边界

## 失败 / 分支行为

- CLI/TUI 参数校验可能在进入运行时之前失败。
- 缺失 session/agent/model 的错误会通过 session error event 和客户端渲染暴露出来。
- compaction 和 subtask 处理是 `SessionPrompt.runLoop(...)` 内部的显式分支。
- 工具权限拒绝或问题拒绝会阻塞当前步骤并停止循环。
- provider 可能触发重试，或启用针对 LiteLLM 类代理的 `_noop` 工具兼容分支。
- 最终输出可能是普通助手文本、结构化输出、工具副作用，或一个持久化到会话中的错误状态。

## 证据表

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 1-2 | `workspace/source/opencode/packages/opencode/src/index.ts` | yargs CLI + command dispatch | 原始 shell 输入转换成命令处理器调用 |
| 2-3 | `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts` | `execute(sdk)` / local `fetchFn` | 本地 CLI 通过进程内 server 变成 SDK client |
| 3-4 | `workspace/source/opencode/packages/opencode/src/server/router.ts` | `WorkspaceRouterMiddleware` | 将请求绑定到 project/workspace instance |
| 5 | `workspace/source/opencode/packages/opencode/src/server/routes/session.ts` | `session.prompt` / `session.command` routes | 传输层切入 session runtime |
| 6-7 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `prompt`, `loop`, `runLoop` | 主编排核心 |
| 8 | `workspace/source/opencode/packages/opencode/src/session/processor.ts` | `process(...)` | 将流式事件消费成转录状态 |
| 9 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | `LLM.stream(...)` | provider + tool 切入 AI SDK |
| 9 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | internal `resolveTools(...)` | 构建绑定会话的工具执行器 |
| 10 | `workspace/source/opencode/packages/opencode/src/session/index.ts` | `updateMessage/updatePart/...` | 持久化会话变更 API |
| 10 | `workspace/source/opencode/packages/opencode/src/sync/index.ts` | `SyncEvent.run(...)` | 持久化/事件投影边界 |
| 10 | `workspace/source/opencode/packages/opencode/src/session/projectors.ts` | session/message/part projectors | SQLite 写入 |
| 11-12 | `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts` | event subscription loop | CLI 渲染最终事件/输出 |
| 11-12 | `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/context/sync.tsx` | `SyncProvider` | TUI 同步状态/渲染路径 |

## 待验证

- 在高强度工具调用场景下，普通 CLI 与 TUI 的事件顺序是否存在精确差异。
- 是否存在少数命令绕过标准 session mutation 路由，从而改写这条链路的前半段。
