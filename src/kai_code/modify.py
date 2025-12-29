from __future__ import annotations

from dataclasses import dataclass

from .agent import KaiAgent


def update_agent_llm_config(
    agent: KaiAgent,
    model_handle: str,
    update_args: dict | None = None,
) -> KaiAgent:
    """Return a new KaiAgent instance using the same persisted session, but a new model.

    In `letta-code`, this mutates a server-backed agent's model settings.
    Locally, we simply create a new wrapper pointing at the same `state_path`.

    `update_args` is accepted for parity but currently unused.
    """
    _ = update_args
    new_agent = KaiAgent(
        root_dir=agent.config.root_dir,
        state_path=agent.config.state_path,
        model=model_handle,
        yolo=agent.config.yolo,
        system_prompt=agent.config.system_prompt,
        skills_dir=agent.config.skills_dir,
        permissions=agent.config.permissions,
        enabled_tools=agent.config.enabled_tools,
    )
    new_agent.save()
    return new_agent


@dataclass(frozen=True)
class SystemPromptUpdateResult:
    success: bool
    message: str


def update_agent_system_prompt(agent: KaiAgent, system_prompt: str) -> SystemPromptUpdateResult:
    """Update the additional system prompt used by the wrapper.

    Returns a new wrapper instance implicitly by writing nothing; callers should
    create a new agent wrapper with the desired prompt if they want to keep a handle.
    This mirrors `letta-code`'s function name but differs in semantics (local sessions).
    """
    updated = KaiAgent(
        root_dir=agent.config.root_dir,
        state_path=agent.config.state_path,
        model=agent.config.model if isinstance(agent.config.model, str) else None,
        yolo=agent.config.yolo,
        system_prompt=system_prompt,
        skills_dir=agent.config.skills_dir,
        permissions=agent.config.permissions,
        enabled_tools=agent.config.enabled_tools,
    )
    updated.save()
    return SystemPromptUpdateResult(success=True, message="Updated system_prompt for future agent wrappers")


@dataclass(frozen=True)
class LinkResult:
    success: bool
    message: str
    added_count: int | None = None


@dataclass(frozen=True)
class UnlinkResult:
    success: bool
    message: str
    removed_count: int | None = None


def link_tools_to_agent(agent: KaiAgent) -> LinkResult:
    """Compatibility no-op.

    In `letta-code`, this attaches tools to a server-backed agent.
    In this local deepagents-based port, tools are available at runtime.
    """
    _ = agent
    return LinkResult(success=True, message="No-op: tools are local and always available", added_count=0)


def unlink_tools_from_agent(agent: KaiAgent) -> UnlinkResult:
    _ = agent
    return UnlinkResult(success=True, message="No-op: tools are local and always available", removed_count=0)


# TypeScript-compat aliases
updateAgentLLMConfig = update_agent_llm_config
linkToolsToAgent = link_tools_to_agent
unlinkToolsFromAgent = unlink_tools_from_agent
updateAgentSystemPrompt = update_agent_system_prompt
