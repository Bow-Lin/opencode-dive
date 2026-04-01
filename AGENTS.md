# AGENTS.md

## Mission

This repository is an agent-friendly analysis workbench for studying one specific version of Opencode.

Primary goals:

- Analyze a pinned Opencode version from overall architecture down to concrete code paths.
- Produce durable technical documentation in `docs/en/` and `docs/zh/`.
- Keep transient findings, open questions, and rough notes in `reports/`.
- Make every important conclusion traceable to concrete code evidence.

## Scope

In scope:

- Repository inventory
- Entrypoints and startup flow
- Module boundaries
- Key call flows
- Concrete implementations of critical types, functions, and runtime paths
- Version-to-version structural differences when explicitly requested

Out of scope unless a task file says otherwise:

- Refactoring or changing Opencode business logic
- Product redesign proposals detached from code evidence
- Broad summaries that do not cite files, symbols, and control flow

## Working Rules

1. Treat `docs/en/` and `docs/zh/` as the mirrored long-term knowledge base and `reports/` as disposable working output.
2. Read `OPENCODE_VERSION.md` before deep analysis. If version metadata is incomplete, state that limitation explicitly.
3. Start global, then narrow:
   - repository metadata and top-level layout
   - entrypoints and bootstrap path
   - module boundaries
   - end-to-end call flows
   - implementation details
4. Every conclusion should point back to code with file paths and symbol names.
5. Distinguish clearly between:
   - Confirmed: supported directly by code evidence
   - Inferred: strong interpretation from multiple code signals
   - Unknown: not yet verified
6. Do not describe a module only by folder names. Explain responsibilities, key types, and upstream/downstream dependencies.
7. Do not present speculative claims as facts. Mark unresolved points as `Pending verification`.
8. Prefer updating existing canonical docs over creating duplicative notes.
9. When promoting stable conclusions, keep English and Chinese final docs structurally aligned.

## Required Workflow

For a new analysis pass:

1. Read:
   - `README.md`
   - `OPENCODE_VERSION.md`
   - `docs/en/overview.md` or `docs/zh/overview.md`
   - `docs/en/analysis-rules.md` or `docs/zh/analysis-rules.md`
   - the relevant file in `tasks/`
2. Generate or refresh the repository inventory.
3. Locate entrypoints and initialization logic.
4. Trace the target flow/module through concrete symbols and call sites.
5. Write findings to `reports/run-YYYY-MM-DD/` first if they are exploratory.
6. Promote stable conclusions into `docs/en/` and `docs/zh/` using the templates in `templates/`.
7. Update open questions when evidence is incomplete.

## Output Contracts

Each module analysis in `docs/{en,zh}/modules/` must contain:

- Module responsibility
- Key files
- Key types and functions
- Initialization or entry path
- Main control flow
- Upstream and downstream dependencies
- Important implementation details
- Design tradeoffs or risks
- Pending verification items

Each call-flow analysis in `docs/{en,zh}/callflows/` must contain:

- Trigger
- Start file/symbol
- Ordered steps through the system
- State transitions
- External/tool/model boundaries
- Failure handling or branching
- Evidence table with file references

## Directory Conventions

- `docs/en/`: English durable knowledge after review
- `docs/zh/`: Chinese durable knowledge after review
- `tasks/`: bounded analysis tasks with input scope and exit criteria
- `templates/`: required structure for repeatable output
- `reports/`: run-scoped exploratory artifacts
- `scripts/`: helper scripts for inventory, grep, and diff work
- `workspace/source/`: checked-out Opencode source for the target version
- `workspace/notes/`: temporary scratch notes

## Editing Constraints

- Default to read-only analysis of Opencode source.
- Do not modify `workspace/source/` unless the task is explicitly about instrumentation or local analysis helpers.
- Prefer adding analysis docs or scripts in this repository over annotating the target source tree.
- Keep documents concise, technical, and code-anchored.

## Acceptance Criteria

An analysis task is complete only when:

- the target scope is covered,
- the output matches the relevant template,
- important claims cite code evidence,
- open questions are listed explicitly,
- and the result is placed in the correct long-term or run-scoped location.
