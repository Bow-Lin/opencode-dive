# SessionPrompt / `prompt.ts`

## 为什么这个文件名容易误导

第一眼看到 `workspace/source/opencode/packages/opencode/src/session/prompt.ts`，很容易把它理解成一个“存放 prompt 模板的文件”。这种理解很自然，但并不准确。

仓库里确实存在放文本 prompt 资产的目录 `workspace/source/opencode/packages/opencode/src/session/prompt/`，但 `prompt.ts` 本身并不是一堆提示词字符串的集合。它实际上是交互式 session 执行的运行时编排核心。

这个区别很重要，因为如果读者因为文件名而跳过它，往往就会误判系统里真正的控制权归属。

## 这个文件真正是什么

`prompt.ts` 是把一个 session 作用域请求推进成实时执行循环的主控制层。

更具体地说，它掌管：

- 接收 prompt / command / shell 三类入口，
- 创建新的 user message，
- 决定是否进入 session loop，
- 通过 `Runner` 保证每个 session 的串行执行，
- 选择模型和 agent，
- 解析绑定后的 tools 与 MCP tools，
- 协调 subtask、compaction、command、shell 等分支，
- 并决定 loop 何时继续、停止或移交。

因此，`SessionPrompt` 是运行时编排器，而不是提示词内容定义器。

## 控制权归属

理解这个文件最有效的方式，是把它当成“控制权地图”。

`SessionPrompt` 真正掌握的是：

1. 在 CLI / SDK / server routes 之后接管请求；
2. 通过 `loop(...)` 和 `runLoop(...)` 持有 session loop；
3. 通过按 session 隔离的 `Runner` 处理并发与取消边界；
4. 在模型调用前准备 model / tools / system prompt；
5. 决定高层运行时分支策略：
   - 普通 assistant 回合
   - subtask 执行
   - compaction
   - command 展开
   - shell 执行
   - structured-output enforcement

它并不独占整个运行时，但它是这些关注点被汇总和协调的地方。

## 它把什么委托出去

这个文件之所以强，是因为它协调了很多东西；但它并不是自己做完所有事情。

### 委托给 `Session`

- 创建 / 更新 / touch session 状态
- 持久化 messages 和 parts
- 管理 session 元数据，例如 permission 和 revert 状态

`SessionPrompt` 不直接写数据库行，它调用的是 `Session.*`。

### 委托给 `SessionProcessor`

- 消费模型 / tool 的流式事件
- 在输出到达时持续更新 assistant parts
- 把低层 stream 活动转成 `continue` / `stop` / `compact`

也就是说，`SessionPrompt` 决定 loop 策略，而 `SessionProcessor` 负责一次模型运行内部的事件消费。

### 委托给 `LLM`

- 面向 provider 的模型执行
- 真正进入选中 language model 的 `stream(...)`

### 委托给 `ToolRegistry` 和具体工具

- 发现当前可用的 tool surface
- 初始化内置工具、配置目录工具、plugin 工具和 MCP tools
- 执行具体工具业务逻辑

`prompt.ts` 负责把 tools 绑定进 session context，但多数工具业务逻辑并不在这里实现。

### 委托给 `SessionStatus`

- 发布 busy / retry / idle 状态

它掌握“何时切状态”，但不掌握状态存储抽象本身。

### 委托给 `SessionCompaction`

- 检测并执行摘要 compaction 分支

## 它和 `Session` 的关系

`Session` 和 `SessionPrompt` 不是两个并列编排器。

它们的关系更准确地说是：

- `Session` 是耐久状态边界，
- `SessionPrompt` 是建立在这份状态之上的实时执行协调器。

也就是说：

1. `SessionPrompt` 先从 `Session` 读取历史和元数据，
2. 再基于这些状态决定下一步运行时动作，
3. 最后把执行结果再通过 `Session` 写回去。

这就是为什么 `SessionPrompt` 看起来非常核心，但它并没有替代 session 模块本身。

## 主要入口

它对外暴露的 API 已经足以说明这个文件的真实角色。

### `prompt(input)`

这是主要的交互入口。

它会：

1. 加载目标 session，
2. 清理 revert state，
3. 创建 user message，
4. 应用按请求传入的 permission override，
5. 在 `noReply` 未开启时进入 `loop(...)`。

### `loop({ sessionID })`

这是串行化包装层。

它自己不实现 loop 逻辑本体，而是：

- 取得或创建当前 session 的 runner，
- 保证同一时刻只有一个活跃 loop 持有该 session，
- 再把控制权转给 `runLoop(sessionID)`。

### `runLoop(sessionID)`

这才是真正的编排核心。

每轮迭代中它会：

