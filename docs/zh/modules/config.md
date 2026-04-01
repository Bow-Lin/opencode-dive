# Config 模块

## 模块职责

config 模块是运行时配置的事实来源，负责：

- `opencode` 核心配置 schema
- 多层配置加载与合并优先级
- 从配置目录发现 plugin / command / agent / skill
- 全局配置与实例级配置访问
- 配置更新与失效处理

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/config/config.ts` | 主配置 schema、加载器、合并逻辑、更新 API 与 service 层 | `Config.Info`, `Config.Service`, `loadGlobal`, `loadInstanceState` |
| `workspace/source/opencode/packages/opencode/src/config/paths.ts` | 配置路径发现、文件读取、JSONC 解析、`{env:...}` / `{file:...}` 替换 | `ConfigPaths.projectFiles`, `ConfigPaths.directories`, `ConfigPaths.parseText` |
| `workspace/source/opencode/packages/opencode/src/config/tui.ts` | TUI 专用配置加载器 | `TuiConfig.get()` 路径加载 |
| `workspace/source/opencode/packages/opencode/src/config/markdown.ts` | 基于 frontmatter 的 command / agent markdown 解析 | `ConfigMarkdown.parse(...)` |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Config.Info` | schema/type | `config.ts` | 规范化后的运行时配置结构 |
| `Config.Service` | service | `config.ts` | 提供 get/update/invalidate/directories 的 Effect service |
| `loadGlobal()` | loader | `config.ts` | 加载用户级全局配置，并迁移遗留 TOML |
| `loadInstanceState(ctx)` | loader | `config.ts` | 合并所有层次后生成实例级有效配置 |
| `mergeConfigConcatArrays(...)` | merge helper | `config.ts` | 合并配置时对 `plugin` 和 `instructions` 数组做追加 |
| `ConfigPaths.projectFiles(...)` | path helper | `paths.ts` | 向上查找到 worktree 根的项目配置文件 |
| `ConfigPaths.directories(...)` | path helper | `paths.ts` | 构建 `.opencode` 资产的配置发现目录 |
| `ConfigPaths.parseText(...)` | parser | `paths.ts` | 先做替换，再解析 JSONC |

## 初始化 / 入口

这个模块以 Effect service 的形式暴露：

- `Config.Service`
- `Config.defaultLayer`

CLI / server 表面会直接消费它，很多子系统也会间接依赖它，例如：

- `agent`
- `provider`
- `plugin`
- `tool/registry`
- `session`
- `skill`
- `file/watcher`
- `lsp`
- `format`

## 主控制流

### 1. 全局配置

`loadGlobal()` 会合并：

1. `Global.Path.config/config.json`
2. `Global.Path.config/opencode.json`
3. `Global.Path.config/opencode.jsonc`

同时，它还会把遗留的 TOML 风格 `Global.Path.config/config` 文件迁移成 JSON。

### 2. 实例级有效配置

`loadInstanceState(ctx)` 大致按下面顺序构建当前实例的有效配置：

1. 从鉴权相关来源拉取远端 well-known config
2. `getGlobal()` 返回的全局配置
3. 来自 `OPENCODE_CONFIG` 的显式文件
4. 通过 `ConfigPaths.projectFiles("opencode", ...)` 发现的项目配置
5. `ConfigPaths.directories(...)` 返回的目录中的 overlay、markdown、plugin 资产
6. 来自 `OPENCODE_CONFIG_CONTENT` 的内联 JSON
7. account service 提供的远端 account/org 配置
8. `managedConfigDir()` 提供的最高优先级管理配置目录
9. 基于环境变量的 permission/autocompact/prune 调整，以及遗留兼容重写

### 3. 发现阶段的副作用

在处理配置目录时，模块还会：

- 加载 markdown commands
- 加载 markdown agents 和 modes
- 加载本地 plugin 脚本
- 在需要时为配置目录触发依赖安装

## 上下游依赖

Upstream:

- `Auth`
- `Account`
- `AppFileSystem`
- 环境变量与进程环境
- project/worktree 实例上下文

Downstream:

- `cli/network.ts` 中的网络 / server 配置解析
- `session/instruction.ts` 中的 instruction 加载
- `tool/registry.ts` 中的 tool 可用性
- `provider/provider.ts` 中的 provider/model 配置
- `agent/agent.ts` 中的 agent 行为与权限

## 实现细节

- 配置文本在 JSONC 解析前支持 `{env:VAR}` 和 `{file:path}` 替换。
- 接受带尾逗号的 JSONC。
- 来自配置文件的 plugin 路径会被规范化成 file URL。
- `plugin` 和 `instructions` 数组采用追加合并，而不是覆盖语义。
- 遗留 `tools` 配置会被翻译成权限规则。
- 遗留 `mode` 条目会被并入 `agent` 条目。
- 全局配置失效时会释放所有实例，并发出全局 disposed 事件。

## 设计取舍 / 风险

- 配置加载同时混合了纯解析和远端拉取、依赖安装等副作用，因此功能强，但理解有效配置管线并不轻松。
- 配置来源非常多，优先级出错是现实的调试风险。
- 模块既处理类型化配置，又负责 command / agent / plugin 的发现逻辑，职责边界较宽。

## 待验证

- 在真实仓库中，项目级 `.opencode/` 目录 overlay 与最近的 `opencode.json[c]` 文件之间的精确优先级关系。
- `managedConfigDir()` 是否总是设计成最终硬覆盖，还是某些运行时状态仍能在后面部分绕过它。
