# Opencode Deep Dive

## Who This Is For

This article is written for engineers who want to understand how Opencode is structured without reading the entire repository first. It focuses on the main control path, the core runtime abstractions, and the architectural tradeoffs that shape the system.

## Reading Strategy

The main article explains the design in narrative form and only cites the most important code anchors. The appendices under `../modules/` and `../callflows/` carry the detailed evidence trail.

## 1. What Opencode Actually Is

Opencode is not just a command-line wrapper around a language model. The pinned version is a TypeScript monorepo whose behavioral core lives in `workspace/source/opencode/packages/opencode`, while additional packages provide web, desktop, SDK, plugin, and UI surfaces.

The practical implication is that the system should be read as a shared runtime with multiple front doors, not as a single-purpose CLI application.

Key anchors:

- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/server/server.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`

## 2. The Request Does Not Stop At The CLI

The CLI is an entry surface, not the whole system. A user command enters the CLI bootstrap path, but the implementation quickly routes into an internal SDK client and then into the in-process server/control-plane stack.

That layering matters because Opencode reuses the same backend orchestration logic across local CLI usage and server-style request handling.

Key anchors:

- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts`
- `workspace/source/opencode/packages/opencode/src/server/routes.ts`

## 3. Why `SessionPrompt` Is The Real Control Core

The strongest control hotspot is `workspace/source/opencode/packages/opencode/src/session/prompt.ts`. Transport layers accept and normalize requests, but `SessionPrompt` owns the prompt loop, session-level orchestration policy, and downstream coordination with providers, tools, and persistence.

This is the most important architectural shortcut for reading the repository: if the question is "where does the interactive loop really live?", the answer is not the CLI file or the router tree. It is `SessionPrompt`.

Key anchors:

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/index.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`

## 4. Provider, Tool, And Session Split

Opencode keeps three major concerns separate:

- provider modules define how models are selected and invoked,
- tool modules define executable capabilities around the model loop,
- session modules own conversation state, streaming, and persistence.

This separation is what keeps the system from collapsing into one giant "agent runtime" file. It also makes the code easier to extend, even though the central orchestration path is still concentrated.

Key anchors:

- `workspace/source/opencode/packages/opencode/src/provider/provider.ts`
- `workspace/source/opencode/packages/opencode/src/tool/tool.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`

## 5. Why The Backend Is Shared

The repository exposes multiple user-facing shells, but they converge on a shared backend model built around Effect services, instance-scoped runtime context, and server-style routing. In practice, even local CLI flows often talk to the shared backend through an in-process fetch layer.

That design increases indirection, but it reduces duplication across CLI, app, and other surfaces.

Key anchors:

- `workspace/source/opencode/packages/opencode/src/project/instance.ts`
- `workspace/source/opencode/packages/opencode/src/server/server.ts`
- `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts`

## 6. Extension Is Not One Thing

The repository uses several extension mechanisms that look similar at first glance but behave differently:

- server plugins hook into runtime behavior,
- TUI plugins extend the interface shell,
- skills supply reusable task-oriented content and command exposure,
- tools provide executable actions inside the prompt loop.

Treating all of these as a single "plugin system" makes the architecture harder to understand. The code is clearer once these mechanisms are separated by lifecycle and responsibility.

Key anchors:

- `workspace/source/opencode/packages/opencode/src/plugin/index.ts`
- `workspace/source/opencode/packages/opencode/src/skill/index.ts`
- `workspace/source/opencode/packages/opencode/src/tool/tool.ts`
- `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/plugin/runtime.ts`

## 7. The Main Tradeoff

Opencode gains flexibility by splitting the system into transport surfaces, instance scoping, orchestration, providers, tools, events, and persistence layers. The tradeoff is that control ownership is not obvious from a single file. The architecture is powerful, but it is only legible once the reader follows the request across those boundaries.

That is why the most effective reading order is:

1. CLI or request entry
2. instance bootstrap
3. `SessionPrompt`
4. provider/tool/session internals
5. persistence and event propagation

## Where To Read Next

- Architecture overview: `../architecture.md`
- Repository map: `../repo-map.md`
- Module appendices: `../modules/`
- Callflow appendices: `../callflows/`