1. 加载过滤后的 session history，
2. 找出最新 user / assistant 状态，
3. 处理挂起的 subtask 或 compaction，
4. 解析 agent / model / tools，
5. 创建下一条 assistant message，
6. 创建 `SessionProcessor`，
7. 委托一次流式执行，
8. 解释执行结果，
9. 决定继续还是退出。

如果你真正想回答“runtime loop 活在哪里”，答案就是这个函数。

### `shell(input)`

它不是一个边角工具，而是与普通 prompt 并列的编排入口，只是通过 `runner.startShell(...)` 走 shell 执行路径。

### `command(input)`

它会展开命名 command 模板，解析参数、shell 替换、目标 agent/model，然后再把最终结果重新收束回 `prompt(...)`。

这暴露出一个重要设计事实：command 不是独立执行系统，它只是进入同一套 session 编排核心的另一条入口。

## 文件内部结构导读

这个文件很大，但并不是杂乱堆叠。它内部其实有一条比较清晰的结构。

### 1. Service Wiring 与依赖组装

在 `Layer.effect(...)` 顶部，这个文件会拉起它的主要协作者：

- `Session`
- `Agent`
- `Provider`
- `SessionProcessor`
- `SessionCompaction`
- `Plugin`
- `Command`
- `Permission`
- `MCP`
- `LSP`
- `ToolRegistry`
- `SessionStatus`

这部分本身就是“它是 orchestration hub”的最强证据。

### 2. Runner Cache 与并发控制

`InstanceState` 缓存里存的是 `Map<sessionID, Runner<...>>`。

这部分建立了：

- 每个 session 只有一个活跃 runner，
- 取消路径如何路由，
- idle / busy 状态如何切换，
- scope 结束时如何统一清理。

### 3. Prompt 准备辅助函数

`resolvePromptParts(...)`、标题生成、reminder 插入、command-template 展开等逻辑都放在这里。

这些逻辑不是主 loop 本身，但它们负责准备 loop 依赖的上下文。

### 4. Tool 解析

`resolveTools(...)` 是这个文件里最能说明问题的辅助函数之一。

它把 registry 层的 tool 定义绑定成真实的 session 上下文：

- `sessionID`
- `messageID`
- `callID`
- 当前模型元数据
- permission 请求
- 写回匹配 tool part 的 metadata 更新

这也是为什么 `prompt.ts` 位于 `ToolRegistry` 之上：它把“静态工具定义”变成“带会话语义的执行能力”。

### 5. 分支辅助逻辑

`handleSubtask(...)` 和 `shellImpl(...)` 这样的辅助函数支撑的是特殊分支，但它们仍然归属同一套总编排模型。

### 6. 核心入口

随后文件会定义：

- `prompt`
- `runLoop`
- `loop`
- `shell`
- `command`

这就是这个文件的真正主干。

### 7. 导出的输入 Schema 与包装器

文件底部的 `PromptInput`、`LoopInput`、`ShellInput`、`CommandInput` 定义了这套编排 API 的公开输入形状。导出的 async wrapper 则通过 `runPromise(...)` 把 service 暴露给 Effect 层之外的调用方。

## 为什么这个名字还留着

这个文件仍然叫 `prompt.ts`，很可能反映的是它的历史演化：

- 它最开始也许更接近“处理一次 prompt”，
- 但后来不断吸收更多运行时协调职责，
- 直到演变成今天实际上的 session orchestration core。

所以，这个名字更接近它最早的入口角色，而不是它现在真实的架构重量。

## 设计取舍与风险

这种设计有一个很强的优点：一旦你知道这个文件重要，控制权归属就会变得比较容易定位。

但代价也很明显：

- 文件里集中了大量策略，
- transport concerns 和 runtime policy 在这里汇合，
- subtask、compaction、command、shell 等分支不断累积到同一处，
- 这里出现 bug 时，会同时影响 CLI 和 server 两侧。

这也是为什么它既是理解系统运行时的最佳入口之一，又是最容易形成架构复杂度热点的地方。

## 阅读建议

如果想高效读这个文件，我建议按下面顺序：

1. `prompt(...)`
2. `loop(...)`
3. `runLoop(...)`
4. `resolveTools(...)`
5. `command(...)`
6. `shell(...)`

然后再去对照：

- `runtime.md`
- `session.md`
- `callflows/prompt-to-model.md`
- `callflows/tool-call-execution.md`

## 主要代码锚点

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/index.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`
- `workspace/source/opencode/packages/opencode/src/session/compaction.ts`
- `workspace/source/opencode/packages/opencode/src/session/status.ts`
- `workspace/source/opencode/packages/opencode/src/tool/registry.ts`
- `workspace/source/opencode/packages/opencode/src/session/llm.ts`
