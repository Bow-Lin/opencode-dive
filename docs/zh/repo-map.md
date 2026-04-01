# 仓库地图

## 分析仓库

这个仓库是分析控制平面，不是 Opencode 源码仓本身。

### 顶层目录

- `docs/en/`：英文正式产物
- `docs/zh/`：中文正式产物
- `tasks/`：有边界的分析任务
- `templates/`：稳定输出模板
- `reports/`：按轮次组织的分析发现
- `scripts/`：辅助自动化脚本
- `workspace/source/`：目标源码检出目录
- `workspace/notes/`：临时笔记

## 目标源码仓地图

被固定版本的目标源码仓是一个 Bun/TypeScript monorepo，根目录位于 `workspace/source/opencode`。

### 元数据

- 包与构建文件：
  - `workspace/source/opencode/package.json`
  - `workspace/source/opencode/bunfig.toml`
  - `workspace/source/opencode/tsconfig.json`
  - `workspace/source/opencode/turbo.json`
  - `workspace/source/opencode/sst.config.ts`
  - `workspace/source/opencode/bun.lock`
- 应用/运行时入口：
  - 根目录 dev 脚本指向 `packages/opencode/src/index.ts`
  - package bin 入口为 `packages/opencode/bin/opencode`
- 测试目录：
  - `workspace/source/opencode/packages/opencode/test`
  - `packages/app`、`packages/enterprise` 等包内的测试或 e2e 目录
- 配置文件：
  - 根目录 `package.json`、`bunfig.toml`、`tsconfig.json`、`turbo.json`
  - 仓库本地的 `.opencode/opencode.jsonc` 与 `.opencode/tui.json`

### 顶层源码区域

| 路径 | 职责 | 置信度 | 说明 |
| --- | --- | --- | --- |
| `workspace/source/opencode/packages/opencode` | 编码代理的主要 CLI / server / runtime 包 | High | 包含 `bin/`、`src/`、`migration/` 和密集测试 |
| `workspace/source/opencode/packages/app` | Web 应用客户端 | High | monorepo 中独立的 app 包 |
| `workspace/source/opencode/packages/web` | 官网/营销站点及相关资源 | Medium | 与 `app` 区分开的独立包 |
| `workspace/source/opencode/packages/desktop` | 桌面应用壳层 | High | 基于 Tauri |
| `workspace/source/opencode/packages/desktop-electron` | Electron 桌面变体 | High | 单独的桌面运行时打包路径 |
| `workspace/source/opencode/packages/console` | 面向 console 的界面和后端组件 | Medium | 继续拆成 `app`、`core`、`function`、`mail`、`resource` |
| `workspace/source/opencode/packages/plugin` | 插件 SDK / runtime 支持包 | High | 除了这个工作区包，`packages/opencode/src/plugin` 中也有核心插件逻辑 |
| `workspace/source/opencode/packages/sdk/js` | JavaScript SDK | High | 供外部集成使用的 SDK 表面 |
| `workspace/source/opencode/packages/ui` | 共享 UI 组件 | High | 共享组件包 |
| `workspace/source/opencode/packages/util` | 共享工具函数 | High | 通用辅助库 |
| `workspace/source/opencode/script` | 仓库自动化与发布脚本 | High | 发布、changelog、统计等 TypeScript 脚本 |
| `workspace/source/opencode/infra` | 基础设施定义 | High | 面向 SST 的部署定义 |
| `workspace/source/opencode/github` | GitHub action / package 集成 | Medium | 独立包，有自己的 `package.json` |
| `workspace/source/opencode/.opencode` | 仓库本地 agent 命令、工具、主题和词汇表 | High | 运维配置与自举资产，不是主运行时源码 |

### 主包地图：`packages/opencode/src`

主包已经按子系统目录做了拆分，包括：

- `agent`
- `bus`
- `cli`
- `command`
- `config`
- `control-plane`
- `mcp`
- `plugin`
- `project`
- `provider`
- `server`
- `session`
- `skill`
- `storage`
- `tool`
- `worktree`

这说明核心分析目标应该是 `packages/opencode/src`，其余工作区包更多提供客户端、SDK 和部署表面。

## 关键入口

在更细的入口追踪之前，仓库盘点阶段已经识别出这些入口候选：

| 文件 | 符号 | 角色 | 已验证 |
| --- | --- | --- | --- |
| `workspace/source/opencode/package.json` | `scripts.dev` | 根目录 dev 命令把执行引到主包 | Yes |
| `workspace/source/opencode/packages/opencode/package.json` | `bin.opencode` | 发布后的 CLI 二进制映射 | Yes |
| `workspace/source/opencode/packages/opencode/src/index.ts` | `TBD` | 可能的运行时 / dev 入口模块 | Pending |
| `workspace/source/opencode/packages/opencode/bin/opencode` | `TBD` | CLI 启动脚本 | Pending |
