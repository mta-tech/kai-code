# HybridTaskManager Guide

## Overview

The `HybridTaskManager` is a new async-based task management system that provides significant performance improvements over the legacy `TaskManager`. It uses a hybrid architecture:

- **AsyncIO** for I/O-bound shell tasks (up to 20 concurrent)
- **ThreadPoolExecutor** for CPU-bound agent tasks (2 workers)
- Proper timeout enforcement with `asyncio.timeout()`
- Thread-safe task display updates via `janus.Queue`

## Quick Start

```python
import asyncio
from kai_code.tasks import get_hybrid_task_manager

async def main():
    manager = get_hybrid_task_manager()

    # Run a shell command
    task_id = await manager.run_shell("echo 'Hello, World!'")

    # Wait for completion
    await asyncio.sleep(0.5)

    # Check result
    task = manager.get_task(task_id)
    print(f"Status: {task.status.value}")
    print(f"Output: {task.output}")

    # Cleanup
    await manager.shutdown()

asyncio.run(main())
```

## Architecture

### Shell Tasks (AsyncIO)

Shell commands run asynchronously using `asyncio.create_subprocess_exec()`:

- Non-blocking I/O
- Up to 20 concurrent tasks
- Automatic timeout enforcement
- Memory-efficient output capture

```python
# Shell task execution flow
async def run_shell(command: str, timeout: float = 30):
    async with asyncio.timeout(timeout):
        proc = await asyncio.create_subprocess_exec(...)
        stdout, stderr = await proc.communicate()
```

### Agent Tasks (ThreadPoolExecutor)

Agent prompts run in a thread pool to avoid blocking the event loop:

- 2 worker threads for CPU-bound work
- Prevents event loop blocking
- Proper thread isolation

```python
# Agent task execution flow
async def run_agent(prompt: str, timeout: float = 300):
    loop = asyncio.get_event_loop()
    async with asyncio.timeout(timeout):
        result = await loop.run_in_executor(
            self._agent_executor,
            self._run_agent_sync,
            prompt,
        )
```

## API Reference

### Core Methods

#### `async run_shell(command: str, timeout: float = 30) -> str`

Run a shell command asynchronously.

```python
task_id = await manager.run_shell("pytest tests/ -v")
task_id = await manager.run_shell("sleep 10", timeout=5)  # Auto-kill after 5s
```

**Parameters:**
- `command`: Shell command to execute
- `timeout`: Maximum seconds to wait (default: 30)

**Returns:**
- Task ID string

#### `async run_agent(prompt: str, timeout: float = 300) -> str`

Run an agent prompt asynchronously.

```python
task_id = await manager.run_agent("Review the auth module")
task_id = await manager.run_agent("Fix this bug", timeout=600)  # 10 minutes
```

**Parameters:**
- `prompt`: Agent prompt to execute
- `timeout`: Maximum seconds to wait (default: 300)

**Returns:**
- Task ID string

#### `get_task(task_id: str) -> Task | None`

Get a task by ID.

```python
task = manager.get_task(task_id)
if task:
    print(f"Status: {task.status.value}")
    print(f"Command: {task.command}")
    print(f"Output: {task.output}")
    print(f"Error: {task.error}")
```

#### `get_all_tasks() -> list[Task]`

Get all tasks, sorted by creation time (newest first).

```python
for task in manager.get_all_tasks():
    print(f"{task.command}: {task.status.value}")
```

#### `async kill(task_id: str) -> bool`

Cancel a running task.

```python
success = await manager.kill(task_id)
if success:
    print("Task killed")
```

#### `async kill_all() -> int`

Kill all running tasks.

```python
count = await manager.kill_all()
print(f"Killed {count} tasks")
```

#### `async clear_completed() -> int`

Remove all completed tasks.

```python
count = await manager.clear_completed()
print(f"Cleared {count} completed tasks")
```

#### `async clear_all() -> int`

Remove all tasks.

```python
count = await manager.clear_all()
print(f"Cleared {count} tasks")
```

#### `async shutdown(timeout: float = 5.0) -> None`

Shutdown gracefully, canceling all tasks.

```python
await manager.shutdown()
```

### Query Methods

#### `active_count() -> int`

Get count of active (running or queued) tasks.

```python
print(f"Active tasks: {manager.active_count()}")
```

#### `total_count() -> int`

Get total task count.

```python
print(f"Total tasks: {manager.total_count()}")
```

## Task Status

Tasks have the following states (via `TaskStatus` enum):

- `queued`: Task is waiting to execute
- `running`: Task is currently executing
- `completed`: Task finished successfully
- `failed`: Task finished with error
- `killed`: Task was canceled
- `timed_out`: Task exceeded timeout

```python
from kai_code.tasks.hybrid_manager import TaskStatus

task = manager.get_task(task_id)
if task.status == TaskStatus.COMPLETED:
    print(task.output)
elif task.status == TaskStatus.FAILED:
    print(f"Error: {task.error}")
```

## Task Model

The `Task` dataclass contains:

```python
@dataclass
class Task:
    id: str                    # Unique task ID
    status: TaskStatus          # Current status
    command: str                # Command or prompt
    type: str                   # "shell" or "agent"
    output: str                 # Captured output
    error: str | None           # Error message if failed
    created_at: datetime        # Creation timestamp
    started_at: datetime | None # Start timestamp
    finished_at: datetime | None # Finish timestamp
    exit_code: int | None       # Process exit code (shell tasks)
```

