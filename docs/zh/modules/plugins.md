# Plugins / Skills 模块

## 模块职责

这个固定版本中的扩展系统不是单一机制，而是混合式结构。它包括：

- 注册运行时 hook 的 server plugins，
- 扩展终端 UI 壳层的 TUI plugins，
- 以及通过 system prompt、command 列表和 `skill` tool 暴露的可复用技能包。

这些机制共同负责：

- 从配置、文件系统和远程来源发现扩展产物，
- 加载并校验扩展入口点，
- 把 hook 或内容注入运行时流程，
- 并强制执行兼容性和权限约束。

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/plugin/index.ts` | server plugin 服务、hook 加载与触发执行 | `Plugin.Service`, `applyPlugin(...)`, `trigger(...)` |
| `workspace/source/opencode/packages/opencode/src/plugin/loader.ts` | plugin 的 plan/resolve/load 流水线 | `PluginLoader.plan`, `resolve`, `load` |
| `workspace/source/opencode/packages/opencode/src/plugin/shared.ts` | plugin spec 解析、入口点解析、兼容性规则 | `parsePluginSpecifier`, `checkPluginCompatibility`, `readV1Plugin` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/plugin/runtime.ts` | 独立的 TUI plugin runtime 与激活模型 | `resolveExternalPlugins`, `activatePluginEntry`, `load(api)` |
| `workspace/source/opencode/packages/opencode/src/skill/index.ts` | skill 发现与可用性过滤 | `Skill.Service`, `loadSkills(...)`, `available(...)` |
| `workspace/source/opencode/packages/opencode/src/skill/discovery.ts` | 远程 skill 索引拉取与缓存 | `Discovery.pull(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/skill.ts` | 运行时 skill 加载 tool | `SkillTool` |
| `workspace/source/opencode/packages/opencode/src/command/index.ts` | skill 到 command 的暴露路径 | 遍历 `skill.all()` 并添加 `source: "skill"` command |
| `workspace/source/opencode/packages/opencode/src/session/system.ts` | 注入到 system prompt 中的 skill 清单 | `SystemPrompt.skills(...)` |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Plugin.Service` | service | `plugin/index.ts` | 服务端 plugin 注册表与 hook 触发表面 |
| `Plugin.trigger(name, input, output)` | hook runner | `plugin/index.ts` | 按顺序执行某个扩展点的 hook 链 |
| `PluginLoader.resolve(...)` | resolver | `plugin/loader.ts` | 为 `server` 或 `tui` plugins 解析安装目标与入口点 |
| `checkPluginCompatibility(...)` | validator | `plugin/shared.ts` | 对 npm plugins 强制执行 `engines.opencode` 兼容性 |
| `Skill.Service` | service | `skill/index.ts` | 已发现的 skill 注册表 |
| `Skill.available(agent)` | filter | `skill/index.ts` | 按权限过滤后的可用 skill 列表 |
| `Discovery.pull(url)` | loader | `skill/discovery.ts` | 从 `index.json` 下载远程 skill 包 |
| `SkillTool` | tool | `tool/skill.ts` | 把加载后的 skill 内容注入运行时上下文 |

## 初始化 / 入口

### Server Plugins

`Plugin.init()` 会落实按实例隔离的 plugin 缓存。初始化过程中它会：

1. 创建一个绑定到 `Server.Default().fetch(...)` 的内部 SDK client，
2. 加载内置 server plugins，
3. 从 `cfg.plugin` 解析配置声明的外部 plugins，
4. 运行每个 plugin factory 并得到 hook 对象，
5. 调用可选的 `config(...)` hooks，
6. 把所有 hooks 订阅到 bus 事件上。

### TUI Plugins

TUI plugins 是 `cli/cmd/tui/plugin/runtime.ts` 中的一套独立 runtime。它们在 TUI 启动时加载，而不是在 server/plugin service 初始化时加载。

### Skills

`Skill.Service` 会通过扫描下面这些位置来初始化按实例隔离的 skill 注册表：

- `~/.claude` 和 `~/.agents` 这类全局外部目录，
- 向上搜索 project 的外部目录，
- `Config.directories()` 给出的配置目录，
- 显式声明的 `cfg.skills.paths`，
- 以及通过 `Discovery.pull(...)` 拉取的远程 `cfg.skills.urls`。

## 主控制流程

### 1. 解析 Plugin 产物

对于外部 plugins，`PluginLoader` 会执行一个分阶段流水线：

1. 通过 `Config.pluginSpecifier(...)` 规范化配置项，
2. 从文件路径或 npm package 解析安装目标，
3. 推导 `server` 或 `tui` 的入口点，
4. 通过 `engines.opencode` 校验兼容性，
5. 导入模块。

兼容性约束包括：

- 已弃用的“内置替代包”会被跳过，
- 若 npm plugin 支持的 opencode 版本范围不匹配，则可能被拒绝，
- 路径型 plugin 必须以现代 plugin 形状显式暴露 IDs。

### 2. 注册运行时 Hooks

Server plugins 最终会产出 `Hooks` 对象。

这些 hooks 会按确定顺序存储，并通过 `Plugin.trigger(...)` 顺序触发。

当前在运行时里可以观察到的 hook 表面包括：

- `tool.definition`
- `tool.execute.before`
- `tool.execute.after`
- `experimental.chat.messages.transform`
- 与 compaction/chat/system 相关的 hooks
- 通用的 `event` 与 `config` 通知

### 3. 发现 Skills

Skills 是以 `SKILL.md` 为核心的 Markdown 指令包。

`Skill.loadSkills(...)` 会解析 frontmatter 与正文，按 skill name 去重，记录 base 目录，并把每个 skill 暴露为：

- 结构化的 `Skill.Info`，
- 按权限过滤后的可用 skill 列表，
- command 暴露来源，
- system prompt 中的 skill 清单来源，
- 以及可由 `SkillTool` 在运行时加载的内容。

### 4. 把 Skills 暴露进运行时

Skills 通过三条路径影响运行时：

1. `SystemPrompt.skills(agent)` 在模型 prompt 中公布可用 skills。
2. `Command.Service` 会把每个 skill 暴露为一个 `source: "skill"` command，前提是没有 command 名冲突。
3. `SkillTool` 按需加载完整 skill 内容，申请 `skill` 权限，并把内容和采样后的文件列表注入会话。

### 5. 单独激活 TUI Plugins

TUI plugins 使用同一套共享的 plugin spec 解析原语，但它们会在 UI 专属 runtime 中被激活，并带有：

- plugin 元数据跟踪，
- 本地启用/禁用状态，
- theme 安装，
- route/slot/keybind 注册，
- 确定性的激活顺序。

它与 server plugin hooks 有关联，但不是同一套机制。

## 上下游依赖

上游：

- 提供 `plugin` 规格与 skill path/URL 的 `Config`
- 文件系统 / 全局 home / project 目录
- `Flag.OPENCODE_PURE` 等 feature flags

下游：

- 调用 `Plugin.trigger(...)` 的运行时模块
- fanout 到 plugins 的 `Bus` 事件
- 用于 skill 暴露的 `Command`、`SystemPrompt` 和 `SkillTool`
- 负责 UI 侧扩展激活的 TUI plugin runtime

## 实现细节

- Server plugins 和 TUI plugins 共享 spec/entrypoint 解析逻辑，但运行在不同 runtime 中。
- Server plugin 的 hook 执行刻意保持顺序化，以保证执行顺序可预测。
- `Flag.OPENCODE_PURE` 会同时禁用 server 和 TUI plugin runtimes 中的外部 plugins。
- 远程 skills 通过基于索引的缓存拉取，而不是任意递归远程浏览。
- 重复的 skill name 会以 warning 方式容忍，后加载的定义会覆盖内存 map 中更早的定义。

## 设计取舍 / 风险

- 扩展表面很强，但也分散在 hooks、TUI plugins、skills、commands、MCP prompts 和 config overlays 之间。
- 确定性的顺序化 plugin 执行有利于推理，但在 plugin 很多时可能拖慢启动。
- Skills 在运维上比 plugins 简单，但它们仍然会影响 prompt 行为、command 列表和权限表面，因此并不只是“文档”。
- Server 与 TUI 共用 plugin 解析逻辑减少了重复，但两套 plugin runtime 的存在也意味着扩展行为强烈依赖上下文。

## 待验证

- 哪些 plugin hooks 可以被视为稳定的公开扩展合约，哪些仍属于内部实验性 hooks。
- 在日常工作流里，远程 skill URLs 相比本地 skill 目录究竟有多常用。
