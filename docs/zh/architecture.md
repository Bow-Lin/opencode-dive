# 架构

## 当前状态

这份文档是当前固定版本 Opencode 的长期系统视图。只有在具体分析轮次已经确认主要模块和运行时链路之后，才应该把结论提升到这里。

配套的可视化图集见 `system-diagrams.md`。

## 系统边界

- 目标应用：`OPENCODE_VERSION.md` 中固定的 Opencode 版本
- 源码位置：`workspace/source/opencode`
- 分析重点：运行时结构、数据流、模块职责和关键执行链路

## 高层组件

整个仓库是一个 monorepo，但主要行为核心集中在 `workspace/source/opencode/packages/opencode`。

从初始盘点可见的顶层组件拆分是：

- `packages/opencode` 中的 CLI / runtime 核心
- `packages/app`、`packages/web`、`packages/desktop`、`packages/desktop-electron` 中的客户端表面
- `packages/plugin`、`packages/sdk/js`、`packages/ui`、`packages/util` 中的共享库
- `infra/`、`script/`、`github/` 中的基础设施与自动化

## 核心抽象家族

核心包围绕一套重复出现的 Effect 服务模式组织起来：

- 诸如 `Agent`、`Provider`、`Plugin`、`Command`、`Bus`、`Worktree` 之类的服务命名空间
- 描述能力面的 `Interface` 类型
- 通过 `ServiceMap.Service` 完成的 `Service` 注册
- 用来拼装依赖的 `layer` 或 `defaultLayer`

这个模式可以在下面这些文件中看到：

- `workspace/source/opencode/packages/opencode/src/agent/agent.ts`
- `workspace/source/opencode/packages/opencode/src/provider/provider.ts`
- `workspace/source/opencode/packages/opencode/src/plugin/index.ts`
- `workspace/source/opencode/packages/opencode/src/command/index.ts`
- `workspace/source/opencode/packages/opencode/src/bus/index.ts`
- `workspace/source/opencode/packages/opencode/src/worktree/index.ts`

围绕这层服务核心，系统还反复使用下面几类抽象：

### 1. 服务能力

长期存在的子系统通过 Effect service 暴露，而不是单例对象。这是 provider 访问、agent 行为、plugin 加载、config 读取、command、session 管理和 worktree 处理的主导抽象。

### 2. 实例级运行时状态

运行时状态按 project/worktree 实例隔离。`project/instance.ts` 提供环境中的实例上下文，`effect/instance-state.ts` 提供按实例缓存的状态容器，服务如果需要按目录/worktree 隔离，就会依赖这套机制。

### 3. Schema 优先的领域模型

很多核心类型都先用 Zod schema 定义，再导出推断类型。这个模式在 `agent/agent.ts`、`session/index.ts`、`provider/provider.ts` 和 `tool/tool.ts` 等模块都能看到。标识符还会在 `provider/schema.ts`、`session/schema.ts`、`tool/schema.ts` 之类的 schema 文件里进一步规范化。

### 4. 事件与投影模型

系统里并存两套事件抽象：

- `bus/bus-event.ts` + `bus/index.ts`：进程内的发布/订阅通知
- `sync/index.ts`：带版本、支持 replay/projector、并且可选发布到 bus 的领域事件

这说明运行时同时使用了短暂的内存信号和更耐久的事件驱动状态变更。

### 5. 声明式的 Tool / Command / Extension 合约

- `tool/tool.ts` 定义通用 tool 合约
- 各个 tool 通过 `Tool.define(...)` 注册
- `command/index.ts` 把内置命令、MCP prompts 和 skills 聚合成统一 command 抽象
- `plugin/index.ts` 与 `skill/index.ts` 把扩展内容接入运行时

### 6. 多个入口，共享核心

代码库暴露了多个面向用户的入口：

- `packages/opencode/src/index.ts` 中基于 yargs 的 CLI 启动
- `packages/opencode/src/server/server.ts` 中的 Hono server 构建
- monorepo 里其余 app / desktop / web 包提供的外围表面

这与 README 中“Opencode 采用 client/server 架构，而不是单纯 CLI 壳层”的描述一致。

## 运行时数据流

从高层看，架构大致沿着下面这条链路流动：

1. 包装脚本 / 二进制解析，或直接 dev 启动
2. `src/index.ts` 中构建 CLI
3. 进程级日志和 migration 中间层
4. command 分发
5. 针对 project 作用域命令的实例级 bootstrap，或在 server 模式下按请求延迟 bootstrap
6. session、agent、provider、tool、plugin 的相互作用
7. bus / sync 事件以及基于存储的状态变更

更细的确认应放到入口和调用链分析任务里。

## 高层请求管线

当前主导的交互路径大致是：

1. 在 `packages/opencode/src/index.ts` 中选择一个 CLI 命令，例如 `run`
2. 命令进入 `cli/bootstrap.ts`，通过 `Instance.provide(..., init: InstanceBootstrap)` 建立 project/worktree 上下文
3. CLI 构造一个内部 SDK client，它的 `fetch` 实现直接指向 `Server.Default().fetch(...)`
4. SDK 对进程内 Hono app 发起 session API 调用，而不是真的走网络
5. `ControlPlaneRoutes` 把带 project 作用域的请求交给 `WorkspaceRouterMiddleware`，确保当前实例正确
6. `InstanceRoutes` 再把请求分发到 `SessionRoutes` 等路由组
7. session 变更类接口继续委托给 `SessionPrompt.*`、`Session.*`、`SessionStatus.*` 等服务
8. `SessionPrompt` 协调 agent 选择、provider/model 访问、tool 注册、权限、MCP/LSP 和 session 处理

