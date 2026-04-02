# System Diagrams Design

> This document records the approved design for the bilingual Opencode system diagram set.

## Goal

Add a reader-facing system diagram page that makes Opencode easier to understand visually, while keeping the diagrams aligned with the repository's code-anchored architecture analysis.

## Audience

The primary audience is mid-to-senior engineers who want to understand Opencode's design quickly before reading the full module and call-flow appendices.

## Chosen Structure

Use a standalone bilingual diagram page:

- `docs/en/system-diagrams.md`
- `docs/zh/system-diagrams.md`

Then link to those pages from:

- `docs/en/architecture.md`
- `docs/zh/architecture.md`
- `docs/en/blog/opencode-deep-dive.md`
- `docs/zh/blog/opencode-deep-dive.md`

## Chosen Format

Use a narrative diagram set, not a flat module map.

Diagram types are intentionally mixed:

- `flowchart` for structure and control ownership
- `sequenceDiagram` for request and tool execution timing
- `stateDiagram-v2` for session-state evolution

## Approved Diagram Set

The final page should contain seven diagrams:

1. System overview
2. Startup and entry flow
3. End-to-end user request sequence
4. Runtime orchestration core
5. Tool execution sequence
6. Session lifecycle state machine
7. Extension architecture

## Scope Boundary

The diagram page should:

- explain the major runtime relationships,
- reinforce the existing architecture narrative,
- point readers toward module and call-flow appendices,
- and stay code-anchored.

It should not:

- try to visualize every package in the monorepo,
- replace the textual analysis docs,
- or turn into a giant unreadable "everything map."
