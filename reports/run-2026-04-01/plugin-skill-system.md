# Plugin / Skill System

## Goal

Explain how Opencode discovers, loads, and applies plugins and skills, and record where extension behavior actually enters the runtime.

## Summary

Opencode does not have one extension mechanism. It has at least three:

1. server plugins for hook-based backend/runtime extension,
2. TUI plugins for UI-shell extension,
3. skills for reusable instruction packages.

Treating them as one abstraction would hide important lifecycle differences.

## Findings

### 1. Server plugins are hook registries, not generic modules

`Plugin.Service` loads server plugins into an ordered `hooks[]` array and exposes `Plugin.trigger(...)`.

Interpretation:

- server plugins matter only when runtime code calls a hook surface;
- they are not free-floating background modules.

### 2. External plugin loading is staged and compatibility-aware

Observed pipeline:

- plan from config spec,
- resolve install target,
- resolve `server` or `tui` entrypoint,
- validate compatibility,
- import module,
- initialize plugin.

Key constraints:

- deprecated auth plugins are skipped,
- npm plugins may be rejected by `engines.opencode`,
- path plugins must satisfy stricter ID/export expectations.

### 3. Built-in plugins are first-class

The server plugin runtime includes directly imported internal plugins such as auth-related plugins before external config plugins are processed.

Interpretation:

- the plugin layer is part of core product behavior, not only third-party customization.

### 4. Hook execution order is intentionally deterministic

Both server plugin hooks and TUI plugin activation are processed sequentially.

Interpretation:

- ordering is treated as semantically meaningful;
- this favors predictability over maximum parallel startup speed.

### 5. Skills are Markdown instruction packs, not code plugins

Skills are discovered from local directories and optional remote indexes, parsed via `ConfigMarkdown`, and stored as `Skill.Info`.

Interpretation:

- they are operationally lighter than plugins;
- but they still have runtime consequences because they affect prompts, commands, and permissions.

### 6. Skills enter runtime through three different surfaces

Observed paths:

- advertised in `SystemPrompt.skills(...)`,
- exposed as `source: "skill"` commands,
- loaded on demand via `SkillTool`.

Interpretation:

- skills are more deeply integrated than a passive reference library;
- they are a cross-cutting instruction extension surface.

### 7. Remote skill discovery is explicit and index-based

`Discovery.pull(url)` fetches `index.json`, validates that each entry contains `SKILL.md`, downloads files into cache, and returns local directories for scanning.

Interpretation:

- remote skills are supported, but only through a constrained package shape rather than arbitrary URL fetches.

### 8. TUI plugins are a separate runtime

TUI plugins reuse plugin spec/loader utilities, but activation happens in `cli/cmd/tui/plugin/runtime.ts` with UI-specific concerns:

- theme installation,
- route/slot registration,
- persisted enable/disable state,
- per-plugin metadata tracking.

Interpretation:

- “plugin support” in Opencode is split between backend runtime hooks and UI-shell augmentation.

## Key Conclusions

- Extension behavior in Opencode is hybrid, not monolithic.
- Server plugins, TUI plugins, and skills should be analyzed as separate lifecycles.
- Skills are content-driven extensions that still materially affect runtime behavior.
- Compatibility/version gating is already built into plugin resolution, especially for npm plugins.

## Open Questions

- Which currently observed hook names are stable public contracts versus internal/experimental internals.
- Whether TUI plugins and server plugins are expected to converge or remain permanently separate extension surfaces.
