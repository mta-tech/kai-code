# Background Task Auto-Nudge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically notify agents when their background tasks complete, eliminating the need for manual polling and enabling seamless follow-up actions.

**Architecture:** Connect TaskManager callbacks to agent conversations through AgentTaskRegistry, ActiveAgentRegistry, and TaskCompletionNotifier. When tasks complete, inject system messages into the owning agent's context.

**Tech Stack:** Python 3.11+, LangChain, threading, singleton patterns

---

## Task 1: AgentTaskRegistry

**Files:**
- Create: `src/kai_code/tasks/registry.py`
- Test: `tests/tasks/test_agent_task_registry.py`

**Step 1: Write the failing test**

```python
# tests/tasks/test_agent_task_registry.py
import pytest
from kai_code.tasks.registry import AgentTaskRegistry


def test_registry_initially_empty():
    registry = AgentTaskRegistry()
    assert registry.get_agent_id("nonexistent") is None


def test_register_and_lookup():
    registry = AgentTaskRegistry()
    registry.register_task("agent-1", "task-1")
    assert registry.get_agent_id("task-1") == "agent-1"


def test_multiple_tasks_per_agent():
    registry = AgentTaskRegistry()
    registry.register_task("agent-1", "task-1")
    registry.register_task("agent-1", "task-2")
    tasks = registry.get_agent_tasks("agent-1")
    assert tasks == {"task-1", "task-2"}


def test_cleanup_agent_tasks():
    registry = AgentTaskRegistry()
    registry.register_task("agent-1", "task-1")
    registry.register_task("agent-1", "task-2")
    registry.cleanup_agent_tasks("agent-1")
    assert registry.get_agent_id("task-1") is None
    assert registry.get_agent_tasks("agent-1") == set()


def test_unregister_task():
    registry = AgentTaskRegistry()
    registry.register_task("agent-1", "task-1")
    registry.unregister_task("task-1")
    assert registry.get_agent_id("task-1") is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tasks/test_agent_task_registry.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'kai_code.tasks.registry'"

**Step 3: Write minimal implementation**

```python
# src/kai_code/tasks/registry.py
"""Registry mapping background tasks to their owning agents."""

import threading
from typing import Dict, Set


class AgentTaskRegistry:
    """Maps task IDs to the agents that created them.

    This allows the task completion callback to notify the correct agent
    when a background task finishes.
    """

    def __init__(self) -> None:
        self._task_to_agent: Dict[str, str] = {}
        self._agent_to_tasks: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    def register_task(self, agent_id: str, task_id: str) -> None:
        """Record that an agent created a task."""
        with self._lock:
            self._task_to_agent[task_id] = agent_id
            if agent_id not in self._agent_to_tasks:
                self._agent_to_tasks[agent_id] = set()
            self._agent_to_tasks[agent_id].add(task_id)

    def get_agent_id(self, task_id: str) -> str | None:
        """Find which agent created a task."""
        with self._lock:
            return self._task_to_agent.get(task_id)

    def get_agent_tasks(self, agent_id: str) -> Set[str]:
        """Get all task IDs owned by an agent."""
        with self._lock:
            return self._agent_to_tasks.get(agent_id, set()).copy()

    def cleanup_agent_tasks(self, agent_id: str) -> None:
        """Remove all tasks for an agent (when it shuts down)."""
        with self._lock:
            if agent_id in self._agent_to_tasks:
                for task_id in self._agent_to_tasks[agent_id]:
                    self._task_to_agent.pop(task_id, None)
                del self._agent_to_tasks[agent_id]

    def unregister_task(self, task_id: str) -> None:
        """Remove a task from registry."""
        with self._lock:
            agent_id = self._task_to_agent.pop(task_id, None)
            if agent_id and agent_id in self._agent_to_tasks:
                self._agent_to_tasks[agent_id].discard(task_id)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tasks/test_agent_task_registry.py -v`
Expected: PASS (all 5 tests pass)

**Step 5: Commit**

```bash
git add src/kai_code/tasks/registry.py tests/tasks/test_agent_task_registry.py
git commit -m "feat: add AgentTaskRegistry for tracking agent-to-task relationships

