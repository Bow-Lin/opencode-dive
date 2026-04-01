# Task 12: End-To-End Call Flow

## Goal

Produce a single, code-anchored end-to-end flow from user input to final output, crossing the relevant modules.

## Input Scope

- UI / CLI entry
- runtime orchestration
- provider interaction
- tool execution
- session updates

## Must Read

- `docs/{en,zh}/callflows/startup.md`
- `docs/{en,zh}/callflows/prompt-to-model.md`
- `docs/{en,zh}/callflows/tool-call-execution.md`
- `docs/{en,zh}/callflows/session-persistence.md`
- `docs/{en,zh}/callflows/end-to-end-user-request.md`

## Expected Output

- `reports/run-YYYY-MM-DD/end-to-end-callflow.md`
- updates to `docs/{en,zh}/callflows/end-to-end-user-request.md`
- updates to `docs/{en,zh}/architecture.md`

## Completion Standard

- trigger and output boundary are explicit,
- cross-module control flow is ordered,
- major state transitions are documented,
- and the flow is backed by concrete code references.
