# Async Task System Refactor

**Date:** 2026-01-23
**Status:** Brainstorm Complete
**Author:** AI-assisted brainstorming session

## Problem Statement

The current background task system hangs/freezes when spawning multiple parallel tasks. Observed behavior:
- UI freezes completely (cannot interact)
- Ctrl+C also hangs (requires manual process kill)
- Happens consistently when spawning 5-6+ parallel tasks
- Example: Running `task("uv run stockai quality BBCA")` for multiple stocks simultaneously

### Root Cause Analysis

Investigation of `src/kai_code/tasks/` revealed:
1. **Threading-based architecture** - Uses `ThreadPoolExecutor` with max 5 concurrent tasks
2. **No watchdog timeout** - Running tasks have no automatic timeout mechanism
3. **Background agents spawn fresh KaiAgent instances** - Each task creates a new agent
4. **Blocking I/O patterns** - Subprocess communication can block indefinitely
5. **Signal handling issues** - Ctrl+C doesn't propagate to child threads/processes properly

## What We're Building

An async-first task system that:
1. Uses `asyncio` for task orchestration
2. Provides reliable timeout enforcement (default: 15 minutes)
3. Allows graceful cancellation that responds to Ctrl+C
4. Supports concurrent agent execution without deadlocks
5. Makes both task system and `agent.run()` async-capable

## Why Async-First Architecture

**Chosen over alternatives:**
- **Process-based isolation**: More reliable but higher overhead, chosen approach is more modern
- **Thread safety fixes**: Band-aid solution, doesn't address fundamental issues

**Benefits of async:**
- Cooperative multitasking avoids deadlocks
- `asyncio.wait_for()` provides built-in timeout enforcement
- Modern Python patterns with wide ecosystem support
- `asyncio.shield()` for proper cancellation handling
- Event loop is visible, making debugging easier

## Key Decisions

### 1. Scope: Tasks + Agent Execution
Convert both the task manager and `agent.run()` to async. This ensures end-to-end async flow without sync/async boundary issues.

### 2. Default Timeout: 15 Minutes
Balances allowing complex operations while catching hung tasks. Configurable per-task if needed.

### 3. Breaking Changes Allowed
The task API can change if it improves the design. Existing callers will need updates.

### 4. Cancellation Strategy
- Use `asyncio.CancelledError` for cooperative cancellation
- Background processes receive SIGTERM, then SIGKILL after grace period
- Ctrl+C triggers cancellation of all pending tasks

## Design Sketch

```
┌─────────────────────────────────────────────────────────┐
│                   AsyncTaskManager                       │
│  - asyncio.Queue for task scheduling                    │
│  - asyncio.Semaphore for concurrency limit (5)          │
│  - Watchdog task monitors all running tasks             │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    AsyncTask                             │
│  - async def run() with timeout wrapper                 │
│  - asyncio.subprocess for shell commands                │
│  - Proper CancelledError handling                       │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│               AsyncKaiAgent.run()                        │
│  - Agent execution becomes async                        │
│  - Tool calls wrapped with timeouts                     │
│  - Streaming output via async generators                │
└─────────────────────────────────────────────────────────┘
```

## Success Criteria

1. **No hangs** - Parallel tasks complete or timeout, never hang indefinitely
2. **Ctrl+C works** - Can always interrupt and exit cleanly
3. **Timeout enforcement** - Tasks killed after 15 minutes (configurable)
4. **Concurrent execution** - 5+ tasks run in parallel without issues
5. **Graceful degradation** - Failing tasks don't crash others

## Open Questions

1. **LangChain compatibility** - Does `langchain.agents` support async? May need wrappers.
2. **Subprocess streaming** - How to stream subprocess output in async context?
3. **Rich UI integration** - How does async task system integrate with Rich live displays?
4. **Migration path** - How to handle existing sync code during transition?

## Next Steps

1. Run `/workflows:plan` to create detailed implementation plan
2. Investigate LangChain async support
3. Prototype async task execution with simple test case
4. Plan migration strategy for existing code
