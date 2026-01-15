# Background Task Auto-Nudge Design

> **Status**: Design Complete
> **Created**: 2025-01-15
> **Author**: Fitra Kacamarga + Claude

## Overview

Improve kai-code's background task system to automatically notify agents when their tasks complete, eliminating the need for agents to repeatedly poll `get_task_output()` and enabling seamless follow-up actions.

## Problem Statement

**Current Behavior** (Passive):
```
Agent → execute_async() → task_id returned
Agent → get_task_output(task_id) → "still running"
Agent → get_task_output(task_id) → "still running"
Agent → get_task_output(task_id) → "still running"
... (infinite polling loop bug we just fixed)
```

**Desired Behavior** (Proactive):
```
Agent → execute_async() → task_id returned
                     ↓
              Task runs in background
                     ↓
          Task completes → Auto-nudge agent
                     ↓
      Agent receives: "Background task completed. Output: {...}"
                     ↓
         Agent's next action sees this and can follow up
```

## Requirements

1. **Auto-nudge all background tasks** - No opt-in required
2. **Context injection** - Output injected into agent's context for next action
3. **System message format** - Clear, structured completion notification
4. **Agent-specific** - Only notify the agent that created the task
5. **Non-blocking** - Don't interrupt agent if it's busy working
6. **Handle edge cases** - Large output, failed tasks, agent shutdown

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                         KaiAgent                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  execute_async_tool()                                       │  │
│  │    1. Run task via TaskManager                              │  │
│  │    2. Register with AgentTaskRegistry                       │  │
│  │    3. Return task_id                                        │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  _add_system_message()                                      │  │
│  │    - Inject system message into conversation history        │  │
│  │    - Available for next agent action                       │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    ↑
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                    TaskCompletionNotifier                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  __call__(task)                                             │  │
│  │    1. Called by TaskManager when task completes            │  │
│  │    2. Lookup agent_id from AgentTaskRegistry              │  │
│  │    3. Get agent from ActiveAgentRegistry                  │  │
│  │    4. Format completion message                             │  │
│  │    5. Call agent._add_system_message()                     │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    ↑
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                      TaskManager                                    │
│  - Runs background tasks                                         │
│  - Calls registered callbacks on completion                      │
│  - Already has callback mechanism: on_task_complete()           │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Agent calls execute_async_tool()
   ├─ TaskManager.run_shell()
   ├─ AgentTaskRegistry.register(agent_id, task_id)
   └─ Return task_id to agent

2. Task runs in background thread...

3. Task completes
   ├─ TaskManager._notify_completion(task)
   ├─ TaskCompletionNotifier.__call__(task)
   ├─ AgentTaskRegistry.get_agent_id(task_id) → agent_id
   ├─ ActiveAgentRegistry.get_agent(agent_id) → agent
   ├─ agent._add_system_message(completion_message)
   └─ Message now in agent's context

4. Agent's next action
   ├─ Sees system message in conversation
   ├─ Can process output immediately
   └─ No need to call get_task_output()
```

## Component Specifications

### 1. AgentTaskRegistry

**Location**: `src/kai_code/tasks/registry.py`

```python
class AgentTaskRegistry:
    """Maps task IDs to the agents that created them."""

    def __init__(self) -> None:
        self._task_to_agent: dict[str, str] = {}  # task_id → agent_id
        self._agent_to_tasks: dict[str, set[str]] = {}  # agent_id → {task_ids}

    def register_task(self, agent_id: str, task_id: str) -> None:
        """Record that an agent created a task."""

    def get_agent_id(self, task_id: str) -> str | None:
        """Find which agent created a task."""

    def cleanup_agent_tasks(self, agent_id: str) -> None:
        """Remove all tasks for an agent (when it shuts down)."""

    def get_agent_tasks(self, agent_id: str) -> set[str]:
        """Get all task IDs owned by an agent."""

    def unregister_task(self, task_id: str) -> None:
        """Remove a task from registry."""
```

### 2. ActiveAgentRegistry

**Location**: `src/kai_code/tasks/active_agents.py`

```python
class ActiveAgentRegistry:
    """Singleton registry of currently running agents."""

    _instance: ActiveAgentRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> ActiveAgentRegistry:
        # Singleton pattern...

    def __init__(self) -> None:
        self._agents: dict[str, KaiAgent] = {}

    def register(self, agent_id: str, agent: KaiAgent) -> None:
        """Register an active agent."""

    def get(self, agent_id: str) -> KaiAgent | None:
        """Get an active agent by ID."""

    def unregister(self, agent_id: str) -> None:
        """Remove agent when it shuts down."""

    def list_all(self) -> list[KaiAgent]:
        """Get all active agents."""
