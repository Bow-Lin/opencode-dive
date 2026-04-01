# Entrypoints

## Goal

Identify concrete startup files, symbols, and bootstrap control flow for the pinned Opencode version.

## Primary Entrypoints

### 1. Published CLI Entrypoint

- File: `packages/opencode/package.json`
- Symbol: `bin.opencode`
- Value: `./bin/opencode`

Interpretation:

- this is the first published command boundary for installed CLI usage.

### 2. CLI Wrapper Script

- File: `packages/opencode/bin/opencode`
- Role: resolve cached or platform-specific executable and forward argv

Observed behavior:

- honors `OPENCODE_BIN_PATH` override first
- prefers sibling cached executable `.opencode`
- otherwise probes platform/arch-specific packages in `node_modules`
- exits with an install error if no compatible binary is found

### 3. Development Entrypoint

- File: root `package.json`
- Symbol: `scripts.dev`
- Value: `bun run --cwd packages/opencode --conditions=browser src/index.ts`

Interpretation:

- local development bypasses the published wrapper and enters the TypeScript source directly.

### 4. Application Entry Module

- File: `packages/opencode/src/index.ts`
- Role: real CLI composition root

Observed behavior:

- installs `unhandledRejection` and `uncaughtException` handlers
- builds the yargs CLI
- registers global options
- registers all command modules
- runs middleware before command handlers
- parses and executes the selected command

## Bootstrap Path

### Project-Bound Command Path

Representative evidence:

- `packages/opencode/src/cli/cmd/run.ts`
- `packages/opencode/src/cli/cmd/session.ts`
- `packages/opencode/src/cli/cmd/acp.ts`
- `packages/opencode/src/cli/cmd/github.ts`

Observed pattern:

- these commands call `bootstrap(process.cwd(), async () => { ... })`
- `cli/bootstrap.ts` wraps execution with `Instance.provide({ init: InstanceBootstrap, ... })`
- `project/bootstrap.ts` initializes plugin/LSP/file/VCS/snapshot-related services for that instance

Interpretation:

- for most user-facing project commands, the operational bootstrap point is not `src/index.ts` alone;
- it is `src/index.ts` -> command handler -> `cli/bootstrap.ts` -> `project/bootstrap.ts`.

### Server Path

Representative evidence:

- `packages/opencode/src/cli/cmd/serve.ts`
- `packages/opencode/src/server/server.ts`
- `packages/opencode/src/server/router.ts`

Observed pattern:

- `serve` resolves network options and calls `Server.listen(opts)`
- `Server.listen` creates a Hono app and starts `Bun.serve`
- `WorkspaceRouterMiddleware` later calls `Instance.provide(..., init: InstanceBootstrap)` per request/workspace

Interpretation:

- server startup is split:
  - process startup happens immediately,
  - project instance bootstrap is deferred until request routing.

## Middleware-Level Startup Work

Inside `packages/opencode/src/index.ts`, yargs middleware performs:

- `Log.init(...)`
- environment marker setup:
  - `AGENT=1`
  - `OPENCODE=1`
  - `OPENCODE_PID=<pid>`
- one-time SQLite migration via `JsonMigration.run(...)` when the data marker DB does not exist

This makes middleware part of the startup path, not just argument normalization.

## Key Conclusions

- The true startup chain has at least two layers:
  - distribution wrapper resolution
  - application CLI composition and command dispatch
- `src/index.ts` is the most important code-level entrypoint for runtime analysis.
- Instance initialization is command-dependent and can happen either:
  - immediately in CLI command handlers,
  - or later at HTTP request time for server mode.

## Open Questions

- Which CLI commands are intentionally non-instance-bound besides `generate` and `serve`?
- Do packaged binaries embed a build artifact equivalent of `src/index.ts`, or do they introduce startup differences worth documenting separately?
