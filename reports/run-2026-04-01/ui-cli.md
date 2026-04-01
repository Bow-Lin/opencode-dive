# UI / CLI

## Goal

Explain how user-facing shells in Opencode accept input, render output, and bridge into the backend runtime.

## Summary

The pinned version has two distinct interaction layers:

1. a CLI command layer based on yargs,
2. a richer TUI layer built as an SDK client over a synchronized local store.

They are related, but they should not be treated as one module.

## Findings

### 1. `src/index.ts` is the raw CLI boundary

`src/index.ts` owns:

- top-level yargs construction,
- global options,
- logging/env/migration middleware,
- command registration,
- fatal error formatting.

Interpretation:

- this is where raw shell invocation becomes structured command dispatch;
- there is no large custom command framework above yargs.

### 2. CLI handlers stop being “argv code” once they choose a runtime bridge

In commands like `run`, the handler first:

- validates flags,
- normalizes cwd and file inputs,
- assembles prompt text.

After that it switches to runtime interaction through either:

- `bootstrap(...)+direct service calls`, or
- SDK calls such as `sdk.session.*` and `sdk.event.subscribe()`.

Interpretation:

- the CLI layer is mostly transport/adaptation logic, not business orchestration.

### 3. `run.ts` is a terminal client for the backend, not just a one-shot command

`run.ts`:

- creates or resumes a session,
- subscribes to runtime events,
- formats tool/text/reasoning output,
- handles permission prompts,
- exits on `session.status=idle`.

Interpretation:

- it behaves like a lightweight text client over the backend event model;
- this is materially different from simple admin/list commands.

### 4. Local CLI execution often still goes through the internal server boundary

In local mode, `run.ts` creates an SDK client whose `fetch` calls `Server.Default().fetch(...)`.

Interpretation:

- local and remote runtime interaction are intentionally converged;
- the backend control-plane API is a real internal boundary even inside one process.

### 5. The TUI is a separate client architecture

The TUI path is built around:

- `SDKProvider`
- `SyncProvider`
- Solid/OpenTUI component tree

Interpretation:

- the TUI is not a thin wrapper around CLI printing;
- it is a full stateful client layered over the same backend APIs/events.

### 6. The TUI renders from synchronized local state

Observed model:

- initial state comes from SDK snapshot calls;
- live changes arrive through event streams;
- `SyncProvider` updates a local store;
- components render from that store with `useSync()`.

Interpretation:

- UI rendering is store-driven rather than service-driven.

### 7. Local TUI mode uses a worker bridge

`thread.ts` starts a worker that:

- proxies HTTP-style backend calls into `Server.Default().fetch(...)`,
- subscribes to `Bus.subscribeAll(...)`,
- forwards events over RPC to the UI thread.

Interpretation:

- local TUI mode separates rendering from backend work;
- the worker is effectively an in-process transport adapter.

### 8. Mutations still go back through the SDK

Prompt submission, session creation, abort, fork, and similar actions use `sdk.client.*`.

Interpretation:

- even local UI components behave like clients of the backend rather than calling runtime services directly.

## Key Conclusions

- The CLI command layer and the TUI layer are separate modules and should be documented separately.
- CLI responsibilities end at argument normalization and bridge selection.
- The TUI is an SDK-driven client with a synchronized local state cache.
- Both local CLI and local TUI frequently reuse the same backend control-plane surface rather than bypassing it.

## Open Questions

- How much the web/app/desktop packages mirror the same `SDK + event stream + sync cache` architecture.
- Whether more CLI commands will migrate toward SDK-mediated interaction instead of direct bootstrap/service calls.
