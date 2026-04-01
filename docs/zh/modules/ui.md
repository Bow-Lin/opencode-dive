# UI 模块

## 模块职责

UI 层是超出原始 CLI 参数解析之外的交互壳层。在这个固定版本里，主要分析的 UI 表面是终端 UI（TUI），它负责：

- 渲染交互式 session 与 workspace 视图，
- 收集用户输入与命令动作，
- 维护与运行时状态同步的本地 view-model，
- 并通过 SDK 把 UI 侧的变更回写到后端。

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/app.tsx` | TUI 组合根节点与顶层事件反应 | `tui(...)`, `App`, `SDKProvider`, `SyncProvider` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/context/sdk.tsx` | 面向 UI 组件的 SDK client + 事件流 provider | `SDKProvider`, `createOpencodeClient(...)`, `sdk.event.subscribe(...)` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/context/sync.tsx` | 由快照和事件流喂养的本地同步存储 | `SyncProvider`, `bootstrap()`, `sdk.event.listen(...)` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/thread.ts` | 本地 TUI 模式下的 worker-thread 启动器与传输模式选择 | `TuiThreadCommand`, `createWorkerFetch`, `createEventSource` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/worker.ts` | 对进程内 server 和 event bus 的 worker 侧 RPC bridge | `rpc.fetch`, `Bus.subscribeAll(...)`, `startEventStream(...)` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/routes/session/index.tsx` | 消费同步状态并发起 SDK 变更的主 session 页面 | `useSync()`, `useSDK()` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/component/prompt/index.tsx` | prompt 输入表面，以及 prompt/command/shell 提交 | `sdk.client.session.create/prompt/command/shell(...)` |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `tui(input)` | entrypoint | `app.tsx` | 启动 TUI 渲染器和 provider 树 |
| `SDKProvider` | context/provider | `context/sdk.tsx` | 持有 SDK client 和入站事件流 |
| `SyncProvider` | context/provider | `context/sync.tsx` | 持有本地同步 UI store |
| `EventSource` | transport type | `context/sdk.tsx` | 抽象由 worker 提供的自定义事件流 |
| `TuiThreadCommand` | launcher | `thread.ts` | 启动基于 worker 的本地 TUI 或 network 模式 |
| `rpc.fetch(...)` | bridge | `worker.ts` | 把 SDK 的 HTTP 调用转发到 `Server.Default().fetch(...)` |

## 初始化 / 入口

本地 TUI 主路径起始于 `TuiThreadCommand`：

1. 解析目标目录和配置，
2. 启动 worker 线程，
3. 选择传输模式，
4. 调用 `tui(...)`。

传输模式包括：

- internal/local mode：
  - 由 worker RPC 提供 `fetch` 与事件桥
  - 后端请求保持在进程内
- external/server mode：
  - TUI 直接指向真实 server URL
- attach mode：
  - `AttachCommand` 跳过 worker，直接连接已存在的 server

## 主控制流程

### 1. 构建 UI 运行时上下文

`tui(...)` 围绕一组 provider 堆栈组合整个 UI，包括：

- `SDKProvider`
- `SyncProvider`
- theme/dialog/keybind/local-state providers

这建立了一个清晰的分层：后端访问、同步运行时状态和纯本地 UI 状态彼此分离。

### 2. 接收运行时状态

`SDKProvider` 创建 `@opencode-ai/sdk/v2` client，并管理事件摄入：

- 如果没有自定义 event source，则直接通过 `sdk.event.subscribe(...)` 订阅 SSE，
- 否则接收由 worker bridge 转发来的自定义事件。

事件会先被批处理，以减少渲染抖动。

### 3. 维护本地同步 Store

`SyncProvider` 才是面向 UI 的实际状态缓存。

它承担两项工作：

1. 通过 SDK 查询启动初始快照，例如：
   - `session.list`
   - `config.get`
   - `app.agents`
   - `command.list`
   - `session.get/messages/todo/diff`
2. 再从流式事件中增量更新本地 store，例如：
   - `session.updated`
   - `message.updated`
   - `message.part.updated`
   - `session.status`
   - permission/question 事件

### 4. 从同步状态渲染

UI 路由和组件通常从 `useSync()` 数据渲染，而不是直接读取运行时服务。

例如：

- session route 读取已同步的 session/message/part 状态；
- prompt 组件从 sync store 推导 session status 和 transcript 上下文；
- plugin API 会把同一份同步数据暴露给 UI plugins。

### 5. 通过 SDK 把变更发回后端

当用户发起动作时，组件会调用 `sdk.client.*` 方法执行变更或一次性查询：

- `session.create`
- `session.prompt`
- `session.command`
- `session.shell`
- `session.abort`
- `session.fork`

这意味着即使在本地执行模式下，UI 仍然保持 client 模式。

## 上下游依赖

上游：

- CLI thread/attach commands
- 终端渲染器 / 输入系统

下游：

- `@opencode-ai/sdk/v2`
- 本地模式下的 worker RPC bridge
- 通过 worker fetch 调用的 `Server.Default().fetch(...)`
- 通过 worker 事件转发接入的 `Bus.subscribeAll(...)`
- routes/components/plugins 中消费本地 Solid store 的各类 UI 代码

## 实现细节

- TUI 基于 Solid 和 `@opentui/*` 构建，而不是简单的 readline 循环。
- 本地模式使用 worker thread，从而把 UI 线程与后端/server 工作隔离开。
- UI 的主要渲染源是同步后的本地状态，而不是直接调用后端服务。
- Workspace 切换会带着 `experimental_workspaceID` 重建 SDK client，并刷新事件流。
- `App` 仍然会直接监听一部分事件以处理 toast/navigation，但这些只是建立在更大 sync store 之上的 UI 反应。

## 设计取舍 / 风险

- TUI 架构的分层很清晰，但同时也引入了多套缓存与传输层：SDK 快照、事件流、sync store 和本地 UI 状态。
- 本地 worker 模式提升了响应性和隔离性，但也增加了 RPC / event-bridge 复杂度。
- 由于渲染依赖 sync store，如果事件缺失或乱序，即使后端状态正确，UI 也可能出现陈旧视图。

## 待验证

- `web/app/desktop` 包有多少复用了同一套后端交互模型，又有多少叠加了各自 UI 专属状态层。
- 是否仍有某些 TUI 页面严重依赖零散的直接 SDK fetch，而不是共享的 sync store。
