# Memory Management Module

## Module Responsibility

Memory management in Opencode 1.3.13 is not a vector database or semantic retrieval system. It is a set of prompt-visible memory paths:

- instruction files loaded into the system prompt,
- local instruction files discovered when the `read` tool opens files,
- session transcript replay from persisted message/part rows,
- summary compaction and tool-output pruning for long sessions,
- and skill instruction packages that are advertised and loaded on demand.

## Key Files

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/session/instruction.ts` | instruction file discovery, loading, and read-time local instruction resolution | `InstructionPrompt.systemPaths(...)`, `system(...)`, `resolve(...)`, `loaded(...)`, `clear(...)` |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | main loop that assembles environment, skills, instructions, and transcript before model calls | `runLoop(...)`, `InstructionPrompt.system()`, `MessageV2.toModelMessages(...)` |
| `workspace/source/opencode/packages/opencode/src/session/llm.ts` | final provider-facing prompt assembly | `LLM.stream(...)`, system message construction, `experimental.chat.system.transform` |
| `workspace/source/opencode/packages/opencode/src/tool/read.ts` | dynamic local instruction injection triggered by file reads | `InstructionPrompt.resolve(...)`, `<system-reminder>`, `metadata.loaded` |
| `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | session transcript replay and provider-message projection | `stream(...)`, `filterCompacted(...)`, `toModelMessages(...)` |
| `workspace/source/opencode/packages/opencode/src/session/compaction.ts` | summary compaction and old tool-output pruning | `SessionCompaction.process(...)`, `prune(...)` |
| `workspace/source/opencode/packages/opencode/src/config/config.ts` | config-level instruction declaration and merge semantics | `instructions`, `mergeConfigConcatArrays(...)` |
| `workspace/source/opencode/packages/opencode/src/skill/index.ts` | skill instruction discovery and in-memory skill registry | `Skill.available(...)`, `Skill.get(...)`, `loadSkills(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/skill.ts` | tool that injects full skill content into the conversation | `SkillTool` |

## Key Types And Functions

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `InstructionPrompt.systemPaths(...)` | loader | `session/instruction.ts` | discovers system-level instruction file paths |
| `InstructionPrompt.system(...)` | loader | `session/instruction.ts` | reads local instruction files and HTTP instruction URLs into prompt strings |
| `InstructionPrompt.resolve(...)` | resolver | `session/instruction.ts` | finds directory-local instruction files when a target file is read |
| `InstructionPrompt.loaded(...)` | dedupe helper | `session/instruction.ts` | reconstructs already-loaded local instruction files from prior `read` tool metadata |
| `InstructionPrompt.clear(...)` | cleanup | `session/instruction.ts` | clears per-message instruction claims after a run |
| `MessageV2.filterCompacted(...)` | replay filter | `session/message-v2.ts` | trims runtime replay around successful compaction summaries |
| `MessageV2.toModelMessages(...)` | projector | `session/message-v2.ts` | converts stored transcript to model messages |
| `SystemPrompt.skills(...)` | prompt builder | `session/system.ts` | advertises available skills in the system prompt when skill use is allowed |
| `SkillTool.execute(...)` | tool execution | `tool/skill.ts` | injects full skill content as tool output after permission approval |

## Initialization / Entry

The normal model-call path loads memory in this order:

1. `SessionPrompt.runLoop(...)` loads stored transcript with `MessageV2.filterCompacted(MessageV2.stream(sessionID))`.
2. Before calling the model, the loop resolves skills, environment, system instructions, and model messages in parallel.
3. `InstructionPrompt.system()` contributes instruction-file memory to the `system` array.
4. `MessageV2.toModelMessages(...)` contributes conversation history memory.
5. `LLM.stream(...)` prepends the agent/provider prompt, the runtime system entries, and optional per-user system text before sending the request to the provider.

For OpenAI OAuth mode, the assembled system prompt is placed into `options.instructions`; otherwise it is sent as system-role messages before the normal transcript.

## Main Control Flow

### 1. Load System-Level Instruction Files

`InstructionPrompt.systemPaths(...)` discovers prompt-level instruction files.

Project discovery runs only when project config is enabled. It checks this priority list:

1. `AGENTS.md`
2. `CLAUDE.md`, unless `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT` is set
3. deprecated `CONTEXT.md`

For each filename, it searches upward from `Instance.directory` to `Instance.worktree`. If it finds any matches for a higher-priority filename, it adds those paths and stops checking lower-priority filenames.

Global discovery then checks:

1. `$OPENCODE_CONFIG_DIR/AGENTS.md`, when `OPENCODE_CONFIG_DIR` is set
2. `Global.Path.config/AGENTS.md`
3. `~/.claude/CLAUDE.md`, unless Claude prompt compatibility is disabled

It adds only the first existing global file in that order.

### 2. Load Config-Declared Instructions

`config.instructions` is an optional string array. Config merging deduplicates and concatenates this array rather than replacing it.

