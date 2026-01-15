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