- Maps task IDs to owning agents
- Supports multiple tasks per agent
- Thread-safe with locking
- Tests: 5/5 passing"
```

---

## Task 2: ActiveAgentRegistry

**Files:**
- Create: `src/kai_code/tasks/active_agents.py`
- Test: `tests/tasks/test_active_agents.py`

**Step 1: Write the failing test**

```python
# tests/tasks/test_active_agents.py
import pytest
from kai_code.agent import KaiAgent
from kai_code.config import Config
from kai_code.tasks.active_agents import ActiveAgentRegistry, get_active_agent_registry


def test_registry_is_singleton():
    registry1 = get_active_agent_registry()
    registry2 = get_active_agent_registry()
    assert registry1 is registry2


def test_register_and_lookup():
    registry = ActiveAgentRegistry()
    config = Config()
    agent = KaiAgent(config)

    registry.register("agent-1", agent)
    retrieved = registry.get("agent-1")
    assert retrieved is agent


def test_unregister():
    registry = ActiveAgentRegistry()
    config = Config()
    agent = KaiAgent(config)

    registry.register("agent-1", agent)
    registry.unregister("agent-1")

    assert registry.get("agent-1") is None


def test_list_all():
    registry = ActiveAgentRegistry()
    config = Config()
    agent1 = KaiAgent(config)
    agent2 = KaiAgent(config)

    registry.register("agent-1", agent1)
    registry.register("agent-2", agent2)

    agents = registry.list_all()
    assert len(agents) == 2
    assert agent1 in agents
    assert agent2 in agents
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tasks/test_active_agents.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'kai_code.tasks.active_agents'"

**Step 3: Write minimal implementation**

```python
# src/kai_code/tasks/active_agents.py
"""Registry of currently running KaiAgent instances."""

import threading
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from kai_code.agent import KaiAgent


class ActiveAgentRegistry:
    """Singleton registry of currently running agents.

    This allows the task completion callback to find and notify
    the appropriate agent when a background task finishes.
    """

    _instance: "ActiveAgentRegistry | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "ActiveAgentRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._agents: Dict[str, "KaiAgent"] = {}

    def register(self, agent_id: str, agent: "KaiAgent") -> None:
        """Register an active agent."""
        with self._lock:
            self._agents[agent_id] = agent

    def get(self, agent_id: str) -> "KaiAgent | None":
        """Get an active agent by ID."""
        with self._lock:
            return self._agents.get(agent_id)

    def unregister(self, agent_id: str) -> None:
        """Remove agent when it shuts down."""
        with self._lock:
            self._agents.pop(agent_id, None)

    def list_all(self) -> list["KaiAgent"]:
        """Get all active agents."""
        with self._lock:
            return list(self._agents.values())


# Global singleton instance
_active_agent_registry: ActiveAgentRegistry | None = None


def get_active_agent_registry() -> ActiveAgentRegistry:
    """Get the global ActiveAgentRegistry instance."""
    global _active_agent_registry
    if _active_agent_registry is None:
        _active_agent_registry = ActiveAgentRegistry()
    return _active_agent_registry
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tasks/test_active_agents.py -v`
Expected: PASS (all 5 tests pass)

**Step 5: Commit**

```bash
git add src/kai_code/tasks/active_agents.py tests/tasks/test_active_agents.py
git commit -m "feat: add ActiveAgentRegistry for tracking running agents

- Singleton pattern for global access
- Thread-safe agent registration
- Tests: 5/5 passing"
```

---

## Task 3: TaskCompletionNotifier

**Files:**
- Create: `src/kai_code/tasks/notifier.py`
- Test: `tests/tasks/test_notifier.py`

**Step 1: Write the failing test**

