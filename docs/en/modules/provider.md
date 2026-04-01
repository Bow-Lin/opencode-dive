# Provider Module

## Module Responsibility

The provider module is responsible for:

- building the active provider registry,
- merging model metadata from built-in catalogs, config, auth, and plugins,
- selecting default and small models,
- resolving an SDK/language model instance for a chosen model,
- and exposing provider-aware option transforms to the LLM layer.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/provider/provider.ts` | main provider registry, model lookup, SDK resolution, default/small-model selection | `Provider.Service`, `getModel`, `getLanguage`, `defaultModel` |
| `workspace/source/opencode/packages/opencode/src/provider/auth.ts` | provider-specific auth method discovery and OAuth/API token flows | `ProviderAuth.Service` |
| `workspace/source/opencode/packages/opencode/src/provider/transform.ts` | provider/model-specific option and message normalization | `ProviderTransform.options`, `ProviderTransform.smallOptions`, `ProviderTransform.message` |
| `workspace/source/opencode/packages/opencode/src/session/llm.ts` | runtime bridge from selected provider/model into `streamText(...)` | `Provider.getLanguage(...)` |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Provider.Info` | schema/type | `provider.ts` | provider-level metadata and model map |
| `Provider.Model` | schema/type | `provider.ts` | normalized model metadata/capabilities/cost/limits |
| `Provider.Service` | service | `provider.ts` | registry/query API for providers and models |
| `getModel(providerID, modelID)` | lookup | `provider.ts` | fetch validated model or raise suggestion-bearing error |
| `getLanguage(model)` | resolver | `provider.ts` | create/cache an AI SDK language model instance |
| `defaultModel()` | selector | `provider.ts` | choose model from config, recents, or sorted provider defaults |
| `getSmallModel(providerID)` | selector | `provider.ts` | choose a cheaper small model for auxiliary tasks |
| `ProviderTransform.*` | transform helpers | `transform.ts` | normalize messages and provider options for downstream SDK calls |

## Initialization / Entry

The provider module is instantiated through `Provider.defaultLayer`, which depends on:

- `Config.defaultLayer`
- `Auth.defaultLayer`

Its main runtime consumer is `SessionPrompt` / `LLM.stream`, though it is also exposed through server routes and CLI/provider commands.

## Main Control Flow

### 1. Build Provider Registry

`Provider.Service` state construction performs roughly this sequence:

1. load base provider/model catalog from `ModelsDev.get()`
2. merge config-defined provider/model overrides into that catalog
3. activate providers discovered from env variables
4. activate providers with stored API auth
5. patch provider options from auth-aware plugins
6. install custom loaders for special providers
7. filter providers/models via enabled/disabled lists, whitelist/blacklist, alpha/deprecated handling
8. optionally discover extra models for selected providers such as GitLab

### 2. Resolve Model Metadata

Once a provider is active:

- `getModel(...)` returns the normalized `Provider.Model`
- model metadata includes:
  - API package and upstream model id
  - capabilities
  - cost/limits
  - headers/options
  - generated variants

### 3. Resolve Language Model Instance

`getLanguage(model)`:

1. builds provider-specific options from config/auth/model metadata
2. resolves or creates the underlying AI SDK instance
3. applies custom loaders when a provider needs non-default model instantiation
4. caches the resulting language model per `providerID/modelID`

## Upstream And Downstream Dependencies

Upstream:

- `Config`
- `Auth`
- `Plugin`
- `ModelsDev`
- environment variables

Downstream:

- `session/prompt.ts` for model selection
- `session/llm.ts` for actual `streamText(...)` invocation
- `server/routes/provider.ts` for provider listing and OAuth flows

## Implementation Details

- Provider activation is multi-source: catalog + config + env + auth + plugin loader.
- Bundled SDKs are used when the provider package is known ahead of time; otherwise packages can be installed/imported dynamically.
- `defaultModel()` prefers explicit config, then recent model history, then a sorted provider default.
- `getSmallModel()` uses heuristics by provider family and can be overridden via `cfg.small_model`.
- `ProviderTransform` carries a large amount of provider-specific compatibility logic, including message normalization, caching hints, and provider options.

## Design Tradeoffs / Risks

- The registry builder combines catalog ingestion, auth activation, plugin-based patching, and dynamic SDK loading, which is flexible but dense.
- Provider-specific behavior is distributed between `provider.ts` and `transform.ts`, so debugging one provider can require reading both layers.
- Dynamic installs/imports increase extensibility but also make exact runtime behavior environment-sensitive.

## Pending Verification

- Which providers are most common in real user paths versus optional edge integrations.
- Whether any provider-specific loaders materially change tool-calling semantics beyond option normalization.
