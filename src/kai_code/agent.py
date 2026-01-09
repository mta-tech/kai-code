from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from fnmatch import fnmatch

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
from .stats import RunStats
from .permissions import PermissionConfig, permission_denied_message
from .prompts import load_prompt
from .skills import discover_skills, format_skills_for_prompt, initialize_skills_system
from .memory import MemoryManager
from .tools import load_skill, unload_skill, list_skills, reload_skills
from .tools.web import http_request as _http_request, web_search as _web_search, fetch_url as _fetch_url
from .tasks import BACKGROUND_TASK_TOOLS
from .ralph_loop import RalphLoopManager
from .hooks.ralph_stop_hook import RalphStopHook


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
    enabled_tools: list[str] | None = None
    memory_manager: MemoryManager | None = None


@dataclass(frozen=True)
class KaiResult:
    output: str
    messages: list[dict[str, Any]]
    raw: dict[str, Any]
    stats: RunStats | None = None


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _safe_json(obj: Any) -> Any:
    """Best-effort JSON-serializable conversion.

    We persist messages to a session file; LangChain/DeepAgents messages may contain
    pydantic models or other objects.
    """

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
    if hasattr(obj, "dict"):
        try:
            return _safe_json(obj.dict())
        except Exception:
            pass
    return str(obj)


def _message_to_dict(m: Any) -> dict[str, Any]:
    """Convert message-like objects into a dict without dropping tool metadata.

    IMPORTANT: Tool messages must keep `tool_call_id` (and ideally the tool name),
    otherwise LangChain will raise KeyError('tool_call_id') when reconstructing
    history.
    """

    # Already dict-like
    if isinstance(m, dict):
        return _safe_json(m)

    # LangChain messages
    if isinstance(m, BaseMessage):
        role = getattr(m, "type", None) or getattr(m, "role", None)
        out: dict[str, Any] = {
            "role": role,
            "content": _safe_json(getattr(m, "content", None)),
        }

        # Preserve common optional fields.
        for key in (
            "name",
            "tool_call_id",
            "tool_calls",
            "additional_kwargs",
            "response_metadata",
            "id",
        ):
            if hasattr(m, key):
                out[key] = _safe_json(getattr(m, key))

        return out

    return {"role": None, "content": str(m)}


