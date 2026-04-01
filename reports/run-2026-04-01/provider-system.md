# Provider System

## Goal

Explain how Opencode selects providers/models and issues model calls.

## Provider Registry Construction

The active registry is built in `packages/opencode/src/provider/provider.ts`.

Observed inputs:

- `ModelsDev.get()` base provider catalog
- config-defined provider/model overrides
- env-derived activation through provider env vars
- stored auth credentials
- plugin auth loaders
- custom provider loaders and discovery hooks

Observed filtering:

- `disabled_providers`
- `enabled_providers`
- provider whitelist/blacklist
- alpha/deprecated model filtering

## Model Selection Paths

### Explicit Selection

- user input may provide a concrete `provider/model`
- command config may provide a concrete model
- agent config may bind a model

### Implicit Selection

- last model used in the session
- `Provider.defaultModel()` if no session/user override exists
- `Provider.getSmallModel()` for auxiliary small-model tasks

## Runtime Invocation Path

1. `SessionPrompt` chooses a model identifier.
2. `provider.getModel(...)` resolves normalized model metadata.
3. `LLM.stream(...)` asks `Provider.getLanguage(model)` for an executable language model.
4. `Provider.getLanguage(...)` resolves the provider SDK and caches the model object.
5. `ProviderTransform` normalizes messages/options/tool settings.
6. `streamText(...)` executes the actual provider call.

## Auth Integration

Provider auth is split out into `provider/auth.ts`.

Capabilities include:

- listing provider auth methods
- initiating OAuth authorization
- handling OAuth callbacks
- reusing stored API keys or OAuth tokens during model calls

Provider auth state also feeds provider activation and option construction.

## Key Behaviors

- bundled providers are used directly for known SDK packages
- unknown/local providers can be installed or imported dynamically
- provider-specific `baseURL`, headers, timeout, chunk timeout, and API key injection are normalized before model creation
- small-model and default-model selection are config-aware

## Key Conclusions

- Provider selection is not a simple static map; it is a dynamically assembled registry.
- The real provider execution boundary sits between `LLM.stream(...)` and `Provider.getLanguage(...)`.
- `ProviderTransform` is a critical part of provider behavior, not just cosmetic post-processing.

## Open Questions

- Which provider-specific transforms are mandatory for correctness versus optional optimization.
- Whether dynamic provider installation is used in ordinary local workflows or mainly for extension scenarios.