```

### 3. TaskCompletionNotifier

**Location**: `src/kai_code/tasks/notifier.py`

```python
class TaskCompletionNotifier:
    """Callback that notifies agents when tasks complete."""

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

    def _inject_completion_message(self, agent: KaiAgent, task: Task) -> None:
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

        # Truncate if too large
        max_output = 10000
        if len(output) > max_output:
            output = output[:max_output] + f"\n\n... (output truncated, use get_task_output('{task.id}') for full output)"

        lines.append(output)

        return "\n".join(lines)
```

### 4. KaiAgent Modifications

**Location**: `src/kai_code/agent.py`

**Add agent ID**:
```python
class KaiAgent:
    def __init__(self, config: Config | None = None):
        # ... existing init ...
        self._agent_id = str(uuid.uuid4())[:8]

        # Register with active agents
        from kai_code.tasks.active_agents import get_active_agent_registry
        get_active_agent_registry().register(self._agent_id, self)
```

**Modify execute_async_tool**:
```python
@tool("execute_async")
def execute_async_tool(command: str, timeout: int) -> str:
    """Execute shell command with auto-background on timeout."""
    from kai_code.tasks import get_task_manager, get_agent_task_registry

    task_id = task_manager.run_shell(command, working_dir=root_dir)

    # NEW: Register this task with current agent
    agent_registry = get_agent_task_registry()
    agent_registry.register_task(self._agent_id, task_id)

    # ... existing return logic ...
```

**Add message injection method**:
```python
def _add_system_message(self, message: str) -> None:
    """Add a system message to the conversation.

    This is called by TaskCompletionNotifier when a background task completes.
    """
    if self._graph is None:
        return

    state = self._graph.state
    if 'messages' not in state:
        return

    from langchain_core.messages import SystemMessage
    state['messages'].append(SystemMessage(content=message))
```

**Add cleanup on shutdown**:
```python
def shutdown(self) -> None:
    """Clean up agent resources."""
    from kai_code.tasks.active_agents import get_active_agent_registry
    from kai_code.tasks import get_agent_task_registry

    # Unregister from active agents
    get_active_agent_registry().unregister(self._agent_id)

    # Clean up task registry
    get_agent_task_registry().cleanup_agent_tasks(self._agent_id)

    # ... existing shutdown logic ...