def _normalize_legacy_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Repair older on-disk sessions that dropped tool_call_id.

    Previously we persisted only {role, content}. If a `tool` message is missing
    `tool_call_id`, LangChain will crash when using it as history. We degrade such
    messages into plain assistant text.
    """

    out: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, dict):
            out.append(_message_to_dict(m))
            continue

        role = m.get("role") or m.get("type")
        if role in ("tool", "tool_result") and not (isinstance(m.get("tool_call_id"), str) and m.get("tool_call_id")):
            content = m.get("content")
            if content is None:
                content = ""
            out.append({"role": "assistant", "content": f"[tool_result]\n{content}".strip()})
            continue

        out.append(_safe_json(m))

    return out


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
        enabled_tools: list[str] | None = None,
        memory_manager = None,
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
        persisted_enabled_tools = (
            list(persisted.get("enabled_tools"))
            if isinstance(persisted.get("enabled_tools"), list)
            and all(isinstance(x, str) for x in persisted.get("enabled_tools"))
            else None
        )

        final_model = model if model is not None else persisted_model
        final_system_prompt = system_prompt if system_prompt is not None else persisted_system_prompt
        # Heuristic: if caller used the default skills_dir but state file has a custom one, restore it.
        final_skills_dir = skills_dir
        if skills_dir == ".skills" and persisted_skills_dir and persisted_skills_dir != skills_dir:
            final_skills_dir = persisted_skills_dir

        # If caller didn't specify an enabled-tools filter, restore from persisted session.
        final_enabled_tools = enabled_tools if enabled_tools is not None else persisted_enabled_tools

        # Initialize memory manager if not provided
        memory_manager = memory_manager or MemoryManager(root_dir=root)
        
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
            memory_manager=memory_manager,
        )
        self._backend = KaiLocalBackend(root, permissions=permissions, enabled_tools=final_enabled_tools)

        # Initialize Ralph loop manager and hook
        self._ralph_manager = RalphLoopManager(root)
        self._ralph_hook = RalphStopHook(self._ralph_manager)

        # Initialize skills system
        if memory_manager:
            initialize_skills_system(root, self._config.skills_dir, memory_manager)
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

    @property
    def backend(self) -> KaiLocalBackend:
        """The backend used for file operations."""
        return self._backend

    @property
    def ralph_manager(self) -> RalphLoopManager:
        """The Ralph loop manager for autonomous operation."""
        return self._ralph_manager

    def _get_base_prompt_name(self) -> str:
        """Get the name of the base prompt to load.

        Override in subclasses to use different prompts.
        Returns:
            Prompt name (e.g., "kai-code", "kai-dbt")
        """
        return "kai-code"

    def save(self) -> None:
        """Persist current messages/thread_id/config to `state_path`."""
        self._save_state()

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
                raw_msgs = [m for m in data["messages"] if isinstance(m, dict)]
                # Normalize legacy tool messages that were persisted without tool_call_id.
                self._messages = _normalize_legacy_messages(raw_msgs)
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
            "enabled_tools": self._config.enabled_tools,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _load_project_context(self) -> str | None:
        """Load project context from CLAUDE.md or AGENTS.md if present.

        Looks for these files in the project root directory and returns
        their contents formatted as project context for the system prompt.

        Returns:
            Formatted project context string, or None if no context file found.
        """
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
                    # If we can't read the file, try the next one
                    continue

        return None

    def _build_graph(self):
        if self._graph is not None:
            return self._graph

        model = self._config.model
        if isinstance(model, str):
            # Handle OpenRouter models with custom base_url
            if model.startswith("openrouter:"):
                from langchain_openai import ChatOpenAI
                openrouter_model_id = model[len("openrouter:"):]
                chat_model = ChatOpenAI(
                    model=openrouter_model_id,
                    base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ.get("OPENROUTER_API_KEY"),
                )
            else:
                chat_model = init_chat_model(model)
        else:
            chat_model = model

        # Get memory blocks for prompt assembly
        memory_manager = getattr(self._config, 'memory_manager', None)
        
        # Discover and format skills if memory manager available
        skills_prompt = None
        if memory_manager:
            skills_block, loaded_block = memory_manager.get_skill_blocks()
            if skills_block:
                # Update skills discovery
                from .skills_parser import discover_skills, format_skills_for_prompt
                skills_result = discover_skills(self._config.root_dir, self._config.skills_dir)
                memory_manager.update_skills_discovery(skills_result.skills, self._config.skills_dir)
                
                # Format skills for prompt
                skills_prompt = format_skills_for_prompt(skills_result.skills, skills_directory=self._config.skills_dir)
        else:
            # Fallback to old method
            from .skills import discover_skills_legacy, format_skills_for_prompt_legacy
            skills = discover_skills_legacy(self._config.root_dir, self._config.skills_dir)
            skills_prompt = format_skills_for_prompt_legacy(skills, skills_dir=self._config.skills_dir)

        # Build prompt parts: base prompt + project context + user custom + skills + memory
        base_prompt = load_prompt(self._get_base_prompt_name())
        prompt_parts = [base_prompt]

        # Load project context from CLAUDE.md or AGENTS.md if present
        project_context = self._load_project_context()
        if project_context:
            prompt_parts.append(project_context)

        # Add user's custom system_prompt if provided
        if self._config.system_prompt:
            prompt_parts.append(self._config.system_prompt)

        # Add skills prompt
        if skills_prompt:
            prompt_parts.append(skills_prompt)

        # Add memory blocks to prompt if available
        if memory_manager:
            memory_content = memory_manager.format_for_prompt()
            if memory_content.strip():
                prompt_parts.append(memory_content)

        full_system_prompt = "\n\n".join(prompt_parts)

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
            enabled = self._config.enabled_tools
            if enabled is not None and not any(fnmatch("apply_patch", p) for p in enabled):
                return permission_denied_message("apply_patch")
            if self._config.permissions is not None and not self._config.permissions.tool_allowed("apply_patch"):
                return permission_denied_message("apply_patch")
            res = _apply_patch(self._config.root_dir, patch)
            if res.ok:
                return res.output or "OK"
            return f"Error applying patch:\n{res.output}".strip()

        @tool("web_search")
        def web_search_tool(
            query: str,
            max_results: int = 5,
            topic: str = "general",
            include_raw_content: bool = False,
        ) -> str:
            """Search the web using Tavily for current information and documentation.

            Args:
                query: The search query (be specific and detailed)
                max_results: Number of results to return (default: 5)
                topic: Search topic type - "general" for most queries, "news" for current events
                include_raw_content: Include full page content (warning: uses more tokens)

            Returns:
                JSON string with search results
            """
            import json
            result = _web_search(query, max_results=max_results, topic=topic, include_raw_content=include_raw_content)
            return json.dumps(result, indent=2)

        @tool("fetch_url")
        def fetch_url_tool(url: str, timeout: int = 30) -> str:
            """Fetch content from a URL and convert HTML to markdown format.

            Args:
                url: The URL to fetch (must be a valid HTTP/HTTPS URL)
                timeout: Request timeout in seconds (default: 30)

            Returns:
                JSON string with markdown content and metadata
            """
            import json
            result = _fetch_url(url, timeout=timeout)
            return json.dumps(result, indent=2)

        @tool("http_request")
        def http_request_tool(
            url: str,
            method: str = "GET",
            headers: str | None = None,
            data: str | None = None,
            params: str | None = None,
            timeout: int = 30,
        ) -> str:
            """Make HTTP requests to APIs and web services.

            Args:
                url: Target URL
                method: HTTP method (GET, POST, PUT, DELETE, etc.)
                headers: JSON string of HTTP headers to include
                data: Request body data (JSON string)
                params: JSON string of URL query parameters
                timeout: Request timeout in seconds

            Returns:
                JSON string with response data including status, headers, and content
            """
            import json
            # Parse JSON strings to dicts if provided
            headers_dict = json.loads(headers) if headers else None
            data_dict = json.loads(data) if data else None
            params_dict = json.loads(params) if params else None
            result = _http_request(url, method=method, headers=headers_dict, data=data_dict, params=params_dict, timeout=timeout)
            return json.dumps(result, indent=2)

        @tool("execute_async")
        def execute_async_tool(command: str, timeout: int) -> str:
            """Execute shell command with auto-background on timeout.

            Use this for commands that may take a while. If the command exceeds
            the specified timeout, it automatically moves to a background task
            so you can continue working.

            Args:
                command: Shell command to execute
                timeout: Seconds to wait before moving to background (required)

            Returns:
                JSON with either:
                - {exit_code, output} if completed within timeout
                - {moved_to_background, task_id, message} if promoted to background

            After promotion, use get_task_output(task_id) to check results.
            """
            import subprocess as sp
            from kai_code.tasks import get_task_manager

            root_dir = self._config.root_dir

            try:
                result = sp.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(root_dir),
                    env={**os.environ},
                )
                output = (result.stdout or "") + (result.stderr or "")
                # Truncate if too long
                if len(output) > 80000:
                    output = output[:80000] + "\n... (truncated)"
                return json.dumps({
                    "exit_code": result.returncode,
                    "output": output,
                })
            except sp.TimeoutExpired as e:
                # Capture any partial output before promoting to background
                partial_stdout = e.stdout or ""
                partial_stderr = e.stderr or ""
                if isinstance(partial_stdout, bytes):
                    partial_stdout = partial_stdout.decode("utf-8", errors="replace")
                if isinstance(partial_stderr, bytes):
                    partial_stderr = partial_stderr.decode("utf-8", errors="replace")
                partial_output = partial_stdout + partial_stderr

                # Auto-promote to background
                task_manager = get_task_manager()
                task_id = task_manager.run_shell(command, working_dir=root_dir)
                return json.dumps({
                    "moved_to_background": True,
                    "task_id": task_id,
                    "partial_output": partial_output[:5000] if partial_output else None,
                    "message": f"Command exceeded {timeout}s timeout, moved to background. Use get_task_output('{task_id}') to check results.",
                })

        # Collect all tools including skill tools, web tools, and background task tools
        tools = [
            apply_patch_tool,
            load_skill, unload_skill, list_skills, reload_skills,
            web_search_tool, fetch_url_tool, http_request_tool,
            execute_async_tool,
            *BACKGROUND_TASK_TOOLS,
        ]

        self._graph = create_deep_agent(
            model=chat_model,
            tools=tools,
            system_prompt=full_system_prompt,
            backend=self._backend,
            interrupt_on=interrupt_on,
            checkpointer=checkpointer,
        )
        return self._graph

    def _update_from_state(self, state: Any) -> None:
        raw_messages = state.get("messages", []) if isinstance(state, dict) else []
        converted = [_message_to_dict(m) for m in raw_messages]
        self._messages = _normalize_legacy_messages([m for m in converted if isinstance(m, dict)])
        self._save_state()

    def run(self, prompt: str) -> KaiResult:
        """Run the agent with the given prompt.

        If a Ralph loop is active, this method will re-feed the prompt
        recursively until the loop completes or safety limits are reached.

        Args:
            prompt: User prompt to execute.

        Returns:
            KaiResult with output, messages, and raw state.
        """
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

        result = KaiResult(output=output, messages=list(self._messages), raw=state)

        # Check Ralph stop hook - enables autonomous loops
        should_continue, next_prompt = self._ralph_hook.on_agent_complete(self, result)

        if should_continue and next_prompt:
            # Ralph loop continues - recursively re-feed the prompt
            return self.run(next_prompt)

        return result

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
            # Use stream_mode="values" to get full state with messages after each node
            for chunk in graph.stream(
                {"messages": messages},
                config={"configurable": {"thread_id": self._thread_id}},
                stream_mode="values",
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
