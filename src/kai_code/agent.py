from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from .backend import KaiLocalBackend
from .checkpointer import KaiFileCheckpointer
from .patching import apply_patch as _apply_patch
from .permissions import PermissionConfig, permission_denied_message
from .skills import discover_skills, format_skills_for_prompt


@dataclass(frozen=True)
class KaiAgentConfig:
    root_dir: Path
    model: str | BaseChatModel | None = None
    yolo: bool = True
    interrupt_on: dict[str, bool] | None = None
    system_prompt: str | None = None
    skills_dir: str = ".skills"
    state_path: Path | None = None
    permissions: PermissionConfig | None = None


@dataclass(frozen=True)
class KaiResult:
    output: str
    messages: list[dict[str, Any]]
    raw: dict[str, Any]


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _message_to_dict(m: Any) -> dict[str, Any]:
    # Best-effort: support both BaseMessage objects and dicts.
    if isinstance(m, dict):
        return {"role": m.get("role"), "content": m.get("content")}
    if isinstance(m, BaseMessage):
        role = getattr(m, "type", None) or getattr(m, "role", None)
        return {"role": role, "content": m.content}
    return {"role": None, "content": str(m)}


class KaiAgent:
    def __init__(
        self,
        root_dir: str | Path,
        *,
        model: str | BaseChatModel | None = None,
        yolo: bool = True,
        interrupt_on: dict[str, bool] | None = None,
        system_prompt: str | None = None,
        skills_dir: str = ".skills",
        state_path: str | Path | None = None,
        permissions: PermissionConfig | None = None,
    ) -> None:
        root = Path(root_dir).resolve()

        resolved_state_path = (
            Path(state_path).resolve()
            if state_path is not None
            else (root / ".kai" / "session.json").resolve()
        )

        # Load persisted config defaults (if present) before finalizing config.
        persisted = self._read_state_file(resolved_state_path)
        persisted_model = persisted.get("model") if isinstance(persisted.get("model"), str) else None
        persisted_system_prompt = (
            persisted.get("system_prompt") if isinstance(persisted.get("system_prompt"), str) else None
        )
        persisted_skills_dir = persisted.get("skills_dir") if isinstance(persisted.get("skills_dir"), str) else None

        final_model = model if model is not None else persisted_model
        final_system_prompt = system_prompt if system_prompt is not None else persisted_system_prompt
        # Heuristic: if caller used the default skills_dir but state file has a custom one, restore it.
        final_skills_dir = skills_dir
        if skills_dir == ".skills" and persisted_skills_dir and persisted_skills_dir != skills_dir:
            final_skills_dir = persisted_skills_dir

        self._config = KaiAgentConfig(
            root_dir=root,
            model=final_model,
            yolo=yolo,
            interrupt_on=interrupt_on,
            system_prompt=final_system_prompt,
            skills_dir=final_skills_dir,
            state_path=resolved_state_path,
            permissions=permissions,
        )
        self._backend = KaiLocalBackend(root, permissions=permissions)
        self._messages: list[dict[str, Any]] = []
        self._thread_id: str = uuid.uuid4().hex
        self._graph = None
        self._load_state()

    @property
    def config(self) -> KaiAgentConfig:
        return self._config

    @property
    def thread_id(self) -> str:
        """LangGraph thread id used for interrupts/checkpointing."""
        return self._thread_id

    def save(self) -> None:
        """Persist current messages/thread_id/config to `state_path`."""
        self._save_state()

    def fork(self, *, state_path: str | Path) -> "KaiAgent":
        other = KaiAgent(
            root_dir=self._config.root_dir,
            model=self._config.model,
            yolo=self._config.yolo,
            system_prompt=self._config.system_prompt,
            skills_dir=self._config.skills_dir,
            state_path=state_path,
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
                self._messages = list(data["messages"])
            if isinstance(data, dict) and isinstance(data.get("thread_id"), str):
                self._thread_id = data["thread_id"]
        except Exception:
            # Best-effort; ignore corrupted state.
            return

    def _save_state(self) -> None:
        path = self._config.state_path
        if path is None:
            return
        _ensure_parent(path)
        payload = {
            "messages": self._messages,
            "thread_id": self._thread_id,
            "model": self._config.model if isinstance(self._config.model, str) else None,
            "system_prompt": self._config.system_prompt,
            "skills_dir": self._config.skills_dir,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _build_graph(self):
        if self._graph is not None:
            return self._graph

        model = self._config.model
        if isinstance(model, str):
            chat_model = init_chat_model(model)
        else:
            chat_model = model

        skills = discover_skills(self._config.root_dir, self._config.skills_dir)
        skills_prompt = format_skills_for_prompt(skills, skills_dir=self._config.skills_dir)

        prompt_parts = [p for p in [self._config.system_prompt, skills_prompt] if p]
        full_system_prompt = "\n\n".join(prompt_parts) if prompt_parts else None

        # YOLO mode means no HITL interrupts.
        interrupt_on = None
        checkpointer = None
        if not self._config.yolo:
            interrupt_on = self._config.interrupt_on or {
                "execute": True,
                "write_file": True,
                "edit_file": True,
                "apply_patch": True,
            }
            # Required for HITL interrupts to work.
            # Use a disk-backed saver so resume survives process restarts.
            if self._config.state_path is not None:
                cp_path = (self._config.state_path.parent / "checkpoints.pkl").resolve()
                checkpointer = KaiFileCheckpointer(cp_path)
            else:
                checkpointer = MemorySaver()

        @tool("apply_patch")
        def apply_patch_tool(patch: str) -> str:
            """Apply a unified diff patch under the project root."""
            if self._config.permissions is not None and not self._config.permissions.tool_allowed("apply_patch"):
                return permission_denied_message("apply_patch")
            res = _apply_patch(self._config.root_dir, patch)
            if res.ok:
                return res.output or "OK"
            return f"Error applying patch:\n{res.output}".strip()

        self._graph = create_deep_agent(
            model=chat_model,
            tools=[apply_patch_tool],
            system_prompt=full_system_prompt,
            backend=self._backend,
            interrupt_on=interrupt_on,
            checkpointer=checkpointer,
        )
        return self._graph

    def _update_from_state(self, state: Any) -> None:
        raw_messages = state.get("messages", []) if isinstance(state, dict) else []
        self._messages = [_message_to_dict(m) for m in raw_messages]
        self._save_state()

    def run(self, prompt: str) -> KaiResult:
        graph = self._build_graph()
        # deepagents uses LangChain message objects internally, but accepts dict-style too.
        messages = list(self._messages) + [{"role": "user", "content": prompt}]
        state = graph.invoke(
            {"messages": messages},
            config={"configurable": {"thread_id": self._thread_id}},
        )

        self._update_from_state(state)

        output = ""
        if self._messages:
            last = self._messages[-1]
            if last.get("role") in ("assistant", "ai"):
                output = last.get("content") or ""
            else:
                output = last.get("content") or ""

        return KaiResult(output=output, messages=list(self._messages), raw=state)

    def resume(self, decisions: list[dict[str, Any]]) -> KaiResult:
        """Resume a human-in-the-loop interrupted run.

        This only applies when `yolo=False` and the underlying agent execution
        interrupted on a tool call.

        Decisions should follow LangGraph HITL conventions, e.g.:
        [{"type": "approve"}] or [{"type": "reject"}] or
        [{"type": "edit", "edited_action": {...}}]
        """
        graph = self._build_graph()
        state = graph.invoke(
            Command(resume={"decisions": decisions}),
            config={"configurable": {"thread_id": self._thread_id}},
        )
        self._update_from_state(state)

        output = ""
        if self._messages:
            output = (self._messages[-1].get("content") or "")
        return KaiResult(output=output, messages=list(self._messages), raw=state)

    def stream(self, prompt: str) -> Iterator[Any]:
        graph = self._build_graph()
        messages = list(self._messages) + [{"role": "user", "content": prompt}]
        last_snapshot: dict[str, Any] | None = None
        try:
            for chunk in graph.stream(
                {"messages": messages},
                config={"configurable": {"thread_id": self._thread_id}},
            ):
                if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
                    last_snapshot = chunk
                yield chunk
        finally:
            # Persist only if we observed a full snapshot with messages.
            if last_snapshot is not None:
                try:
                    self._update_from_state(last_snapshot)
                except Exception:
                    pass

    def persist_state_from_stream_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Persist a full state snapshot obtained from streaming.

        This is used by the CLI's stream-json mode to avoid persisting partial deltas.
        """
        self._update_from_state(snapshot)
