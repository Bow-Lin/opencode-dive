# Opencode Analysis Workbench

This repository is a structured workspace for sustained analysis of a specific Opencode version.

The goal is not to keep knowledge in chat history. The goal is to keep versioned analysis assets in the repository so an agent can repeatedly inspect source code, build architectural understanding, and produce traceable technical documentation.

## Layout

- `AGENTS.md`: agent operating rules and output contracts
- `OPENCODE_VERSION.md`: pinned analysis target
- `docs/en/`: English final deliverables
- `docs/zh/`: Chinese final deliverables
- `tasks/`: bounded analysis tasks
- `templates/`: reusable writing templates
- `reports/`: run-scoped intermediate findings
- `scripts/`: repo understanding helpers
- `workspace/source/`: target Opencode checkout
- `workspace/notes/`: scratch notes

## Recommended Workflow

1. Fill in `OPENCODE_VERSION.md`.
2. Place the target Opencode source under `workspace/source/`.
3. Run `tasks/01-repo-inventory.md` and save rough findings to `reports/`.
4. Confirm entrypoints and startup flow.
5. Promote stable findings into `docs/en/` and `docs/zh/`.

## Ground Rules

- Treat `docs/en/` and `docs/zh/` as the mirrored system of record.
- Treat `reports/` as noisy working output.
- Keep every important claim tied to file paths, symbols, and call sites.
- Mark uncertain conclusions as pending verification.