Instruction entries are resolved as follows:

- `~/...` is expanded to the home directory.
- Absolute paths are scanned by basename inside their parent directory.
- Relative paths use `Filesystem.globUp(...)`; when project config is enabled, the search starts at `Instance.directory` and stops at `Instance.worktree`.
- If project config is disabled, relative paths are resolved under `OPENCODE_CONFIG_DIR`; without that directory they are skipped with a warning.
- `http://` and `https://` entries are not part of `systemPaths(...)`; `InstructionPrompt.system()` fetches them separately with a 5-second timeout.

Loaded file and URL contents are wrapped as `Instructions from: <source>\n<content>` and appended into the system prompt.

### 3. Inject Directory-Local Instructions During Reads

When `read` opens a file, it calls `InstructionPrompt.resolve(ctx.messages, filepath, ctx.messageID)`.

The resolver walks from the target file's parent directory up toward `Instance.directory`. In each directory, it looks for the same instruction filenames in priority order. A found file is injected only if all of these are true:

- it is not the target file being read;
- it is not already part of system-level instruction paths;
- it has not already been loaded by earlier non-compacted `read` tool results in the current transcript;
- it has not already been claimed for the same message ID.

The loaded local instructions are appended to the read tool output inside a `<system-reminder>` block, and their paths are stored in `metadata.loaded`. Future `InstructionPrompt.loaded(...)` calls use that metadata to avoid repeating the same local instruction file.

### 4. Replay Session Transcript Memory

Conversation memory is persisted as session/message/part rows. Runtime replay does not directly read raw rows into the provider request. It uses:

1. `MessageV2.stream(sessionID)` to hydrate messages and parts;
2. `MessageV2.filterCompacted(...)` to trim around successful compaction summaries;
3. `MessageV2.toModelMessages(...)` to project the result into provider-facing model messages.

This makes stored transcript and model-visible memory related but not identical.

### 5. Manage Long-Session Memory

When history grows too large, context management takes over:

- summary compaction writes a `summary: true` assistant message and future replay starts from that compressed boundary;
- `MessageV2.filterCompacted(...)` changes replay without deleting the old transcript;
- old completed tool outputs can be marked compacted and projected as `[Old tool result content cleared]`;
- long textual tool output is capped before becoming ordinary tool-result memory.

See `docs/en/modules/context-management.md` for the detailed compaction path.

### 6. Load Skill Memory On Demand

Skills are adjacent instruction packages, not automatically injected in full.

`SystemPrompt.skills(agent)` advertises available skills in the system prompt when the `skill` permission is not disabled. `Skill.available(agent)` filters discovered skills through permission rules. The full `SKILL.md` content is loaded only when the model calls the `skill` tool and permission succeeds. The tool returns a `<skill_content>` block and a sampled list of related files.

## Upstream And Downstream Dependencies

Upstream:

- config files and `config.instructions`,
- project/global instruction files,
- `read` tool activity,
- persisted session transcript,
- skill discovery configuration,
- provider/model mode in `LLM.stream(...)`.

Downstream:

- `SessionPrompt.runLoop(...)` for prompt assembly,
- `LLM.stream(...)` for provider request construction,
- `MessageV2.toModelMessages(...)` for transcript projection,
- `SessionCompaction` for compressed replay,
- `SkillTool` for on-demand instruction package injection.

## Implementation Details

- Instruction file discovery is path-based and priority-based; there is no semantic search or embedding index in the confirmed path.
- System-level instruction paths are deduplicated with a `Set`.
- Read-time local instruction dedupe uses two signals: persisted `read` tool `metadata.loaded` and an in-memory per-message `claims` map.
- `InstructionPrompt.clear(messageID)` removes per-message claims after a processor run finishes.
- URL instructions are best-effort: failed fetches or non-OK responses become empty strings.
- Read tool output has its own caps: default `2000` lines, `2000` characters per line, and `50 KB` total text before adding any local instruction reminder.

## Design Tradeoffs / Risks

- Priority-file discovery is predictable, but if an `AGENTS.md` exists, lower-priority `CLAUDE.md` / `CONTEXT.md` files in the upward search are skipped.
- System-level instruction contents are injected directly; no explicit instruction-file token budget was observed in `InstructionPrompt.system(...)`.
- Read-time local instructions are only discovered when the model reads files in that subtree, so relevant instructions can be missed if the model never opens a nearby file.
- Metadata-based dedupe ignores compacted read results, so local instructions can be reloaded after old tool output is compacted.
- Skill full content enters memory through tool output, which means it is subject to the same long-session compaction/pruning dynamics as other tool results.

## Pending Verification

- Whether any provider-specific transform removes or rewrites instruction content after `experimental.chat.system.transform`.
- Whether remote `config.instructions` URLs have any size limit outside provider context limits.
- Whether all intended local instruction files are reachable when the target file lives directly under `Instance.directory`, since the current walk stops before processing the root directory.
