# CLI Module

## Module Responsibility

The CLI layer is the user-facing shell for command selection, argument parsing, local process setup, and handoff into the runtime. In the pinned version it is responsible for:

- parsing `argv` with yargs,
- installing global CLI middleware and process behavior,
- dispatching to command handlers,
- normalizing command-specific input such as prompts, files, and session flags,
- and bridging from shell interaction into either direct instance-scoped runtime APIs or the internal control-plane SDK/server boundary.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/index.ts` | top-level CLI parser, middleware, and command registration | `yargs(...)`, `.middleware(...)`, `.command(...)`, `cli.parse()` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/cmd.ts` | thin typed wrapper for yargs commands | `cmd(...)` |
| `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts` | instance-scoped runtime bootstrap helper for CLI commands | `bootstrap(directory, cb)` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts` | main non-TUI interactive CLI command | `RunCommand`, `execute(sdk)`, local `Server.Default().fetch(...)` bridge |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/session.ts` | simpler direct-runtime session commands | `SessionListCommand`, `SessionDeleteCommand` |
| `workspace/source/opencode/packages/opencode/src/cli/ui.ts` | basic terminal printing/error styles for non-TUI flows | `UI.println`, `UI.error`, `UI.logo` |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `cli` | parser instance | `index.ts` | global yargs CLI entrypoint |
| `cmd(...)` | helper | `cmd.ts` | typed command descriptor passthrough |
| `bootstrap(directory, cb)` | helper | `bootstrap.ts` | enters instance-scoped runtime and disposes afterward |
| `RunCommand` | command | `run.ts` | sends prompt/command input into runtime and renders streamed output |
| `TuiThreadCommand` | command | `tui/thread.ts` | launches the TUI shell in local/worker/server modes |
| `AttachCommand` | command | `tui/attach.ts` | attaches UI to an already running server |

## Initialization / Entry

`src/index.ts` is the raw CLI boundary:

1. build the yargs parser from `process.argv`,
2. install global logging/env/migration middleware,
3. register command modules,
4. call `await cli.parse()`.

This is where raw shell input first becomes structured command intent.

## Main Control Flow

### 1. Parse And Normalize Shell Input

At the top level, `index.ts` handles:

- `--help`, `--version`, `--print-logs`, `--log-level`, `--pure`
- one-time DB migration
- fatal error formatting and exit behavior

Each command module then declares its own arguments in a yargs `builder`.

### 2. Hand Off To Command Handler

Once yargs dispatches a concrete handler, raw `argv` handling continues only long enough to:

- assemble message text,
- resolve `--dir` / cwd behavior,
- validate session/fork constraints,
- resolve file inputs,
- combine stdin with prompt text when needed.

After that, the handler moves into runtime interaction.

### 3. Choose Runtime Bridge

The CLI uses two main runtime-bridge patterns.

Direct instance-scoped runtime access:

- commands such as `session list/delete` call `bootstrap(process.cwd(), async () => ...)`
- then use runtime services directly inside that instance context.

SDK/control-plane access:

- `run.ts` creates an `OpencodeClient`
- in local mode it points the SDK at an in-process `Server.Default().fetch(...)`
- in attach mode it points the SDK at a remote server URL
- then it uses `sdk.session.*`, `sdk.event.subscribe()`, `sdk.permission.reply()`, and related APIs.

### 4. Render Non-TUI Output

`run.ts` is a CLI-specific interaction adapter layered on top of the SDK:

- it subscribes to runtime events,
- formats tool completions and text output for terminal use,
- auto-rejects permission prompts in plain CLI mode,
- and exits when `session.status` returns to `idle`.

This makes it distinct from both raw yargs parsing and the richer TUI shell.

## Upstream And Downstream Dependencies

Upstream:

- OS shell / `process.argv`
- stdin/stdout/stderr

Downstream:

- `Instance.provide(..., init: InstanceBootstrap)` through `bootstrap(...)`
- `Server.Default()` for in-process control-plane access
- `@opencode-ai/sdk/v2` for session/config/event calls
- `UI` helpers for non-TUI printing
- TUI command entrypoints for richer interactive shells

## Implementation Details

- `cmd.ts` adds almost no abstraction; the real command system is still yargs.
- `index.ts` forces `process.exit()` in `finally`, reflecting a pragmatic preference for avoiding hanging subprocesses.
- Local CLI usage often still traverses the server/control-plane API via in-process fetch rather than calling session services directly.
- `run.ts` therefore acts more like a terminal client for the backend than a monolithic all-in-one command implementation.

## Design Tradeoffs / Risks

- The CLI is a thin transport layer in some commands and a richer event-rendering client in others, so the abstraction boundary varies by command.
- Routing local execution through the internal server/SDK path improves consistency with remote mode, but adds indirection.
- Global middleware in `index.ts` mixes CLI startup concerns with one-time storage migration and process env mutation.

## Pending Verification

- Which less-common commands still bypass the internal SDK/server bridge and operate entirely through direct runtime calls.
- Whether future command growth is expected to favor SDK-mediated flows over direct service invocation.