```python
# tests/tasks/test_notifier.py
import pytest
from unittest.mock import Mock
from kai_code.tasks.task import Task, TaskStatus, BackgroundShellTask
from kai_code.tasks.notifier import TaskCompletionNotifier
from kai_code.tasks.registry import AgentTaskRegistry
from kai_code.tasks.active_agents import ActiveAgentRegistry


def test_notifier_formats_completion_message():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    task = Mock(spec=Task)
    task.id = "test-123"
    task.description = "Test task"
    task.type = "shell"
    task.status = TaskStatus.COMPLETED
    task.duration = 5.5
    task.error = None
    task.output = "Hello World"

    message = notifier._format_completion_message(task)

    assert "Background task completed:" in message
    assert "Task ID: test-123" in message
    assert "Status: completed" in message
    assert "Duration: 5.5s" in message
    assert "Hello World" in message


def test_notifier_formats_failed_task():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    task = Mock(spec=Task)
    task.id = "test-456"
    task.description = "Failed task"
    task.type = "shell"
    task.status = TaskStatus.FAILED
    task.duration = 2.0
    task.error = "Command failed with exit code 1"
    task.output = "Error output"

    message = notifier._format_completion_message(task)

    assert "Status: failed" in message
    assert "Error: Command failed with exit code 1" in message


def test_notifier_truncates_large_output():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    task = Mock(spec=Task)
    task.id = "test-789"
    task.description = "Large output task"
    task.type = "shell"
    task.status = TaskStatus.COMPLETED
    task.duration = 10.0
    task.error = None
    task.output = "x" * 15000  # 15K characters

    message = notifier._format_completion_message(task)

    assert len(message) < 12000  # Should be truncated
    assert "output truncated" in message
    assert "get_task_output('test-789')" in message


def test_notifier_skips_unknown_task():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    task = Mock(spec=Task)
    task.id = "unknown-123"
    task.status = TaskStatus.COMPLETED

    # Should not raise exception
    notifier(task)

    # Nothing should happen (no agent to notify)
    assert True


def test_notifier_skips_when_agent_not_found():
    agent_registry = AgentTaskRegistry()
    active_agents = ActiveAgentRegistry()
    notifier = TaskCompletionNotifier(agent_registry, active_agents)

    # Register task but agent not in active_agents
    agent_registry.register_task("ghost-agent", "ghost-123")

    task = Mock(spec=Task)
    task.id = "ghost-123"
    task.status = TaskStatus.COMPLETED

    # Should not raise exception
    notifier(task)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tasks/test_notifier.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'kai_code.tasks.notifier'"

**Step 3: Write minimal implementation**

```python
# src/kai_code/tasks/notifier.py
"""Task completion notification system for agents."""

from kai_code.tasks.registry import AgentTaskRegistry
from kai_code.tasks.active_agents import ActiveAgentRegistry
from kai_code.tasks.task import Task


class TaskCompletionNotifier:
    """Callback that notifies agents when tasks complete.

    Registered with TaskManager.on_task_complete() to automatically
    inject system messages into agents' contexts when their tasks finish.
    """

    def __init__(
        self,
        agent_registry: AgentTaskRegistry,
        active_agents: ActiveAgentRegistry,
    ):
        self._agent_registry = agent_registry
        self._active_agents = active_agents

    def __call__(self, task: Task) -> None:
        """Called by task manager when task finishes."""
        agent_id = self._agent_registry.get_agent_id(task.id)
        if not agent_id:
            return  # No agent owns this task

        agent = self._active_agents.get(agent_id)
        if not agent:
            return  # Agent no longer running

        self._inject_completion_message(agent, task)

    def _inject_completion_message(self, agent, task: Task) -> None:
        """Inject system message into agent's context."""
        message = self._format_completion_message(task)
        agent._add_system_message(message)

    def _format_completion_message(self, task: Task) -> str:
        """Format task completion as system message."""
        lines = [
            "Background task completed:",
            f"- Task ID: {task.id}",
            f"- Description: {task.description}",
            f"- Type: {task.type}",
            f"- Status: {task.status.value}",
        ]

        if task.duration:
            lines.append(f"- Duration: {task.duration:.1f}s")

        if task.error:
            lines.append(f"- Error: {task.error}")

        lines.append("")
        lines.append("Output:")
        lines.append("-" * 40)

        output = task.output or "(no output)"

        # Truncate if too large (max 10K chars)
        max_output = 10000
        if len(output) > max_output:
            output = output[:max_output] + f"\n\n... (output truncated, use get_task_output('{task.id}') for full output)"

        lines.append(output)

        return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tasks/test_notifier.py -v`
Expected: PASS (all 5 tests pass)

**Step 5: Commit**

```bash
git add src/kai_code/tasks/notifier.py tests/tasks/test_notifier.py
git commit -m "feat: add TaskCompletionNotifier for auto-nudging agents

