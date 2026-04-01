# Tool Call Execution Flow

## Trigger

The model decides to call a tool during a `SessionPrompt` generation step, after Opencode has already assembled the session-scoped tool map for that request.

## Start File / Symbol

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- key symbols:
  - internal `resolveTools(...)`
  - `handle.process(...)`

## Ordered Execution Steps

1. `SessionPrompt` asks `ToolRegistry.tools(...)` for the tool definitions available to the current model and agent.
2. `SessionPrompt.resolveTools(...)` wraps each returned definition as an AI SDK `tool({...})`, building a `Tool.Context` with session/message/permission callbacks.
3. `LLM.stream(...)` receives that tool map, removes user-disabled and permission-disabled tools, and passes the filtered set to `streamText(...)` as `tools` plus `activeTools`.
4. When the model begins a tool call, stream events such as `tool-input-start` and `tool-call` reach `SessionProcessor`, which creates or updates a `MessageV2.ToolPart` in `pending` then `running` state.
5. The AI SDK invokes the wrapped tool `execute(...)` function.
6. Opencode runs `tool.execute.before` hooks, executes the concrete tool, normalizes attachments and metadata, then runs `tool.execute.after` hooks.
7. The resulting structured payload is emitted back through the stream as `tool-result` or `tool-error`.
8. `SessionProcessor` updates the same `MessageV2.ToolPart` to `completed` or `error`, including input, output, metadata, timing, and attachments.
9. The model loop continues with the tool result now present in the conversation state.

## State Transitions

- registry definitions become session-bound AI SDK tools
- eligible tools become `activeTools` after permission and user override filtering
- tool part state progresses:
  - `pending`
  - `running`
  - `completed` or `error`
- execution metadata can be updated mid-flight through `ctx.metadata(...)`

## External Boundaries

- AI SDK tool boundary at `tool({...})` / `streamText(...)`
- permission boundary through `Permission.ask(...)`
- plugin hook boundary through `tool.execute.before` and `tool.execute.after`
- optional MCP boundary for externally supplied tools

## Failure / Branching Behavior

- Invalid tool arguments fail at the `Tool.define(...)` wrapper before the underlying tool logic runs.
- `LLM.experimental_repairToolCall(...)` can lowercase mismatched tool names or reroute broken calls to the `invalid` tool.
- Repeated identical tool calls trigger the doom-loop permission check in `SessionProcessor`.
- Permission or question rejection marks the processor as blocked and ends the current step differently from a normal tool failure.
- LiteLLM-style proxies may receive a synthetic `_noop` tool when the history already contains tool calls but no real tools are active.
- GitLab workflow models use a custom `toolExecutor` path, but still target the same session tool map.

## Evidence Table

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 1 | `workspace/source/opencode/packages/opencode/src/tool/registry.ts` | `ToolRegistry.tools(...)` | builds initialized tool defs for model + agent |
| 2 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | internal `resolveTools(...)` | binds defs to session-aware AI SDK tools |
| 3 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | local `resolveTools(...)` | removes disabled tools before provider call |
| 4 | `workspace/source/opencode/packages/opencode/src/session/processor.ts` | `handleEvent(...)` | records `tool-input-start` and `tool-call` |
| 5 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | wrapped `execute(args, options)` | execution adapter into concrete tool logic |
| 6 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `plugin.trigger("tool.execute.before/after", ...)` | hookable execution lifecycle |
| 7 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | `streamText(...)` | tool result returns through model stream |
| 8 | `workspace/source/opencode/packages/opencode/src/session/processor.ts` | `tool-result` / `tool-error` cases | final message-part state writeback |

## Pending Verification

- Exact differences between normal AI SDK tool streaming and the GitLab workflow `toolExecutor` path under real traffic.
- Whether any providers materially alter tool-result event ordering.
