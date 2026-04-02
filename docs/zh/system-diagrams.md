# 系统流程图集

这页是文字架构分析的可视化配套。你如果想先快速把 Opencode 的整体形状、控制边界和关键运行时链路看清楚，先读这里；如果想继续下钻，再回到 `architecture.md`、`modules/` 和 `callflows/`。

推荐阅读顺序：

1. 先看这页，把系统形状建立起来
2. 再看 `architecture.md`，理解结构化叙事
3. 再看 `modules/`，理解各子系统职责
4. 最后看 `callflows/`，核对具体调用链证据

## 1. 系统总览图

```mermaid
flowchart TD
    User[用户]
    CLI[CLI 命令]
    TUI[TUI 壳层]
    SDK[SDK / Control-Plane Client]
    Server[进程内或远端 Server]
    Instance[Instance Context / Workspace Binding]
    Prompt[SessionPrompt]
    Processor[SessionProcessor]
    LLM[LLM.stream]
    Provider[Provider Registry / Language Model]
    Tools[Tool Registry / Bound Tools]
    Session[Session Services]
    Sync[SyncEvent / Projectors / Storage]
    Status[SessionStatus / Bus]
    Plugins[Server Plugins]
    Skills[Skills / Commands]
    TuiPlugins[TUI Plugins]

    User --> CLI
    User --> TUI
    CLI --> SDK
    TUI --> SDK
    SDK --> Server
    Server --> Instance
    Instance --> Prompt
    Prompt --> Processor
    Processor --> LLM
    LLM --> Provider
    Prompt --> Tools
    Prompt --> Session
    Session --> Sync
    Prompt --> Status
    Plugins -. hooks .-> Prompt
    Plugins -. hooks .-> Tools
    Skills -. content .-> Prompt
    Skills -. exposed as .-> CLI
    TuiPlugins -. extend .-> TUI
```

主要代码锚点：

- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/server/server.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`
- `workspace/source/opencode/packages/opencode/src/provider/provider.ts`
- `workspace/source/opencode/packages/opencode/src/tool/registry.ts`

## 2. 启动与入口图

```mermaid
flowchart TD
    Start[用户运行 opencode]
    Bin[bin/opencode wrapper]
    Dev[dev 脚本 -> src/index.ts]
    Index[src/index.ts]
    Yargs[yargs parser + middleware]
    Run[run / session commands]
    TuiCmd[TUI commands]
    Serve[serve command]
    Bootstrap[cli/bootstrap.ts]
    InstanceBootstrap[InstanceBootstrap]
    LocalSDK[本地 SDK client]
    ServerFetch[Server.Default().fetch]
    Listen[Server.listen]
    Router[WorkspaceRouterMiddleware]

    Start --> Bin
    Start --> Dev
    Bin --> Index
    Dev --> Index
    Index --> Yargs
    Yargs --> Run
    Yargs --> TuiCmd
    Yargs --> Serve
    Run --> Bootstrap
    TuiCmd --> Bootstrap
    Bootstrap --> InstanceBootstrap
    Bootstrap --> LocalSDK
    LocalSDK --> ServerFetch
    Serve --> Listen
    Listen --> Router
    Router --> InstanceBootstrap
```

主要代码锚点：

- `workspace/source/opencode/packages/opencode/bin/opencode`
- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts`
- `workspace/source/opencode/packages/opencode/src/project/bootstrap.ts`
- `workspace/source/opencode/packages/opencode/src/cli/cmd/serve.ts`
- `workspace/source/opencode/packages/opencode/src/server/router.ts`

## 3. 用户请求端到端时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant C as CLI/TUI
    participant S as SDK Client
    participant R as Server / Routes
    participant I as Instance Context
    participant P as SessionPrompt
    participant X as SessionProcessor
    participant L as LLM / Provider
    participant T as Tool
    participant DB as Session Persistence

    U->>C: 输入 prompt / command
    C->>S: 规范化请求
    S->>R: 调用 session API
    R->>I: 绑定 workspace instance
    I->>P: 移交请求
    P->>DB: 创建或更新 session message
    P->>X: 创建 processor
    X->>L: 发起模型流式执行
    alt 需要 tool call
        L->>T: 执行工具
        T-->>X: 返回 tool result
        X->>DB: 持久化 tool 相关 parts
        X->>L: 继续模型循环
    end
    L-->>X: 返回最终 assistant 输出
    X->>DB: 持久化最终 message 状态
    P-->>R: 返回完成结果 / 流结束
    R-->>S: 返回响应 / 事件
    S-->>C: 更新客户端状态
    C-->>U: 渲染结果
