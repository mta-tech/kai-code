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