```

### 5. Wire Up the Callback

**Location**: `src/kai_code/tasks/__init__.py`

```python
def get_task_manager() -> TaskManager:
    """Get the global TaskManager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()

        # Register completion callback
        from kai_code.tasks.notifier import TaskCompletionNotifier
        from kai_code.tasks import get_agent_task_registry
        from kai_code.tasks.active_agents import get_active_agent_registry

        notifier = TaskCompletionNotifier(
            get_agent_task_registry(),
            get_active_agent_registry(),
        )
        _task_manager.on_task_complete(notifier)

    return _task_manager
```

## Edge Cases

### 1. Agent No Longer Running
**Scenario**: Task finishes after agent shut down
**Handling**: Check `active_agents.get()` returns None → Skip notification, log warning

### 2. Multiple Tasks Complete Simultaneously
**Scenario**: 3 tasks finish at same time
**Handling**: Callbacks are already sequential (called in thread) → Messages injected in order

### 3. Task Output Too Large
**Scenario**: Task output is 50K characters
**Handling**: Truncate to 10K chars with message: `... (output truncated, use get_task_output('abc123') for full output)`

### 4. Task Failed/Timeout
**Scenario**: Task had error
**Handling**: Include error field in completion message, status shows "failed" or "timeout"

### 5. Agent in Middle of Action
**Scenario**: Agent executing tool when task completes
**Handling**: Don't interrupt → Inject message into state, available for next action

### 6. Agent Created Task vs Inherited Tools
**Scenario**: Multiple agents have access to background task tools
**Handling**: Only the agent that called `execute_async()` gets notified (tracked via registry)

## Testing Strategy

### Unit Tests

**File**: `tests/tasks/test_agent_task_registry.py`
- Register and lookup tasks
- Cleanup agent tasks
- Handle unknown tasks
- Multiple tasks per agent

**File**: `tests/tasks/test_active_agents.py`
- Register and unregister agents
- Lookup agents
- Handle unknown agents
- List all agents

**File**: `tests/tasks/test_notifier.py`
- Format completion message (success, failed, timeout)
- Handle agent not found
- Handle agent not running
- Output truncation

**File**: `tests/agents/test_agent_lifecycle.py`
- Agent gets unique ID
- Agent registers on init
- Agent unregisters on shutdown
- Tasks cleaned up on shutdown

### Integration Tests

**File**: `tests/integration/test_auto_nudge.py`
- End-to-end: Agent creates task → Completes → Notification injected
- Multiple agents: Tasks notify correct respective agents
- Agent shutdown: Tasks don't notify after agent unregistered
- Large output: Truncation works correctly
- Failed task: Error notification delivered properly
- Concurrent completions: Multiple notifications delivered in order

### Test Example

```python
def test_auto_nudge_on_task_completion():
    """Test that agent receives notification when task completes."""
    agent = KaiAgent()

    # Create a quick task
    result = json.loads(agent._execute_async_tool("echo test123", timeout=5))

    # If it went to background (which it shouldn't for echo), wait for completion
    if "task_id" in result:
        task_id = result["task_id"]
        time.sleep(1)  # Wait for task to complete

    # Check system message was injected
    messages = agent._graph.state['messages']
    completion_msgs = [
        m for m in messages
        if isinstance(m, SystemMessage) and 'Background task completed' in m.content
    ]

    assert len(completion_msgs) >= 1
    assert 'test123' in completion_msgs[0].content
```

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] AgentTaskRegistry implementation
- [ ] ActiveAgentRegistry implementation
- [ ] TaskCompletionNotifier implementation
- [ ] Unit tests for all three

### Phase 2: Agent Integration
- [ ] Add agent_id to KaiAgent
- [ ] Register/unregister with active agents
- [ ] Implement _add_system_message()
- [ ] Modify execute_async_tool to register tasks
- [ ] Add shutdown cleanup

### Phase 3: Callback Wiring
- [ ] Wire up TaskCompletionNotifier in get_task_manager()
- [ ] Test callback is called
- [ ] Test message injection

### Phase 4: Testing & Polish
- [ ] Integration tests
- [ ] Edge case handling
- [x] Documentation
- [x] Verify no regressions

## Backward Compatibility

- All existing functionality preserved
- Auto-nudge is purely additive
- Agents can still call get_task_output() if desired
- No changes to task manager core behavior

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

agent = KaiAgent(root_dir=Path.cwd())

# Execute async command (internally calls execute_async_tool)
result = agent.run("Run long-running task")

# When task completes, agent receives:
# "Background task completed: - Task ID: abc123 - Status: completed ..."

# Agent can then process the output in next action
```

### Files Created/Modified

**Created:**
- src/kai_code/tasks/registry.py (62 lines)
- src/kai_code/tasks/active_agents.py (73 lines)
- src/kai_code/tasks/notifier.py (84 lines)
- tests/tasks/test_agent_task_registry.py (28 lines)
- tests/tasks/test_active_agents.py (45 lines)
- tests/tasks/test_notifier.py (85 lines)
- tests/agents/test_agent_id.py (16 lines)
- tests/agents/test_agent_registration.py (25 lines)
- tests/agents/test_agent_message_injection.py (21 lines)
- tests/agents/test_execute_async_registration.py (24 lines)
- tests/integration/test_auto_nudge.py (33 lines)
- tests/integration/test_auto_nudge_edge_cases.py (64 lines)

**Modified:**
- src/kai_code/agent.py (added agent_id, registration, shutdown, _add_system_message, execute_async registration)
- src/kai_code/tasks/__init__.py (exported new classes)
- src/kai_code/tasks/manager.py (wired up callback)

### Test Coverage

- Unit tests: 20 tests passing
- Integration tests: 4 tests passing
- Total: 24 tests passing

### Git Commits

- 8c4d101 - feat: add AgentTaskRegistry
- 92cdef0 - feat: add ActiveAgentRegistry
- 3d9ac2e - feat: add TaskCompletionNotifier
- 4742a69 - feat: add unique agent_id to KaiAgent
- 4875a3f - feat: register agents with ActiveAgentRegistry
- e335452 - feat: add _add_system_message method to KaiAgent
- e46d003 - feat: register tasks created by execute_async_tool
- c09a1d1 - feat: wire up TaskCompletionNotifier for auto-nudge
- b9053db - test: add integration tests for auto-nudge edge cases

## Future Enhancements

- [ ] Agent preference for notification style (system vs user message)
- [ ] Task priority in notification formatting
- [ ] Batch notifications (multiple tasks in one message)
- [ ] Notification filters (only notify on failure, only on specific task types)
- [ ] Webhook support for external notifications
