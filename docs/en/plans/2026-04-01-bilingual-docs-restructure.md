# Bilingual Docs Restructuring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the repository so `docs/` becomes a bilingual final-output area with mirrored Chinese and English technical-blog documentation, while `reports/` remains monolingual process output.

**Architecture:** Move the existing Chinese analysis corpus into `docs/zh/`, create a mirrored `docs/en/` tree with the same information architecture, and introduce a blog-first top layer without discarding the existing module and callflow evidence structure. Update repository rules so future work treats paired `zh/en` docs as the final system of record.

**Tech Stack:** Markdown, git, shell file moves, Codex editing workflow, existing analysis docs in this repository.

---

### Task 1: Save the approved restructuring shape

**Files:**
- Create: `docs/plans/2026-04-01-bilingual-docs-restructure.md`

**Step 1: Record the approved target structure**

Write the plan with:

- `docs/zh/` and `docs/en/` as mirrored final-output trees
- `reports/` remaining monolingual
- a hybrid blog + appendix model

**Step 2: Confirm migration scope**

List the current `docs/` files that must move into `docs/zh/`.

**Step 3: Commit**

```bash
git add docs/plans/2026-04-01-bilingual-docs-restructure.md
git commit -m "docs: add bilingual docs restructuring plan"
```

### Task 2: Create mirrored `docs/zh` and `docs/en` skeletons

**Files:**
- Create: `docs/zh/`
- Create: `docs/en/`
- Create: `docs/zh/blog/`
- Create: `docs/en/blog/`
- Create: `docs/zh/modules/`
- Create: `docs/en/modules/`
- Create: `docs/zh/callflows/`
- Create: `docs/en/callflows/`
- Create: `docs/zh/version-notes/`
- Create: `docs/en/version-notes/`
- Create: `docs/zh/plans/`
- Create: `docs/en/plans/`

**Step 1: Create target directories**

Use shell directory creation so the final tree exists before moving files.

**Step 2: Verify directory tree**

Run:

```bash
find docs -maxdepth 3 -type d | sort
```

Expected: both `docs/zh/...` and `docs/en/...` directory families appear.

**Step 3: Commit**

```bash
git add docs
git commit -m "docs: create bilingual docs directory layout"
```

### Task 3: Move current Chinese docs into `docs/zh`

**Files:**
- Modify/move: `docs/overview.md`
- Modify/move: `docs/repo-map.md`
- Modify/move: `docs/architecture.md`
- Modify/move: `docs/analysis-rules.md`
- Modify/move: `docs/modules/*.md`
- Modify/move: `docs/callflows/*.md`
- Modify/move: `docs/version-notes/vX.Y.Z.md`
- Modify/move: `docs/plans/*.md`

**Step 1: Move existing docs into the Chinese tree**

Relocate current finalized docs into matching `docs/zh/...` paths.

**Step 2: Add a Chinese blog skeleton**

Create:

- `docs/zh/blog/opencode-deep-dive.md`

Seed it with section headings that match the approved hybrid blog structure.

**Step 3: Verify Chinese tree**

Run:

```bash
find docs/zh -maxdepth 3 -type f | sort
```

Expected: all previously finalized docs now exist under `docs/zh/`.

**Step 4: Commit**

```bash
git add docs
git commit -m "docs: move finalized Chinese docs into zh tree"
```

### Task 4: Create English mirrors for final docs

**Files:**
- Create: `docs/en/overview.md`
- Create: `docs/en/repo-map.md`
- Create: `docs/en/architecture.md`
- Create: `docs/en/analysis-rules.md`
- Create: `docs/en/blog/opencode-deep-dive.md`
- Create: `docs/en/modules/*.md`
- Create: `docs/en/callflows/*.md`
- Create: `docs/en/version-notes/vX.Y.Z.md`
- Create: `docs/en/plans/*.md`

**Step 1: Mirror file set**

Ensure every finalized `docs/zh/...` file has a paired `docs/en/...` file with the same relative path.

**Step 2: Translate and adapt content**

For each mirrored file:

- keep the same section order,
- keep the same core claims,
- keep the same code anchors,
- rewrite prose into natural English rather than literal line-by-line translation.

**Step 3: Verify mirror completeness**

Run:

```bash
comm -3 <(cd docs/zh && find . -type f | sort) <(cd docs/en && find . -type f | sort)
```

Expected: no output.

**Step 4: Commit**

```bash
git add docs/en
git commit -m "docs: add english mirrors for finalized docs"
```

### Task 5: Update repository rules for bilingual final outputs

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `tasks/00-analysis-master-plan.md`
- Modify: `tasks/01-repo-inventory.md`
- Modify: `tasks/02-core-abstractions.md`
- Modify: `tasks/03-entrypoints.md`
- Modify: `tasks/04-high-level-callflow.md`
- Modify: `tasks/05-config-system.md`
- Modify: `tasks/06-provider-system.md`
- Modify: `tasks/07-tool-system.md`
- Modify: `tasks/08-runtime-orchestration.md`
- Modify: `tasks/09-memory-session.md`
- Modify: `tasks/10-ui-cli.md`
- Modify: `tasks/11-plugin-skill-system.md`
- Modify: `tasks/12-end-to-end-callflow.md`
- Modify: `tasks/13-open-questions.md`

**Step 1: Update root docs descriptions**

Adjust `README.md` and `AGENTS.md` so they state:

- `docs/zh` and `docs/en` are mirrored final outputs
- updates to final docs should be paired
- `reports/` stays monolingual

**Step 2: Update task output paths**

Revise task files so future analysis writes/promotes final docs into bilingual paths instead of the old flat `docs/` paths.

**Step 3: Commit**

```bash
git add README.md AGENTS.md tasks
git commit -m "docs: update workflow for bilingual finalized docs"
```

### Task 6: Verify the repository after migration

**Files:**
- Verify only

**Step 1: Check git diff formatting**

Run:

```bash
git diff --check
```

Expected: no output.

**Step 2: Check mirrored docs file set**

Run:

```bash
comm -3 <(cd docs/zh && find . -type f | sort) <(cd docs/en && find . -type f | sort)
```

Expected: no output.

**Step 3: Spot-check key files**

Read:

- `docs/zh/blog/opencode-deep-dive.md`
- `docs/en/blog/opencode-deep-dive.md`
- `README.md`
- `AGENTS.md`

**Step 4: Final commit**

```bash
git add docs README.md AGENTS.md tasks
git commit -m "docs: restructure final outputs into bilingual docs"
```
