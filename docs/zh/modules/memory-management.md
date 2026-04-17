# Memory 管理模块

## 模块职责

Opencode 1.3.13 里的 memory 管理不是向量库或语义检索系统。它由几条对模型可见的 prompt memory 路径组成：

- 注入 system prompt 的 instruction files，
- `read` 工具读取文件时发现的局部 instruction files，
- 从持久化 message / part 行重放的 session transcript，
- 长会话场景下的摘要式 compaction 与 tool-output pruning，
- 以及按需公布和加载的 skill instruction packages。

## 关键文件

| File | Role | Evidence |
| --- | --- | --- |
| `workspace/source/opencode/packages/opencode/src/session/instruction.ts` | instruction 文件发现、加载和 read-time 局部 instruction 解析 | `InstructionPrompt.systemPaths(...)`, `system(...)`, `resolve(...)`, `loaded(...)`, `clear(...)` |
| `workspace/source/opencode/packages/opencode/src/session/prompt.ts` | 模型调用前组装 environment、skills、instructions 和 transcript 的主 loop | `runLoop(...)`, `InstructionPrompt.system()`, `MessageV2.toModelMessages(...)` |
| `workspace/source/opencode/packages/opencode/src/session/llm.ts` | 最终面向 provider 的 prompt 组装 | `LLM.stream(...)`, system message construction, `experimental.chat.system.transform` |
| `workspace/source/opencode/packages/opencode/src/tool/read.ts` | 文件读取触发的动态局部 instruction 注入 | `InstructionPrompt.resolve(...)`, `<system-reminder>`, `metadata.loaded` |
| `workspace/source/opencode/packages/opencode/src/session/message-v2.ts` | session transcript replay 与 provider-message projection | `stream(...)`, `filterCompacted(...)`, `toModelMessages(...)` |
| `workspace/source/opencode/packages/opencode/src/session/compaction.ts` | 摘要式 compaction 与旧 tool output pruning | `SessionCompaction.process(...)`, `prune(...)` |
| `workspace/source/opencode/packages/opencode/src/config/config.ts` | config 级 instruction 声明和合并语义 | `instructions`, `mergeConfigConcatArrays(...)` |
| `workspace/source/opencode/packages/opencode/src/skill/index.ts` | skill instruction 发现和内存 registry | `Skill.available(...)`, `Skill.get(...)`, `loadSkills(...)` |
| `workspace/source/opencode/packages/opencode/src/tool/skill.ts` | 把完整 skill 内容注入 conversation 的工具 | `SkillTool` |

## 关键类型与函数

| Symbol | Kind | File | Purpose |
| --- | --- | --- | --- |
| `InstructionPrompt.systemPaths(...)` | loader | `session/instruction.ts` | 发现 system-level instruction 文件路径 |
| `InstructionPrompt.system(...)` | loader | `session/instruction.ts` | 把本地 instruction 文件和 HTTP instruction URL 读成 prompt 字符串 |
| `InstructionPrompt.resolve(...)` | resolver | `session/instruction.ts` | 读取目标文件时发现目录局部 instruction 文件 |
| `InstructionPrompt.loaded(...)` | dedupe helper | `session/instruction.ts` | 从之前 `read` 工具 metadata 里恢复已加载过的局部 instruction 文件 |
| `InstructionPrompt.clear(...)` | cleanup | `session/instruction.ts` | 一轮运行结束后清理 per-message instruction claims |
| `MessageV2.filterCompacted(...)` | replay filter | `session/message-v2.ts` | 围绕成功 compaction summary 裁剪 runtime replay |
| `MessageV2.toModelMessages(...)` | projector | `session/message-v2.ts` | 把已存储 transcript 转成 model messages |
| `SystemPrompt.skills(...)` | prompt builder | `session/system.ts` | 在允许使用 skill 时把可用 skills 公布到 system prompt |
| `SkillTool.execute(...)` | tool execution | `tool/skill.ts` | 权限通过后把完整 skill 内容作为 tool output 注入 |

## 初始化 / 入口

普通模型调用路径会按下面顺序加载 memory：

1. `SessionPrompt.runLoop(...)` 用 `MessageV2.filterCompacted(MessageV2.stream(sessionID))` 加载已存储 transcript。
2. 调模型前，loop 并行解析 skills、environment、system instructions 和 model messages。
3. `InstructionPrompt.system()` 把 instruction-file memory 加到 `system` 数组。
4. `MessageV2.toModelMessages(...)` 提供 conversation history memory。
5. `LLM.stream(...)` 把 agent/provider prompt、runtime system entries 和可选 user-level system text 放到 provider 请求前部。

在 OpenAI OAuth 模式下，组装后的 system prompt 会放入 `options.instructions`；其他常规路径会把它作为 system-role messages 放在 transcript 前面。

## 主控制流程

### 1. 加载 System-Level Instruction Files

`InstructionPrompt.systemPaths(...)` 负责发现 prompt-level instruction files。

Project discovery 只在 project config 未禁用时运行。它按下面优先级检查：

1. `AGENTS.md`
2. `CLAUDE.md`，除非设置了 `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT`
3. 已废弃的 `CONTEXT.md`

对每个文件名，它会从 `Instance.directory` 向上搜索到 `Instance.worktree`。如果较高优先级文件名已经有匹配结果，它会加入这些路径并停止检查更低优先级文件名。

Global discovery 接着检查：

1. 设置了 `OPENCODE_CONFIG_DIR` 时的 `$OPENCODE_CONFIG_DIR/AGENTS.md`
2. `Global.Path.config/AGENTS.md`
3. `~/.claude/CLAUDE.md`，除非 Claude prompt 兼容被禁用

这里也只加入按顺序找到的第一个全局文件。

