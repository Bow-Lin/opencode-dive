# Startup Call Flow

## Trigger

User runs the `opencode` CLI, or a development script launches `packages/opencode/src/index.ts` directly.

## Start File / Symbol

- Installed CLI wrapper: `workspace/source/opencode/packages/opencode/bin/opencode`
- Development/runtime entry module: `workspace/source/opencode/packages/opencode/src/index.ts`

## Ordered Execution Steps

1. Package metadata maps the published command name `opencode` to `packages/opencode/bin/opencode`.
2. `bin/opencode` resolves the platform-specific installed binary or cached executable and forwards `process.argv`.
3. In development, the root workspace script bypasses the wrapper and launches `packages/opencode/src/index.ts` with Bun.
4. `src/index.ts` installs fatal error handlers, constructs the yargs CLI, and registers global options plus subcommands.
5. yargs middleware initializes logging, exports runtime env markers, and performs one-time database migration if `Global.Path.data/opencode.db` is missing.
6. Control passes to the selected command handler.
7. For project-bound commands such as `run`, the handler calls `cli/bootstrap.ts`, which wraps execution in `Instance.provide({ init: InstanceBootstrap, ... })`.
8. `project/bootstrap.ts` initializes core per-instance subsystems such as plugins, formatting, LSP, file services, VCS, snapshots, and a command-executed bus subscription.
9. For server mode, `ServeCommand` calls `Server.listen(...)`; instance bootstrap is deferred until request handling, where `WorkspaceRouterMiddleware` invokes `Instance.provide(..., init: InstanceBootstrap)`.

## State Transitions

- Process-level startup:
  - log initialization
  - environment markers (`AGENT`, `OPENCODE`, `OPENCODE_PID`)
  - optional one-time DB migration
- Command-level startup:
  - yargs resolves the concrete command
- Instance-level startup:
  - `Instance.provide` establishes directory/worktree context
  - `InstanceBootstrap` initializes project-scoped services

## External Boundaries

- OS/package-manager launch boundary at `bin/opencode`
- Bun runtime for `src/index.ts`
- filesystem boundary for cache/data directories and migration marker
- Bun HTTP server boundary for `Server.listen(...)`

## Failure / Branching Behavior

- If the CLI wrapper cannot resolve an installed binary, it exits with an installation error message.
- If yargs argument validation fails, help is printed for common argument errors.
- Fatal runtime errors are formatted through `FormatError`; otherwise a generic log-file pointer is shown.
- `serve` differs from `run` and similar commands because it starts the HTTP server before any project instance is bootstrapped.

## Evidence Table

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 1 | `workspace/source/opencode/packages/opencode/package.json` | `bin.opencode` | published command maps to `./bin/opencode` |
| 2 | `workspace/source/opencode/packages/opencode/bin/opencode` | top-level wrapper script | resolves cached/platform binary and forwards args |
| 3 | `workspace/source/opencode/package.json` | `scripts.dev` | dev path runs `packages/opencode/src/index.ts` directly |
| 4 | `workspace/source/opencode/packages/opencode/src/index.ts` | yargs setup | global options and command registration |
| 5 | `workspace/source/opencode/packages/opencode/src/index.ts` | middleware | logging/env setup and JSON-to-SQLite migration |
| 7 | `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts` | `bootstrap(...)` | wraps command execution in instance context |
| 8 | `workspace/source/opencode/packages/opencode/src/project/bootstrap.ts` | `InstanceBootstrap()` | initializes plugin/LSP/file/VCS/snapshot subsystems |
| 9 | `workspace/source/opencode/packages/opencode/src/cli/cmd/serve.ts` | `ServeCommand.handler` | starts server process |
| 9 | `workspace/source/opencode/packages/opencode/src/server/router.ts` | `WorkspaceRouterMiddleware` | request-scoped instance bootstrap |

## Pending Verification

- Which subcommands bypass `cli/bootstrap.ts` besides `serve` and `generate`.
- Whether packaged native binaries eventually delegate into the same TS entry logic or use a separately built artifact path with startup differences.
