# 启动调用链

## 触发条件

用户运行 `opencode` CLI，或某个开发脚本直接启动 `packages/opencode/src/index.ts`。

## 起始文件 / 符号

- 安装后的 CLI 包装器：`workspace/source/opencode/packages/opencode/bin/opencode`
- 开发/运行时入口模块：`workspace/source/opencode/packages/opencode/src/index.ts`

## 顺序执行步骤

1. 包元数据把已发布命令名 `opencode` 映射到 `packages/opencode/bin/opencode`。
2. `bin/opencode` 解析平台相关的已安装二进制或缓存可执行文件，并转发 `process.argv`。
3. 在开发模式下，根工作区脚本会绕过这个包装器，直接用 Bun 启动 `packages/opencode/src/index.ts`。
4. `src/index.ts` 安装致命错误处理器，构建 yargs CLI，并注册全局选项和子命令。
5. yargs middleware 完成日志初始化、导出运行时环境标记，并在 `Global.Path.data/opencode.db` 缺失时执行一次性数据库迁移。
6. 控制流进入被选中的命令处理器。
7. 对于 `run` 这类绑定到项目的命令，处理器会调用 `cli/bootstrap.ts`，后者通过 `Instance.provide({ init: InstanceBootstrap, ... })` 包裹执行。
8. `project/bootstrap.ts` 初始化实例级核心子系统，例如 plugins、formatting、LSP、file services、VCS、snapshots，以及 command-executed 的 bus 订阅。
9. 对于 server 模式，`ServeCommand` 调用 `Server.listen(...)`；实例初始化会延迟到请求处理阶段，由 `WorkspaceRouterMiddleware` 调用 `Instance.provide(..., init: InstanceBootstrap)` 完成。

## 状态转换

- 进程级启动：
  - 日志初始化
  - 环境标记导出（`AGENT`、`OPENCODE`、`OPENCODE_PID`）
  - 可选的一次性数据库迁移
- 命令级启动：
  - yargs 解析具体命令
- 实例级启动：
  - `Instance.provide` 建立目录/worktree 上下文
  - `InstanceBootstrap` 初始化项目范围服务

## 外部边界

- `bin/opencode` 处的 OS/package-manager 启动边界
- `src/index.ts` 对应的 Bun 运行时
- 缓存/数据目录与迁移标记对应的文件系统边界
- `Server.listen(...)` 对应的 Bun HTTP server 边界

## 失败 / 分支行为

- 如果 CLI 包装器无法解析已安装二进制，它会以安装错误信息退出。
- 如果 yargs 参数校验失败，常见参数错误会打印帮助信息。
- 致命运行时错误会通过 `FormatError` 格式化；否则会显示一个通用的日志文件路径提示。
- `serve` 与 `run` 等命令不同，因为它会在任何 project instance bootstrap 之前先启动 HTTP server。

## 证据表

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 1 | `workspace/source/opencode/packages/opencode/package.json` | `bin.opencode` | 已发布命令映射到 `./bin/opencode` |
| 2 | `workspace/source/opencode/packages/opencode/bin/opencode` | top-level wrapper script | 解析缓存/平台二进制并转发参数 |
| 3 | `workspace/source/opencode/package.json` | `scripts.dev` | 开发路径直接运行 `packages/opencode/src/index.ts` |
| 4 | `workspace/source/opencode/packages/opencode/src/index.ts` | yargs setup | 全局选项与命令注册 |
| 5 | `workspace/source/opencode/packages/opencode/src/index.ts` | middleware | 日志/环境初始化与 JSON 到 SQLite 迁移 |
| 7 | `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts` | `bootstrap(...)` | 在 instance 上下文中包裹命令执行 |
| 8 | `workspace/source/opencode/packages/opencode/src/project/bootstrap.ts` | `InstanceBootstrap()` | 初始化 plugin/LSP/file/VCS/snapshot 子系统 |
| 9 | `workspace/source/opencode/packages/opencode/src/cli/cmd/serve.ts` | `ServeCommand.handler` | 启动 server 进程 |
| 9 | `workspace/source/opencode/packages/opencode/src/server/router.ts` | `WorkspaceRouterMiddleware` | 请求级 instance bootstrap |

## 待验证

- 除了 `serve` 和 `generate` 之外，哪些子命令会绕过 `cli/bootstrap.ts`。
- 打包后的原生二进制最终是否会委托到同一套 TS 入口逻辑，还是走一条存在启动差异的独立构建产物路径。
