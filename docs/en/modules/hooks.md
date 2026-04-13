# Hook Surfaces Module

## Module Responsibility

This document covers the server-plugin hook surface in the pinned Opencode version. Its purpose is to explain:

- where hook contracts are declared,
- how hook implementations are loaded,
- which hook names are actually triggered in runtime code,
- which plugin fields are not `Plugin.trigger(...)` hooks,
- and what execution semantics plugin authors inherit.

The key boundary is that "plugin hooks" are not one uniform mechanism. Some are sequential `(input, output)` transforms, while others are plain exported fields consumed by registries or bus wiring.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/plugin/src/index.ts` | canonical `Hooks` contract | `Hooks`, `Plugin`, `PluginModule` |
| `workspace/source/opencode/packages/opencode/src/plugin/index.ts` | plugin loading, `config` dispatch, `event` subscription, `Plugin.trigger(...)` runtime | `TriggerName`, `applyPlugin(...)`, `trigger(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/registry.ts` | consumes plugin `tool` exports and triggers `tool.definition` | `plugin.list()`, `plugin.trigger("tool.definition", ...)` |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | triggers message, command, tool-execution, and shell-environment hooks | `createUserMessage(...)`, wrapped tool `execute(...)`, `command(...)`, `shellImpl(...)` |
| `workspace/source/opencode/packages/opencode/src/session/llm.ts` | triggers request-shaping hooks before provider calls | `Plugin.trigger("experimental.chat.system.transform", ...)`, `Plugin.trigger("chat.params", ...)`, `Plugin.trigger("chat.headers", ...)` |
| `workspace/source/opencode/packages/opencode/src/session/compaction.ts` | triggers compaction-specific hooks | `plugin.trigger("experimental.session.compacting", ...)`, `plugin.trigger("experimental.chat.messages.transform", ...)` |
| `workspace/source/opencode/packages/opencode/src/session/processor.ts` | triggers text-finalization hook | `plugin.trigger("experimental.text.complete", ...)` |
| `workspace/source/opencode/packages/opencode/src/permission/index.ts` | current permission runtime without observed `permission.ask` trigger usage | `Permission.ask(...)` |
| `workspace/source/opencode/packages/opencode/src/provider/auth.ts` | consumes plugin `auth` exports | `Plugin.list()` -> auth hook map |
| `workspace/source/opencode/packages/opencode/src/provider/provider.ts` | applies plugin `auth.loader(...)` output to provider options | `plugin.auth.loader(...)` |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Hooks` | interface | `packages/plugin/src/index.ts` | declares the full plugin extension contract |
| `TriggerName` | type filter | `packages/opencode/src/plugin/index.ts` | narrows `Plugin.trigger(...)` to hooks with `(input, output) => Promise<void>` signature |
| `Plugin.Service` | service | `packages/opencode/src/plugin/index.ts` | owns the instance-scoped loaded hook list |
| `applyPlugin(...)` | loader helper | `packages/opencode/src/plugin/index.ts` | normalizes v1 and legacy server plugin exports into loaded `Hooks` objects |
| `Plugin.trigger(name, input, output)` | hook runner | `packages/opencode/src/plugin/index.ts` | sequentially executes a named hook chain and returns the mutated output object |
| `plugin.list()` / `Plugin.list()` | registry accessor | `packages/opencode/src/plugin/index.ts` | exposes loaded hook objects to non-trigger consumers such as tool/auth registries |

## Initialization / Entry

`Plugin.Service` builds an instance-scoped `hooks: Hooks[]` list during `Plugin.init()` / first service access.

Initialization sequence:

1. load built-in server plugins,
2. resolve and import configured external server plugins,
3. execute each plugin factory and append its `Hooks` object to the ordered `hooks[]` array,
4. invoke optional `config(...)` hooks with the current config,
5. subscribe optional `event(...)` hooks to the shared bus,
6. expose `trigger(...)` and `list()` for downstream runtime modules.

The `hooks[]` ordering is intentionally deterministic because both registration and later trigger dispatch use the same array order.

## Main Control Flow

### 1. Classify Hook Surfaces

The declared `Hooks` interface contains both trigger-style and non-trigger entries.

Trigger-style entries:

- are typed as `(input, output) => Promise<void>`,
- are included in `TriggerName`,
- and are callable through `Plugin.trigger(...)`.

Non-trigger entries:

- `tool`
- `auth`
- `config`
- `event`

These do not participate in `TriggerName`. They are consumed through explicit registry logic or bus wiring.

### 2. Load Hooks Into Runtime

`applyPlugin(...)` accepts both modern v1 plugin modules and legacy server-plugin exports, executes the server factory, and stores the resulting `Hooks` object in the ordered `hooks[]` list.

After load:

- `config(...)` is called once per hook object,
- `event(...)` is attached to `bus.subscribeAll()`,
- everything else remains dormant until a runtime module explicitly triggers or reads it.

### 3. Dispatch Trigger Hooks

`Plugin.trigger(...)` performs a simple sequential loop:

1. read the current `hooks[]` array from instance state,
2. for each hook object, look up `hook[name]`,
3. skip missing implementations,
4. await the hook with the shared `input` and `output`,
5. return the same `output` object after the loop finishes.

This means hook composition happens by in-place mutation rather than by returning replacement values.

### 4. Observed Trigger Hooks In Runtime

| Hook | Trigger file / symbol | Mutable output | Runtime role |
| --- | --- | --- | --- |
| `tool.definition` | `packages/opencode/src/tool/registry.ts`, `ToolRegistry.tools(...)` | `{ description, parameters }` | rewrites tool schema before model exposure |
| `tool.execute.before` | `packages/opencode/src/session/prompt.ts`, wrapped tool/MCP/task execution | `{ args }` | rewrites tool-call arguments before execution |
| `tool.execute.after` | `packages/opencode/src/session/prompt.ts`, wrapped tool/MCP/task execution | result object | post-processes tool output, metadata, attachments |
| `chat.message` | `packages/opencode/src/session/prompt.ts`, `createUserMessage(...)` | `{ message, parts }` | rewrites user message and parts before persistence |
| `command.execute.before` | `packages/opencode/src/session/prompt.ts`, `command(...)` | `{ parts }` | rewrites resolved command prompt parts before prompt creation |
| `chat.params` | `packages/opencode/src/session/llm.ts`, `LLM.stream(...)` | `{ temperature, topP, topK, options }` | mutates provider request options |
| `chat.headers` | `packages/opencode/src/session/llm.ts`, `LLM.stream(...)` | `{ headers }` | injects provider request headers |
| `experimental.chat.system.transform` | `packages/opencode/src/session/llm.ts`, `LLM.stream(...)`; `packages/opencode/src/agent/agent.ts`, `Agent.generate(...)` | `{ system }` | rewrites system prompt lines |
| `experimental.chat.messages.transform` | `packages/opencode/src/session/prompt.ts`, main loop; `packages/opencode/src/session/compaction.ts`, compaction | `{ messages }` | rewrites message history before model conversion |
| `experimental.session.compacting` | `packages/opencode/src/session/compaction.ts`, compaction create path | `{ context, prompt }` | extends or replaces the compaction prompt |
| `experimental.text.complete` | `packages/opencode/src/session/processor.ts`, `text-end` event | `{ text }` | rewrites final assistant text before save |
| `shell.env` | `packages/opencode/src/session/prompt.ts`, `shellImpl(...)`; `packages/opencode/src/tool/bash.ts`; `packages/opencode/src/pty/index.ts` | `{ env }` | injects shell / PTY environment variables |

### 5. Non-Trigger Surfaces

| Surface | Consumption path | Purpose |
| --- | --- | --- |
| `tool` | `packages/opencode/src/tool/registry.ts` | registers plugin-defined tools into the tool registry |
| `auth` | `packages/opencode/src/provider/auth.ts`, `packages/opencode/src/provider/provider.ts`, `packages/opencode/src/cli/cmd/providers.ts` | contributes provider auth methods and provider option loaders |
| `config` | `packages/opencode/src/plugin/index.ts` | receives config once after plugin initialization |
| `event` | `packages/opencode/src/plugin/index.ts` | receives bus events through `bus.subscribeAll()` |

### 6. Defined But Not Observed As Runtime Trigger

`permission.ask` is present in the `Hooks` interface, but current runtime evidence does not show `Plugin.trigger("permission.ask", ...)`.

Observed behavior instead:

- `Permission.ask(...)` evaluates rules and publishes `permission.asked` bus events,
- UI / CLI consumers react to the bus event,
- no analyzed `packages/opencode/src` path routes permission requests through plugin-trigger dispatch.

## Upstream And Downstream Dependencies

Upstream:

- `Config` for plugin declarations
- plugin module resolution / loading pipeline
- `Bus` for event fanout
- instance state for per-project hook caches

Downstream:

- `ToolRegistry` for plugin-provided tools and `tool.definition`
- `SessionPrompt` for message / command / tool / shell hooks
- `LLM.stream(...)` for request-shaping hooks
- `SessionCompaction` and `SessionProcessor` for compaction/text hooks
- provider auth flows for `auth` exports

## Implementation Details

- `TriggerName` intentionally excludes `tool`, `auth`, `config`, and `event`, so TypeScript prevents routing those fields through `Plugin.trigger(...)`.
- `config(...)` is individually error-isolated during initialization; failures are logged and ignored.
- `event(...)` is dispatched from bus subscription side effects and is not awaited through the normal trigger pipeline.
- `Plugin.trigger(...)` itself does not isolate hook failures. A thrown error aborts the caller's runtime path.
- `tool.execute.before` / `after` wrap three execution styles in the current source: regular tools, MCP tools, and the `task` tool path.
- `experimental.chat.system.transform` is used both for normal LLM requests and for `Agent.generate(...)`, so system-prompt plugins affect more than the interactive chat loop.
- `shell.env` is shared by shell mode, the bash tool, and PTY startup, so one plugin can affect multiple shell entrypoints.

## Design Tradeoffs / Risks

- Shared mutable outputs make hook composition simple, but they also create strong ordering coupling between plugins.
- Deterministic sequential dispatch improves predictability, but hook latency is additive on hot request paths.
- Missing per-hook isolation in `Plugin.trigger(...)` means one faulty plugin can fail core flows such as tool execution or LLM request shaping.
- The extension contract is fragmented: some surfaces are trigger hooks, while others are registry fields or bus listeners.
- The presence of `permission.ask` in the interface without observed runtime triggering increases the risk of plugin-author confusion.

## Pending Verification

- Which observed hook names are documented public contracts versus internal or experimental implementation details.
- Whether `permission.ask` is a dormant legacy hook or is triggered from code paths outside the analyzed `packages/opencode/src` scope.
- Whether any external plugins depend on ordering across `tool.execute.before`, `tool.execute.after`, and `shell.env` in ways that effectively make that order part of the public contract.
