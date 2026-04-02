# Runtime 模块

## 模块职责

运行时编排层负责在请求已经进入核心后端之后，协调交互式 session loop。在当前固定版本中，它的职责包括：

- 按 session 串行化执行，
- 把一条用户消息推进为一个或多个 model / tool / compaction 步骤，
- 管理取消、繁忙状态和并发所有权，
- 把流式执行委托给 LLM 和 processor 层，
- 并决定 loop 什么时候继续、compact、停止，或切换到 subtask / shell 分支。

关于编排核心文件的更细分析，见 `session-prompt.md`。那篇文档专门解释了为什么 `session/prompt.ts` 并不只是提示词模板文件，以及为什么它实际掌握了这么多运行时控制权。

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | 主运行时编排器，也是每个 session loop 的所有者 | `SessionPrompt.prompt`, `runLoop`, `loop`, `shell`, `command` |
| `workspace/source/opencode/packages/opencode/src/effect/runner.ts` | 按 session 隔离的 single-flight runner，负责 cancel / shell sequencing | `Runner.make`, `ensureRunning`, `startShell`, `cancel` |
| `workspace/source/opencode/packages/opencode/src/session/processor.ts` | 编排器使用的流式 model / tool 事件消费者 | `SessionProcessor.create`, `process(...)`, `abort(...)` |
| `workspace/source/opencode/packages/opencode/src/session/compaction.ts` | 主 session loop 调用的 compaction 支路 | `SessionCompaction.process`, `create`, `prune` |
| `workspace/source/opencode/packages/opencode/src/session/status.ts` | 发布 session busy / retry / idle 状态 | `SessionStatus.set(...)` |
| `workspace/source/opencode/packages/opencode/src/server/routes/session.ts` | 把控制权移交给 `SessionPrompt` 的请求边界 | `session.prompt`, `session.command`, `session.shell` routes |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `SessionPrompt.prompt(...)` | entrypoint | `prompt.ts` | 创建用户消息并进入 session loop |
| `runLoop(sessionID)` | orchestrator loop | `prompt.ts` | 逐步控制一个活跃 session 的运行 |
| `loop({ sessionID })` | serialization wrapper | `prompt.ts` | 保证同一时刻只有一个 runner 持有该 session loop |
| `Runner.make(...)` | concurrency primitive | `runner.ts` | 创建按 session 使用的 single-flight runner |
| `SessionProcessor.create(...)` | processor factory | `processor.ts` | 为新 assistant message 绑定一个流式事件处理器 |
| `SessionProcessor.process(...)` | delegated execution | `processor.ts` | 消费 LLM stream 事件，并返回 `continue` / `stop` / `compact` |
| `SessionCompaction.process(...)` | branch handler | `compaction.ts` | 在 loop 切换模式时执行摘要 compact |
| `SessionStatus.set(...)` | signaling helper | `status.ts` | 向观察者发布 busy / retry / idle 状态 |

## 初始化 / 入口

运行时层主要通过两个前门进入：

1. CLI 流程：
   - `cli/cmd/run.ts` 构造一个 SDK client，
   - 通常把请求指向 `Server.Default().fetch(...)`，
   - 然后调用 `sdk.session.prompt(...)` 或 `sdk.session.command(...)`。
2. Server 流程：
   - `server/routes/session.ts` 校验请求，
   - 然后直接调用 `SessionPrompt.prompt(...)`、`SessionPrompt.command(...)` 或 `SessionPrompt.shell(...)`。

真正的运行时交接发生在这些导出的 `SessionPrompt.*` 包装器调用 `makeRuntime(...)` 返回的 `runPromise(...)` 之时。从这一刻起，控制权离开 transport layer，进入基于 Effect 的 orchestration service。

## 主控制流

### 1. Enter SessionPrompt

`SessionPrompt.prompt(...)` 会：

1. 加载目标 session，
2. 清理 revert state，
3. 创建新的用户消息，
4. 应用按请求传入的 tool permission override，
5. 并在没有设置 `noReply` 时进入 `loop({ sessionID })`。

### 2. Serialize Per Session

`loop(...)` 会从一个 instance-scoped 的 `Map<sessionID, Runner<...>>` 中查找 runner。

这意味着：

