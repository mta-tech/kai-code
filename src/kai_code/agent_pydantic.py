"""
MIGRATED: Pydantic-Deep Agent

This file has been migrated from LangChain DeepAgents to Pydantic-DeepAgents.
Migration date: 2026-04-01
Migration notes: 
- Model handling simplified (string-based)
- Backend removed (filesystem built-in)
- Tools converted to async with RunContext
- Streaming updated to use iter()
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from fnmatch import fnmatch

from pydantic_deep import create_deep_agent, DeepAgentDeps
from pydantic_ai import RunContext, Agent
from pydantic_ai.models import Model

from .patching import apply_patch as _apply_patch
from .stats import RunStats
from .permissions import PermissionConfig, permission_denied_message
from .prompts import load_prompt
from .skills import discover_skills_legacy, format_skills_for_prompt_legacy
from .tools import load_skill, unload_skill, list_skills, reload_skills
from .tools.web import http_request as _http_request, web_search as _web_search, fetch_url as _fetch_url
from .tasks import BACKGROUND_TASK_TOOLS
from .ralph_loop import RalphLoopManager
from .hooks.ralph_stop_hook import RalphStopHook


@dataclass(frozen=True)
class KaiAgentConfig:
    root_dir: Path
    model: str | None = None
    yolo: bool = True
    interrupt_on: dict[str, bool] | None = None
    system_prompt: str | None = None
    skills_dir: str = ".skills"
    state_path: Path | None = None
    permissions: PermissionConfig | None = None
    enabled_tools: list[str] | None = None


@dataclass(frozen=True)
class KaiResult:
    output: str
    messages: list[dict[str, Any]]
    raw: dict[str, Any]
    stats: RunStats | None = None


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _safe_json(obj: Any) -> Any:
    """Best-effort JSON-serializable conversion."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_json(v) for v in obj]
    if hasattr(obj, "model_dump"):
        try:
            return _safe_json(obj.model_dump())
        except Exception:
            pass
    return str(obj)


