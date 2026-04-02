# Session Prompt 分析设计说明

> 这份文档记录了 `prompt.ts` 专题分析文档的已确认设计。

## 目标

新增一篇聚焦文档，解释为什么 `workspace/source/opencode/packages/opencode/src/session/prompt.ts` 这个文件名具有误导性，以及为什么它实际上是 Opencode 的运行时编排核心。

## 读者问题

`prompt.ts` 这个名字很容易让人以为它主要存放 prompt 模板或提示词文本。但实际情况是，这个文件掌握了交互式 session 编排、控制权移交、loop 策略、tool 绑定、command 展开和取消逻辑。

## 选定产物形态

同时采用这两种产物：

- 一篇独立深挖文档：
  - `docs/en/modules/session-prompt.md`
  - `docs/zh/modules/session-prompt.md`
- 在 runtime 模块文档中保留摘要与跳转：
  - `docs/en/modules/runtime.md`
  - `docs/zh/modules/runtime.md`

## 选定写法

采用混合写法：

1. 先讲控制权和职责边界，
2. 再讲文件内部结构与主要导出入口。

## 必须回答的问题

文档必须回答：

- 为什么 `prompt.ts` 这个名字容易误导，
- `SessionPrompt` 到底掌握哪些控制权，
- 它把哪些事情委托给 `Session`、`SessionProcessor`、`LLM`、`ToolRegistry`、`SessionStatus`，
- `prompt`、`loop`、`runLoop`、`shell`、`command` 之间是什么关系，
- 以及为什么把这么多运行时策略集中在一个文件里会带来复杂度风险。
