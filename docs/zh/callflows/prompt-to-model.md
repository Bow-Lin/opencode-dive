# Prompt 到模型的调用链

## 触发条件

某个 session mutation 端点或 CLI 命令要求 Opencode 将一条 prompt 发送给模型，通常经由 `SessionPrompt.prompt(...)`，或基于同一服务实现的 command/shell 变体。

## 起始文件 / 符号

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- 关键符号：
  - `SessionPrompt.prompt`
  - `SessionPrompt.createUserMessage`
  - internal `getModel(...)`

## 顺序执行步骤

1. 某个调用方选择或创建一个 session，然后直接调用 `SessionPrompt.prompt(...)`，或通过 server route 间接调用它。
2. `SessionPrompt.createUserMessage(...)` 解析最终生效的 agent 和 model：
   - 显式传入的 model
   - 绑定在 agent 上的 model
   - 上一次 session 使用的 model
   - 或 `Provider.defaultModel()`
3. `SessionPrompt` 通过 `provider.getModel(providerID, modelID)` 校验该模型。
4. prompt 管线组装用户消息 part、instructions、system prompt 片段以及 session history。
5. `SessionPrompt` 把生成/流式处理委托给 `LLM.stream(...)`。
6. `LLM.stream(...)` 会解析：
   - `Provider.getLanguage(input.model)`
   - `Config.get()`
   - `Provider.getProvider(input.model.providerID)`
   - `Auth.get(input.model.providerID)`
7. `Provider.getLanguage(...)` 解析或缓存一个由 SDK 支撑的语言模型实例，底层可能使用内置的 provider 实现，也可能动态加载。
8. `ProviderTransform` 准备 provider 特定的消息与选项变换。
9. 调用 AI SDK 的 `streamText(...)`，传入：
   - model
   - 转换后的 messages
   - provider options
   - active tools
   - headers 和 retries
10. 流式事件返回给 `SessionPrompt`，随后它继续驱动会话循环和后续处理。

## 状态转换

- 会话用户消息以确定的 agent/model 元数据被创建
- 对该条消息而言，模型选择被固定下来
- provider/model 元数据被解析为可执行的语言模型实例
- 下游循环开始消费模型的流式输出

## 外部边界

- `Provider.getLanguage(...)` 处的 provider SDK 边界
- AI SDK 调用内部的上游 provider HTTP 边界
- 通过已存储 API key 或 OAuth access token 形成的鉴权边界

## 失败 / 分支行为

- 缺失 provider/model 会产生 `Provider.ModelNotFoundError`；`SessionPrompt` 会尽量附带建议，把它转换成 session error event。
- 显式 `small` 任务会走 `Provider.getSmallModel(...)` / `ProviderTransform.smallOptions(...)`。
- provider 特定的鉴权或传输行为可能改变 headers、base URL、响应 API 或流式处理行为。

## 证据表

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 2 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `createUserMessage(...)` | 为新用户消息解析 agent 和 model |
| 3 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `getModel(...)` | 校验选中的 provider/model |
| 5 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `LLM.stream(...)` call sites | 切入基于 provider 的生成调用 |
| 6 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | `LLM.stream(...)` | 解析 provider/config/auth 依赖 |
| 7 | `workspace/source/opencode/packages/opencode/src/provider/provider.ts` | `getLanguage(...)` | 解析缓存/内置/动态 SDK 模型 |
| 8 | `workspace/source/opencode/packages/opencode/src/provider/transform.ts` | `ProviderTransform.*` | provider 特定的消息/选项整形 |
| 9 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | `streamText(...)` | 最终模型调用边界 |

## 待验证

- 长时间运行的会话中，模型流式输出与工具执行循环之间的精确事件顺序。
- 是否有部分 provider 绕过标准 `sdk.languageModel(...)`，从而实质性改变下游行为。
