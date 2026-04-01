# Config System

## Goal

Explain how configuration is defined, loaded, validated, merged, and consumed.

## Canonical Config Surface

The main schema lives in `packages/opencode/src/config/config.ts` as `Config.Info`.

Major config areas include:

- `server`
- `command`
- `skills`
- `plugin`
- `agent`
- `provider`
- `mcp`
- `formatter`
- `lsp`
- `instructions`
- `permission`
- `compaction`
- `experimental`

There is a parallel TUI-specific config path in `packages/opencode/src/config/tui.ts`.

## Parsing And Validation

### JSONC + Substitution

`ConfigPaths.parseText(...)` performs:

1. `{env:VAR}` substitution from process env
2. `{file:path}` substitution from filesystem content
3. JSONC parsing with trailing commas allowed
4. structured error reporting with file path and line/column info

### Schema Validation

After parsing, `Config.Info.safeParse(...)` validates the shape.

Notable compatibility rewrites:

- legacy TUI keys are stripped from main config with a warning
- missing `$schema` may be added back to file-based configs
- legacy `tools` booleans are translated into permissions
- legacy `mode` entries are folded into `agent`
- `autoshare` is normalized into `share`

## Config Sources And Precedence

The effective per-instance config is built in `loadInstanceState(ctx)`.

Observed merge order:

1. remote well-known config from authenticated sources
2. global config from `loadGlobal()`
3. explicit file path from `OPENCODE_CONFIG`
4. nearest project config files from `ConfigPaths.projectFiles("opencode", ctx.directory, ctx.worktree)`
5. per-directory overlays and discovered assets from `ConfigPaths.directories(...)`
6. inline JSON from `OPENCODE_CONFIG_CONTENT`
7. remote account/org config from account service
8. managed config directory from `managedConfigDir()`
9. env flag rewrites and final normalization

Important detail:

- `mergeConfigConcatArrays(...)` makes `plugin` and `instructions` additive rather than replacement-based.

## Directory-Based Discovery

`ConfigPaths.directories(...)` returns a list including:

- `Global.Path.config`
- `.opencode` directories found upwards from the current project
- `.opencode` under the user's home path
- `OPENCODE_CONFIG_DIR` if set

For those directories, the config system can also discover:

- markdown commands
- markdown agents
- markdown modes
- local plugin scripts

This means config directories are not only passive data files; they are extension roots.

## Write / Update Paths

### Instance Update

`Config.update(config)`:

- writes merged JSON to `<instance directory>/config.json`
- disposes the current instance so the new config reloads

### Global Update

`Config.updateGlobal(config)`:

- updates whichever global config file currently exists, preferring JSONC patching when applicable
- invalidates cached global config
- disposes all instances
- emits a global disposed event

## Runtime Consumers

Representative consumers found during this pass:

| Consumer | Use |
| --- | --- |
| `cli/network.ts` | resolve serve/web network settings from global config |
| `provider/provider.ts` | provider registry/model loading and options |
| `agent/agent.ts` | agent definitions, permissions, defaults |
| `tool/registry.ts` | tool availability and config-directory tool loading |
| `session/instruction.ts` | instruction file discovery |
| `plugin/index.ts` | plugin loading |
| `skill/index.ts` | extra skill paths/URLs |
| `file/watcher.ts` | watcher ignore behavior |

## Key Conclusions

- Config is both a settings system and an extension discovery system.
- The effective config is instance-scoped even though part of it is cached globally.
- Managed config is applied last and appears to function as the strongest override layer.

## Open Questions

- How often remote well-known config and account config are expected to appear in normal local CLI usage.
- Whether any subsystems read raw files directly instead of consistently going through `Config.get()`.
