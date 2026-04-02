# Session Prompt 分析实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `session/prompt.ts` 增加一篇独立的双语分析文档，并从现有 runtime 模块文档中接入它。

**Architecture:** 每种语言各新增一篇深挖文档，把 `prompt.ts` 解释成运行时编排核心，而不是提示词模板文件。然后更新现有 runtime 文档，保留高层摘要，但把读者引到新的文件级分析文档。

**Tech Stack:** Markdown、现有双语模块文档，以及 `workspace/source/opencode/packages/opencode/src/session/prompt.ts` 里的代码锚点。

---

### Task 1: 创建英文深挖文档

**Files:**
- Create: `docs/en/modules/session-prompt.md`

**Step 1: 解释命名误导**

开篇先说明为什么 `prompt.ts` 这个文件名容易让人误解。

**Step 2: 解释控制权**

记录 `SessionPrompt` 真正掌握的职责：

- 从 routes / SDK 接管请求
- 创建 user message
- 持有 session loop
- 解析 model / tools / system prompt
- 编排 command 与 shell
- 处理取消和 busy-state 集成

**Step 3: 解释委托关系**

说明它把哪些事情委托给：

- `Session`
- `SessionProcessor`
- `LLM`
- `ToolRegistry`
- `SessionStatus`
- `SessionCompaction`

**Step 4: 补文件结构导读**

按主要内部区块和导出 API 说明文件结构：

- service wiring
- runner cache 与并发控制
- tool 解析
- subtask / shell 辅助逻辑
- `prompt`
- `runLoop`
- `loop`
- `shell`
- `command`
- 导出的输入 schema 与包装器

### Task 2: 创建中文深挖文档

**Files:**
- Create: `docs/zh/modules/session-prompt.md`

**Step 1: 镜像英文结构**

保持与英文文档相同的章节顺序和代码锚点。

**Step 2: 自然翻译**

用自然中文表达，但保持相同的技术含义。

### Task 3: 更新 runtime 模块文档

**Files:**
- Modify: `docs/en/modules/runtime.md`
- Modify: `docs/zh/modules/runtime.md`

**Step 1: 增加一段摘要提示**

明确说明 `prompt.ts` 是 orchestration core，并在 `session-prompt.md` 中有更细的专题分析。

**Step 2: 保持 runtime 文档简洁**

不要把新文档内容复制过来，只增加导航性的补充。

### Task 4: 验证并提交

**Files:**
- 仅验证

**Step 1: 检查 markdown diff**

运行：

```bash
git diff --check
```

预期：没有输出。

**Step 2: 检查改动边界**

运行：

```bash
git status --short
```

预期：只出现新增计划文档、新增专题文档和 runtime 文档更新。

**Step 3: 提交**

```bash
git add docs/en docs/zh
git commit -m "docs: add session prompt deep dive"
```
