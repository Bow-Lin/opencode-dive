# Open Questions

## Blocking Questions

- Whether alternative interactive surfaces such as ACP or other non-session flows bypass `SessionPrompt` enough to require a second end-to-end architecture path.
- Which provider-specific execution paths materially alter tool-calling or event ordering beyond the LiteLLM and GitLab workflow branches already identified.
- Which plugin hook names should be treated as stable public extension contracts versus internal or experimental implementation details.

## Non-Blocking Questions

- Exact config precedence between project `.opencode/` directory overlays, nearby `opencode.json[c]`, account config, and managed config directories in real-world repos.
- Whether any built-in tools bypass `Tool.define(...)`.
- How often MCP tools and remote skill URLs appear in ordinary local workflows.
- How much of the web/app/desktop packages reuse the same `SDK + event stream + sync cache` pattern already confirmed in TUI.
- Whether `TodoTable`, `session_diff`, and other side data should be treated as core conversation memory or adjacent per-session state.
- Which less-common CLI commands or packaged binaries diverge from the dominant in-process `Server.Default().fetch(...)` path.
- Whether raw sync-event replay is used directly by ordinary readers, or mostly for recovery/rebuild scenarios.

## Evidence Needed

| Question | Candidate files/symbols | Next step |
| --- | --- | --- |
| Alternative orchestration path outside `SessionPrompt` | `workspace/source/opencode/packages/opencode/src/acp/agent.ts`, `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | Trace ACP request lifecycle and compare where provider execution is actually invoked. |
| Provider-specific tool/event deviations | `workspace/source/opencode/packages/opencode/src/session/llm.ts`, provider SDK adapters under `workspace/source/opencode/packages/opencode/src/provider/sdk/**` | Compare at least one non-default provider path against the generic `streamText(...)` route and record event ordering differences. |
| Stable vs experimental plugin hooks | `workspace/source/opencode/packages/opencode/src/plugin/index.ts`, all `plugin.trigger(...)` call sites | Enumerate hook names, classify by namespace/prefix, and correlate with public plugin docs if present. |
| Config precedence edge cases | `workspace/source/opencode/packages/opencode/src/config/config.ts`, `workspace/source/opencode/packages/opencode/src/config/paths.ts` | Build a precedence matrix from code and verify with targeted fixture repos/config files. |
| Tools bypassing `Tool.define(...)` | `workspace/source/opencode/packages/opencode/src/tool/*.ts` | Search every built-in tool export and verify whether it ultimately uses `Tool.define(...)`. |
| MCP and remote skill usage frequency | `workspace/source/opencode/packages/opencode/src/mcp/**`, `workspace/source/opencode/packages/opencode/src/skill/index.ts` | Review default config/docs/examples to determine whether these are core or optional extension paths. |
| Web/app/desktop interaction model parity | `workspace/source/opencode/packages/app/**`, `workspace/source/opencode/packages/web/**`, `workspace/source/opencode/packages/desktop/**` | Sample one client package each to see whether they consume the backend through SDK/events or a different state architecture. |
| Session side-state importance | `workspace/source/opencode/packages/opencode/src/session/session.sql.ts`, `workspace/source/opencode/packages/opencode/src/tool/todo*`, `workspace/source/opencode/packages/opencode/src/session/index.ts` | Trace live reads/writes for TODO and diff data during an ordinary prompt loop. |
| CLI/package startup divergence | `workspace/source/opencode/packages/opencode/bin/opencode`, `workspace/source/opencode/packages/opencode/src/index.ts`, build scripts | Compare packaged launch path against dev/runtime TS entry and note any extra bootstrap layers. |
| Direct sync replay consumers | `workspace/source/opencode/packages/opencode/src/sync/**`, server/global event routes, migration/recovery code | Search for `SyncEvent.replay` / `subscribeAll` consumers and classify production versus maintenance usage. |
