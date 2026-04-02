# 系统图集设计说明

> 这份文档记录了本次双语 Opencode 系统图集的已确认设计。

## 目标

增加一组面向读者的系统图，让 Opencode 的结构能被更快地视觉化理解，同时保持这些图与仓库里已有的、基于代码证据的架构分析一致。

## 目标读者

主要面向想在阅读完整模块附录和调用链附录之前，先快速把握 Opencode 设计思路的中高级工程师。

## 选定结构

使用独立的双语图集页面：

- `docs/en/system-diagrams.md`
- `docs/zh/system-diagrams.md`

并从下面这些文档跳转过去：

- `docs/en/architecture.md`
- `docs/zh/architecture.md`
- `docs/en/blog/opencode-deep-dive.md`
- `docs/zh/blog/opencode-deep-dive.md`

## 选定表达形式

采用“叙事型图集”，而不是平铺所有模块的静态大地图。

图的类型混合使用：

- `flowchart`：表达结构关系和控制权边界
- `sequenceDiagram`：表达请求与 tool 执行时序
- `stateDiagram-v2`：表达 session 状态演化

## 已确认的图单

最终页面包含 7 张图：

1. 系统总览图
2. 启动与入口图
3. 用户请求端到端时序图
4. Runtime 编排核心图
5. Tool 执行时序图
6. Session 生命周期状态图
7. 扩展系统图

## 范围边界

这组图应该：

- 解释主要运行时关系，
- 强化现有架构叙事，
- 把读者继续引向模块附录和调用链附录，
- 并保持与代码实现的锚定关系。

它不应该：

- 试图把 monorepo 的每个 package 都画出来，
- 取代文字分析文档，
- 或退化成一张难以阅读的“万物总图”。
