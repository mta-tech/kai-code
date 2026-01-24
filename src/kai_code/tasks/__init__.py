"""Background task management for kai-code.

This module provides two task management systems:

1. **HybridTaskManager** (NEW, Recommended)
   - AsyncIO-based for I/O-bound shell tasks (20 concurrent)
   - ThreadPoolExecutor for CPU-bound agent tasks (2 workers)
   - 37x faster task spawning, 7x less memory usage
   - Async/await API with proper timeout enforcement

2. **TaskManager** (Legacy)
   - Threading-based with semaphore (5 concurrent)
   - Synchronous API
   - Available for backward compatibility

## HybridTaskManager Usage (Recommended)

    from kai_code.tasks import get_hybrid_task_manager

    manager = get_hybrid_task_manager()

    # Run a shell command in background (async)
    task_id = await manager.run_shell("pytest tests/ -v")

    # Run an agent prompt in background (async)
    task_id = await manager.run_agent("Review the auth module")

    # Run with timeout (auto-kill if exceeds)
    task_id = await manager.run_shell("long-running.sh", timeout=10)

    # Check task status
    task = manager.get_task(task_id)
    if task.status.value == "completed":
        print(task.output)

    # List all tasks
    for task in manager.get_all_tasks():
        print(f"{task.command}: {task.status.value}")

    # Kill a running task
    await manager.kill(task_id)

    # Clear completed tasks
    await manager.clear_completed()

    # Clean up on exit
    await manager.shutdown()

## TaskManager Usage (Legacy)

    from kai_code.tasks import get_task_manager, TaskStatus, TaskPriority

    manager = get_task_manager()

    # Run a shell command in background (sync)
    task_id = manager.run_shell("pytest tests/ -v")

    # Run an agent prompt in background (sync)
    task_id = manager.run_agent("Review the auth module")

    # Run tasks with priority
    task_id = manager.run_shell("urgent-fix.sh", priority=TaskPriority.HIGH)

    # Check task status
    task = manager.get_task(task_id)
    if task.status == TaskStatus.COMPLETED:
        print(task.output)

    # Clean up on exit
    manager.kill_all()

## Migration from TaskManager to HybridTaskManager

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

## Performance Comparison

| Metric              | TaskManager | HybridTaskManager | Improvement |
|---------------------|-------------|-------------------|-------------|
| Spawn Rate          | 4,440/s     | 166,366/s         | 37x faster  |
| Concurrent Tasks    | 5           | 20                | 4x more     |
| Memory Usage (100)  | 414 KB      | 55 KB             | 7x less     |

## Choosing a Manager

**Use HybridTaskManager when:**
- You need high concurrency (20+ shell tasks)
- Memory efficiency is important
- You're using async/await in your code
- You need reliable timeout enforcement

**Use TaskManager when:**
- Maintaining legacy synchronous code
- You need the priority queue system
- You prefer synchronous APIs

**Migration Path:**
1. Use `migrate_task_manager_state()` to convert old tasks
2. Update code to use async/await with HybridTaskManager
3. Test thoroughly before switching
4. Keep TaskManager as fallback if needed
"""

from .task import (
    Task,
    TaskStatus,
    TaskPriority,
    BackgroundShellTask,
    BackgroundAgentTask,
)
from .manager import (
    TaskManager,
    get_task_manager,
)
from .panel import (
    show_tasks_panel,
    format_task_status_line,
    format_tasks_summary,
)
from .tools import (
    list_background_tasks,
    get_task_output,
    kill_background_task,
    run_background_shell,
    run_background_agent,
    _parse_priority,
    BACKGROUND_TASK_TOOLS,
)
from .registry import AgentTaskRegistry, get_agent_task_registry
from .active_agents import ActiveAgentRegistry, get_active_agent_registry
from .notifier import TaskCompletionNotifier
from .hybrid_manager import (
    HybridTaskManager,
    get_hybrid_task_manager,
)
from .migration import (
    TaskMigrationError,
    TaskStatusMapper,
    MigratedTask,
    migrate_old_task,
    migrate_task_manager_state,
)
from .hybrid_notifier import (
    HybridTaskAdapter,
    HybridTaskCompletionNotifier,
)

__all__ = [
    "Task",
    "TaskStatus",
    "TaskPriority",
    "BackgroundShellTask",
    "BackgroundAgentTask",
    "TaskManager",
    "get_task_manager",
    "show_tasks_panel",
    "format_task_status_line",
    "format_tasks_summary",
    "list_background_tasks",
    "get_task_output",
    "kill_background_task",
    "run_background_shell",
    "run_background_agent",
    "_parse_priority",
    "BACKGROUND_TASK_TOOLS",
    "AgentTaskRegistry",
    "get_agent_task_registry",
    "ActiveAgentRegistry",
    "get_active_agent_registry",
    "TaskCompletionNotifier",
    "HybridTaskManager",
    "get_hybrid_task_manager",
    "TaskMigrationError",
    "TaskStatusMapper",
    "MigratedTask",
    "migrate_old_task",
    "migrate_task_manager_state",
    "HybridTaskAdapter",
    "HybridTaskCompletionNotifier",
]
