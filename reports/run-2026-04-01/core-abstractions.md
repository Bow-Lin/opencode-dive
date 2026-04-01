# Core Abstractions

## Goal

Identify the central abstractions that organize the pinned Opencode version before detailed module-by-module tracing.

## Summary

The main package `packages/opencode/src` is not organized around large classes or a single application object. Instead, it is structured around repeated Effect service namespaces plus schema-first domain types, instance-scoped runtime context, and declarative extension contracts.

## Main Abstraction Families

### 1. Effect Service Namespaces

Representative files:

| Abstraction | Evidence | Role |
| --- | --- | --- |
| `Agent.Service` | `packages/opencode/src/agent/agent.ts` | agent registry/default agent generation and runtime-facing agent behaviors |
| `Provider.Service` | `packages/opencode/src/provider/provider.ts` | provider/model lookup, auth-aware loading, bundled/custom provider handling |
| `Plugin.Service` | `packages/opencode/src/plugin/index.ts` | plugin discovery/loading and runtime integration |
| `Command.Service` | `packages/opencode/src/command/index.ts` | command registry spanning built-in commands, MCP prompts, and skills |
| `Bus.Service` | `packages/opencode/src/bus/index.ts` | in-process pub/sub event fabric |
| `Worktree.Service` | `packages/opencode/src/worktree/index.ts` | git worktree creation/removal/reset operations |

Common structure:

- `export namespace X`
- `export interface Interface`
- `export class Service extends ServiceMap.Service<...>()`
- `export const layer = Layer.effect(...)`
- often `export const defaultLayer = ...`

### 2. Instance-Bound Execution Context

Representative files:

| Symbol | File | Role |
| --- | --- | --- |
| `Instance` | `packages/opencode/src/project/instance.ts` | ambient project/worktree context and instance lifecycle |
| `InstanceState.make/get/...` | `packages/opencode/src/effect/instance-state.ts` | per-instance cached state for services keyed by directory |

Interpretation:

- many services are not global singletons;
- they are effectively scoped to a project/worktree instance;
- ambient instance restoration is used to bridge async callbacks and Effect service execution.

### 3. Schema-First Domain Types

Representative files:

| Symbol | File | Role |
| --- | --- | --- |
| `Agent.Info` | `packages/opencode/src/agent/agent.ts` | schema for agent definitions |
| `Session.Info` | `packages/opencode/src/session/index.ts` | canonical session record shape |
| `Provider.Model` / `Provider.Info` | `packages/opencode/src/provider/provider.ts` | provider and model metadata |
| `Tool.Context` / `Tool.Def` / `Tool.Info` | `packages/opencode/src/tool/tool.ts` | generic tool contract |
| `SessionID`, `MessageID`, `ToolID`, `ProviderID` | `session/schema.ts`, `tool/schema.ts`, `provider/schema.ts` | typed identifiers |

Interpretation:

- data contracts are explicit and reused across runtime, storage, and API surfaces;
- this makes schemas a first-class abstraction alongside services.

### 4. Event Definitions And Projectors

Representative files:

| Symbol | File | Role |
| --- | --- | --- |
| `BusEvent.define` | `packages/opencode/src/bus/bus-event.ts` | define typed in-memory bus events |
| `Bus.publish/subscribe` | `packages/opencode/src/bus/index.ts` | publish/subscribe transport |
| `SyncEvent.define/project/run/replay` | `packages/opencode/src/sync/index.ts` | versioned domain events with projector/replay support |
| `Session.Event.*` | `packages/opencode/src/session/index.ts` | concrete session lifecycle events |

Interpretation:

- there is a clear split between transient bus notifications and more durable sync events;
- later tasks need to trace where each one is used and whether one is derived from the other.

### 5. Declarative Tooling And Extension Contracts

Representative files:

| Symbol | File | Role |
| --- | --- | --- |
| `Tool.define(...)` | `packages/opencode/src/tool/tool.ts` | declarative tool definition wrapper with validation and truncation |
| `TodoWriteTool`, `LspTool`, `WebSearchTool` | `packages/opencode/src/tool/*.ts` | concrete tools built on the shared contract |
| `Command.Info` | `packages/opencode/src/command/index.ts` | normalized command abstraction |
| `Plugin.Service` + `plugin/shared.ts` | `packages/opencode/src/plugin/index.ts`, `plugin/shared.ts` | plugin loading/spec parsing |
| `Skill.Service` + `Discovery.Service` | `packages/opencode/src/skill/index.ts`, `skill/discovery.ts` | skill registry and discovery |

Interpretation:

- Opencode exposes multiple extension surfaces, but each has a distinct abstraction:
  - tools for executable capabilities,
  - commands for prompt-like invocations,
  - plugins/skills for loaded extensions.

### 6. Transport Surfaces Over Shared Core

Representative files:

| Surface | File | Role |
| --- | --- | --- |
| CLI | `packages/opencode/src/index.ts` | yargs command registration and bootstrap middleware |
| HTTP server | `packages/opencode/src/server/server.ts` | Hono app creation, middleware, route mounting |

Interpretation:

- the same core subsystems are likely reused across CLI and server surfaces;
- detailed ownership between them remains for later tracing.

## Preliminary Conclusions

- The dominant architectural style is service-oriented rather than object-oriented.
- Runtime identity is instance-scoped, not purely process-global.
- Schemas, events, and service layers are the three most important cross-module abstractions.
- `packages/opencode/src` is the right focal point for subsequent task execution.

## Open Questions

- Which services are purely internal helpers versus stable module boundaries?
- Where is the main composition root for `defaultLayer` wiring across the runtime?
- How are CLI commands bridged into session/agent/tool execution after initial yargs parsing?
