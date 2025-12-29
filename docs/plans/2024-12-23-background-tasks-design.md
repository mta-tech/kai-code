# Background Tasks Design

## Overview

Add background task support to kai-code Rich CLI, enabling users to run shell commands and agent prompts in the background while continuing to interact with the main conversation.

## User Experience

### Launching Background Tasks

- **Ctrl+B** sends current input as background task
- Shell commands (prefixed with `!`) run as subprocess
- Agent prompts run as fresh KaiAgent instance

### Viewing Tasks

- `/tasks` opens full-screen panel showing all tasks
- Status bar shows "N background tasks" when tasks exist
- Panel navigation: ↑/↓ select, Enter view, k kill, c clear, Esc close

### Agent Integration

Main agent can observe and act on background tasks via tools:
- `list_background_tasks()` - See all tasks and status
- `get_task_output(task_id)` - Get full output
- `kill_task(task_id)` - Terminate running task

## Architecture

### Directory Structure

```
src/kai_code/tasks/
├── __init__.py      # Exports: TaskManager, Task, TaskStatus
├── manager.py       # TaskManager singleton, ThreadPoolExecutor
├── task.py          # Task, BackgroundShellTask, BackgroundAgentTask
├── panel.py         # Rich-based /tasks panel UI
└── tools.py         # Agent tools for task interaction
```

### Task Model

```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"

@dataclass
class Task:
    id: str                           # UUID
    type: Literal["shell", "agent"]
    description: str                  # Truncated for display
    status: TaskStatus
    output: str                       # Captured output
    created_at: datetime
    finished_at: datetime | None
    exit_code: int | None             # Shell tasks only
    error: str | None
```

### TaskManager

```python
class TaskManager:
    """Singleton managing all background tasks."""

    _instance: TaskManager | None = None
    _executor: ThreadPoolExecutor     # Max 5 concurrent tasks
    _tasks: dict[str, Task]

    def run_shell(self, command: str) -> str:
        """Run shell command in background. Returns task_id."""

    def run_agent(self, prompt: str) -> str:
        """Run agent prompt in background. Returns task_id."""

    def get_task(self, task_id: str) -> Task | None
    def get_all_tasks(self) -> list[Task]
    def get_active_tasks(self) -> list[Task]
    def active_count(self) -> int

    def kill_task(self, task_id: str) -> bool
    def kill_all(self) -> None
    def clear_completed(self) -> int
```

### Shell Task Execution

```python
class BackgroundShellTask(Task):
    def run(self):
        self.status = TaskStatus.RUNNING
        process = subprocess.Popen(
            self.command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.working_dir,
        )
        self.output, _ = process.communicate()
        self.exit_code = process.returncode
        self.status = TaskStatus.COMPLETED if self.exit_code == 0 else TaskStatus.FAILED
        self.finished_at = datetime.now()
```

### Agent Task Execution

```python
class BackgroundAgentTask(Task):
    def run(self):
        self.status = TaskStatus.RUNNING
        agent = KaiAgent(
            root_dir=self.root_dir,
            model=self.model,
            yolo=True,  # Background agents auto-approve
        )
        result = agent.run(self.prompt)
        self.output = result.output
        self.status = TaskStatus.COMPLETED
        self.finished_at = datetime.now()
```

## UI Components

### Status Bar Integration

```python
def get_prompt():
    task_count = task_manager.active_count()
    suffix = f" | {task_count} background tasks" if task_count > 0 else ""
    return f"kai>{suffix} "
```

### Task Panel Layout

```
┌─ Background tasks ─────────────────────────────────────┐
│ 2 active, 4 completed                                  │
│                                                        │
│ Running (2)                                            │
│ › ! pytest tests/ -v              ⟳ 12.3s             │
│   Agent: review the auth module   ⟳ 8.1s              │
│                                                        │
│ Completed (4)                                          │
│   ! dbt build                     ✓ done (45.2s)      │
│   ! docker-compose up -d          ✓ done (3.1s)       │
│   Agent: summarize changes        ✓ completed         │
│   ! git status                    ✓ done (0.2s)       │
│                                                        │
├────────────────────────────────────────────────────────┤
│ ↑/↓ select · Enter view · k kill · c clear · Esc close│
└────────────────────────────────────────────────────────┘
```

### Output View

```
┌─ Output: pytest tests/ -v ─────────────────────────────┐
│ ===== test session starts =====                        │
│ collected 28 items                                     │
│                                                        │
│ tests/test_loader.py::test_loads ✓                    │
│ tests/test_loader.py::test_cache ✓                    │
│ ...                                                    │
├────────────────────────────────────────────────────────┤
│ Esc back · q close                                     │
└────────────────────────────────────────────────────────┘
```

## Agent Tools

```python
@tool("list_background_tasks")
def list_background_tasks() -> str:
    """List all background tasks with status and summary."""
    tasks = task_manager.get_all_tasks()
    # Format as table: id, type, description, status, duration

@tool("get_task_output")
def get_task_output(task_id: str) -> str:
    """Get full output of a completed background task."""
    task = task_manager.get_task(task_id)
    return task.output if task else "Task not found"

@tool("kill_task")
def kill_task(task_id: str) -> str:
    """Kill a running background task."""
    success = task_manager.kill_task(task_id)
    return "Task killed" if success else "Failed to kill task"
```

## Files to Modify

| File | Changes |
|------|---------|
| `rich_input.py` | Add Ctrl+B key binding |
| `rich_main.py` | Integrate TaskManager, cleanup on exit |
| `rich_commands.py` | Add `/tasks` command handler |
| `agent.py` | Register task tools in `_build_graph()` |

## Lifecycle

1. **Startup:** TaskManager initialized as singleton
2. **Ctrl+B pressed:** Detect shell vs agent, spawn task in thread pool
3. **Task runs:** Output captured, status updated
4. **Completion:** Status changes to completed/failed, output stored
5. **Exit:** All running tasks killed, cleanup

## Key Decisions

- **Fresh agents:** Background agent tasks have no conversation history
- **Auto-approve:** Background agents run with `yolo=True`
- **No persistence:** Tasks killed on CLI exit (no orphan processes)
- **Unified list:** Shell and agent tasks in same list (no separate sections)
- **Max concurrency:** 5 concurrent tasks via ThreadPoolExecutor
- **Silent completion:** No auto-injection, users check `/tasks`

## Testing Strategy

1. Unit tests for TaskManager (create, run, kill, clear)
2. Unit tests for Task state transitions
3. Integration tests for Ctrl+B binding
4. Integration tests for `/tasks` panel navigation
5. Integration tests for agent tools
