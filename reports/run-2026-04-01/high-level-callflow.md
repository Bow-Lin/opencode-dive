# High-Level Call Flow

## Goal

Map the major control path at system level before detailed config/provider/tool/session analysis.

## Main Path

### CLI-Driven Interactive Flow

1. User launches `opencode` or a dev script.
2. Startup resolves into `packages/opencode/src/index.ts`.
3. yargs selects a command such as `run`.
4. The command enters `cli/bootstrap.ts`.
5. `bootstrap(...)` calls `Instance.provide({ directory, init: InstanceBootstrap, ... })`.
6. The command creates an SDK client pointed at the in-process server via `Server.Default().fetch(...)`.
7. The CLI uses SDK methods such as `sdk.session.create(...)` and `sdk.session.prompt(...)`.
8. The server control plane routes the request through `WorkspaceRouterMiddleware`.
9. `InstanceRoutes` dispatches the request to `SessionRoutes`.
10. Session endpoints delegate to `SessionPrompt`, `Session`, `SessionStatus`, or related session services.
11. `SessionPrompt` becomes the orchestration hub for downstream agent/provider/tool/permission/session-processing work.

## Evidence

| Stage | File | Symbol | Note |
| --- | --- | --- | --- |
| CLI startup | `packages/opencode/src/index.ts` | yargs CLI construction | top-level command registration |
| Project bootstrap | `packages/opencode/src/cli/bootstrap.ts` | `bootstrap(...)` | wraps commands in instance context |
| Instance init | `packages/opencode/src/project/bootstrap.ts` | `InstanceBootstrap()` | initializes project-scoped services |
| In-process client bridge | `packages/opencode/src/cli/cmd/run.ts` | `createOpencodeClient(... fetch: Server.Default().fetch ...)` | CLI reuses server API surface locally |
| Control plane | `packages/opencode/src/server/server.ts` | `ControlPlaneRoutes` / `Server.Default` | root Hono app |
| Workspace binding | `packages/opencode/src/server/router.ts` | `WorkspaceRouterMiddleware` | activates the correct instance |
| Route fanout | `packages/opencode/src/server/instance.ts` | `InstanceRoutes` | mounts `SessionRoutes`, `ProviderRoutes`, etc. |
| Session entry | `packages/opencode/src/server/routes/session.ts` | `SessionPrompt.prompt`, `SessionPrompt.command`, `SessionPrompt.shell` | main message mutation endpoints |
| Runtime hub | `packages/opencode/src/session/prompt.ts` | `SessionPrompt.Service` | pulls in Agent/Provider/ToolRegistry/Permission/etc. |

## Major Branch Points

### Server Mode

- `ServeCommand` starts `Server.listen(...)` directly.
- Instance bootstrap is deferred to request routing instead of command bootstrap time.

### Attached Remote Mode

- `run` can also connect to an external server via `createOpencodeClient({ baseUrl: args.attach, ... })`.
- In that branch, the CLI skips the in-process `Server.Default().fetch(...)` bridge.

### Non-Interactive Commands

- Some commands do not appear to require project bootstrap in the same way as `run`.
- `generate` is an example of a command that directly uses `Server.openapi()` instead.

## Key Conclusions

- The server API is not only a remote interface; it is also the internal composition boundary used by the CLI.
- `SessionRoutes` and `SessionPrompt` are the strongest current candidates for the main orchestration spine.
- Instance scoping is established before or during request routing, depending on the entry path.

## Pending Questions

- Which session endpoint is the dominant path for the interactive TUI versus one-shot CLI prompts?
- At what point does session orchestration hand off into tool execution loops versus pure model generation?
