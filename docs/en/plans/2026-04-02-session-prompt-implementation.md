# Session Prompt Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a dedicated bilingual analysis doc for `session/prompt.ts` and connect it from the runtime module docs.

**Architecture:** Create one deep-dive module doc per language that treats `prompt.ts` as the runtime orchestration core rather than a prompt-template file. Then update the existing runtime docs so they keep the high-level summary but link readers to the dedicated file analysis.

**Tech Stack:** Markdown, existing bilingual module docs, code anchors from `workspace/source/opencode/packages/opencode/src/session/prompt.ts`.

---

### Task 1: Create the English deep-dive doc

**Files:**
- Create: `docs/en/modules/session-prompt.md`

**Step 1: Explain the naming trap**

Open with a section that explains why the filename `prompt.ts` is easy to misread.

**Step 2: Explain control ownership**

Document what `SessionPrompt` owns:

- request handoff from routes/SDK
- user message creation
- session loop ownership
- model/tool/system prompt resolution
- command and shell orchestration
- cancellation and busy-state integration

**Step 3: Explain delegation**

Document what it delegates to:

- `Session`
- `SessionProcessor`
- `LLM`
- `ToolRegistry`
- `SessionStatus`
- `SessionCompaction`

**Step 4: Add a file-structure walkthrough**

Walk through the major internal sections and exported APIs:

- service wiring
- runner cache and concurrency control
- tool resolution
- subtask/shell helpers
- `prompt`
- `runLoop`
- `loop`
- `shell`
- `command`
- exported input schemas and wrappers

### Task 2: Create the Chinese deep-dive doc

**Files:**
- Create: `docs/zh/modules/session-prompt.md`

**Step 1: Mirror the English structure**

Keep section order and code anchors aligned with the English doc.

**Step 2: Translate naturally**

Use natural Chinese while keeping the same technical meaning.

### Task 3: Update the runtime module docs

**Files:**
- Modify: `docs/en/modules/runtime.md`
- Modify: `docs/zh/modules/runtime.md`

**Step 1: Add a short summary note**

Clarify that `prompt.ts` is the orchestration core and that a dedicated deep dive exists in `session-prompt.md`.

**Step 2: Keep the runtime docs compact**

Do not duplicate the new deep-dive content. Add only enough text to improve navigation.

### Task 4: Verify and commit

**Files:**
- Verify only

**Step 1: Check markdown formatting**

Run:

```bash
git diff --check
```

Expected: no output.

**Step 2: Check affected files**

Run:

```bash
git status --short
```

Expected: only the new plan/docs and runtime doc updates appear.

**Step 3: Commit**

```bash
git add docs/en docs/zh
git commit -m "docs: add session prompt deep dive"
```