这条路径很重要，因为它跨越了 CLI 表面、server 表面、实例作用域和 session 编排核心。

## 端到端交互主干

当前最有代表性的端到端路径是：

1. CLI / TUI 中的用户动作，
2. 客户端侧参数归一化，
3. SDK / control-plane 请求，
4. workspace 实例绑定，
5. `SessionPrompt` 编排，
6. `SessionProcessor` 流式执行，
7. provider / tool 交互，
8. 基于 sync 的 session 持久化，
9. 根据事件或同步状态在客户端渲染结果。

这个主干把前面各模块分析串成了一条顺序控制链，也说明最终产物不只是“模型返回的文本”，它同时还是客户端渲染结果、持久化后的 session/message/part 数据，以及某些 tool 带来的副作用。

## 运行时编排核心

主要运行时编排器是 `workspace/source/opencode/packages/opencode/src/session/prompt.ts`，而不是 server router、CLI command handler 或 event bus。

目前观察到的控制拆分如下：

- 传输表面：
  - CLI `run.ts`
  - `server/routes/session.ts` 中的 server routes
- 实例 / workspace 边界：
  - `WorkspaceRouterMiddleware`
  - `Instance.provide(..., init: InstanceBootstrap)`
- 编排核心：
  - `SessionPrompt.prompt(...)`
  - `SessionPrompt.loop(...)`
  - 内部 `runLoop(sessionID)`
- 流式执行层：
  - `SessionProcessor.process(...)`
  - `LLM.stream(...)`
- 侧向信号通道：
  - `SessionStatus`
  - `Bus`

最重要的架构结论是：Opencode 有一个被多个前端入口复用的共享后端编排核心。CLI 经常通过一个指向 `Server.Default().fetch(...)` 的进程内 SDK client 与这个核心交互，这意味着 server 表面不仅仅是远程部署外壳，它同时也是本地控制 API。

## 控制权归属

目前最清晰的控制权模型是：

1. 传输层接收请求并校验输入形状；
2. 实例层建立目录 / worktree 上下文；
3. `SessionPrompt` 通过导出的 `runPromise(...)` 包装进入 Effect runtime，并接管 session 级控制流与 loop 策略；
4. `SessionProcessor` 接管单次模型运行中的逐事件消费；
5. provider / tool / session 模块分别执行被委托的职责；
6. bus / status 层把可观察状态向外发布。

这意味着 `Bus` 对通知与集成很重要，但它不是驱动交互循环的主调度器。`SyncEvent` 虽然也在 `Session.*` 的热写路径上出现，但它承担的是持久化事件投影 / 重放角色，而不是 prompt loop 调度。

## 扩展架构

扩展机制是混合式的：

- server plugins：
  - 由 `plugin/index.ts` 加载
  - 通过 hook 注入 tool 定义 / 执行、聊天消息变换等运行时流程
- TUI plugins：
  - 由 `cli/cmd/tui/plugin/runtime.ts` 加载
  - 扩展 UI 壳层中的 routes、slots、themes 和 commands
- skills：
  - 由 `skill/index.ts` 发现
  - 通过 system prompt 清单、`skill` tool 加载和 command 列表暴露

这很关键，因为在 Opencode 中，“plugin”并不是单一运行时抽象。skill 是内容导向扩展，server plugin 是 hook 导向扩展，TUI plugin 是 UI runtime 扩展。它们共享了一部分 config/spec 机制，但并不共享同一个生命周期。

## 模块边界

目前最明确的模块边界是：

- `cli`、`server`、`command`：入口和控制表面
- `config`、`provider`、`tool`、`plugin`、`skill`、`session`：核心运行时关注点
- `storage`、`sync`、`bus`：持久化与信号基础设施
- `project`、`worktree`、`instance-state`：workspace 作用域执行上下文

这些边界在目录层级上很明确，也被 service interface 强化，但很多模块仍然依赖共享的实例上下文，因此整体运行时并不是严格意义上纯粹的依赖注入系统。

## 关键风险 / 设计张力

- 实例上下文是环境式、横切的，这提高了易用性，但也会模糊控制权归属。
- 服务模式虽然一致，但子系统和默认 layer 很多，如果不结合调用链追踪，依赖装配会比较难跟。
- tool、command、skill、plugin 和 MCP prompt 都能作为扩展表面，灵活性很高，但也形成了多条注册路径。
- 短暂 bus 事件和持久化 sync 事件并存，意味着后续分析必须明确区分两种信号模型。
- 运行时编排中心高度集中在 `session/prompt.ts`，虽然降低了“去哪里看控制流”的成本，但也形成了高复杂度热点。
- 扩展行为强烈依赖上下文，因为 server plugin、TUI plugin 和 skill 相关但不可互换。

## 证据要求

只有当底层模块文档和调用链文档已经引用具体文件与符号后，才应把结论提升到这里。
