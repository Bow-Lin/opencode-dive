# Task 03: Entrypoints

## Goal

Identify concrete startup files, symbols, and bootstrap control flow.

## Input Scope

- CLI binaries
- package main/module exports
- bootstrap/init/register files

## Must Read

- `docs/{en,zh}/repo-map.md`
- `scripts/find-entrypoints.sh`

## Expected Output

- `reports/run-YYYY-MM-DD/entrypoints.md`
- updates to `docs/{en,zh}/callflows/startup.md`
- updates to `docs/{en,zh}/architecture.md`

## Completion Standard

- first executable entrypoint is named,
- bootstrap path is traced through concrete symbols,
- and config/runtime handoff is documented.
