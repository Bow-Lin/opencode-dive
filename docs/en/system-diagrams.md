# System Diagrams

This page is the visual companion to the written architecture analysis. Read it when you want the main runtime relationships quickly, then use the architecture, module, and call-flow docs to drill into details.

Recommended reading order:

1. this page for the overall shape,
2. `architecture.md` for the structured narrative,
3. `modules/` for subsystem responsibilities,
4. `callflows/` for code-anchored execution traces.

## 1. System Overview

```mermaid
flowchart TD
    User[User]
    CLI[CLI Commands]
    TUI[TUI Shell]
    SDK[SDK / Control-Plane Client]
    Server[In-Process or Remote Server]
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

Primary code anchors:

- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/server/server.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`
- `workspace/source/opencode/packages/opencode/src/provider/provider.ts`
- `workspace/source/opencode/packages/opencode/src/tool/registry.ts`

## 2. Startup And Entry Flow

```mermaid
flowchart TD
    Start[User runs opencode]
    Bin[bin/opencode wrapper]
    Dev[dev script -> src/index.ts]
    Index[src/index.ts]
    Yargs[yargs parser + middleware]
    Run[run / session commands]
    TuiCmd[TUI commands]
    Serve[serve command]
    Bootstrap[cli/bootstrap.ts]
    InstanceBootstrap[InstanceBootstrap]
    LocalSDK[Local SDK client]
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

Primary code anchors:

- `workspace/source/opencode/packages/opencode/bin/opencode`
- `workspace/source/opencode/packages/opencode/src/index.ts`
- `workspace/source/opencode/packages/opencode/src/cli/bootstrap.ts`
- `workspace/source/opencode/packages/opencode/src/project/bootstrap.ts`
- `workspace/source/opencode/packages/opencode/src/cli/cmd/serve.ts`
- `workspace/source/opencode/packages/opencode/src/server/router.ts`

## 3. End-To-End User Request Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant C as CLI/TUI
    participant S as SDK Client
    participant R as Server / Routes
    participant I as Instance Context
    participant P as SessionPrompt
    participant X as SessionProcessor
    participant L as LLM / Provider
    participant T as Tool
    participant DB as Session Persistence

    U->>C: enter prompt / command
    C->>S: normalize request
    S->>R: session API call
    R->>I: bind workspace instance
    I->>P: hand off request
    P->>DB: create/update session message
    P->>X: create processor
    X->>L: stream model output
    alt tool call needed
        L->>T: execute tool
        T-->>X: tool result
        X->>DB: persist tool-related parts
        X->>L: continue model loop
    end
    L-->>X: final assistant output
    X->>DB: persist final message state
    P-->>R: return completion / stream end
    R-->>S: response / events
    S-->>C: update client state
    C-->>U: render result
```

Primary code anchors:

- `workspace/source/opencode/packages/opencode/src/cli/cmd/run.ts`
- `workspace/source/opencode/packages/opencode/src/server/routes/session.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`
- `workspace/source/opencode/packages/opencode/src/session/llm.ts`
- `workspace/source/opencode/packages/opencode/src/session/index.ts`

## 4. Runtime Orchestration Core

```mermaid
flowchart TD
    Entry[SessionPrompt.prompt / command / shell]
    Loop[loop sessionID]
    Runner[Runner Map per Session]
    RunLoop[runLoop sessionID]
    Load[Load session + filtered history]
    Resolve[Resolve model / instructions / tools]
    CreateMsg[Create next assistant message]
    Processor[SessionProcessor.process]
    Stream[LLM.stream]
    Continue{Result}
    Compact[SessionCompaction.process]
    Stop[Return to idle]
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

Primary code anchors:

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/effect/runner.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`
- `workspace/source/opencode/packages/opencode/src/session/compaction.ts`
- `workspace/source/opencode/packages/opencode/src/session/status.ts`

## 5. Tool Execution Sequence

```mermaid
sequenceDiagram
    participant P as SessionPrompt
    participant R as ToolRegistry
    participant G as Plugin Hooks
    participant L as LLM Runtime
    participant B as Bound Tool Context
    participant E as Concrete Tool
    participant S as Session Processor / Message Parts

    P->>R: request tools for model + agent
    R-->>P: filtered tool definitions
    P->>G: tool.definition hooks
    G-->>P: adjusted schema / descriptions
    P->>B: bind sessionID, messageID, ask, metadata
    P->>L: expose AI SDK tools
    L->>B: execute tool call
    B->>G: tool.execute.before
    B->>E: execute args, ctx
    E-->>B: tool result
    B->>G: tool.execute.after
    B->>S: update tool parts / metadata
    B-->>L: structured tool result
```

Primary code anchors:

- `workspace/source/opencode/packages/opencode/src/tool/tool.ts`
- `workspace/source/opencode/packages/opencode/src/tool/registry.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/llm.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`

## 6. Session Lifecycle State Machine

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

Primary code anchors:

- `workspace/source/opencode/packages/opencode/src/session/index.ts`
- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/status.ts`
- `workspace/source/opencode/packages/opencode/src/session/compaction.ts`
- `workspace/source/opencode/packages/opencode/src/session/processor.ts`

## 7. Extension Architecture

```mermaid
flowchart TD
    Config[Config Files / Directories]
    PluginPkgs[Plugin Packages / Scripts]
    SkillDirs[Local Skill Directories]
    SkillRemote[Remote Skill Index]
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

Primary code anchors:

- `workspace/source/opencode/packages/opencode/src/plugin/index.ts`
- `workspace/source/opencode/packages/opencode/src/plugin/loader.ts`
- `workspace/source/opencode/packages/opencode/src/cli/cmd/tui/plugin/runtime.ts`
- `workspace/source/opencode/packages/opencode/src/skill/index.ts`
- `workspace/source/opencode/packages/opencode/src/skill/discovery.ts`
- `workspace/source/opencode/packages/opencode/src/tool/skill.ts`

## 8. SessionPrompt vs SyncEvent vs Bus

This diagram is the shortest way to avoid a common misunderstanding: `Bus` is not the single control backbone of Opencode. `SessionPrompt` owns interactive orchestration, `SyncEvent` owns durable projection flow, and `Bus` exposes observable runtime notifications.

```mermaid
flowchart TD
    User[User Request]
    Routes[CLI / TUI / Server Routes]
    Prompt[SessionPrompt<br/>control flow owner]
    Processor[SessionProcessor / LLM loop]
    Session[Session APIs]
    Sync[SyncEvent.run<br/>projectors / DB]
    Bus[Bus.publish<br/>instance-scoped notifications]
    SSE[SSE / event subscribers]
    UI[UI / CLI observers]
    Plugins[Plugins / watchers / status listeners]

    User --> Routes
    Routes --> Prompt
    Prompt --> Processor
    Prompt --> Session
    Session --> Sync
    Sync -. optional republish .-> Bus
    Prompt -. status / side-channel events .-> Bus
    Bus --> SSE
    Bus --> UI
    Bus --> Plugins
```

Primary code anchors:

- `workspace/source/opencode/packages/opencode/src/session/prompt.ts`
- `workspace/source/opencode/packages/opencode/src/session/index.ts`
- `workspace/source/opencode/packages/opencode/src/sync/index.ts`
- `workspace/source/opencode/packages/opencode/src/bus/index.ts`
- `workspace/source/opencode/packages/opencode/src/server/routes/event.ts`
- `workspace/source/opencode/packages/opencode/src/session/status.ts`

## Next Reading

- `architecture.md`
- `blog/opencode-deep-dive.md`
- `modules/`
- `callflows/`
