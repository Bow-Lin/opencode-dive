# Architecture

## Current Status

This document is the long-term system view for the pinned Opencode version. It should be updated only after concrete analysis passes confirm the major modules and runtime paths.

## System Boundary

- Target application: Opencode at the version pinned in `OPENCODE_VERSION.md`
- Source location: `workspace/source/opencode`
- Analysis focus: runtime structure, data flow, module responsibilities, and key execution chains

## High-Level Components

The repository is a monorepo, but the primary behavioral core is concentrated in `workspace/source/opencode/packages/opencode`.

The top-level component split visible from inventory is:

- CLI/runtime core in `packages/opencode`
- client surfaces in `packages/app`, `packages/web`, `packages/desktop`, and `packages/desktop-electron`
- shared libraries in `packages/plugin`, `packages/sdk/js`, `packages/ui`, and `packages/util`
- infrastructure and automation in `infra/`, `script/`, and `github/`

## Core Abstraction Families

The core package is organized around a repeated service pattern built with Effect:

- service namespaces such as `Agent`, `Provider`, `Plugin`, `Command`, `Bus`, and `Worktree`
- an `Interface` type describing the capability surface
- a `Service` registration via `ServiceMap.Service`
- a `layer` or `defaultLayer` that wires dependencies

This pattern appears in:

- `workspace/source/opencode/packages/opencode/src/agent/agent.ts`
- `workspace/source/opencode/packages/opencode/src/provider/provider.ts`
- `workspace/source/opencode/packages/opencode/src/plugin/index.ts`
- `workspace/source/opencode/packages/opencode/src/command/index.ts`
- `workspace/source/opencode/packages/opencode/src/bus/index.ts`
- `workspace/source/opencode/packages/opencode/src/worktree/index.ts`

Around that service core, the architecture uses several recurring abstraction families:

### 1. Service Capabilities

Long-lived subsystems are exposed as Effect services rather than singleton objects. This is the dominant abstraction for provider access, agent behavior, plugin loading, config access, commands, session management, and worktree handling.

### 2. Instance-Scoped Runtime State

Runtime state is keyed by project/worktree instance. `project/instance.ts` provides the ambient instance context, while `effect/instance-state.ts` provides per-instance cached state for services that need isolation by directory/worktree.

### 3. Schema-First Domain Models

Many core types are defined as Zod schemas and exported as inferred types. This is visible in modules like `agent/agent.ts`, `session/index.ts`, `provider/provider.ts`, and `tool/tool.ts`. Identifiers are further normalized in dedicated schema files such as `provider/schema.ts`, `session/schema.ts`, and `tool/schema.ts`.

### 4. Event And Projection Model

Two event abstractions coexist:

- `bus/bus-event.ts` + `bus/index.ts` for in-process publish/subscribe notifications
- `sync/index.ts` for versioned domain events with replay/projector support and optional bus publication

This suggests the runtime mixes transient in-memory signaling with more durable event-sourced state transitions.

### 5. Declarative Tool / Command / Extension Contracts

- `tool/tool.ts` defines the generic tool contract
- individual tools register through `Tool.define(...)`
- `command/index.ts` aggregates built-in commands, MCP prompts, and skills into a uniform command abstraction
- `plugin/index.ts` and `skill/index.ts` load extension content into the runtime

### 6. Multiple Front Doors, Shared Core

The codebase exposes multiple user-facing surfaces:

- yargs-based CLI bootstrapping from `packages/opencode/src/index.ts`
- Hono server construction in `packages/opencode/src/server/server.ts`
- additional app/desktop/web packages layered around the monorepo

This matches the README claim that Opencode uses a client/server architecture rather than a single CLI-only shell.

## Runtime Data Flow

At a high level, the architecture appears to flow through:

1. wrapper/binary resolution or direct dev launch
2. CLI construction in `src/index.ts`
3. process-level logging and migration middleware
4. command dispatch
5. instance-bound bootstrap for project-scoped commands, or deferred bootstrap at request time for server mode
6. session, agent, provider, tool, and plugin interaction
7. bus/sync events plus storage-backed state changes

Detailed confirmation of this path belongs to later entrypoint and call-flow tasks.

## Module Boundaries

The strongest explicit module boundaries so far are:

- `cli`, `server`, and `command` for entry/control surfaces
- `config`, `provider`, `tool`, `plugin`, `skill`, and `session` for core runtime concerns
- `storage`, `sync`, and `bus` for persistence/signaling infrastructure
- `project`, `worktree`, and `instance-state` for workspace-scoped execution context

These boundaries are explicit at the directory level and reinforced by service interfaces, but many modules also depend on shared ambient instance context, so the runtime is not purely dependency-injected in a strict sense.

## Key Risks / Design Tensions

- Instance context is ambient and cross-cutting, which improves ergonomics but can obscure control ownership.
- The service pattern is consistent, but the number of subsystems and default layers can make dependency wiring hard to follow without call-flow tracing.
- Tools, commands, skills, plugins, and MCP prompts all act as extensibility surfaces, which increases flexibility but also creates multiple registration paths to reason about.
- The coexistence of transient bus events and persistent sync events introduces two signaling models that later tasks need to separate carefully.

## Evidence Requirements

Promote content here only after the underlying module docs and call-flow docs cite concrete files and symbols.