- 同一时刻只有一个交互 loop 能拥有某个 session；
- 重复的 prompt 调用会复用已在飞行中的 runner；
- shell 执行通过 `startShell(...)` 走独立的 runner 分支；
- 取消逻辑集中在 runner 上，而不是分散到各模块里。

### 3. Run The Main Orchestration Loop

`runLoop(sessionID)` 是核心编排器。

每次迭代时，它会：

1. 加载 compact 过的消息历史，
2. 找出最新的 user / assistant 状态，
3. 选择模型，
4. 在 subtask、compaction 或普通 assistant 生成之间做分支，
5. 创建下一条 assistant message 记录，
6. 为该消息创建一个 `SessionProcessor`，
7. 解析 tools、system prompts、instructions 和 model messages，
8. 把执行委托给 `handle.process(...)`，
9. 再把结果解释成 `break`、`continue` 或 `compact`。

### 4. Delegate Streaming Work

编排器本身不会直接消费 provider 事件。它把这个责任交给 `SessionProcessor.process(...)`，后者会：

- 调用 `LLM.stream(...)`，
- 更新 text / reasoning / tool parts，
- 管理重试，
- 记录错误，
- 并把控制信号返回给 loop。

这条边界区分了“control-plane orchestration”和“stream event consumption”。

### 5. Handle Side Branches

loop 会显式处理这些分支：

- subtask execution，
- overflow 或 auto compaction，
- shell mode，
- command-template expansion，
- structured-output enforcement，
- cancellation 与 abort cleanup。

因此，高层运行时策略实际集中在 `SessionPrompt` 中，即便具体的 provider / tool / state 工作仍被委托给外部模块。

## 上下游依赖

Upstream:

- `server/routes/session.ts` 和 CLI SDK 调用方
- 用于建立 workspace-scoped context 的 `Instance.provide(..., init: InstanceBootstrap)`
- `Agent`、`Provider`、`Command`、`Permission`、`Plugin`、`Config`

Downstream:

- 用于事件处理的 `SessionProcessor`
- 用于模型执行的 `LLM` / `Provider`
- 提供可执行能力的 `ToolRegistry` 以及 MCP / LSP
- 用于持久化消息状态更新的 `Session` / `MessageV2`
- 用于落库的、由 `SyncEvent` 驱动的 session / message projector
- 用于摘要回退的 `SessionCompaction`
- 用于状态发布的 `SessionStatus` / `Bus`

## 实现细节

- 运行时串行化是 instance-scoped 的，并且按 session ID 建立键，而不是纯全局的。
- `Runner.onIdle` 和 `Runner.onBusy` 被接到 `SessionStatus.set(...)` 上，因此 session status 是 orchestrator state 的投影，而不是一个单独调度器。
- `SessionPrompt.command(...)` 和 `SessionPrompt.shell(...)` 是并列的 orchestration entrypoint，但仍复用同一套 runner 模型。
- loop 依赖消息历史和 finish reason 的具体分支条件，而不是通用 reducer 或显式状态机对象。
- `SessionCompaction` 不只是后台任务；它是主 loop 里的一级分支，而且可能递归触发下一轮 loop。
- 编排过程中发生的 session / message mutation 最终都会流经以 `SyncEvent.run(...)` 为后端的 `Session.*` API，因此 persistence 虽然不是 loop driver，却处在热路径上。

## 设计取舍 / 风险

- 主编排逻辑集中在体量很大的 `session/prompt.ts` 中，这让控制权归属更清晰，但也提高了局部复杂度。
- 通过 `Runner` 做 session 串行化可以避免重叠执行，但也意味着长时间运行的操作会直接影响该 session 的响应性。
- 高层策略和底层分支逻辑同处一个模块，使得 `SessionPrompt` 有演变成 runtime god object 的风险。
- 因为多个 transport entrypoint 都汇聚到同一个 orchestration core，`SessionPrompt` 中的 bug 会同时影响 CLI 和 server 两侧。

## 待验证

- 是否存在任何非 session 的交互流程，会绕过 `SessionPrompt` 直接执行 provider 调用。
- TUI 特有行为中，有多少属于 runtime orchestration，本质上又有多少只是纯客户端订阅 / 渲染。
