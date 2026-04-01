# Prompt To Model Call Flow

## Trigger

A session mutation endpoint or CLI command asks Opencode to send a prompt to a model, typically through `SessionPrompt.prompt(...)` or command/shell variants built on the same service.

## Start File / Symbol

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- key symbols:
  - `SessionPrompt.prompt`
  - `SessionPrompt.createUserMessage`
  - internal `getModel(...)`

## Ordered Execution Steps

1. A caller chooses or creates a session and invokes `SessionPrompt.prompt(...)` directly or through a server route.
2. `SessionPrompt.createUserMessage(...)` resolves the effective agent and model:
   - explicit input model
   - agent-bound model
   - last session model
   - or `Provider.defaultModel()`
3. `SessionPrompt` validates the model via `provider.getModel(providerID, modelID)`.
4. The prompt pipeline assembles user message parts, instructions, system prompt segments, and session history.
5. `SessionPrompt` delegates generation/streaming to `LLM.stream(...)`.
6. `LLM.stream(...)` resolves:
   - `Provider.getLanguage(input.model)`
   - `Config.get()`
   - `Provider.getProvider(input.model.providerID)`
   - `Auth.get(input.model.providerID)`
7. `Provider.getLanguage(...)` resolves or caches an SDK-backed language model, using bundled or dynamically loaded provider implementations.
8. `ProviderTransform` prepares provider-specific message and option transformations.
9. `streamText(...)` from the AI SDK is called with:
   - model
   - transformed messages
   - provider options
   - active tools
   - headers and retries
10. Streaming events return to `SessionPrompt`, which continues the session loop and downstream processing.

## State Transitions

- session user message is created with concrete agent/model metadata
- model selection becomes fixed for that message
- provider/model metadata is resolved into an executable language model instance
- downstream loop consumes streamed model output

## External Boundaries

- provider SDK boundary in `Provider.getLanguage(...)`
- upstream provider HTTP boundary inside AI SDK calls
- auth boundary through stored API keys or OAuth access tokens

## Failure / Branching Behavior

- Missing provider/model yields `Provider.ModelNotFoundError`, which `SessionPrompt` translates into a session error event with suggestions when possible.
- Explicit `small` tasks use `Provider.getSmallModel(...)` / `ProviderTransform.smallOptions(...)`.
- Provider-specific auth or transport behavior may alter headers, base URLs, response APIs, or streaming behavior.

## Evidence Table

| Step | File | Symbol | Notes |
| --- | --- | --- | --- |
| 2 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `createUserMessage(...)` | resolves agent and model for the new user message |
| 3 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `getModel(...)` | validates selected provider/model |
| 5 | `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | `LLM.stream(...)` call sites | handoff into provider-backed generation |
| 6 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | `LLM.stream(...)` | resolves provider/config/auth dependencies |
| 7 | `workspace/source/opencode/packages/opencode/src/provider/provider.ts` | `getLanguage(...)` | resolves cached/bundled/dynamic SDK model |
| 8 | `workspace/source/opencode/packages/opencode/src/provider/transform.ts` | `ProviderTransform.*` | provider-specific message/option shaping |
| 9 | `workspace/source/opencode/packages/opencode/src/session/llm.ts` | `streamText(...)` | final model invocation boundary |

## Pending Verification

- Exact event sequence between streamed model output and tool execution loops in long-running sessions.
- Whether some providers bypass standard `sdk.languageModel(...)` and materially change downstream behavior.
