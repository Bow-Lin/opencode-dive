# Inventory Report

## Version Context

- Target version: `1.3.13`
- Commit: `c8ecd640220331ce7695d72ea8c618dd8909eab1`
- Tag/Describe: `v1.3.13-4-gc8ecd6402`
- Source root: `workspace/source/opencode`

## Repository Identity

- Repository description from root `README.md`: "The open source AI coding agent."
- Monorepo manager: Bun workspaces
- Root package manager: `bun@1.3.11`
- Primary language/runtime signal: TypeScript + Bun

## Top-Level Inventory

| Path | Type | Notes |
| --- | --- | --- |
| `package.json` | workspace metadata | Root scripts, workspace package definitions, repo metadata |
| `packages/` | product and library workspaces | Main code surface; includes CLI/runtime, app, desktop, sdk, plugin, ui, util |
| `script/` | repo automation | Release, changelog, formatting, stats, sync tasks |
| `infra/` | infrastructure code | SST-oriented deployment/app definitions |
| `github/` | GitHub action/package | Separate package with its own build metadata |
| `.opencode/` | repo-local agent assets | Commands, tools, plugins, themes, glossary, local config |
| `sdks/` | external SDK-related assets | Includes `sdks/vscode` |
| `nix/` | packaging/integration | Nix expressions and hashes |
| `patches/` | dependency patches | Patched third-party packages |
| `specs/` | repo specs | Contains high-level project spec material |

## Build And Runtime Metadata

- Root build/config files:
  - `package.json`
  - `bunfig.toml`
  - `tsconfig.json`
  - `turbo.json`
  - `sst.config.ts`
  - `bun.lock`
- Main package metadata:
  - `packages/opencode/package.json`
  - `packages/opencode/bin/opencode`
- Repo documentation/control files:
  - `README.md`
  - `AGENTS.md`
  - `.opencode/opencode.jsonc`
  - `.opencode/tui.json`

## Workspace Packages

Top-level packages discovered under `packages/`:

- `app`
- `console`
- `containers`
- `desktop`
- `desktop-electron`
- `docs`
- `enterprise`
- `extensions`
- `function`
- `identity`
- `opencode`
- `plugin`
- `script`
- `sdk`
- `slack`
- `storybook`
- `ui`
- `util`
- `web`

## Main Analysis Target

The core implementation target appears to be `packages/opencode/`:

- `package.json` declares version `1.3.13`
- `bin.opencode` points to `./bin/opencode`
- root `scripts.dev` points at `packages/opencode/src/index.ts`
- `src/` is subdivided into runtime-oriented subsystems such as `agent`, `cli`, `config`, `mcp`, `plugin`, `provider`, `server`, `session`, `skill`, `storage`, `tool`, and `worktree`
- `test/` mirrors many of those subsystems, suggesting `packages/opencode` is the canonical behavioral core

## Likely Entrypoints

- Root workspace dev command:
  - `workspace/source/opencode/package.json` -> `scripts.dev` -> `bun run --cwd packages/opencode --conditions=browser src/index.ts`
- Published CLI binary:
  - `workspace/source/opencode/packages/opencode/package.json` -> `bin.opencode` -> `./bin/opencode`
- Concrete files to inspect next:
  - `workspace/source/opencode/packages/opencode/src/index.ts`
  - `workspace/source/opencode/packages/opencode/bin/opencode`

## Candidate Modules

Within `packages/opencode/src`, the strongest module candidates from directory structure are:

- `cli`
- `config`
- `provider`
- `tool`
- `session`
- `plugin`
- `skill`
- `server`
- `agent`
- `bus`
- `storage`
- `mcp`
- `worktree`

## Initial Observations

- The repo is not a single-package CLI; it is a broad monorepo with multiple clients and deployment targets.
- README explicitly describes a client/server architecture, so runtime analysis should not assume a purely local CLI-only execution model.
- The `packages/opencode/src` layout is already modular enough to support the planned task split.
- `.opencode/` is important repository context but should be treated separately from the product runtime source.

## Open Questions

- Which file is the true first process entry in normal CLI execution: `bin/opencode`, `src/index.ts`, or another bootstrap layer?
- How do `packages/console/*`, `packages/app`, and `packages/opencode` divide responsibilities at runtime?
- Which of the subsystem directories under `packages/opencode/src` are public boundaries versus internal implementation partitions?
