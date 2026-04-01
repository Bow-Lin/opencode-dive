# Provider 模块

## 模块职责

provider 模块负责：

- 构建当前激活的 provider registry
- 合并内置目录、配置、鉴权和 plugin 带来的模型元数据
- 选择默认模型和 small model
- 为选中的模型解析 SDK / language model 实例
- 向 LLM 层暴露 provider 感知的 option transform

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/provider/provider.ts` | 主 provider registry、模型查找、SDK 解析、默认/小模型选择 | `Provider.Service`, `getModel`, `getLanguage`, `defaultModel` |
| `workspace/source/opencode/packages/opencode/src/provider/auth.ts` | provider 专属鉴权方式发现与 OAuth/API token 流程 | `ProviderAuth.Service` |
| `workspace/source/opencode/packages/opencode/src/provider/transform.ts` | provider/model 专属 option 与 message 归一化 | `ProviderTransform.options`, `ProviderTransform.smallOptions`, `ProviderTransform.message` |
| `workspace/source/opencode/packages/opencode/src/session/llm.ts` | 从选中的 provider/model 进入 `streamText(...)` 的运行时桥梁 | `Provider.getLanguage(...)` |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Provider.Info` | schema/type | `provider.ts` | provider 级元数据及模型映射 |
| `Provider.Model` | schema/type | `provider.ts` | 标准化后的模型元数据、能力、成本与限制 |
| `Provider.Service` | service | `provider.ts` | provider / model 的查询与 registry API |
| `getModel(providerID, modelID)` | lookup | `provider.ts` | 获取已校验模型，找不到时抛出带建议的错误 |
| `getLanguage(model)` | resolver | `provider.ts` | 创建或缓存 AI SDK language model 实例 |
| `defaultModel()` | selector | `provider.ts` | 从 config、最近使用记录或排序后的默认值中选模型 |
| `getSmallModel(providerID)` | selector | `provider.ts` | 为辅助任务选择更便宜的小模型 |
| `ProviderTransform.*` | transform helpers | `transform.ts` | 为下游 SDK 调用规范化消息和 provider 选项 |

## 初始化 / 入口

provider 模块通过 `Provider.defaultLayer` 实例化，依赖：

- `Config.defaultLayer`
- `Auth.defaultLayer`

它的主要运行时消费者是 `SessionPrompt` / `LLM.stream`，但也通过 server routes 和 CLI/provider 命令暴露给外层。

## 主控制流

### 1. 构建 Provider Registry

`Provider.Service` 的状态构建大致经历这条序列：

1. 通过 `ModelsDev.get()` 加载基础 provider/model 目录
2. 把配置中的 provider/model 覆盖合并进去
3. 激活从环境变量发现的 provider
4. 激活带有已存储 API 鉴权的 provider
5. 用鉴权感知的 plugin 修补 provider 选项
6. 为特殊 provider 安装自定义 loader
7. 通过 enabled/disabled、white/blacklist、alpha/deprecated 等规则过滤 provider 和模型
8. 对 GitLab 等特定 provider 额外发现模型

### 2. 解析模型元数据

provider 激活之后：

- `getModel(...)` 返回标准化后的 `Provider.Model`
- 模型元数据包含：
  - API 包和上游模型 id
  - capabilities
  - cost / limits
  - headers / options
  - 派生变体

### 3. 解析 Language Model 实例

`getLanguage(model)` 会：

1. 从 config / auth / model 元数据构建 provider 专属选项
2. 解析或创建底层 AI SDK 实例
3. 当 provider 需要非默认实例化方式时应用自定义 loader
4. 按 `providerID/modelID` 缓存结果 language model

## 上下游依赖

Upstream:

- `Config`
- `Auth`
- `Plugin`
- `ModelsDev`
- 环境变量

Downstream:

- `session/prompt.ts` 中的模型选择
- `session/llm.ts` 中真正的 `streamText(...)` 调用
- `server/routes/provider.ts` 中的 provider 列表和 OAuth 流程

## 实现细节

- provider 激活是多来源的：catalog + config + env + auth + plugin loader。
- 当 provider package 已知时会使用内置 SDK；未知时则可能动态安装 / 导入包。
- `defaultModel()` 优先显式配置，其次最近模型历史，最后才是排序后的 provider 默认值。
- `getSmallModel()` 依据 provider 家族启发式选择，也可由 `cfg.small_model` 覆盖。
- `ProviderTransform` 承载了大量 provider 兼容逻辑，包括消息归一化、缓存提示和 provider options。

## 设计取舍 / 风险

- registry 构建同时混合了目录读取、鉴权激活、plugin 修补和动态 SDK 加载，灵活但相当密集。
- provider 专属行为分散在 `provider.ts` 与 `transform.ts`，排查单个 provider 往往要同时阅读两层。
- 动态安装 / 导入增强了扩展性，但也让运行时行为更受环境影响。

## 待验证

- 真实用户路径里最常见的是哪些 provider，哪些只是边缘集成。
- 是否存在某些 provider 专属 loader，不只是 option 归一化，而会实质改变 tool-calling 语义。
