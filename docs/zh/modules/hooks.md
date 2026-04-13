# Hook 机制

## 模块职责

本文档专门分析这个固定版本中的 server plugin hook 表面。目标是说明：

- hook 契约在哪里声明，
- hook 实现如何被加载，
- 运行时里到底有哪些 hook 名称被实际触发，
- 哪些 plugin 字段其实不是 `Plugin.trigger(...)` hook，
- 以及 plugin 作者实际上继承了什么执行语义。

关键边界在于：“plugin hook”并不是单一机制。有些是顺序执行的 `(input, output)` 变换，有些只是被 registry 或 bus 消费的普通导出字段。

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/plugin/src/index.ts` | `Hooks` 契约定义 | `Hooks`, `Plugin`, `PluginModule` |
| `workspace/source/opencode/packages/opencode/src/plugin/index.ts` | plugin 加载、`config` 分发、`event` 订阅与 `Plugin.trigger(...)` 运行时 | `TriggerName`, `applyPlugin(...)`, `trigger(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/registry.ts` | 消费 plugin `tool` 导出并触发 `tool.definition` | `plugin.list()`, `plugin.trigger("tool.definition", ...)` |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | 触发 message、command、tool execution 与 shell environment hooks | `createUserMessage(...)`, 包装后的 tool `execute(...)`, `command(...)`, `shellImpl(...)` |
| `workspace/source/opencode/packages/opencode/src/session/llm.ts` | 在 provider 调用前触发请求整形 hooks | `Plugin.trigger("experimental.chat.system.transform", ...)`, `Plugin.trigger("chat.params", ...)`, `Plugin.trigger("chat.headers", ...)` |
| `workspace/source/opencode/packages/opencode/src/session/compaction.ts` | 触发 compaction 相关 hooks | `plugin.trigger("experimental.session.compacting", ...)`, `plugin.trigger("experimental.chat.messages.transform", ...)` |
| `workspace/source/opencode/packages/opencode/src/session/processor.ts` | 触发文本收尾 hook | `plugin.trigger("experimental.text.complete", ...)` |
| `workspace/source/opencode/packages/opencode/src/permission/index.ts` | 当前 permission runtime，未观察到 `permission.ask` trigger 用法 | `Permission.ask(...)` |
| `workspace/source/opencode/packages/opencode/src/provider/auth.ts` | 消费 plugin `auth` 导出 | `Plugin.list()` -> auth hook map |
| `workspace/source/opencode/packages/opencode/src/provider/provider.ts` | 把 plugin `auth.loader(...)` 输出合入 provider options | `plugin.auth.loader(...)` |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Hooks` | interface | `packages/plugin/src/index.ts` | 声明完整的 plugin 扩展契约 |
| `TriggerName` | type filter | `packages/opencode/src/plugin/index.ts` | 只把 `(input, output) => Promise<void>` 形状的 hook 纳入 `Plugin.trigger(...)` |
| `Plugin.Service` | service | `packages/opencode/src/plugin/index.ts` | 管理按实例隔离的已加载 hook 列表 |
| `applyPlugin(...)` | loader helper | `packages/opencode/src/plugin/index.ts` | 把 v1 与 legacy server plugin 导出统一成 `Hooks` 对象 |
| `Plugin.trigger(name, input, output)` | hook runner | `packages/opencode/src/plugin/index.ts` | 顺序执行某个 hook 链并返回被原地修改后的 output |
| `plugin.list()` / `Plugin.list()` | registry accessor | `packages/opencode/src/plugin/index.ts` | 向 tool/auth 等非 trigger 消费方暴露已加载 hook 对象 |

## 初始化 / 入口

`Plugin.Service` 会在 `Plugin.init()` 或第一次访问 service 时构建一个按实例隔离的 `hooks: Hooks[]` 列表。

初始化顺序：

1. 加载内置 server plugins，
2. 解析并导入配置声明的外部 server plugins，
3. 执行每个 plugin factory，并把返回的 `Hooks` 对象追加到有序的 `hooks[]` 数组，
4. 对每个 hook 对象调用可选的 `config(...)`，
5. 把可选的 `event(...)` 订阅到共享 bus，
6. 向下游 runtime 暴露 `trigger(...)` 与 `list()`。

`hooks[]` 的顺序是刻意保持确定性的，因为注册顺序和后续触发顺序都依赖同一个数组。

## 主控制流程

### 1. 给 Hook 表面分型

声明出来的 `Hooks` interface 同时包含 trigger 式与非 trigger 式入口。

Trigger 式入口：

- 形状是 `(input, output) => Promise<void>`，
- 会被纳入 `TriggerName`，
- 可以通过 `Plugin.trigger(...)` 调用。

非 trigger 式入口：

- `tool`
- `auth`
- `config`
- `event`

这些字段不会进入 `TriggerName`，而是通过显式的 registry 逻辑或 bus wiring 被消费。

### 2. 把 Hooks 加载进 Runtime

`applyPlugin(...)` 同时接受现代 v1 plugin module 和 legacy server-plugin 导出，执行 server factory 后，把得到的 `Hooks` 对象存入有序的 `hooks[]` 列表。

加载完成后：

- `config(...)` 会被调用一次，
- `event(...)` 会挂到 `bus.subscribeAll()`，
- 其他字段只有在运行时模块显式触发或读取时才会生效。

### 3. 分发 Trigger Hooks

`Plugin.trigger(...)` 的执行模型很直接：

1. 从 instance state 取出当前 `hooks[]`，
2. 对每个 hook 对象读取 `hook[name]`，
3. 没有实现就跳过，
4. 用同一个 `input` 和 `output` 顺序 await 该 hook，
5. 循环结束后返回同一个 `output` 对象。

这意味着 hook 组合是靠原地修改共享 output 来完成，而不是靠返回替换值。

### 4. 当前运行时里观察到的 Trigger Hooks

| Hook | Trigger file / symbol | Mutable output | Runtime role |
| --- | --- | --- | --- |
| `tool.definition` | `packages/opencode/src/tool/registry.ts`, `ToolRegistry.tools(...)` | `{ description, parameters }` | 在工具暴露给模型前改写 schema 与描述 |
| `tool.execute.before` | `packages/opencode/src/session/prompt.ts`, 包装后的普通工具 / MCP / task 执行路径 | `{ args }` | 在工具实际执行前改写调用参数 |
| `tool.execute.after` | `packages/opencode/src/session/prompt.ts`, 包装后的普通工具 / MCP / task 执行路径 | result object | 在工具执行后处理 output、metadata、attachments |
| `chat.message` | `packages/opencode/src/session/prompt.ts`, `createUserMessage(...)` | `{ message, parts }` | 在用户消息落盘前拦截并改写消息与 parts |
| `command.execute.before` | `packages/opencode/src/session/prompt.ts`, `command(...)` | `{ parts }` | 在 command 解析成 prompt parts 后、转成用户消息前进行改写 |
| `chat.params` | `packages/opencode/src/session/llm.ts`, `LLM.stream(...)` | `{ temperature, topP, topK, options }` | 改写 provider 请求参数 |
| `chat.headers` | `packages/opencode/src/session/llm.ts`, `LLM.stream(...)` | `{ headers }` | 注入 provider 请求头 |
| `experimental.chat.system.transform` | `packages/opencode/src/session/llm.ts`, `LLM.stream(...)`; `packages/opencode/src/agent/agent.ts`, `Agent.generate(...)` | `{ system }` | 改写 system prompt 行列表 |
| `experimental.chat.messages.transform` | `packages/opencode/src/session/prompt.ts`, 主 prompt loop；`packages/opencode/src/session/compaction.ts`, compaction | `{ messages }` | 在转成 model messages 前改写消息历史 |
| `experimental.session.compacting` | `packages/opencode/src/session/compaction.ts`, compaction create path | `{ context, prompt }` | 扩展或替换 compaction prompt |
| `experimental.text.complete` | `packages/opencode/src/session/processor.ts`, `text-end` 事件 | `{ text }` | 在 assistant 最终文本保存前改写文本 |
| `shell.env` | `packages/opencode/src/session/prompt.ts`, `shellImpl(...)`; `packages/opencode/src/tool/bash.ts`; `packages/opencode/src/pty/index.ts` | `{ env }` | 注入 shell / PTY 环境变量 |

### 5. 非 Trigger 表面

| Surface | Consumption path | Purpose |
| --- | --- | --- |
| `tool` | `packages/opencode/src/tool/registry.ts` | 向 tool registry 注册 plugin 定义的工具 |
| `auth` | `packages/opencode/src/provider/auth.ts`, `packages/opencode/src/provider/provider.ts`, `packages/opencode/src/cli/cmd/providers.ts` | 提供 provider auth 方法和 provider option loader |
| `config` | `packages/opencode/src/plugin/index.ts` | 在 plugin 初始化后接收一次当前配置 |
| `event` | `packages/opencode/src/plugin/index.ts` | 通过 `bus.subscribeAll()` 接收 bus 事件 |

### 6. 已定义但当前未观察到运行时 Trigger 的项

`permission.ask` 出现在 `Hooks` interface 中，但当前源码证据里没有发现 `Plugin.trigger("permission.ask", ...)`。

当前观察到的实际行为是：

- `Permission.ask(...)` 自己完成规则判断，
- 然后发布 `permission.asked` bus 事件，
- UI / CLI 再消费这个 bus 事件，
- 分析范围内的 `packages/opencode/src` 没有经过 plugin-trigger 分发这一步。

## 上下游依赖

上游：

- 提供 plugin 声明的 `Config`
- plugin 模块解析 / 加载流水线
- 负责事件扇出的 `Bus`
- 提供按项目隔离缓存的 instance state

下游：

- 负责 plugin tool 和 `tool.definition` 的 `ToolRegistry`
- 负责 message / command / tool / shell hooks 的 `SessionPrompt`
- 负责请求整形 hooks 的 `LLM.stream(...)`
- 负责 compaction / text hooks 的 `SessionCompaction` 与 `SessionProcessor`
- 负责 `auth` 导出的 provider auth 流程

## 实现细节

- `TriggerName` 刻意排除了 `tool`、`auth`、`config`、`event`，因此 TypeScript 层面就不会把这些字段路由进 `Plugin.trigger(...)`。
- `config(...)` 在初始化阶段按单个 hook 做错误隔离；失败只记日志并忽略。
- `event(...)` 通过 bus 订阅副作用分发，不走正常的 trigger pipeline，也不会被 await 到业务返回路径里。
- `Plugin.trigger(...)` 自身没有对单个 hook 做错误隔离；某个 hook 抛错会直接中断调用它的运行时路径。
- 当前版本里 `tool.execute.before` / `after` 覆盖了三种执行路径：普通工具、MCP 工具和 `task` 工具。
- `experimental.chat.system.transform` 不只影响主聊天环，还会影响 `Agent.generate(...)`。
- `shell.env` 被 shell mode、bash tool 和 PTY 创建三条路径共用，因此一个 plugin 可以同时影响多个 shell 入口。

## 设计取舍 / 风险

- 共享可变 output 让 hook 组合简单直接，但也使 plugin 之间形成很强的顺序耦合。
- 确定性的顺序执行有利于推理，但 hook 延迟会直接叠加到热路径上。
- `Plugin.trigger(...)` 缺少单个 hook 级别的隔离，意味着一个有缺陷的 plugin 就可能让工具执行或 LLM 请求整形失败。
- 扩展契约是碎片化的：一部分是 trigger hooks，一部分是 registry 字段，一部分是 bus listeners。
- `permission.ask` 在 interface 中存在、但当前未见运行时触发，会提高 plugin 作者误判可用扩展点的风险。

## 待验证

- 目前观察到的 hook 名称里，哪些是公开稳定扩展契约，哪些只是内部或实验性实现细节。
- `permission.ask` 究竟是遗留未接线 hook，还是只会在分析范围外的代码路径中被触发。
- 外部 plugins 是否已经依赖 `tool.execute.before`、`tool.execute.after`、`shell.env` 的现有顺序，从而把这个顺序事实上变成公开契约的一部分。
