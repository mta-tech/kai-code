from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .permissions import PermissionConfig, permission_denied_message

from .letta_client import LettaClientConfig, get_letta_client
from .letta_settings import (
    load_letta_project_settings,
    load_letta_settings,
    update_letta_project_settings,
    update_letta_settings,
)


@dataclass(frozen=True)
class LettaRunResult:
    output: str
    agent_id: str
    raw: Any


class LettaRunner:
    """Minimal Letta server-mode runner.

    This intentionally starts small (headless parity first), then we will layer:
    - tool upsert + approval execution
    - interactive TUI flow
    """

    def __init__(
        self,
        *,
        root_dir: Path,
        api_key: str | None = None,
        base_url: str | None = None,
        project: str | None = None,
        model: str | None = None,
        system: str | None = None,
    ) -> None:
        self._root_dir = root_dir

        settings = load_letta_settings()
        env_settings = settings.env or {}

        resolved_api_key = api_key or os.environ.get("LETTA_API_KEY") or env_settings.get("LETTA_API_KEY")
        resolved_base_url = base_url or os.environ.get("LETTA_BASE_URL") or env_settings.get("LETTA_BASE_URL")

        self._client = get_letta_client(
            LettaClientConfig(api_key=resolved_api_key, base_url=resolved_base_url, project=project)
        )
        self._project = project
        self._model = model
        self._system = system

    def resolve_agent_id(self, *, agent_id: str | None, force_new: bool, should_continue: bool) -> str:
        if agent_id and not force_new:
            return agent_id

        project_settings = load_letta_project_settings(self._root_dir)
        global_settings = load_letta_settings()

        if not force_new and project_settings.last_agent:
            return project_settings.last_agent

        if should_continue and global_settings.last_agent:
            return global_settings.last_agent

        raise RuntimeError(
            "No Letta agent selected. Provide --agent, or run with --new to create an agent."
        )

    def create_agent(
        self,
        *,
        name: str | None = None,
        include_base_tools: bool = False,
        enable_sleeptime: bool = False,
        init_blocks: list[str] | None = None,
    ) -> str:
        memory_blocks = None
        if init_blocks:
            memory_blocks = []
            for item in init_blocks:
                if not isinstance(item, str) or "=" not in item:
                    continue
                label, text = item.split("=", 1)
                label = label.strip()
                text = text.strip()
                if not label:
                    continue
                memory_blocks.append({"label": label, "value": text, "limit": 2000})

        agent = self._client.agents.create(
            name=name or "kai-code",
            model=self._model or None,
            system=self._system or None,
            project=self._project or None,
            include_base_tools=include_base_tools,
            enable_sleeptime=enable_sleeptime,
            memory_blocks=memory_blocks,
        )
        agent_id = getattr(agent, "id", None) or getattr(agent, "agent_id", None)
        if not isinstance(agent_id, str) or not agent_id:
            raise RuntimeError(f"Unexpected Letta agent create response: {agent!r}")
        self.persist_last_agent(agent_id)
        return agent_id

    @staticmethod
    def _assistant_content_to_text(content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif hasattr(item, "text") and isinstance(getattr(item, "text"), str):
                    parts.append(getattr(item, "text"))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)

    def _ensure_tools_attached(self, *, agent_id: str) -> None:
        # Register a minimal set of client-executed tools, and mark them as approval-required.
        from .letta_tools import build_default_tools

        tools = build_default_tools(root_dir=self._root_dir)
        for t in tools:
            src = (
                f"def {t.name}(*args, **kwargs):\n"
                f"    raise RuntimeError('Tool {t.name} is executed client-side via approvals')\n"
            )
            tool_obj = self._client.tools.upsert(
                source_code=src,
                description=t.description,
                args_json_schema=t.args_json_schema,
                default_requires_approval=True,
                tags=["kai"],
            )
            tool_id = getattr(tool_obj, "id", None)
            if isinstance(tool_id, str) and tool_id:
                try:
                    self._client.agents.tools.attach(agent_id, tool_id=tool_id)
                except Exception:
                    # Best-effort: tool might already be attached.
                    pass
                try:
                    self._client.agents.tools.update_approval(agent_id, tool_id=tool_id, requires_approval=True)
                except Exception:
                    pass

    def persist_last_agent(self, agent_id: str) -> None:
        update_letta_project_settings(self._root_dir, last_agent=agent_id)
        update_letta_settings(last_agent=agent_id)

    def run_headless(self, *, agent_id: str, prompt: str) -> LettaRunResult:
        from letta_client.types.agents.approval_request_message import ApprovalRequestMessage
        from letta_client.types.agents.assistant_message import AssistantMessage
        from letta_client.types.agents.tool_call import ToolCall
        from letta_client.types.agents.tool_call_delta import ToolCallDelta

        from .letta_tools import build_default_tools

        self._ensure_tools_attached(agent_id=agent_id)
        tool_map = {t.name: t for t in build_default_tools(root_dir=self._root_dir)}

        output_parts: list[str] = []
        raw: list[object] = []
        pending_tool_calls: dict[str, dict[str, object]] = {}
        approval_request_id_for_tool_call: dict[str, str] = {}

        stream = self._client.agents.messages.stream(agent_id, input=prompt, stream_tokens=True)
        for evt in stream:
            raw.append(evt)

            if isinstance(evt, AssistantMessage):
                text = self._assistant_content_to_text(evt.content)
                if text:
                    output_parts.append(text)
                continue

            if isinstance(evt, ApprovalRequestMessage):
                tc = evt.tool_call
                tool_call_id = getattr(tc, "tool_call_id", None)
                if isinstance(tool_call_id, str) and tool_call_id:
                    approval_request_id_for_tool_call[tool_call_id] = evt.id
                    pending_tool_calls[tool_call_id] = {
                        "name": getattr(tc, "name", None),
                        "arguments": getattr(tc, "arguments", None),
                    }
                # Attempt to execute immediately if we have enough info.
                self._maybe_execute_and_respond(
                    agent_id=agent_id,
                    pending_tool_calls=pending_tool_calls,
                    approval_request_id_for_tool_call=approval_request_id_for_tool_call,
                    tool_map=tool_map,
                )
                continue

            # Some streams may send partial tool call deltas.
            if isinstance(evt, (ToolCall, ToolCallDelta)):
                tool_call_id = getattr(evt, "tool_call_id", None)
                if isinstance(tool_call_id, str) and tool_call_id:
                    cur = pending_tool_calls.get(tool_call_id, {})
                    name = getattr(evt, "name", None)
                    args = getattr(evt, "arguments", None)
                    if name is not None:
                        cur["name"] = name
                    if args is not None:
                        cur["arguments"] = args
                    pending_tool_calls[tool_call_id] = cur
                    self._maybe_execute_and_respond(
                        agent_id=agent_id,
                        pending_tool_calls=pending_tool_calls,
                        approval_request_id_for_tool_call=approval_request_id_for_tool_call,
                        tool_map=tool_map,
                    )

        output = "".join(output_parts).strip()
        self.persist_last_agent(agent_id)
        return LettaRunResult(output=output, agent_id=agent_id, raw=raw)

    def stream_json(
        self,
        *,
        agent_id: str,
        prompt: str,
        run_id: str,
        permission_mode: str,
        permissions: PermissionConfig | None,
        enabled_tools: list[str] | None,
        include_traceback: bool,
        emit: Any,
    ) -> int:
        """Emit kai stream-json events for a Letta run.

        `emit` is a callable that accepts a dict payload.
        """

        from letta_client.types.agents.approval_request_message import ApprovalRequestMessage
        from letta_client.types.agents.assistant_message import AssistantMessage

        from .letta_tools import build_default_tools
        from .stats import now_ms

        schema_version = 1
        started_ms = now_ms()
        tools_meta = enabled_tools

        def _emit(payload: dict[str, Any]) -> None:
            payload.setdefault("schema_version", schema_version)
            payload.setdefault("run_id", run_id)
            payload.setdefault("thread_id", agent_id)
            payload.setdefault("state_path", None)
            payload.setdefault("model", self._model)
            payload.setdefault("provider", (self._model.split(":", 1)[0] if self._model and ":" in self._model else None))
            payload.setdefault("permission_mode", permission_mode)
            payload.setdefault("tools", tools_meta)
            emit(payload)

        next_event_id = 0

        def _emit_with_id(payload: dict[str, Any]) -> None:
            nonlocal next_event_id
            payload["event_id"] = next_event_id
            next_event_id += 1
            _emit(payload)

        _emit_with_id({"type": "init", "ts_ms": started_ms})

        yolo = permission_mode == "bypassPermissions"

        self._ensure_tools_attached(agent_id=agent_id)
        tool_list = build_default_tools(root_dir=self._root_dir)
        tool_map = {t.name: t for t in tool_list}

        def _tool_enabled(name: str) -> bool:
            if enabled_tools is None:
                return True
            from fnmatch import fnmatch

            return any(fnmatch(name, p) for p in enabled_tools)

        output_parts: list[str] = []
        tool_call_count = 0
        tool_result_count = 0
        tool_call_started_ms: dict[str, int] = {}
        tool_latencies: list[int] = []
        ttft_ms: int | None = None
        stop_reason = "end_turn"

        try:
            stream = self._client.agents.messages.stream(agent_id, input=prompt, stream_tokens=True)
            for evt in stream:
                ts_ms = now_ms()
                if ttft_ms is None:
                    ttft_ms = max(0, ts_ms - started_ms)

                if isinstance(evt, AssistantMessage):
                    text = self._assistant_content_to_text(evt.content)
                    if text:
                        output_parts.append(text)
                        _emit_with_id({"type": "message", "ts_ms": ts_ms, "delta": text, "raw": _safe(evt)})
                    continue

                if isinstance(evt, ApprovalRequestMessage):
                    tc = evt.tool_call
                    tool_name = getattr(tc, "name", None)
                    tool_args = getattr(tc, "arguments", None)
                    tool_call_id = getattr(tc, "tool_call_id", None)

                    # If not YOLO, emit interrupt and stop.
                    if not yolo:
                        stop_reason = "interrupt"
                        _emit_with_id(
                            {
                                "type": "interrupt",
                                "ts_ms": ts_ms,
                                "tool_call_id": tool_call_id,
                                "tool_name": tool_name,
                                "args": tool_args,
                                "approval_request_id": evt.id,
                            }
                        )
                        _emit_with_id(
                            {
                                "type": "result",
                                "ts_ms": ts_ms,
                                "stop_reason": stop_reason,
                                "output": "".join(output_parts).strip(),
                                "stats": {
                                    "duration_ms": max(0, ts_ms - started_ms),
                                    "ttft_ms": ttft_ms,
                                    "chunk_count": None,
                                    "tool_call_count": tool_call_count,
                                    "tool_result_count": tool_result_count,
                                },
                            }
                        )
                        return 2

                    # YOLO: execute + respond.
                    if isinstance(tool_call_id, str) and tool_call_id:
                        tool_call_started_ms[tool_call_id] = ts_ms

                    tool_call_count += 1
                    _emit_with_id(
                        {
                            "type": "tool_call",
                            "ts_ms": ts_ms,
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "args": tool_args,
                        }
                    )

                    if not isinstance(tool_name, str) or not _tool_enabled(tool_name):
                        tool_return = {
                            "type": "tool",
                            "tool_call_id": tool_call_id or "unknown",
                            "status": "error",
                            "tool_return": permission_denied_message(tool_name or "unknown", {"reason": "disabled"}),
                        }
                    elif permissions is not None and not permissions.tool_allowed(tool_name):
                        tool_return = {
                            "type": "tool",
                            "tool_call_id": tool_call_id or "unknown",
                            "status": "error",
                            "tool_return": permission_denied_message(tool_name, {"reason": "disallowed"}),
                        }
                    else:
                        tool = tool_map.get(tool_name)
                        if tool is None:
                            tool_return = {
                                "type": "tool",
                                "tool_call_id": tool_call_id or "unknown",
                                "status": "error",
                                "tool_return": f"Unknown tool: {tool_name}",
                            }
                        else:
                            try:
                                args_obj = json.loads(tool_args) if isinstance(tool_args, str) else {}
                            except Exception:
                                args_obj = {"_raw": tool_args}
                            try:
                                out = tool.handler(args_obj if isinstance(args_obj, dict) else {"value": args_obj})
                                tool_return = {
                                    "type": "tool",
                                    "tool_call_id": tool_call_id or "unknown",
                                    "status": "success",
                                    "tool_return": out,
                                }
                            except Exception as e:
                                tool_return = {
                                    "type": "tool",
                                    "tool_call_id": tool_call_id or "unknown",
                                    "status": "error",
                                    "tool_return": f"Tool error: {e}",
                                }

                    tool_result_count += 1
                    ended_ms = now_ms()
                    latency = None
                    if isinstance(tool_call_id, str) and tool_call_id in tool_call_started_ms:
                        latency = max(0, ended_ms - tool_call_started_ms[tool_call_id])
                        tool_latencies.append(latency)
                    _emit_with_id(
                        {
                            "type": "tool_result",
                            "ts_ms": ended_ms,
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "status": tool_return.get("status"),
                            "output": tool_return.get("tool_return"),
                            "tool_latency_ms": latency,
                        }
                    )

                    approval = {
                        "type": "approval",
                        "tool_call_id": tool_call_id,
                        "approve": True,
                        "reason": None,
                    }
                    self._client.agents.messages.create(
                        agent_id,
                        messages=[
                            {
                                "type": "approval",
                                "approval_request_id": evt.id,
                                "approvals": [approval, tool_return],
                            }
                        ],
                    )
                    continue

            ended_ms = now_ms()
            _emit_with_id(
                {
                    "type": "result",
                    "ts_ms": ended_ms,
                    "stop_reason": stop_reason,
                    "output": "".join(output_parts).strip(),
                    "stats": {
                        "duration_ms": max(0, ended_ms - started_ms),
                        "ttft_ms": ttft_ms,
                        "chunk_count": None,
                        "tool_call_count": tool_call_count,
                        "tool_result_count": tool_result_count,
                        "tool_latency_ms_total": sum(tool_latencies) if tool_latencies else 0,
                        "tool_latency_ms_avg": (sum(tool_latencies) / len(tool_latencies) if tool_latencies else 0),
                        "tool_latency_ms_max": (max(tool_latencies) if tool_latencies else 0),
                    },
                }
            )
            return 0
        except Exception as e:
            ended_ms = now_ms()
            payload: dict[str, Any] = {
                "type": "error",
                "ts_ms": ended_ms,
                "stop_reason": "error",
                "error_type": e.__class__.__name__,
                "message": str(e),
            }
            if include_traceback:
                import traceback as _tb

                payload["traceback"] = _tb.format_exc()
            _emit_with_id(payload)
            _emit_with_id(
                {
                    "type": "result",
                    "ts_ms": ended_ms,
                    "stop_reason": "error",
                    "output": "".join(output_parts).strip(),
                    "stats": {
                        "duration_ms": max(0, ended_ms - started_ms),
                        "ttft_ms": ttft_ms,
                        "tool_call_count": tool_call_count,
                        "tool_result_count": tool_result_count,
                    },
                }
            )
            return 1