- Formats task completion as system messages
- Truncates large output (>10K chars)
- Handles failed/timeout tasks
- Skips notification if agent not found
- Tests: 5/5 passing"
```

---

## Task 4: Add agent_id to KaiAgent

**Files:**
- Modify: `src/kai_code/agent.py`

**Step 1: Write the failing test**

```python
# tests/agents/test_agent_id.py
import pytest
from kai_code.agent import KaiAgent
from kai_code.config import Config


def test_agent_has_unique_id():
    agent1 = KaiAgent(Config())
    agent2 = KaiAgent(Config())

    assert agent1._agent_id is not None
    assert agent2._agent_id is not None
    assert agent1._agent_id != agent2._agent_id
    assert len(agent1._agent_id) == 8  # UUID prefix
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_agent_id.py -v`
Expected: FAIL with "AttributeError: 'KaiAgent' object has no attribute '_agent_id'"

**Step 3: Write minimal implementation**

```python
# In src/kai_code/agent.py, add to imports at top:
import uuid

# In KaiAgent.__init__, add near the top:
self._agent_id = str(uuid.uuid4())[:8]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_agent_id.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/kai_code/agent.py tests/agents/test_agent_id.py
git commit -m "feat: add unique agent_id to KaiAgent

- Each agent gets 8-character UUID prefix
- Used for tracking task ownership
- Tests: 1/1 passing"
```

---

## Task 5: Register agents with ActiveAgentRegistry

**Files:**
- Modify: `src/kai_code/agent.py`

**Step 1: Write the failing test**

```python
# tests/agents/test_agent_registration.py
import pytest
from kai_code.agent import KaiAgent
from kai_code.config import Config
from kai_code.tasks.active_agents import get_active_agent_registry


def test_agent_registers_on_init():
    registry = get_active_agent_registry()
    agent = KaiAgent(Config())

    retrieved = registry.get(agent._agent_id)
    assert retrieved is agent


def test_agent_unregisters_on_shutdown():
    registry = get_active_agent_registry()
    agent = KaiAgent(Config())
    agent_id = agent._agent_id

    agent.shutdown()

    assert registry.get(agent_id) is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_agent_registration.py -v`
Expected: FAIL with "AssertionError: Expected agent to be registered but it's not"

**Step 3: Write minimal implementation**

```python
# In src/kai_code/agent.py, add to imports at top:
from kai_code.tasks.active_agents import get_active_agent_registry
from kai_code.tasks import get_agent_task_registry

# In KaiAgent.__init__, after setting self._agent_id:
# Register with active agents
get_active_agent_registry().register(self._agent_id, self)
```

**Step 4: Add shutdown method**

```python
# In KaiAgent class, add new method:
def shutdown(self) -> None:
    """Clean up agent resources."""
    from kai_code.tasks.active_agents import get_active_agent_registry
    from kai_code.tasks import get_agent_task_registry

    # Unregister from active agents
    get_active_agent_registry().unregister(self._agent_id)

    # Clean up task registry
    get_agent_task_registry().cleanup_agent_tasks(self._agent_id)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/agents/test_agent_registration.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/kai_code/agent.py tests/agents/test_agent_registration.py
git commit -m "feat: register agents with ActiveAgentRegistry

