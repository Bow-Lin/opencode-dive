# Opencode 深入拆解

## 适合谁读

这篇文章面向想快速理解 Opencode 设计思路的中高级工程师。目标不是替你读完整个仓库，而是先把最重要的控制主线、运行时抽象和关键设计取舍讲清楚。

## 阅读方式

主文采用叙事方式串起系统，只保留最关键的代码锚点。更细的证据链和展开分析放在 `../modules/` 与 `../callflows/` 下的附录里。

如果你想先用图把结构看顺，可以先读 `../system-diagrams.md`，再继续看这些附录。

## 1. Opencode 到底是什么

Opencode 不是一个简单的“LLM 命令行壳”。在这个固定版本里，它是一个 TypeScript monorepo，行为核心主要位于 `workspace/source/opencode/packages/opencode`，而 web、desktop、SDK、plugin、UI 等能力则分布在其他工作区包中。

真正重要的阅读姿势是：把它理解成一个拥有多个前端入口的共享运行时，而不是单一用途的 CLI 应用。

关键锚点：

- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/server/server.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`

## 2. 请求并不会停在 CLI

CLI 只是入口表面，不是系统全貌。用户命令先进入 CLI bootstrap 路径，但实现很快就会转到内部 SDK client，再进一步进入进程内的 server/control-plane 栈。

这一层设计很关键，因为它意味着 Opencode 会在本地 CLI 场景和 server 式请求处理之间复用同一套后端编排逻辑。

关键锚点：

- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts`
- `workspace/source/opencode/packages/opencode/src/server/routes.ts`

## 3. 为什么 `SessionPrompt` 才是真正的控制核心

最强的控制热点是 `workspace/source/opencode/packages/opencode/src/session/prompt.ts`。传输层负责接收和规整请求，但真正拥有 prompt loop、session 级编排策略以及下游 provider、tool、持久化协调权的是 `SessionPrompt`。

这是阅读仓库时最重要的捷径之一：如果问题是“交互循环到底真正活在哪里”，答案既不是 CLI 文件，也不是 router 树，而是 `SessionPrompt`。

关键锚点：

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/index.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`

## 4. Provider、Tool、Session 是怎么分工的

Opencode 把三个重要关注点拆开处理：

- provider 模块负责模型选择与调用，
- tool 模块负责 prompt loop 周围的可执行能力，
- session 模块负责会话状态、流式处理和持久化。

正是这种拆分，避免了整个系统坍缩成一个巨大的“agent runtime”文件。虽然中心编排路径仍然集中，但扩展性和可读性都因此更强。

关键锚点：

- `workspace/source/opencode/packages/opencode/src/provider/provider.ts`
- `workspace/source/opencode/packages/opencode/src/tool/tool.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`

## 5. 为什么它是共享后端，而不只是 CLI

仓库暴露了多个用户侧壳层，但它们最终会汇聚到一个共享的后端模型上。这个模型建立在 Effect service、实例级运行时上下文，以及 server 风格路由之上。实际运行时，即使是本地 CLI 流程，也往往会通过进程内 fetch 层去访问这套共享后端。

这种设计增加了间接层，但它减少了 CLI、app 和其他入口之间的重复实现。

关键锚点：

- `workspace/source/opencode/packages/opencode/src/project/instance.ts`
- `workspace/source/opencode/packages/opencode/src/server/server.ts`
- `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts`

## 6. 扩展机制并不是一回事

仓库里有几类看上去相似、但运行方式不同的扩展机制：

- server plugin 用来 hook 运行时行为，
- TUI plugin 用来扩展界面壳层，
- skill 提供可复用的任务内容和命令暴露，
- tool 则是在 prompt loop 内执行动作的能力。

如果把这些都混成一个“插件系统”，会让架构理解变得更混乱。按生命周期和职责把它们拆开看，代码会清晰很多。

关键锚点：

- `workspace/source/opencode/packages/opencode/src/plugin/index.ts`
- `workspace/source/opencode/packages/opencode/src/skill/index.ts`
- `workspace/source/opencode/packages/opencode/src/tool/tool.ts`
- `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/plugin/runtime.ts`

## 7. 这套架构最核心的取舍

Opencode 通过把系统拆成传输表面、实例作用域、运行时编排、provider、tool、事件和持久化层，换来了很强的灵活性。代价是：你无法从单个文件直接看清控制权归属，必须沿着一次请求穿过这些边界，系统才会真正“显形”。

因此，最有效的阅读顺序是：

1. CLI 或请求入口
2. 实例 bootstrap
3. `SessionPrompt`
4. provider / tool / session 内部实现
5. 持久化与事件传播

## 接下来读什么

- 可视化图集：`../system-diagrams.md`
- 架构总览：`../architecture.md`
- 仓库地图：`../repo-map.md`
- 模块附录：`../modules/`
- 调用链附录：`../callflows/`