### 2. 加载 Config-Declared Instructions

`config.instructions` 是可选字符串数组。配置合并时会对该数组做去重追加，而不是覆盖。

instruction entries 的解析规则如下：

- `~/...` 会展开到用户 home 目录。
- 绝对路径会在其父目录内按 basename 扫描。
- 相对路径使用 `Filesystem.globUp(...)`；project config 启用时从 `Instance.directory` 搜到 `Instance.worktree`。
- project config 禁用时，相对路径在 `OPENCODE_CONFIG_DIR` 下解析；如果没有该目录，会记录 warning 并跳过。
- `http://` 和 `https://` entries 不进入 `systemPaths(...)`；`InstructionPrompt.system()` 会另外用 5 秒 timeout 拉取它们。

加载到的文件和 URL 内容会被包装成 `Instructions from: <source>\n<content>`，再追加进 system prompt。

### 3. Read 时注入目录局部 Instructions

`read` 打开文件时会调用 `InstructionPrompt.resolve(ctx.messages, filepath, ctx.messageID)`。

resolver 会从目标文件的父目录向上走到 `Instance.directory`。每个目录里都按相同优先级找 instruction 文件。只有满足以下条件的文件才会被注入：

- 不是当前正在读取的目标文件；
- 不属于 system-level instruction paths；
- 没有被当前 transcript 中之前未 compacted 的 `read` tool result 加载过；
- 没有被同一个 message ID claim 过。

加载到的局部 instructions 会被追加到 read tool output 的 `<system-reminder>` 块里，并把路径记录到 `metadata.loaded`。后续 `InstructionPrompt.loaded(...)` 会用这个 metadata 避免重复注入同一个局部 instruction 文件。

### 4. 重放 Session Transcript Memory

conversation memory 以 session / message / part 行持久化。runtime replay 不会把原始行直接塞给 provider，而是经过：

1. `MessageV2.stream(sessionID)` hydrate messages 和 parts；
2. `MessageV2.filterCompacted(...)` 围绕成功 compaction summary 裁剪；
3. `MessageV2.toModelMessages(...)` 投影成 provider-facing model messages。

因此，存储里的 transcript 和模型实际可见的 memory 相关但不完全相同。

### 5. 管理长会话 Memory

历史变长时，context management 会接管：

- 摘要式 compaction 会写入 `summary: true` assistant message，后续 replay 从压缩边界之后开始；
- `MessageV2.filterCompacted(...)` 会改变 replay，但不会删除旧 transcript；
- 旧 completed tool output 可以被标记为 compacted，并在投影时变成 `[Old tool result content cleared]`；
- 过长文本 tool output 会在成为普通 tool-result memory 前被截断。

详细 compaction 路径见 `docs/zh/modules/context-management.md`。

### 6. 按需加载 Skill Memory

Skills 是相邻的 instruction packages，不会默认完整注入。

`SystemPrompt.skills(agent)` 会在 `skill` permission 未禁用时把可用 skills 公布到 system prompt。`Skill.available(agent)` 会按 permission rules 过滤已发现的 skills。只有当模型调用 `skill` 工具并通过权限检查时，完整 `SKILL.md` 内容才会被加载。工具输出包含 `<skill_content>` 块和采样的相关文件列表。

## 上下游依赖

上游：

- config files 与 `config.instructions`，
- project / global instruction files，
- `read` 工具活动，
- 已持久化 session transcript，
- skill discovery 配置，
- `LLM.stream(...)` 中的 provider / model 模式。

下游：

- 负责 prompt assembly 的 `SessionPrompt.runLoop(...)`，
- 负责 provider request construction 的 `LLM.stream(...)`，
- 负责 transcript projection 的 `MessageV2.toModelMessages(...)`，
- 负责 compressed replay 的 `SessionCompaction`，
- 负责按需 instruction package 注入的 `SkillTool`。

## 实现细节

- instruction 文件发现是 path-based 和 priority-based；已确认路径里没有 semantic search 或 embedding index。
- system-level instruction paths 使用 `Set` 去重。
- read-time 局部 instruction 去重依赖两个信号：持久化 `read` tool 的 `metadata.loaded`，以及内存里的 per-message `claims` map。
- `InstructionPrompt.clear(messageID)` 会在 processor run 结束后移除 per-message claims。
- URL instructions 是 best-effort：拉取失败或 HTTP 非 OK 会变成空字符串。
- `read` 工具有自己的输出上限：默认 `2000` 行、每行 `2000` 字符、总文本 `50 KB`，然后才追加局部 instruction reminder。

## 设计取舍 / 风险

- 优先级文件发现很可预测，但如果存在 `AGENTS.md`，同一次向上搜索里的低优先级 `CLAUDE.md` / `CONTEXT.md` 会被跳过。
- system-level instruction 内容会直接注入；在 `InstructionPrompt.system(...)` 中没有看到针对 instruction 文件的显式 token budget。
- read-time 局部 instruction 只有在模型读取该子树里的文件时才会发现；如果模型从不打开附近文件，相关 instruction 可能不会进入上下文。
- metadata-based dedupe 会忽略已经 compacted 的 read result，因此旧 tool output compacted 后局部 instructions 可能再次加载。
- 完整 skill 内容通过 tool output 进入 memory，因此会受到其他 tool result 一样的长会话 compaction / pruning 影响。

## 待验证

- 是否有 provider-specific transform 会在 `experimental.chat.system.transform` 之后移除或重写 instruction 内容。
- 远程 `config.instructions` URL 除 provider context limit 外是否还有额外 size limit。
- 当目标文件直接位于 `Instance.directory` 下时，当前向上遍历会在处理 root 前停止，是否符合局部 instruction 文件的预期覆盖范围。