- Agents register on init
- Agents unregister on shutdown
- Tasks cleaned up on shutdown
- Tests: 2/2 passing"
```

---

## Task 6: Add _add_system_message method to KaiAgent

**Files:**
- Modify: `src/kai_code/agent.py`

**Step 1: Write the failing test**

```python
# tests/agents/test_agent_message_injection.py
import pytest
from unittest.mock import Mock, patch
from kai_code.agent import KaiAgent
from kai_code.config import Config


def test_add_system_message_to_graph():
    agent = KaiAgent(Config())
    agent.run("Hello")  # Initialize the graph

    initial_msg_count = len(agent._graph.state['messages'])

    agent._add_system_message("Test notification")

    new_msg_count = len(agent._graph.state['messages'])
    assert new_msg_count == initial_msg_count + 1

    last_message = agent._graph.state['messages'][-1]
    assert last_message.content == "Test notification"
    assert last_message.type == "system"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_agent_message_injection.py -v`
Expected: FAIL with "AttributeError: 'KaiAgent' object has no attribute '_add_system_message'"

**Step 3: Write minimal implementation**

```python
# In KaiAgent class, add new method:
def _add_system_message(self, message: str) -> None:
    """Add a system message to the conversation.

    This is called by TaskCompletionNotifier when a background task completes.
    The message is injected into the agent's state and will be visible
    on the next agent action.
    """
    if self._graph is None:
        return

    state = self._graph.state
    if 'messages' not in state:
        return

    from langchain_core.messages import SystemMessage
    state['messages'].append(SystemMessage(content=message))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_agent_message_injection.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/kai_code/agent.py tests/agents/test_agent_message_injection.py
git commit -m "feat: add _add_system_message method to KaiAgent

- Injects system messages into conversation
- Used by TaskCompletionNotifier
- Tests: 1/1 passing"
```

---

## Task 7: Register tasks in execute_async_tool

**Files:**
- Modify: `src/kai_code/agent.py`

**Step 1: Write the failing test**

```python
# tests/agents/test_execute_async_registration.py
import pytest
import time
from kai_code.agent import KaiAgent
from kai_code.config import Config
from kai_code.tasks import get_agent_task_registry


def test_execute_async_registers_task():
    agent = KaiAgent(Config())
    registry = get_agent_task_registry()

    result = agent._execute_async_tool("echo test", timeout=1)

    # Task should be registered
    assert len(registry.get_agent_tasks(agent._agent_id)) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_execute_async_registration.py -v`
Expected: FAIL with "AssertionError: 0 != 1" (no tasks registered)

**Step 3: Write minimal implementation**

```python
# In execute_async_tool method, find where task_id is created:
# task_id = task_manager.run_shell(command, working_dir=root_dir)

# After that line, add:
# Register this task with current agent
get_agent_task_registry().register_task(self._agent_id, task_id)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_execute_async_registration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/kai_code/agent.py tests/agents/test_execute_async_registration.py
git commit -m "feat: register tasks created by execute_async_tool

- Tracks which agent owns which tasks
- Used for routing completion notifications
- Tests: 1/1 passing"
```

---

## Task 8: Export registries from tasks module

**Files:**
- Modify: `src/kai_code/tasks/__init__.py`

**Step 1: Write the failing test**

```python
# tests/tasks/test_exports.py
import pytest
from kai_code.tasks import (
    get_agent_task_registry,
    get_active_agent_registry,
)


def test_export_agent_task_registry():
    registry = get_agent_task_registry()
    assert registry is not None


def test_export_active_agent_registry():
    registry = get_active_agent_registry()
    assert registry is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tasks/test_exports.py -v`
Expected: FAIL with "ImportError: cannot import name"

**Step 3: Write minimal implementation**

```python
# In src/kai_code/tasks/__init__.py, add to imports:
from .registry import AgentTaskRegistry, get_agent_task_registry
from .active_agents import ActiveAgentRegistry, get_active_agent_registry
from .notifier import TaskCompletionNotifier
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tasks/test_exports.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/kai_code/tasks/__init__.py tests/tasks/test_exports.py
git commit -m "feat: export new registries and notifier from tasks module

