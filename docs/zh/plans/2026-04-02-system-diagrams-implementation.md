# 系统图集实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 Opencode 增加一组双语、叙事型的 Mermaid 系统图，并从主文和架构文档中接入这些图。

**Architecture:** 每种语言各创建一页专门的图集页面，包含同一组 7 张图，解释文字使用对应语言，但代码锚点和图的结构保持一致。然后更新主文与架构文档，让读者能从文字叙事自然跳转到视觉附录。

**Tech Stack:** Markdown、Mermaid（`flowchart`、`sequenceDiagram`、`stateDiagram-v2`），以及本仓库现有的双语文档。

---

### Task 1: 创建英文图集页

**Files:**
- Create: `docs/en/system-diagrams.md`

**Step 1: 补页面定位说明**

写一段简短引言，说明：

- 这页为什么存在，
- 应该怎么阅读这些图，
- 它与 `architecture.md`、`modules/`、`callflows/` 的关系。

**Step 2: 加入已确认的 7 张图**

按顺序加入下面这些 Mermaid 图：

1. system overview
2. startup and entry flow
3. end-to-end request sequence
4. runtime orchestration core
5. tool execution sequence
6. session lifecycle state machine
7. extension architecture

**Step 3: 加上代码锚点**

每张图后面补一小段 “Primary code anchors”，指向最相关的源码文件。

### Task 2: 创建中文图集页

**Files:**
- Create: `docs/zh/system-diagrams.md`

**Step 1: 镜像英文结构**

保持与英文页相同的图顺序和 Mermaid 结构。

**Step 2: 自然翻译说明文字**

标题和代码锚点保持对齐，但周围说明文字要写成自然中文，而不是逐句硬翻。

### Task 3: 从架构文档接入图集

**Files:**
- Modify: `docs/en/architecture.md`
- Modify: `docs/zh/architecture.md`

**Step 1: 在前部加入显眼跳转**

增加一小段提示，告诉读者可在 `system-diagrams.md` 查看可视化配套图。

**Step 2: 控制改动范围**

不要重写架构文档本身，只补足导航能力。

### Task 4: 从博客主文接入图集

**Files:**
- Modify: `docs/en/blog/opencode-deep-dive.md`
- Modify: `docs/zh/blog/opencode-deep-dive.md`

**Step 1: 增加图集引用**

从下面这些位置之一接入图集：

- 阅读方式 / 阅读策略段落
- “接下来读什么” 段落

**Step 2: 保持主文节奏**

图集链接应被呈现为配套资源，而不是打断叙事的岔路。

### Task 5: 验证并提交

**Files:**
- 仅验证

**Step 1: 检查 markdown diff**

运行：

```bash
git diff --check
```

预期：没有输出。

**Step 2: 检查文件是否存在**

运行：

```bash
find docs/en -maxdepth 2 -type f | sort
find docs/zh -maxdepth 2 -type f | sort
```

预期：两棵树都包含 `system-diagrams.md`。

**Step 3: 提交**

```bash
git add docs/en docs/zh
git commit -m "docs: add bilingual system diagrams"
```
