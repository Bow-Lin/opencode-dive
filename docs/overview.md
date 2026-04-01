# Overview

## Purpose

This repository exists to support deep, repeatable analysis of one pinned Opencode version. It is designed for agent execution: scoped tasks, stable templates, persistent docs, and a clear path from repository inventory to detailed call-flow analysis.

## What "Done" Looks Like

The workbench is considered productive when it can support the following loop:

1. ingest a specific Opencode version,
2. inventory the source,
3. identify entrypoints and module boundaries,
4. trace critical runtime paths,
5. publish code-anchored documentation,
6. capture unresolved questions for later passes.

## Analysis Outputs

- `docs/repo-map.md`: source layout and key entrypoints
- `docs/architecture.md`: system-level architecture and major relationships
- `docs/modules/*.md`: per-module breakdowns
- `docs/callflows/*.md`: critical execution paths
- `docs/version-notes/*.md`: version deltas

## Non-Goals

- Maintaining general Opencode product documentation
- Replacing the original source repository README
- Storing raw scratch output in long-term docs