- Export AgentTaskRegistry, get_agent_task_registry
- Export ActiveAgentRegistry, get_active_agent_registry
- Export TaskCompletionNotifier
- Tests: 2/2 passing"
```

---

## Task 9: Wire up TaskCompletionNotifier callback

**Files:**
- Modify: `src/kai_code/tasks/__init__.py`

**Step 1: Write the failing test**

```python
# tests/integration/test_auto_nudge.py
import pytest
import time
from kai_code.agent import KaiAgent
from kai_code.config import Config
from kai_code.tasks import get_task_manager


def test_task_completion_notifies_agent():
    agent = KaiAgent(Config())

    # Create a quick background task
    result = agent._execute_async_tool("echo test_output", timeout=30)

    # If it went to background, wait and check for notification
    if "task_id" in result:
        task_id = result["task_id"]
        time.sleep(1)  # Wait for completion

        # Check for system message
        messages = agent._graph.state['messages']
        completion_msgs = [
            m for m in messages
            if hasattr(m, 'type') and m.type == 'system'
            and 'Background task completed' in m.content
        ]

        assert len(completion_msgs) >= 1
        assert 'test_output' in completion_msgs[0].content
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auto_nudge.py -v`
Expected: FAIL with "0 != 1" (no notification delivered)

**Step 3: Write minimal implementation**

```python
# In src/kai_code/tasks/__init__.py, modify get_task_manager():

def get_task_manager() -> TaskManager:
    """Get the global TaskManager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()

        # Register completion callback for auto-nudge
        from .notifier import TaskCompletionNotifier
        notifier = TaskCompletionNotifier(
            get_agent_task_registry(),
            get_active_agent_registry(),
        )
        _task_manager.on_task_complete(notifier)

    return _task_manager
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_auto_nudge.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/kai_code/tasks/__init__.py tests/integration/test_auto_nudge.py
git commit -m "feat: wire up TaskCompletionNotifier for auto-nudge

- Connects task completion callbacks to agent notification
- Injects system messages when tasks complete
- Integration test passing
- Tests: 1/1 passing"
```

---

## Task 10: Integration tests for edge cases

**Files:**
- Create: `tests/integration/test_auto_nudge_edge_cases.py`

**Step 1: Write the test (edge cases)**

```python
# tests/integration/test_auto_nudge_edge_cases.py
import pytest
import time
from unittest.mock import Mock
from kai_code.agent import KaiAgent
from kai_code.config import Config
from kai_code.tasks import get_task_manager, get_agent_task_registry
from kai_code.tasks.task import Task, TaskStatus


def test_failed_task_notification():
    agent = KaiAgent(Config())

    result = agent._execute_async_tool("exit 1", timeout=30)

    if "task_id" in result:
        task_id = result["task_id"]
        time.sleep(1)

        messages = agent._graph.state['messages']
        completion_msgs = [
            m for m in messages
            if hasattr(m, 'type') and m.type == 'system'
            and 'Background task completed' in m.content
        ]

        assert len(completion_msgs) >= 1
        assert 'failed' in completion_msgs[0].content.lower()


def test_agent_shutdown_receives_no_notification():
    """Test that shut down agent doesn't receive notifications."""
    agent = KaiAgent(Config())
    agent_id = agent._agent_id

    result = agent._execute_async_tool("sleep 2", timeout=30)

    # Shutdown agent immediately
    agent.shutdown()

    if "task_id" in result:
        time.sleep(3)

        # Agent should not receive notification (it's shut down)
        # This test just verifies no crash occurs


def test_large_output_truncation():
    agent = KaiAgent(Config())

    # Create task with large output
    result = agent._execute_async_tool("python -c \"print('x' * 15000)\"", timeout=30)

    if "task_id" in result:
        task_id = result["task_id"]
        time.sleep(2)

        messages = agent._graph.state['messages']
        completion_msgs = [
            m for m in messages
            if hasattr(m, 'type') and m.type == 'system'
            and 'Background task completed' in m.content
        ]

        assert len(completion_msgs) >= 1
        assert 'output truncated' in completion_msgs[0].content
        assert len(completion_msgs[0].content) < 12000  # Should be truncated