def _safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe(v) for v in obj]
    if hasattr(obj, "model_dump"):
        try:
            return _safe(obj.model_dump())
        except Exception:
            pass
    return str(obj)

    def _maybe_execute_and_respond(
        self,
        *,
        agent_id: str,
        pending_tool_calls: dict[str, dict[str, object]],
        approval_request_id_for_tool_call: dict[str, str],
        tool_map: dict[str, object],
    ) -> None:
        """If we have tool name+args + approval_request_id, execute and respond."""

        to_delete: list[str] = []
        for tool_call_id, info in pending_tool_calls.items():
            if tool_call_id not in approval_request_id_for_tool_call:
                continue
            name = info.get("name")
            arguments = info.get("arguments")
            if not isinstance(name, str) or not name:
                continue
            if not isinstance(arguments, str) or not arguments:
                continue
            tool = tool_map.get(name)
            if tool is None:
                tool_return = {
                    "type": "tool",
                    "tool_call_id": tool_call_id,
                    "status": "error",
                    "tool_return": f"Unknown tool: {name}",
                }
            else:
                try:
                    args_obj = json.loads(arguments)
                except Exception:
                    args_obj = {"_raw": arguments}

                try:
                    tool_return_str = tool.handler(args_obj if isinstance(args_obj, dict) else {"value": args_obj})
                    tool_return = {
                        "type": "tool",
                        "tool_call_id": tool_call_id,
                        "status": "success",
                        "tool_return": tool_return_str,
                    }
                except Exception as e:
                    tool_return = {
                        "type": "tool",
                        "tool_call_id": tool_call_id,
                        "status": "error",
                        "tool_return": f"Tool error: {e}",
                    }

            approval = {
                "type": "approval",
                "tool_call_id": tool_call_id,
                "approve": True,
                "reason": None,
            }
            approval_request_id = approval_request_id_for_tool_call[tool_call_id]
            self._client.agents.messages.create(
                agent_id,
                messages=[
                    {
                        "type": "approval",
                        "approval_request_id": approval_request_id,
                        "approvals": [approval, tool_return],
                    }
                ],
            )
            to_delete.append(tool_call_id)

        for tcid in to_delete:
            pending_tool_calls.pop(tcid, None)
            approval_request_id_for_tool_call.pop(tcid, None)
