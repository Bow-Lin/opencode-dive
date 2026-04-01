# Overview

## Purpose

This repository exists to support deep, repeatable analysis of one pinned Opencode version. It is designed for agent execution: scoped tasks, stable templates, persistent docs, and a clear path from repository inventory to detailed call-flow analysis.

The final documentation set is bilingual:

- English documents live under `docs/en/`
- Chinese documents live under `docs/zh/`
- run-scoped scratch output remains single-language in `reports/`

## What "Done" Looks Like

The workbench is considered productive when it can support the following loop:

1. ingest a specific Opencode version,
2. inventory the source,
3. identify entrypoints and module boundaries,
4. trace critical runtime paths,
5. publish code-anchored documentation,
6. capture unresolved questions for later passes.

## Analysis Outputs

- `blog/opencode-deep-dive.md`: reader-facing deep dive article
- `architecture.md`: system-level architecture and major relationships
- `repo-map.md`: source layout and key entrypoints
- `modules/*.md`: per-module breakdowns
- `callflows/*.md`: critical execution paths
- `version-notes/*.md`: version deltas

Read the article first, then use the appendices as proof and detail:

- `blog/opencode-deep-dive.md`
- `architecture.md`
- `modules/*.md`
- `callflows/*.md`

## Non-Goals

- Maintaining general Opencode product documentation
- Replacing the original source repository README
- Storing raw scratch output in long-term docs