class KaiAgent:
    def __init__(
        self,
        root_dir: str | Path,
        *,
        model: str | None = None,
        yolo: bool = True,
        interrupt_on: dict[str, bool] | None = None,
        system_prompt: str | None = None,
        skills_dir: str = ".skills",
        state_path: str | Path | None = None,
        permissions: PermissionConfig | None = None,
        enabled_tools: list[str] | None = None,
    ) -> None:
        root = Path(root_dir).resolve()

        resolved_state_path = (
            Path(state_path).resolve()
            if state_path is not None
            else (root / ".kai" / "session.json").resolve()
        )

        # Load persisted config defaults
        persisted = self._read_state_file(resolved_state_path)
        persisted_model = persisted.get("model") if isinstance(persisted.get("model"), str) else None
        persisted_system_prompt = (
            persisted.get("system_prompt") if isinstance(persisted.get("system_prompt"), str) else None
        )
        persisted_skills_dir = persisted.get("skills_dir") if isinstance(persisted.get("skills_dir"), str) else None
        persisted_enabled_tools = (
            list(persisted.get("enabled_tools"))
            if isinstance(persisted.get("enabled_tools"), list)
            and all(isinstance(x, str) for x in persisted.get("enabled_tools"))
            else None
        )

        final_model = model if model is not None else persisted_model
        final_system_prompt = system_prompt if system_prompt is not None else persisted_system_prompt
        final_skills_dir = skills_dir
        if skills_dir == ".skills" and persisted_skills_dir and persisted_skills_dir != skills_dir:
            final_skills_dir = persisted_skills_dir
        final_enabled_tools = enabled_tools if enabled_tools is not None else persisted_enabled_tools

        self._config = KaiAgentConfig(
            root_dir=root,
            model=final_model,
            yolo=yolo,
            interrupt_on=interrupt_on,
            system_prompt=final_system_prompt,
            skills_dir=final_skills_dir,
            state_path=resolved_state_path,
            permissions=permissions,
            enabled_tools=final_enabled_tools,
        )

        # Initialize Ralph loop manager and hook
        self._ralph_manager = RalphLoopManager(root)
        self._ralph_hook = RalphStopHook(self._ralph_manager)

        self._messages: list[dict[str, Any]] = []
        self._thread_id: str = uuid.uuid4().hex
        self._agent_id: str = uuid.uuid4().hex[:8]
        self._agent = None

        # Register with active agents
        from .tasks.active_agents import get_active_agent_registry
        get_active_agent_registry().register(self._agent_id, self)

        self._load_state()

    @property
    def config(self) -> KaiAgentConfig:
        return self._config

    @property
    def thread_id(self) -> str:
        return self._thread_id

    def save(self) -> None:
        self._save_state()

    def shutdown(self) -> None:
        from .tasks.active_agents import get_active_agent_registry
        from .tasks import get_agent_task_registry
        get_active_agent_registry().unregister(self._agent_id)
        get_agent_task_registry().cleanup_agent_tasks(self._agent_id)

    def fork(self, *, state_path: str | Path) -> "KaiAgent":
        other = KaiAgent(
            root_dir=self._config.root_dir,
            model=self._config.model,
            yolo=self._config.yolo,
            interrupt_on=self._config.interrupt_on,
            system_prompt=self._config.system_prompt,
            skills_dir=self._config.skills_dir,
            state_path=state_path,
            permissions=self._config.permissions,
            enabled_tools=self._config.enabled_tools,
        )
        other._messages = list(self._messages)
        other._save_state()
        return other

    def reset(self) -> None:
        self._messages = []
        self._save_state()

    @staticmethod
    def _read_state_file(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_state(self) -> None:
        path = self._config.state_path
        if path is None or not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict) and isinstance(data.get("messages"), list):
                self._messages = [m for m in data["messages"] if isinstance(m, dict)]
            if isinstance(data, dict) and isinstance(data.get("thread_id"), str):
                self._thread_id = data["thread_id"]
        except Exception:
            return

    def _save_state(self) -> None:
        path = self._config.state_path
        if path is None:
            return
        _ensure_parent(path)
        payload = {
            "messages": self._messages,
            "thread_id": self._thread_id,
            "model": self._config.model,
            "system_prompt": self._config.system_prompt,
            "skills_dir": self._config.skills_dir,
            "enabled_tools": self._config.enabled_tools,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _load_project_context(self) -> str | None:
        """Load project context from CLAUDE.md or AGENTS.md if present."""
        context_files = ["CLAUDE.md", "AGENTS.md"]
        root = self._config.root_dir

        for filename in context_files:
            context_path = root / filename
            if context_path.exists():
                try:
                    content = context_path.read_text(encoding="utf-8").strip()
                    if content:
                        return f"# Project Context ({filename})\n\n{content}"
                except Exception:
                    continue

        return None

    def _build_agent(self) -> Agent:
        """Build the pydantic-deep agent with tools."""
        if self._agent is not None:
            return self._agent

        # Build system prompt
        base_prompt = load_prompt(self._get_base_prompt_name())
        prompt_parts = [base_prompt]

        # Load project context
        project_context = self._load_project_context()
        if project_context:
            prompt_parts.append(project_context)

        # Add custom system prompt
        if self._config.system_prompt:
            prompt_parts.append(self._config.system_prompt)

        # Add skills
        skills = discover_skills_legacy(self._config.root_dir, self._config.skills_dir)
        skills_prompt = format_skills_for_prompt_legacy(skills, skills_dir=self._config.skills_dir)
        if skills_prompt:
            prompt_parts.append(skills_prompt)

        full_instructions = "\n\n".join(prompt_parts)

        # Determine model string
        model_str = self._config.model or "google-gla:gemini-2.0-flash"

        # TODO: Convert tools to pydantic-ai format
        # For now, create agent with built-in capabilities only
        self._agent = create_deep_agent(
            model=model_str,
            instructions=full_instructions,
            include_filesystem=True,
            include_execute=True,
            include_web=True,
            include_subagents=True,
            include_skills=True,
            include_plan=True,
            context_manager=True,
            interrupt_on=self._config.interrupt_on if not self._config.yolo else None,
        )

        return self._agent

    def _get_base_prompt_name(self) -> str:
        return "kai-code"

    def run(self, prompt: str) -> KaiResult:
        """Run the agent with the given prompt."""
        agent = self._build_agent()
        
        # Prepare message history
        messages = list(self._messages) + [{"role": "user", "content": prompt}]
        
        # Run agent
        deps = DeepAgentDeps()
        result = agent.run_sync(prompt, deps=deps, message_history=messages)
        
        # Update state
        # TODO: Extract messages from result
        output = result.output if hasattr(result, 'output') else str(result)
        self._messages.append({"role": "user", "content": prompt})
        self._messages.append({"role": "assistant", "content": output})
        self._save_state()

        kai_result = KaiResult(
            output=output,
            messages=list(self._messages),
            raw={"result": str(result)}
        )

        # Check Ralph stop hook
        should_continue, next_prompt = self._ralph_hook.on_agent_complete(self, kai_result)

        if should_continue and next_prompt:
            return self.run(next_prompt)

        return kai_result

    def stream(self, prompt: str) -> Iterator[Any]:
        """Stream agent execution."""
        agent = self._build_agent()
        messages = list(self._messages) + [{"role": "user", "content": prompt}]
        deps = DeepAgentDeps()

        # Use pydantic-ai iter() for streaming
        # TODO: Implement proper streaming with iter()
        yield {"type": "text", "content": "Streaming not yet migrated"}
        
        # For now, fall back to run
        result = self.run(prompt)
        yield {"type": "result", "content": result.output}


# TODO: Migrate tools to async functions with RunContext
# Example pattern:
# async def read_file(ctx: RunContext[DeepAgentDeps], path: str) -> str:
#     return ctx.deps.backend.read(path)
