# Repository Map

## Analysis Repository

This repository is the analysis control plane, not the Opencode source itself.

### Top-Level Directories

- `docs/`: curated technical knowledge
- `tasks/`: bounded analysis tasks
- `templates/`: stable output formats
- `reports/`: run-scoped findings
- `scripts/`: helper automation
- `workspace/source/`: target source checkout
- `workspace/notes/`: scratch notes

## Target Source Repository Map

The pinned source repository is a Bun/TypeScript monorepo rooted at `workspace/source/opencode`.

### Metadata

- Package/build files:
  - `workspace/source/opencode/package.json`
  - `workspace/source/opencode/bunfig.toml`
  - `workspace/source/opencode/tsconfig.json`
  - `workspace/source/opencode/turbo.json`
  - `workspace/source/opencode/sst.config.ts`
  - `workspace/source/opencode/bun.lock`
- App/runtime entrypoints:
  - Root dev script points at `packages/opencode/src/index.ts`
  - Package bin entry is `packages/opencode/bin/opencode`
- Test directories:
  - `workspace/source/opencode/packages/opencode/test`
  - package-local test/e2e directories in `packages/app`, `packages/enterprise`, and others
- Config files:
  - root `package.json`, `bunfig.toml`, `tsconfig.json`, `turbo.json`
  - repo-local `.opencode/opencode.jsonc` and `.opencode/tui.json`

### Top-Level Source Areas

| Path | Responsibility | Confidence | Notes |
| --- | --- | --- | --- |
| `workspace/source/opencode/packages/opencode` | Primary CLI/server/runtime package for the coding agent | High | Contains `bin/`, `src/`, `migration/`, and dense test coverage |
| `workspace/source/opencode/packages/app` | Web application client | High | Separate app package under monorepo workspace |
| `workspace/source/opencode/packages/web` | Marketing/site surface and assets | Medium | Versioned package distinct from `app` |
| `workspace/source/opencode/packages/desktop` | Desktop app shell | High | Tauri-based package with `src-tauri` |
| `workspace/source/opencode/packages/desktop-electron` | Electron desktop variant | High | Separate desktop runtime packaging |
| `workspace/source/opencode/packages/console` | Console-oriented surfaces and backend pieces | Medium | Split into `app`, `core`, `function`, `mail`, `resource` |
| `workspace/source/opencode/packages/plugin` | Plugin SDK/runtime support package | High | Distinct workspace package plus core plugin code in `packages/opencode/src/plugin` |
| `workspace/source/opencode/packages/sdk/js` | JavaScript SDK | High | SDK surface for external integration |
| `workspace/source/opencode/packages/ui` | Shared UI components | High | Shared component package |
| `workspace/source/opencode/packages/util` | Shared utilities | High | Common helper package |
| `workspace/source/opencode/script` | Repo automation and release scripts | High | TypeScript scripts for publish, changelog, stats, etc. |
| `workspace/source/opencode/infra` | Infrastructure definitions | High | SST-oriented deployment definitions |
| `workspace/source/opencode/github` | GitHub action/package integration | Medium | Separate package with its own `package.json` |
| `workspace/source/opencode/.opencode` | Repo-local agent commands, tools, themes, glossary | High | Operational config and dogfooding assets, not the main runtime source |

### Primary Package Map: `packages/opencode/src`

The main package is already partitioned into subsystem directories, including:

- `agent`
- `bus`
- `cli`
- `command`
- `config`
- `control-plane`
- `mcp`
- `plugin`
- `project`
- `provider`
- `server`
- `session`
- `skill`
- `storage`
- `tool`
- `worktree`

This package structure suggests the core analysis target is `packages/opencode/src`, while other workspace packages provide clients, SDKs, and deployment surfaces.

## Key Entrypoints

Initial inventory-level entrypoint candidates identified before detailed entrypoint tracing:

| File | Symbol | Role | Verified |
| --- | --- | --- | --- |
| `workspace/source/opencode/package.json` | `scripts.dev` | Root dev command points execution to the main package | Yes |
| `workspace/source/opencode/packages/opencode/package.json` | `bin.opencode` | Published CLI binary mapping | Yes |
| `workspace/source/opencode/packages/opencode/src/index.ts` | `TBD` | Likely runtime/dev entry module | Pending |
| `workspace/source/opencode/packages/opencode/bin/opencode` | `TBD` | CLI launch script | Pending |
