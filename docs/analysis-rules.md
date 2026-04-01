# Analysis Rules

## Core Principles

1. Evidence before abstraction.
2. Entry flow before edge cases.
3. Durable docs in `docs/`, noisy exploration in `reports/`.
4. Version boundaries must be explicit.
5. Unknowns must remain visible.

## Evidence Labels

Use these labels consistently:

- `Confirmed`: direct code evidence exists and is cited.
- `Inferred`: conclusion is likely, but assembled from multiple indirect signals.
- `Pending verification`: not yet confirmed from code.

## What Counts As A Completed Module Analysis

A module is considered analyzed only when the document includes:

- module responsibility,
- concrete files,
- key classes/functions,
- how it initializes or is reached,
- its upstream/downstream dependencies,
- at least one main control path,
- and unresolved questions.

## What Counts As A Confirmed Call Flow

A call flow is confirmed only when:

- the trigger is identified,
- the first concrete entry symbol is named,
- ordered control flow steps are listed,
- branching or failure handling is noted when relevant,
- and each critical step cites the file and symbol that implements it.

## Documentation Style

- Prefer short technical paragraphs and tables over vague prose.
- Use exact file paths and symbol names.
- Separate fact from interpretation.
- Avoid generic summaries that could apply to any codebase.