## Best Practices

### 1. Always Use Async/Await

```python
# GOOD
async def main():
    manager = get_hybrid_task_manager()
    task_id = await manager.run_shell("echo 'test'")
    await asyncio.sleep(0.5)
    await manager.shutdown()

asyncio.run(main())

# BAD - mixing sync and async
manager = get_hybrid_task_manager()
task_id = await manager.run_shell("echo 'test'")  # SyntaxError
```

### 2. Set Appropriate Timeouts

```python
# Quick commands
await manager.run_shell("echo 'test'", timeout=5)

# Long-running tests
await manager.run_shell("pytest tests/", timeout=300)

# Agent prompts (can take longer)
await manager.run_agent("Review this code", timeout=600)
```

### 3. Clean Up Resources

```python
# Always shutdown when done
try:
    await manager.run_shell("...")
finally:
    await manager.shutdown()

# Or use async context manager (if implemented)
async with manager:
    await manager.run_shell("...")
```

### 4. Handle Timeouts Gracefully

```python
task_id = await manager.run_shell("sleep 100", timeout=1)
await asyncio.sleep(2)  # Wait for timeout

task = manager.get_task(task_id)
assert task.status == TaskStatus.TIMED_OUT
assert "timeout" in task.error.lower() if task.error else True
```

### 5. Check Task Status Before Accessing Output

```python
task = manager.get_task(task_id)
if task and task.status == TaskStatus.COMPLETED:
    print(task.output)
elif task and task.status == TaskStatus.FAILED:
    print(f"Error: {task.error}")
```

## Migration from TaskManager

### Step 1: Update Imports

```python
# OLD
from kai_code.tasks import get_task_manager, TaskStatus, TaskPriority

# NEW
from kai_code.tasks import get_hybrid_task_manager
from kai_code.tasks.hybrid_manager import TaskStatus
```

### Step 2: Change to Async/Await

```python
# OLD (sync)
manager = get_task_manager()
task_id = manager.run_shell("echo 'test'")
task = manager.get_task(task_id)
manager.kill_all()

# NEW (async)
async def main():
    manager = get_hybrid_task_manager()
    task_id = await manager.run_shell("echo 'test'")
    task = manager.get_task(task_id)
    await manager.kill_all()

asyncio.run(main())
```

### Step 3: Migrate Existing Tasks

```python
from kai_code.tasks import (
    get_task_manager,
    get_hybrid_task_manager,
    migrate_task_manager_state,
)

# Get old tasks
old_manager = get_task_manager()
old_tasks = old_manager.get_all_tasks()

# Migrate to new format
new_tasks = migrate_task_manager_state(old_tasks)

# Load into new manager
new_manager = get_hybrid_task_manager()
for task in new_tasks:
    new_manager._tasks[task.id] = task
```

### Step 4: Update Status Checks

```python
# OLD
if task.status == TaskStatus.COMPLETED:
    print(task.output)

# NEW
if task.status.value == "completed":
    print(task.output)
# Or:
from kai_code.tasks.hybrid_manager import TaskStatus
if task.status == TaskStatus.COMPLETED:
    print(task.output)
```

## Performance Tips

### 1. Batch Similar Tasks

```python
# GOOD - run similar tasks together
task_ids = []
for i in range(100):
    task_id = await manager.run_shell(f"echo 'Task {i}'")
    task_ids.append(task_id)

# BAD - excessive waiting between spawns
for i in range(100):
    task_id = await manager.run_shell(f"echo 'Task {i}'")
    await asyncio.sleep(0.1)  # Unnecessary delay
```

### 2. Use Appropriate Concurrency

```python
# HybridTaskManager handles up to 20 concurrent shell tasks
# No need to manually limit concurrency

# For more than 20 tasks, they queue automatically
for i in range(100):
    await manager.run_shell(f"echo 'Task {i}'")
# First 20 run immediately, rest queue up
```

### 3. Clear Completed Tasks Periodically

```python
# Prevent memory buildup
await manager.clear_completed()
```

## Troubleshooting

### Tasks Not Completing

```python
# Check if tasks are stuck
active = manager.get_active_tasks()
for task in active:
    print(f"Task {task.id} has been {task.status.value} since {task.created_at}")

# Kill stuck tasks
for task in active:
    await manager.kill(task.id)
```

### Memory Usage Growing

```python
# Clear completed tasks
await manager.clear_completed()

# Or clear all
await manager.clear_all()
```

### Event Loop Issues

```python
# Always run async code in an event loop
asyncio.run(main())

# NOT:
main()  # This won't work
```

## Testing

```python
import pytest
from kai_code.tasks import get_hybrid_task_manager

@pytest.mark.asyncio
async def test_shell_task():
    manager = get_hybrid_task_manager()

    task_id = await manager.run_shell("echo 'test'")
    await asyncio.sleep(0.5)

    task = manager.get_task(task_id)
    assert task.status.value == "completed"
    assert "test" in task.output

    await manager.shutdown()
```

## Further Reading

- [AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html)
- [ThreadPoolExecutor Documentation](https://docs.python.org/3/library/concurrent.futures.html)
- Migration Guide: `src/kai_code/tasks/migration.py`
- Performance Benchmarks: `tests/test_performance_benchmark.py`