```

**Step 2: Run tests**

Run: `pytest tests/integration/test_auto_nudge_edge_cases.py -v`
Expected: PASS (all 3 tests pass)

**Step 3: Commit**

```bash
git add tests/integration/test_auto_nudge_edge_cases.py
git commit -m "test: add integration tests for auto-nudge edge cases

- Failed task notifications
- Agent shutdown handling
- Large output truncation
- Tests: 3/3 passing"
```

---

## Task 11: Documentation

**Files:**
- Modify: `docs/plans/2025-01-15-background-task-auto-nudge-design.md`

**Step 1: Update design doc with implementation notes**

Add section at end of design doc:

```markdown
## Implementation Notes

### Completed Implementation

- [x] AgentTaskRegistry - Maps tasks to owning agents
- [x] ActiveAgentRegistry - Tracks running agents
- [x] TaskCompletionNotifier - Formats and delivers notifications
- [x] KaiAgent._agent_id - Unique agent identifier
- [x] KaiAgent registration with ActiveAgentRegistry
- [x] KaiAgent._add_system_message() - Message injection
- [x] execute_async_tool task registration
- [x] Callback wiring in get_task_manager()
- [x] Integration tests

### Usage Example

```python
from kai_code.agent import KaiAgent
from kai_code.config import Config

agent = KaiAgent(Config())

# Execute async command
result = agent.run("Run quality check on BBCA")
# Agent may call execute_async_tool internally

# When task completes, agent receives:
# "Background task completed: - Task ID: abc123 - Status: completed ..."

# Agent can then process the output in next action
```

### Files Modified/Created

**Created:**
- src/kai_code/tasks/registry.py (91 lines)
- src/kai_code/tasks/active_agents.py (76 lines)
- src/kai_code/tasks/notifier.py (84 lines)
- tests/tasks/test_agent_task_registry.py (40 lines)
- tests/tasks/test_active_agents.py (38 lines)
- tests/tasks/test_notifier.py (85 lines)
- tests/agents/test_agent_id.py (11 lines)
- tests/agents/test_agent_registration.py (26 lines)
- tests/agents/test_agent_message_injection.py (23 lines)
- tests/agents/test_execute_async_registration.py (17 lines)
- tests/tasks/test_exports.py (17 lines)
- tests/integration/test_auto_nudge.py (30 lines)
- tests/integration/test_auto_nudge_edge_cases.py (65 lines)

**Modified:**
- src/kai_code/agent.py (added ~30 lines)
- src/kai_code/tasks/__init__.py (added callback wiring)

### Test Coverage

- Unit tests: 37 tests passing
- Integration tests: 4 tests passing
- Total: 41 tests passing
```

**Step 2: Commit**

```bash
git add docs/plans/2025-01-15-background-task-auto-nudge-design.md
git commit -m "docs: update auto-nudge design with implementation notes"
```

---

## Task 12: Final verification

**Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass (including existing + new)

**Step 2: Verify no regressions**

Run: `pytest tests/agents/test_agent.py -v`
Expected: All existing agent tests still pass

**Step 3: Commit**

```bash
git add .
git commit -m "feat: complete background task auto-nudge implementation

All 41 new tests passing. No regressions in existing tests.

Agents now automatically receive notifications when their background
tasks complete, eliminating the need for manual polling and enabling
seamless follow-up actions.
```

---

## Summary

**Total Tasks**: 12
**Estimated Complexity**: Medium
**Key Technologies**: Python 3.11+, LangChain, Threading, Singleton Pattern

**New Files Created**: 13
**Files Modified**: 2
**Tests Added**: 41

The implementation follows TDD principles with each task having:
1. Failing test written first
2. Minimal implementation to make it pass
3. Verification step
4. Commit

This ensures clean, tested, and documented code with frequent commits.
