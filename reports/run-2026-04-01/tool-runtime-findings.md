# Tool System

## Goal

Explain how Opencode discovers tools, decides which ones a model can use, executes tool calls, and feeds the results back into the session runtime.

## Summary

The tool system is not a single module. It is a pipeline:

1. `tool/tool.ts` defines the shared tool contract.
2. `tool/registry.ts` builds the active tool catalog.
3. `session/prompt.ts` binds tools to a concrete session/message execution context.
4. `session/llm.ts` performs final filtering and exposes tools to `streamText(...)`.
5. `session/processor.ts` records tool lifecycle events back into message state.

## Findings

### 1. Tool definitions are standardized early

`Tool.define(...)` is the main normalization point for concrete tools.

Shared guarantees:

- arguments are validated against a Zod schema;
- invalid calls produce a corrective error message for the model;
- long outputs are truncated automatically unless a tool explicitly manages truncation itself.

Interpretation:

- individual tool files can stay focused on behavior;
- validation and output-size control are centralized rather than reimplemented per tool.

### 2. Registry assembly is multi-source

`ToolRegistry.Service` combines:

- built-in tools,
- feature-flagged tools,
- config-directory tools from `tool/` or `tools/`,
- plugin tools,
- and runtime registrations.

This means "which tools exist" is environment-dependent, not just source-tree-dependent.

### 3. The visible tool surface is model-sensitive

`ToolRegistry.tools(...)` filters tools before initialization:

- `codesearch` and `websearch` require either the `opencode` provider or `OPENCODE_ENABLE_EXA`;
- `apply_patch` replaces `edit` and `write` for some GPT-family models.

Interpretation:

- the model does not see a universal tool set;
- compatibility policy is enforced before the provider call, not after a bad tool invocation.

### 4. The real execution boundary is in `SessionPrompt.resolveTools(...)`

This function is the most important runtime bridge in the tool system.

It adds:

- session IDs,
- message IDs,
- the active agent name,
- permission prompts,
- message-history access,
- metadata update callbacks,
- plugin execution hooks,
- attachment normalization.

Without this layer, registry tools would still be static definitions rather than usable session actions.

### 5. There is a second filter pass right before model invocation

`LLM.resolveTools(...)` removes tools disabled by:

- merged agent/session permission rules,
- user-level `tools` overrides on the current message.

Interpretation:

- registry eligibility and per-request permission eligibility are intentionally separate concerns.

### 6. Tool execution is stateful inside the session processor

`SessionProcessor` treats tool calls as first-class message parts.

Observed lifecycle:

- `tool-input-start` creates a pending tool part;
- `tool-call` marks it running;
- `tool-result` writes completed output, metadata, timing, attachments;
- `tool-error` records failure and may mark the loop as blocked.

This is how tool execution becomes visible in session history and UI/server consumers.

### 7. Compatibility shims exist for provider-specific behavior

Two notable branches exist in `LLM.stream(...)`:

- LiteLLM-like proxies may receive a synthetic `_noop` tool to satisfy API validation;
- `GitLabWorkflowLanguageModel` gets a custom `toolExecutor` that directly executes Opencode tools.

Interpretation:

- tool support is not delegated entirely to the generic AI SDK abstraction;
- Opencode already carries provider/workflow-specific tool-transport logic where needed.

## Key Conclusions

- The most important boundary is not `ToolRegistry`, but `SessionPrompt.resolveTools(...)`.
- Tool execution is deeply integrated with permissions, plugins, and session-state recording.
- Tool compatibility policy is enforced in multiple places: registry filtering, per-request permission filtering, and repair/error routing.

## Open Questions

- Whether any important built-in tools bypass the common `Tool.define(...)` contract.
- How often MCP tools are active in ordinary local workflows.
- Whether provider-specific tool quirks exist beyond the LiteLLM and GitLab workflow branches already observed.