```

主要代码锚点：

- `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts`
- `workspace/source/opencode/packages/opencode/src/server/routes/session.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`
- `workspace/source/opencode/packages/opencode/src/session/llm.ts`
- `workspace/source/opencode/packages/opencode/src/session/index.ts`

## 4. Runtime 编排核心图

```mermaid
flowchart TD
    Entry[SessionPrompt.prompt / command / shell]
    Loop[loop sessionID]
    Runner[Runner Map per Session]
    RunLoop[runLoop sessionID]
    Load[加载 session 与裁剪后的 history]
    Resolve[解析 model / instructions / tools]
    CreateMsg[创建下一条 assistant message]
    Processor[SessionProcessor.process]
    Stream[LLM.stream]
    Continue{结果分支}
    Compact[SessionCompaction.process]
    Stop[返回 idle]
    Status[SessionStatus.set]
    Bus[Bus notifications]

    Entry --> Loop
    Loop --> Runner
    Runner --> RunLoop
    RunLoop --> Load
    Load --> Resolve
    Resolve --> CreateMsg
    CreateMsg --> Processor
    Processor --> Stream
    Stream --> Continue
    Continue -->|continue| RunLoop
    Continue -->|compact| Compact
    Compact --> RunLoop
    Continue -->|stop| Stop
    Runner -. onBusy / onIdle .-> Status
    Status -. publish .-> Bus
```

主要代码锚点：

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/effect/runner.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`
- `workspace/source/opencode/packages/opencode/src/session/compaction.ts`
- `workspace/source/opencode/packages/opencode/src/session/status.ts`

## 5. Tool 执行时序图

```mermaid
sequenceDiagram
    participant P as SessionPrompt
    participant R as ToolRegistry
    participant G as Plugin Hooks
    participant L as LLM Runtime
    participant B as Bound Tool Context
    participant E as Concrete Tool
    participant S as Session Processor / Message Parts

    P->>R: 请求当前 model + agent 可用 tools
    R-->>P: 返回过滤后的 tool definitions
    P->>G: 执行 tool.definition hooks
    G-->>P: 返回调整后的 schema / description
    P->>B: 绑定 sessionID、messageID、ask、metadata
    P->>L: 暴露 AI SDK tools
    L->>B: 执行 tool call
    B->>G: tool.execute.before
    B->>E: execute args, ctx
    E-->>B: tool result
    B->>G: tool.execute.after
    B->>S: 更新 tool parts / metadata
    B-->>L: 返回结构化 tool result
```

主要代码锚点：

- `workspace/source/opencode/packages/opencode/src/tool/tool.ts`
- `workspace/source/opencode/packages/opencode/src/tool/registry.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/llm.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`

## 6. Session 生命周期状态图

```mermaid
stateDiagram-v2
    [*] --> Created
    Created --> Idle: session created
    Idle --> Running: prompt / command / shell starts
    Running --> ToolExecuting: model emits tool call
    ToolExecuting --> Running: tool result returned
    Running --> Compacting: overflow / auto-compaction
    Compacting --> Running: compacted context resumes
    Running --> WaitingPermission: permission prompt required
    WaitingPermission --> Running: permission reply received
    Running --> Idle: assistant turn completes
    Running --> Error: unrecovered provider / tool failure
    Error --> Idle: status cleared or retry path
    Idle --> [*]
```

主要代码锚点：

- `workspace/source/opencode/packages/opencode/src/session/index.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/status.ts`
- `workspace/source/opencode/packages/opencode/src/session/compaction.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`

## 7. 扩展系统图

```mermaid
flowchart TD
    Config[配置文件 / 目录]
    PluginPkgs[Plugin Packages / Scripts]
    SkillDirs[本地 Skill 目录]
    SkillRemote[远端 Skill 索引]
    ServerPlugins[Server Plugins]
    TuiPlugins[TUI Plugins]
    Skills[Skills]
    Runtime[Runtime Hooks]
    UIShell[TUI Shell]
    Commands[Command Inventory]
    SkillTool[skill Tool]
    Prompt[SessionPrompt / System Prompt]
    Tools[Tool Surface]

    Config --> PluginPkgs
    Config --> SkillDirs
    PluginPkgs --> ServerPlugins
    PluginPkgs --> TuiPlugins
    SkillDirs --> Skills
    SkillRemote --> Skills
    ServerPlugins --> Runtime
    ServerPlugins --> Tools
    TuiPlugins --> UIShell
    TuiPlugins --> Commands
    Skills --> SkillTool
    Skills --> Commands
    Skills --> Prompt
    SkillTool --> Prompt
    Runtime --> Prompt
```

主要代码锚点：

- `workspace/source/opencode/packages/opencode/src/plugin/index.ts`
- `workspace/source/opencode/packages/opencode/src/plugin/loader.ts`
- `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/plugin/runtime.ts`
- `workspace/source/opencode/packages/opencode/src/skill/index.ts`
- `workspace/source/opencode/packages/opencode/src/skill/discovery.ts`
- `workspace/source/opencode/packages/opencode/src/tool/skill.ts`

## 接下来读什么

- `architecture.md`
- `blog/opencode-deep-dive.md`
- `modules/`
- `callflows/`
