# Session Prompt Analysis Design

> This document records the approved design for the dedicated `prompt.ts` analysis doc.

## Goal

Add a focused document that explains why `workspace/source/opencode/packages/opencode/src/session/prompt.ts` is misleadingly named and why it is actually the runtime orchestration core of Opencode.

## Reader Problem

The filename `prompt.ts` can easily suggest a file full of prompt templates or text snippets. In reality, the file owns interactive session orchestration, control transfer, loop policy, tool binding, command expansion, and cancellation behavior.

## Chosen Output Shape

Use both of these:

- a dedicated deep-dive doc:
  - `docs/en/modules/session-prompt.md`
  - `docs/zh/modules/session-prompt.md`
- a short summary/link in the runtime module docs:
  - `docs/en/modules/runtime.md`
  - `docs/zh/modules/runtime.md`

## Chosen Writing Style

Use a mixed approach:

1. explain control ownership and responsibilities first,
2. then walk through the file structure and major exported entrypoints.

## Required Questions To Answer

The doc must answer:

- why the name `prompt.ts` is misleading,
- what `SessionPrompt` really owns,
- what it delegates to `Session`, `SessionProcessor`, `LLM`, `ToolRegistry`, and `SessionStatus`,
- how `prompt`, `loop`, `runLoop`, `shell`, and `command` relate,
- and what risks come from concentrating so much runtime policy in one file.
