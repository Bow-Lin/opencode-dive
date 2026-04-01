# Plugins / Skills Module

## Module Responsibility

The extension system in the pinned version is hybrid rather than singular. It includes:

- server plugins that register runtime hooks,
- TUI plugins that extend the terminal UI shell,
- and skills that provide reusable instruction bundles exposed through system prompt, command listing, and the `skill` tool.

Together, these mechanisms are responsible for:

- discovering extension artifacts from config, filesystem, and remote sources,
- loading and validating extension entrypoints,
- injecting hooks or content into runtime flows,
- and enforcing compatibility and permission constraints.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/plugin/index.ts` | server plugin service, hook loading, trigger execution | `Plugin.Service`, `applyPlugin(...)`, `trigger(...)` |
| `workspace/source/opencode/packages/opencode/src/plugin/loader.ts` | plugin plan/resolve/load pipeline | `PluginLoader.plan`, `resolve`, `load` |
| `workspace/source/opencode/packages/opencode/src/plugin/shared.ts` | plugin spec parsing, entrypoint resolution, compatibility rules | `parsePluginSpecifier`, `checkPluginCompatibility`, `readV1Plugin` |
| `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/plugin/runtime.ts` | separate TUI plugin runtime and activation model | `resolveExternalPlugins`, `activatePluginEntry`, `load(api)` |
| `workspace/source/opencode/packages/opencode/src/skill/index.ts` | skill discovery and availability filtering | `Skill.Service`, `loadSkills(...)`, `available(...)` |
| `workspace/source/opencode/packages/opencode/src/skill/discovery.ts` | remote skill index pulling and caching | `Discovery.pull(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/skill.ts` | runtime skill-loading tool | `SkillTool` |
| `workspace/source/opencode/packages/opencode/src/command/index.ts` | skill-to-command exposure | loop over `skill.all()` adding `source: "skill"` commands |
| `workspace/source/opencode/packages/opencode/src/session/system.ts` | skill inventory injected into system prompt | `SystemPrompt.skills(...)` |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `Plugin.Service` | service | `plugin/index.ts` | server-side plugin registry and hook trigger surface |
| `Plugin.trigger(name, input, output)` | hook runner | `plugin/index.ts` | executes hook chain sequentially for a named extension point |
| `PluginLoader.resolve(...)` | resolver | `plugin/loader.ts` | resolves install target and entrypoint for `server` or `tui` plugins |
| `checkPluginCompatibility(...)` | validator | `plugin/shared.ts` | enforces `engines.opencode` compatibility for npm plugins |
| `Skill.Service` | service | `skill/index.ts` | discovered skill registry |
| `Skill.available(agent)` | filter | `skill/index.ts` | permission-aware available skill list |
| `Discovery.pull(url)` | loader | `skill/discovery.ts` | downloads remote skill packs from `index.json` |
| `SkillTool` | tool | `tool/skill.ts` | injects loaded skill content into runtime context |

## Initialization / Entry

### Server Plugins

`Plugin.init()` realizes the instance-scoped plugin cache. During initialization it:

1. creates an internal SDK client bound to `Server.Default().fetch(...)`,
2. loads built-in server plugins,
3. resolves config-declared external plugins from `cfg.plugin`,
4. runs each plugin factory to obtain hook objects,
5. calls optional `config(...)` hooks,
6. subscribes all hooks to bus events.

### TUI Plugins

TUI plugins are a separate runtime in `cli/cmd/tui/plugin/runtime.ts`. They are loaded when the TUI starts, not when the server/plugin service initializes.

### Skills

`Skill.Service` initializes an instance-scoped skill registry by scanning:

- global external dirs like `~/.claude` and `~/.agents`,
- project-upward external dirs,
- config directories from `Config.directories()`,
- explicit `cfg.skills.paths`,
- remote `cfg.skills.urls` pulled through `Discovery.pull(...)`.

## Main Control Flow

### 1. Resolve Plugin Artifacts

For external plugins, `PluginLoader` performs a staged pipeline:

1. normalize config spec via `Config.pluginSpecifier(...)`,
2. resolve install target from file path or npm package,
3. derive entrypoint for `server` or `tui`,
4. validate compatibility through `engines.opencode`,
5. import the module.

Compatibility constraints include:

- deprecated built-in-replacement packages are skipped,
- npm plugins may be rejected if their supported opencode range does not match,
- path plugins must explicitly expose IDs in the modern plugin shape.

### 2. Register Runtime Hooks

Server plugins ultimately produce `Hooks` objects.

Those hooks are stored in deterministic order and triggered sequentially through `Plugin.trigger(...)`.

Observed hook surfaces in the runtime include:

- `tool.definition`
- `tool.execute.before`
- `tool.execute.after`
- `experimental.chat.messages.transform`
- compaction/chat/system-related hooks
- generic `event` and `config` notifications

### 3. Discover Skills

Skills are Markdown-based instruction packages with `SKILL.md`.

`Skill.loadSkills(...)` parses frontmatter and content, deduplicates by skill name, records base directories, and exposes each skill as:

- structured `Skill.Info`,
- available skill list filtered by permission,
- a source for command exposure,
- a source for system-prompt skill inventory,
- and content loadable at runtime through `SkillTool`.

### 4. Expose Skills Into Runtime

Skills influence runtime through three paths:

1. `SystemPrompt.skills(agent)` advertises available skills in the model prompt.
2. `Command.Service` exposes each skill as a `source: "skill"` command if no command name collision exists.
3. `SkillTool` loads full skill content on demand, asks for `skill` permission, and injects content plus sampled file listings into the conversation.

### 5. Activate TUI Plugins Separately

TUI plugins use the same shared plugin-spec resolution primitives, but they are activated in a UI-specific runtime with:

- plugin metadata tracking,
- local enable/disable state,
- theme installation,
- route/slot/keybind registration,
- deterministic activation order.

This is related to, but distinct from, server plugin hooks.

## Upstream And Downstream Dependencies

Upstream:

- `Config` for `plugin` specs and skill paths/URLs
- filesystem/global home/project directories
- `Flag.OPENCODE_PURE` and other feature flags

Downstream:

- runtime modules that call `Plugin.trigger(...)`
- `Bus` event fanout into plugins
- `Command`, `SystemPrompt`, and `SkillTool` for skill exposure
- TUI plugin runtime for UI-side extension activation

## Implementation Details

- Server plugins and TUI plugins share spec/entrypoint resolution logic but run in different runtimes.
- Server plugin hook execution is deliberately sequential to keep ordering deterministic.
- `Flag.OPENCODE_PURE` disables external plugins in both server and TUI plugin runtimes.
- Remote skills are pulled via an index-driven cache, not arbitrary recursive remote browsing.
- Duplicate skill names are tolerated with warnings, with the later loaded definition overwriting the earlier one in the in-memory map.

## Design Tradeoffs / Risks

- The extension surface is powerful but fragmented across hooks, TUI plugins, skills, commands, MCP prompts, and config overlays.
- Deterministic sequential plugin execution simplifies reasoning but can make plugin-heavy startup slower.
- Skills are simpler than plugins operationally, but they still affect prompt behavior, command listings, and permission surfaces, so they are not “just docs”.
- Shared plugin resolution logic for server and TUI reduces duplication, but the existence of two plugin runtimes means extension behavior is context-sensitive.

## Pending Verification

- Which plugin hooks are considered stable public extension contracts versus internal experimental hooks.
- How frequently remote skill URLs are used in ordinary workflows compared with local skill directories.
