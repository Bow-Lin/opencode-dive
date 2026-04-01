# Config Module

## Module Responsibility

The config module is the runtime source of truth for:

- core `opencode` configuration schema,
- multi-layer config loading and merge precedence,
- plugin/command/agent/skill discovery from config directories,
- global versus instance-scoped config access,
- and config mutation plus invalidation.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/config/config.ts` | main config schema, loader, merge logic, update APIs, service layer | `Config.Info`, `Config.Service`, `loadGlobal`, `loadInstanceState` |
| `workspace/source/opencode/packages/opencode/src/config/paths.ts` | config path discovery, file reading, JSONC parsing, `{env:...}` / `{file:...}` substitution | `ConfigPaths.projectFiles`, `ConfigPaths.directories`, `ConfigPaths.parseText` |
| `workspace/source/opencode/packages/opencode/src/config/tui.ts` | parallel TUI-specific config loader | `TuiConfig.get()` path loading |
| `workspace/source/opencode/packages/opencode/src/config/markdown.ts` | frontmatter-backed command/agent markdown parsing | `ConfigMarkdown.parse(...)` |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Config.Info` | schema/type | `config.ts` | canonical runtime config shape |
| `Config.Service` | service | `config.ts` | Effect service for get/update/invalidate/directories |
| `loadGlobal()` | loader | `config.ts` | loads user-global config files and migrates legacy TOML |
| `loadInstanceState(ctx)` | loader | `config.ts` | builds effective per-instance config by merging all layers |
| `mergeConfigConcatArrays(...)` | merge helper | `config.ts` | merges configs while concatenating `plugin` and `instructions` arrays |
| `ConfigPaths.projectFiles(...)` | path helper | `paths.ts` | finds nearest project config files up to worktree root |
| `ConfigPaths.directories(...)` | path helper | `paths.ts` | builds config discovery directories for `.opencode` assets |
| `ConfigPaths.parseText(...)` | parser | `paths.ts` | applies substitutions then parses JSONC |

## Initialization / Entry

The module is exposed as an Effect service:

- `Config.Service`
- `Config.defaultLayer`

It is consumed both directly by CLI/server surfaces and transitively by many subsystems such as:

- `agent`
- `provider`
- `plugin`
- `tool/registry`
- `session`
- `skill`
- `file/watcher`
- `lsp`
- `format`

## Main Control Flow

### 1. Global Config

`loadGlobal()` merges:

1. `Global.Path.config/config.json`
2. `Global.Path.config/opencode.json`
3. `Global.Path.config/opencode.jsonc`

It also migrates a legacy TOML-style `Global.Path.config/config` file into JSON.

### 2. Effective Instance Config

`loadInstanceState(ctx)` builds the active config in roughly this order:

1. remote well-known config fetched from auth-linked sources
2. global config from `getGlobal()`
3. explicit file from `OPENCODE_CONFIG`
4. project config files discovered by `ConfigPaths.projectFiles("opencode", ...)`
5. config-directory overlays and markdown/plugin assets from directories returned by `ConfigPaths.directories(...)`
6. inline JSON from `OPENCODE_CONFIG_CONTENT`
7. remote account/org config from account service
8. managed config directory from `managedConfigDir()` as highest-priority admin override
9. env-driven permission/autocompact/prune adjustments and legacy compatibility rewrites

### 3. Discovery Side Effects

While processing config directories, the module also:

- loads markdown commands,
- loads markdown agents and modes,
- loads local plugin scripts,
- and kicks off dependency installation for config directories when needed.

## Upstream And Downstream Dependencies

Upstream:

- `Auth`
- `Account`
- `AppFileSystem`
- environment flags and process env
- project/worktree instance context

Downstream:

- network/server config resolution in `cli/network.ts`
- instruction loading in `session/instruction.ts`
- tool availability in `tool/registry.ts`
- provider/model configuration in `provider/provider.ts`
- agent behavior and permissions in `agent/agent.ts`

## Implementation Details

- Config text supports `{env:VAR}` and `{file:path}` substitutions before JSONC parsing.
- JSONC is accepted with trailing commas.
- Plugin path specs are normalized to file URLs when sourced from config files.
- `plugin` and `instructions` arrays are merged additively instead of replacement semantics.
- Legacy `tools` config is translated into permission rules.
- Legacy `mode` entries are folded into `agent` entries.
- Global config invalidation disposes all instances and emits a global disposed event.

## Design Tradeoffs / Risks

- Config loading mixes pure parsing with side effects like remote fetches and dependency installation, which makes the effective config pipeline powerful but non-trivial to reason about.
- There are many config sources, so precedence mistakes are a realistic debugging risk.
- The module handles both typed config and operational discovery of commands/agents/plugins, which broadens its responsibility.

## Pending Verification

- Exact precedence interaction between project `.opencode/` directory overlays and nearest `opencode.json[c]` files in real-world repos.
- Whether `managedConfigDir()` is always intended as a hard final override or can be partially bypassed by later runtime state.
