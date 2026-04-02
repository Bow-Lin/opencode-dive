# System Diagrams Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a bilingual, narrative-style Mermaid diagram set for Opencode and connect it from the main architecture and blog docs.

**Architecture:** Create one dedicated diagram page per language, each containing the same seven diagrams with language-appropriate explanations and the same code anchors. Update the architecture and blog documents so readers can jump from the narrative text into the visual appendix without losing context.

**Tech Stack:** Markdown, Mermaid (`flowchart`, `sequenceDiagram`, `stateDiagram-v2`), existing bilingual docs in this repository.

---

### Task 1: Create the English diagram page

**Files:**
- Create: `docs/en/system-diagrams.md`

**Step 1: Add page framing**

Write a short introduction that explains:

- why this page exists,
- how to read the diagrams,
- and how it relates to `architecture.md`, `modules/`, and `callflows/`.

**Step 2: Add the approved seven diagrams**

Add these Mermaid diagrams in order:

1. system overview
2. startup and entry flow
3. end-to-end request sequence
4. runtime orchestration core
5. tool execution sequence
6. session lifecycle state machine
7. extension architecture

**Step 3: Add code anchors**

After each diagram, add a short "Primary code anchors" list pointing to the most relevant source files.

### Task 2: Create the Chinese diagram page

**Files:**
- Create: `docs/zh/system-diagrams.md`

**Step 1: Mirror the English structure**

Use the same diagram order and Mermaid structure as the English page.

**Step 2: Translate explanatory text naturally**

Keep headings and code anchors aligned, but rewrite the surrounding prose in natural Chinese.

### Task 3: Link the diagram pages from the architecture docs

**Files:**
- Modify: `docs/en/architecture.md`
- Modify: `docs/zh/architecture.md`

**Step 1: Add a visible link near the top**

Insert a short note telling readers that the visual companion lives in `system-diagrams.md`.

**Step 2: Keep wording lightweight**

Do not rewrite the architecture docs. Add only enough text to improve navigation.

### Task 4: Link the diagram pages from the deep-dive blog docs

**Files:**
- Modify: `docs/en/blog/opencode-deep-dive.md`
- Modify: `docs/zh/blog/opencode-deep-dive.md`

**Step 1: Add diagram-page references**

Link the diagram page from:

- the reading-strategy section, and/or
- the "Where To Read Next" section.

**Step 2: Preserve article flow**

The link should feel like a companion resource, not a detour.

### Task 5: Verify and commit

**Files:**
- Verify only

**Step 1: Check markdown formatting**

Run:

```bash
git diff --check
```

Expected: no output.

**Step 2: Check file presence**

Run:

```bash
find docs/en -maxdepth 2 -type f | sort
find docs/zh -maxdepth 2 -type f | sort
```

Expected: both trees include `system-diagrams.md`.

**Step 3: Commit**

```bash
git add docs/en docs/zh
git commit -m "docs: add bilingual system diagrams"
```
