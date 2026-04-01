# CLI 模块

## 模块职责

CLI 层是用户可见的外壳，负责命令选择、参数解析、本地进程初始化，以及把控制权交给后端运行时。在当前固定版本里，它主要负责：

- 用 yargs 解析 `argv`
- 安装全局 CLI middleware 和进程级行为
- 把请求分发给具体命令处理器
- 规范化 prompt、文件、session 标志等命令输入
- 把 shell 交互桥接到实例作用域运行时 API，或内部 control-plane SDK / server 边界

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/index.ts` | 顶层 CLI 解析器、middleware 与命令注册 | `yargs(...)`, `.middleware(...)`, `.command(...)`, `cli.parse()` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/cmd.ts` | yargs 命令的轻量类型包装 | `cmd(...)` |
| `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts` | CLI 命令的实例级 bootstrap 辅助函数 | `bootstrap(directory, cb)` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts` | 主要的非 TUI 交互命令 | `RunCommand`, `execute(sdk)`, 本地 `Server.Default().fetch(...)` 桥接 |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/session.ts` | 更直接的 session 管理命令 | `SessionListCommand`, `SessionDeleteCommand` |
| `workspace/source/opencode/packages/opencode/src/cli/ui.ts` | 非 TUI 流程的基础终端输出样式 | `UI.println`, `UI.error`, `UI.logo` |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `cli` | parser instance | `index.ts` | 全局 yargs CLI 入口 |
| `cmd(...)` | helper | `cmd.ts` | 透传类型化命令描述 |
| `bootstrap(directory, cb)` | helper | `bootstrap.ts` | 进入实例上下文并在结束后释放 |
| `RunCommand` | command | `run.ts` | 把 prompt/command 输入送入运行时并渲染流式输出 |
| `TuiThreadCommand` | command | `tui/thread.ts` | 在 local/worker/server 模式下启动 TUI |
| `AttachCommand` | command | `tui/attach.ts` | 连接到已运行的 server |

## 初始化 / 入口

`src/index.ts` 是原始 CLI 边界：

1. 从 `process.argv` 构建 yargs parser
2. 安装全局日志 / 环境 / migration middleware
3. 注册命令模块
4. 调用 `await cli.parse()`

这是原始 shell 输入第一次被转成结构化命令意图的地方。

## 主控制流

### 1. 解析并规范化 shell 输入

顶层 `index.ts` 负责处理：

- `--help`、`--version`、`--print-logs`、`--log-level`、`--pure`
- 一次性的数据库迁移
- 致命错误格式化和退出行为

随后各命令模块在 yargs `builder` 中声明自己的参数。

### 2. 交给具体命令处理器

yargs 选中具体 handler 之后，原始 `argv` 只会继续被处理到这些步骤：

- 组装消息文本
- 解析 `--dir` / cwd 行为
- 校验 session / fork 约束
- 解析文件输入
- 必要时把 stdin 和 prompt 文本拼接起来

之后控制就会进入运行时交互。

### 3. 选择运行时桥接方式

CLI 主要有两种桥接模式。

直接的实例作用域运行时访问：

- `session list/delete` 之类的命令会调用 `bootstrap(process.cwd(), async () => ...)`
- 然后在实例上下文内直接使用运行时 service

SDK / control-plane 访问：

- `run.ts` 会创建 `OpencodeClient`
- 本地模式下，它把 SDK 指向进程内的 `Server.Default().fetch(...)`
- attach 模式下，则指向远端 server URL
- 然后通过 `sdk.session.*`、`sdk.event.subscribe()`、`sdk.permission.reply()` 等 API 交互

### 4. 渲染非 TUI 输出

`run.ts` 是构建在 SDK 之上的 CLI 适配层：

- 订阅运行时事件
- 把 tool 完成结果和文本输出格式化为终端展示
- 在纯 CLI 模式下自动拒绝权限请求
- 当 `session.status` 回到 `idle` 时退出

因此它既不同于原始 yargs 解析，也不同于更完整的 TUI 壳层。

## 上下游依赖

Upstream:

- OS shell / `process.argv`
- stdin/stdout/stderr

Downstream:

- 通过 `bootstrap(...)` 进入 `Instance.provide(..., init: InstanceBootstrap)`
- `Server.Default()` 提供进程内 control-plane 访问
- `@opencode-ai/sdk/v2` 提供 session/config/event API
- `UI` 辅助非 TUI 输出
- TUI 命令入口提供更丰富的交互壳

## 实现细节

- `cmd.ts` 几乎没有增加抽象，真正的命令系统仍然是 yargs。
- `index.ts` 在 `finally` 中强制 `process.exit()`，体现了避免子进程悬挂的务实取向。
- 本地 CLI 运行时往往仍然会经过进程内 server / SDK 路径，而不是直接调用 session service。
- 因此 `run.ts` 更像是后端运行时的终端客户端，而不是单体式命令实现。

## 设计取舍 / 风险

- 某些命令里 CLI 更像薄传输层，另一些命令里又承担较丰富的事件渲染职责，因此抽象边界随命令而变化。
- 把本地执行也路由到内部 server / SDK 路径，有助于与远端模式保持一致，但增加了间接层。
- `index.ts` 中的全局 middleware 同时混合了 CLI 启动、存储迁移和进程环境变量修改等关注点。

## 待验证

- 哪些较少使用的命令仍然完全绕过内部 SDK / server 桥接，只走直接 runtime 调用。
- 后续命令增长是否会继续偏向 SDK 中介路径，而不是直接 service 调用。
