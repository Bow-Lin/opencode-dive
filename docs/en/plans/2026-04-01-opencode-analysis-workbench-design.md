# Opencode Analysis Workbench Design

> This file captures the initial repository design used to bootstrap the analysis workbench.

## Goal

Create an agent-friendly repository that supports repeated, deep analysis of one pinned Opencode version from repository inventory through concrete code-level documentation.

## Chosen Approach

Use the repository itself as the analysis harness:

- `AGENTS.md` defines operating rules.
- `docs/` stores durable knowledge.
- `tasks/` breaks large analysis goals into bounded units.
- `templates/` stabilizes output quality.
- `reports/` isolates transient findings.
- `scripts/` reduces repeated manual inspection work.
- `workspace/source/` holds the pinned Opencode checkout.

## Rejected Alternatives

### Prompt-only approach

Rejected because long-term knowledge would stay in chat history and drift across sessions.

### Docs-only approach without tasks/templates

Rejected because output quality and sequence would vary too much between agent runs.

## Initial Deliverables

- repository skeleton
- agent operating instructions
- version metadata file
- baseline docs
- starter tasks
- reusable templates
- source-analysis helper scripts
