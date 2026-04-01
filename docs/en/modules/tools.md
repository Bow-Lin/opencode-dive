# Tools Module

## Module Responsibility

The tools module is the capability layer that lets Opencode expose concrete runtime actions to the model. In the pinned version it is responsible for:

- defining the common tool contract,
- assembling the active tool registry from built-ins, config directories, and plugins,
- selecting a model-compatible tool surface,
- executing tool calls inside session context,
- and normalizing tool results back into the session loop.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/tool/tool.ts` | common tool contract, argument validation, automatic output truncation | `Tool.Context`, `Tool.Def`, `Tool.Info`, `Tool.define(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/registry.ts` | built-in/custom/plugin tool discovery and model-aware filtering | `ToolRegistry.Service`, `all(...)`, `tools(...)` |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | session-scoped tool adapter construction with permission and metadata callbacks | internal `resolveTools(...)` |
| `workspace/source/opencode/packages/opencode/src/session/llm.ts` | final active-tool filtering and AI SDK `streamText(...)` handoff | local `resolveTools(...)`, `streamText(...)` |
| `workspace/source/opencode/packages/opencode/src/session/processor.ts` | tool event lifecycle tracking inside assistant messages | `tool-input-start`, `tool-call`, `tool-result`, `tool-error` handling |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Tool.Context` | type | `tool.ts` | runtime context passed into every tool execution |
| `Tool.Def` | type | `tool.ts` | executable tool contract with schema + `execute(...)` |
| `Tool.Info` | type | `tool.ts` | registry-facing tool descriptor with lazy `init(...)` |
| `Tool.define(id, init)` | helper | `tool.ts` | wraps validation and truncation around concrete tools |
| `ToolRegistry.Service` | service | `registry.ts` | provides `register`, `ids`, and `tools(...)` |
| `ToolRegistry.tools(...)` | registry query | `registry.ts` | builds initialized tool defs for a given model/agent |
| `SessionPrompt.resolveTools(...)` | adapter builder | `prompt.ts` | converts registry definitions into AI SDK tools with session context |
| `LLM.resolveTools(...)` | filter | `llm.ts` | removes user-disabled or permission-disabled tools before model call |
| `SessionProcessor.Handle.partFromToolCall(...)` | lookup | `processor.ts` | lets execution callbacks update the matching tool part |

## Initialization / Entry

The tool layer is not bootstrapped as a standalone command. It becomes active when `SessionPrompt` prepares a model call and asks `ToolRegistry.Service` for the tools available to the current model and agent.

There are three practical entry points:

1. `Tool.define(...)` for declaring a tool.
2. `ToolRegistry.tools(...)` for discovering and initializing tools.
3. `SessionPrompt.resolveTools(...)` for wiring those tools into a live session execution context.

## Main Control Flow

### 1. Declare Tool Contract

Concrete tools are expressed through `Tool.define(id, init|def)`.

That wrapper adds two shared behaviors:

1. validate arguments with the tool's Zod schema before execution;
2. truncate long textual output through `Truncate.output(...)` unless the tool already marked `metadata.truncated`.

### 2. Build Tool Registry

`ToolRegistry.Service` builds the available tool universe from:

- built-in tool modules such as `bash`, `read`, `glob`, `grep`, `task`, `webfetch`, `todowrite`, `skill`, and `apply_patch`,
- optional feature-flagged tools such as `lsp`, `batch`, and `plan_exit`,
- config-directory scripts under `tool/*.{js,ts}` or `tools/*.{js,ts}`,
- plugin-provided tool definitions exposed through `plugin.list()`,
- and runtime registrations via `ToolRegistry.register(...)`.

Both config-directory and plugin tools are normalized through the same `fromPlugin(...)` adapter into `Tool.Info`.

### 3. Filter By Model / Environment

Before tools are initialized, `ToolRegistry.tools(...)` applies model-aware filtering:

- `codesearch` and `websearch` are only exposed for the `opencode` provider or when `OPENCODE_ENABLE_EXA` is enabled;
- `apply_patch` is preferred for compatible GPT-family models;
- `edit` and `write` are hidden when `apply_patch` is used instead.

Each surviving tool is then initialized and passed through `plugin.trigger("tool.definition", ...)`, which allows plugins to mutate descriptions or schemas before model exposure.

### 4. Bind Tool To Session Context

`SessionPrompt.resolveTools(...)` turns each registry definition into an AI SDK `tool({...})`.

For every execution it constructs a `Tool.Context` carrying:

- `sessionID`, `messageID`, `callID`,
- active agent name,
- current model metadata in `extra.model`,
- the current message history,
- a `metadata(...)` callback that updates the matching `MessageV2.ToolPart`,
- and an `ask(...)` callback that routes permission prompts through `Permission.ask(...)`.

This is the real boundary where a static tool definition becomes a session-bound executable capability.

### 5. Execute And Return Results

When the model issues a tool call:

1. the AI SDK calls the `execute(...)` function created in `SessionPrompt.resolveTools(...)`;
2. Opencode emits `tool.execute.before` plugin hooks;
3. the concrete tool's `execute(args, ctx)` runs;
4. attachments are normalized with generated part IDs and message/session linkage;
5. Opencode emits `tool.execute.after` hooks;
6. the structured result returns to the model loop.

MCP tools are adapted separately in the same function, but they follow the same session-bound pattern plus an explicit permission prompt through `ctx.ask(...)`.

## Upstream And Downstream Dependencies

Upstream:

- `Config` for config-directory discovery and dependency installation
- `Plugin` for plugin tool definitions and lifecycle hooks
- `Provider` / selected model metadata for tool filtering and schema transforms
- `Permission` for execution gating

Downstream:

- `session/prompt.ts` for execution-context binding
- `session/llm.ts` for final active-tool filtering and provider handoff
- `session/processor.ts` for message-part state tracking
- provider SDK calls through AI SDK `streamText(...)`

## Implementation Details

- Plugin/config tools are converted into first-class `Tool.Info` entries rather than handled as a separate runtime path.
- Tool schemas are transformed through `ProviderTransform.schema(...)` before being sent to the model, so tool exposure is provider-aware.
- `SessionPrompt.resolveTools(...)` updates in-flight tool metadata through `processor.partFromToolCall(...)`, which lets tools stream title/metadata changes into the assistant message record.
- `LLM.resolveTools(...)` applies one more filter layer using merged agent/session permissions plus per-user `tools` overrides.
- For LiteLLM-style proxies, `LLM.stream(...)` injects a `_noop` tool when the history contains tool calls but the active tool set is empty, avoiding proxy validation failures.
- For `GitLabWorkflowLanguageModel`, `LLM.stream(...)` supplies a `toolExecutor` that directly reuses the same tool map instead of relying only on normal AI SDK tool-call transport.

## Design Tradeoffs / Risks

- Tool behavior is distributed across registry, prompt, LLM, and processor layers; debugging a bad tool call often requires reading all four.
- Model-aware filtering improves compatibility but means the visible tool surface is not globally stable across models.
- Config-directory tools and plugin tools are powerful extension points, but they make the active runtime surface environment-sensitive.
- Tool metadata and permission behavior depend on session-scoped callbacks, so tools are not pure functions even when their business logic looks simple.

## Pending Verification

- Whether any built-in tools bypass `Tool.define(...)` and therefore skip the standard validation/truncation wrapper.
- How often MCP tool exposure is used in ordinary CLI sessions versus specialized integrations.
