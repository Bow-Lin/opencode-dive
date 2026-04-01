# Architecture

## Current Status

This document is the long-term system view for the pinned Opencode version. It should be updated only after concrete analysis passes confirm the major modules and runtime paths.

## System Boundary

- Target application: Opencode at the version pinned in `OPENCODE_VERSION.md`
- Source location: `workspace/source/`
- Analysis focus: runtime structure, data flow, module responsibilities, and key execution chains

## Expected Architecture Sections

### 1. High-Level Components

Document major subsystems such as:

- CLI / UI shell
- configuration and environment loading
- agent or orchestration runtime
- provider/model integration
- tool discovery and execution
- session or state management
- plugin or skill extension points

### 2. Runtime Data Flow

Describe how control moves from user input to internal orchestration, model/tool interaction, and persisted state.

### 3. Module Boundaries

For each major subsystem, define:

- ownership,
- stable interface surface,
- notable dependencies,
- and whether the boundary is explicit or emergent.

### 4. Key Risks / Design Tensions

Capture architecture-level tradeoffs such as:

- tight coupling,
- implicit state,
- registration-by-side-effect,
- runtime indirection,
- and version-sensitive extension points.

## Evidence Requirements

Promote content here only after the underlying module docs and call-flow docs cite concrete files and symbols.
