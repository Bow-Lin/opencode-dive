# Tools 模块

## 模块职责

tools 模块是把具体运行时能力暴露给模型的能力层。在当前固定版本里，它负责：

- 定义统一的 tool 合约
- 从内置工具、配置目录和 plugin 组装激活的 tool registry
- 选择与模型兼容的 tool 暴露面
- 在 session 上下文中执行 tool call
- 把结果规范化后送回 session loop

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/tool/tool.ts` | 通用 tool 合约、参数校验、自动输出截断 | `Tool.Context`, `Tool.Def`, `Tool.Info`, `Tool.define(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/registry.ts` | 内置 / 自定义 / plugin tool 发现与按模型过滤 | `ToolRegistry.Service`, `all(...)`, `tools(...)` |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | 带权限和元数据回调的 session 级 tool 适配器构建 | 内部 `resolveTools(...)` |
| `workspace/source/opencode/packages/opencode/src/session/llm.ts` | 最终激活 tool 过滤与 AI SDK `streamText(...)` 交接 | 本地 `resolveTools(...)`, `streamText(...)` |
| `workspace/source/opencode/packages/opencode/src/session/processor.ts` | assistant message 内的 tool 事件生命周期跟踪 | `tool-input-start`, `tool-call`, `tool-result`, `tool-error` 处理 |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Tool.Context` | type | `tool.ts` | 每次 tool 执行时注入的运行时上下文 |
| `Tool.Def` | type | `tool.ts` | 带 schema + `execute(...)` 的可执行 tool 合约 |
| `Tool.Info` | type | `tool.ts` | 面向 registry 的 tool 描述，含惰性 `init(...)` |
| `Tool.define(id, init)` | helper | `tool.ts` | 为具体 tool 包装参数校验和输出截断 |
| `ToolRegistry.Service` | service | `registry.ts` | 提供 `register`、`ids` 和 `tools(...)` |
| `ToolRegistry.tools(...)` | registry query | `registry.ts` | 为特定 model/agent 构建已初始化的 tool 定义 |
| `SessionPrompt.resolveTools(...)` | adapter builder | `prompt.ts` | 把 registry 定义转换成带 session 上下文的 AI SDK tools |
| `LLM.resolveTools(...)` | filter | `llm.ts` | 在模型调用前移除用户禁用或权限禁用的 tools |
| `SessionProcessor.Handle.partFromToolCall(...)` | lookup | `processor.ts` | 让执行回调更新匹配的 tool part |

## 初始化 / 入口

tool 层不是通过独立命令启动的。当 `SessionPrompt` 准备一次模型调用，并向 `ToolRegistry.Service` 请求当前模型与 agent 可用的 tools 时，它才真正变为活跃状态。

实际有三类入口：

1. `Tool.define(...)`：声明一个 tool
2. `ToolRegistry.tools(...)`：发现并初始化 tools
3. `SessionPrompt.resolveTools(...)`：把这些工具接入真实 session 执行上下文

## 主控制流

### 1. 声明 Tool 合约

具体工具通过 `Tool.define(id, init|def)` 表达。

这个包装器统一增加了两类行为：

1. 在执行前用 tool 的 Zod schema 校验参数
2. 除非 `metadata.truncated` 已显式声明，否则通过 `Truncate.output(...)` 截断过长文本输出

### 2. 构建 Tool Registry

`ToolRegistry.Service` 从以下来源构建可用 tool 集：

- 内置工具模块，如 `bash`、`read`、`glob`、`grep`、`task`、`webfetch`、`todowrite`、`skill`、`apply_patch`
- 通过特性开关控制的工具，如 `lsp`、`batch`、`plan_exit`
- 配置目录中的 `tool/*.{js,ts}` 或 `tools/*.{js,ts}` 脚本
- `plugin.list()` 暴露的 plugin tool 定义
- 通过 `ToolRegistry.register(...)` 在运行时注册的工具

配置目录工具和 plugin 工具最终都会通过统一的 `fromPlugin(...)` 适配成 `Tool.Info`。

### 3. 按模型 / 环境过滤

在初始化之前，`ToolRegistry.tools(...)` 会先做模型感知过滤：

- `codesearch` 和 `websearch` 只在 `opencode` provider 下，或 `OPENCODE_ENABLE_EXA` 开启时暴露
- 对兼容的 GPT 家族模型优先暴露 `apply_patch`
- 当使用 `apply_patch` 时，隐藏 `edit` 和 `write`

每个保留下来的 tool 随后会被初始化，并经过 `plugin.trigger("tool.definition", ...)`，这样 plugin 可以在暴露给模型前修改描述或 schema。

### 4. 绑定到 Session 上下文

`SessionPrompt.resolveTools(...)` 把每个 registry 定义转换成 AI SDK `tool({...})`。

每次执行时它都会构造一个 `Tool.Context`，其中包含：

- `sessionID`、`messageID`、`callID`
- 当前 agent 名称
- `extra.model` 中的当前模型元数据
- 当前消息历史
- 用于更新匹配 `MessageV2.ToolPart` 的 `metadata(...)` 回调
- 把权限请求路由到 `Permission.ask(...)` 的 `ask(...)` 回调

这是静态 tool 定义真正变成“带 session 绑定的可执行能力”的边界。

### 5. 执行并返回结果

当模型发出 tool call 时：

1. AI SDK 调用 `SessionPrompt.resolveTools(...)` 生成的 `execute(...)`
2. Opencode 触发 `tool.execute.before` plugin hook
3. 具体 tool 执行 `execute(args, ctx)`
4. 生成的附件被规范化，补齐 part id 与 message/session 关联
5. Opencode 触发 `tool.execute.after` hook
6. 结构化结果返回模型循环

MCP 工具在同一个函数里单独适配，但模式相同，只是额外通过 `ctx.ask(...)` 做显式权限确认。

## 上下游依赖

Upstream:

- `Config`：配置目录发现与依赖安装
- `Plugin`：plugin tool 定义和生命周期 hook
- `Provider` / 当前模型元数据：tool 过滤和 schema transform
- `Permission`：执行门控

Downstream:

- `session/prompt.ts`：执行上下文绑定
- `session/llm.ts`：最终激活 tool 过滤与 provider 交接
- `session/processor.ts`：message-part 状态跟踪
- 通过 AI SDK `streamText(...)` 进入 provider SDK 调用

## 实现细节

- plugin/config tools 会先转换成一等公民 `Tool.Info`，而不是走完全独立的运行时分支。
- tool schema 在发给模型前，会先经过 `ProviderTransform.schema(...)`，因此 tool 暴露面是 provider 感知的。
- `SessionPrompt.resolveTools(...)` 通过 `processor.partFromToolCall(...)` 更新运行中的 tool metadata，从而把标题/元数据变化流进 assistant message 记录。
- `LLM.resolveTools(...)` 还会结合 agent/session 权限与用户级 `tools` 覆盖再做一轮过滤。
- 对 LiteLLM 代理而言，如果历史中含有 tool calls 但当前 tool 集为空，`LLM.stream(...)` 会注入 `_noop` tool，避免代理校验失败。
- 对 `GitLabWorkflowLanguageModel`，`LLM.stream(...)` 会提供 `toolExecutor`，直接复用同一份 tool map，而不只依赖普通 AI SDK tool-call 传输。

## 设计取舍 / 风险

- tool 行为分散在 registry、prompt、LLM 和 processor 四层里，排查一次异常 tool call 往往需要一起看。
- 模型感知过滤提升了兼容性，但也意味着不同模型看到的 tool 表面并不稳定。
- 配置目录工具和 plugin 工具是强大的扩展点，但这也使激活的运行时能力更依赖环境。
- tool metadata 和权限行为依赖 session 级回调，因此哪怕工具业务逻辑看起来简单，它也不是纯函数。

## 待验证

- 是否存在绕过 `Tool.define(...)` 的内置工具，因此跳过统一的参数校验和输出截断包装。
- MCP 工具暴露在普通 CLI 会话中的使用频率，是否远低于某些专门集成场景。
