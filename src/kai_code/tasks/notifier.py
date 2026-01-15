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
