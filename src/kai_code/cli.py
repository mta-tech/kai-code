from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
import uuid
from dataclasses import asdict, is_dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable

from .agent import KaiAgent
from .permission_mode import VALID_PERMISSION_MODES, resolve_permission_mode
from .permissions import PermissionConfig
from .settings import (
    load_global_last_session,
    load_settings,
    migrate_global_settings,
    migrate_project_settings,
    update_global_last_session,
    update_local_resume,
)
from .stats import RunStats, now_ms
from .envfile import load_dotenv
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INTERRUPT = 2


from .stream_events import (
    aggregate_usage,
    count_turns_steps,
    detect_tool_events_from_messages,
    last_stop_reason,
    correlate_tool_events,
    synthesize_tool_call_id,
    extract_tool_result_fields,
)


def _parse_csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    parts = [p.strip() for p in value.split(",")]
    parts = [p for p in parts if p]
    return parts


def _safe_json(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_json(v) for v in obj]
    if is_dataclass(obj):
        return _safe_json(asdict(obj))
    # LangChain / LangGraph objects often provide dict-ish APIs
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


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_text:
        return args.prompt_text
    if args.prompt_args:
        return " ".join(args.prompt_args).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    raise SystemExit("Error: No prompt provided. Use -p/--prompt or pipe stdin.")


def _resolve_root_dir(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def _new_session_filename() -> str:
    # Deterministic-ish and readable (no colons for Windows safety)
    ts = time.strftime("%Y%m%d-%H%M%S")
    return f"session.{ts}.{uuid.uuid4().hex[:8]}.json"


def _relpath_if_under_root(root_dir: Path, path: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(root_dir.resolve())
        return str(rel)
    except Exception:
        return None


def _resolve_state_path(
    root_dir: Path,
    *,
    agent_name: str | None,
    explicit_state_path: str | None,
    force_new: bool,
    should_continue: bool,
) -> Path:
    settings = load_settings(root_dir)
    agents = dict(settings.agents or {})

    def _persist_resume(path: Path) -> None:
        rel = _relpath_if_under_root(root_dir, path)
        if rel is not None:
            update_local_resume(root_dir, last_session=rel, agents=agents)
        update_global_last_session(path)

    if explicit_state_path:
        resolved = Path(explicit_state_path).expanduser().resolve()
        if agent_name:
            rel = _relpath_if_under_root(root_dir, resolved)
            if rel is not None:
                agents[agent_name] = rel
        _persist_resume(resolved)
        return resolved

    if agent_name:
        rel = agents.get(agent_name) or str(Path(".kai") / "agents" / f"{agent_name}.json")
        state_path = (root_dir / rel).resolve()
        if force_new:
            rel = str(Path(".kai") / "agents" / f"{agent_name}.{_new_session_filename()}")
            state_path = (root_dir / rel).resolve()
        rel2 = _relpath_if_under_root(root_dir, state_path)
        if rel2 is not None:
            agents[agent_name] = rel2
        _persist_resume(state_path)
        return state_path

    if force_new:
        rel = str(Path(".kai") / _new_session_filename())
        state_path = (root_dir / rel).resolve()
        _persist_resume(state_path)
        return state_path

    if should_continue:
        if settings.last_session:
            return (root_dir / settings.last_session).resolve()
        global_last = load_global_last_session()
        if global_last:
            return Path(global_last).expanduser().resolve()
        raise SystemExit("Error: --continue requested but no previous session found")

    if settings.last_session:
        return (root_dir / settings.last_session).resolve()
    default_path = (root_dir / ".kai" / "session.json").resolve()
    _persist_resume(default_path)
    return default_path


def _build_permissions(args: argparse.Namespace) -> PermissionConfig | None:
    allowed_tools = _parse_csv(args.allowed_tools)
    disallowed_tools = _parse_csv(args.disallowed_tools)
    allowed_commands = _parse_csv(args.allowed_commands)
    disallowed_commands = _parse_csv(args.disallowed_commands)

    if not any([allowed_tools, disallowed_tools, allowed_commands, disallowed_commands]):
        return None

    return PermissionConfig(
        allowed_tools=allowed_tools,
        disallowed_tools=disallowed_tools,
        allowed_commands=allowed_commands,
        disallowed_commands=disallowed_commands,
    )


def _build_permissions_from_settings(settings: Any) -> PermissionConfig | None:
    allowed_tools = getattr(settings, "allowed_tools", None)
    disallowed_tools = getattr(settings, "disallowed_tools", None)
    allowed_commands = getattr(settings, "allowed_commands", None)
    disallowed_commands = getattr(settings, "disallowed_commands", None)
    if not any([allowed_tools, disallowed_tools, allowed_commands, disallowed_commands]):
        return None
    return PermissionConfig(
        allowed_tools=list(allowed_tools) if allowed_tools else None,
        disallowed_tools=list(disallowed_tools) if disallowed_tools else None,
        allowed_commands=list(allowed_commands) if allowed_commands else None,
        disallowed_commands=list(disallowed_commands) if disallowed_commands else None,
    )


def _toolset_to_default_model(toolset: str | None) -> str | None:
    if toolset == "codex":
        return "openai:gpt-4o"
    if toolset == "gemini":
        return "google_genai:gemini-2.0-flash"
    if toolset == "default":
        return "anthropic:claude-sonnet-4-5-20250929"
    return None


def _provider_from_model(model: str | None) -> str:
    """Best-effort provider detection from LangChain model handles."""
    if not model:
        return "anthropic"  # deepagents default
    if ":" in model:
        return model.split(":", 1)[0]
    # Fallback: treat as anthropic-ish
    return "anthropic"


def _credentials_env_vars(provider: str) -> list[str]:
    provider = provider.lower()
    if provider in {"openai"}:
        return ["OPENAI_API_KEY"]
    if provider in {"anthropic"}:
        return ["ANTHROPIC_API_KEY"]
    if provider in {"google_genai", "google"}:
        return ["GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"]
    # Unknown providers: don't guess
    return []


def _has_any_env(var_names: Iterable[str]) -> bool:
    return any(os.environ.get(v) for v in var_names)


def _emit_jsonl(obj: dict[str, Any]) -> None:
    print(json.dumps(obj))


def _traceback_enabled(flag: bool) -> bool:
    if flag:
        return True
    return os.environ.get("KAI_STREAM_INCLUDE_TRACEBACK") in {"1", "true", "TRUE", "yes", "YES"}


def _json_error_payload(
    *,
    run_id: str,
    command: str,
    model: str | None,
    permission_mode: str | None,
    state_path: Path | None,
    thread_id: str | None,
    tools: list[str] | None,
    err: Exception,
    include_traceback: bool,
    started_ms: int | None,
    ended_ms: int | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "error",
        "run_id": run_id,
        "command": command,
        "message": str(err),
        "error_type": err.__class__.__name__,
        "stop_reason": "error",
        "model": model,
        "provider": _provider_from_model(model) if model else None,
        "permission_mode": permission_mode,
        "thread_id": thread_id,
        "state_path": str(state_path) if state_path else None,
        "tools": tools,
        "stats": {
            "started_ms": started_ms,
            "ended_ms": ended_ms,
            "duration_ms": (max(0, ended_ms - started_ms) if started_ms is not None and ended_ms is not None else None),
        },
    }
    if include_traceback:
        payload["traceback"] = traceback.format_exc()
    return payload


def _parse_event_types_csv(value: str | None) -> set[str] | None:
    if value is None:
        return None
    parts = [p.strip() for p in value.split(",")]
    parts = [p for p in parts if p]
    return set(parts)


def _stream_json_run(
    *,
    agent: KaiAgent,
    prompt: str,
    run_id: str,
    permission_mode: str,
    model: str | None,
    include_traceback: bool = False,
) -> int:
    """Stream JSONL events with a stable schema.

    We intentionally keep this schema stable and include the raw chunk so callers
    can evolve their parsing without breakage.
    """

    schema_version = 1
    started_ms = now_ms()
    stats = RunStats(started_ms=started_ms, ended_ms=started_ms)
    next_event_id = 0

    tools = getattr(agent.config, "enabled_tools", None)

    # Event filtering: if provided, only emit those types.
    emit_types = _parse_event_types_csv(os.environ.get("KAI_STREAM_EVENT_TYPES"))
    if emit_types is not None:
        emit_types.add("init")
        emit_types.add("result")

    def _emit(payload: dict[str, Any]) -> None:
        nonlocal next_event_id
        t = payload.get("type")
        if emit_types is None or (isinstance(t, str) and t in emit_types):
            # Provide consistent metadata on all events (additive).
            payload["schema_version"] = schema_version
            payload["run_id"] = run_id
            payload.setdefault("thread_id", agent.thread_id)
            payload.setdefault(
                "state_path",
                str(agent.config.state_path) if agent.config.state_path else None,
            )
            payload.setdefault("model", model)
            payload.setdefault("provider", _provider_from_model(model) if model else None)
            payload.setdefault("permission_mode", permission_mode)
            payload.setdefault("tools", tools)
            payload["event_id"] = next_event_id
            next_event_id += 1
            _emit_jsonl(payload)

    ttft_ms: int | None = None
    stop_reason: str | None = None
    token_usage: dict[str, int | None] = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "cached_input_tokens": None,
        "reasoning_tokens": None,
    }

    _emit(
        {
            "type": "init",
            "schema_version": schema_version,
            "run_id": run_id,
            "ts_ms": started_ms,
            "thread_id": agent.thread_id,
            "state_path": str(agent.config.state_path) if agent.config.state_path else None,
            "model": model,
            "provider": _provider_from_model(model) if model else None,
            "permission_mode": permission_mode,
        }
    )

    last_assistant = ""
    interrupted = False
    last_snapshot: dict[str, Any] | None = None
    seen_tool_calls: set[str] = set()
    seen_tool_results: set[str] = set()
    had_error = False
    last_turn_id: int | None = None
    last_step_id: int | None = None
    open_turn_id: int | None = None
    open_step_id: int | None = None

    tool_call_started_ms: dict[str, int] = {}
    tool_latencies: list[int] = []

    try:
        for chunk in agent.stream(prompt):
            stats.chunk_count += 1
            ts_ms = now_ms()
            emitted = False

            if ttft_ms is None:
                ttft_ms = max(0, ts_ms - started_ms)

            if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
                last_snapshot = chunk
                messages = chunk.get("messages")
                if isinstance(messages, list):
                    turns, steps = count_turns_steps(messages)
                    turn_id = (turns - 1) if isinstance(turns, int) and turns > 0 else None
                    step_id = (steps - 1) if isinstance(steps, int) and steps > 0 else None
                    last_turn_id = turn_id
                    last_step_id = step_id

                    # Deterministic turn/step lifecycle events derived from snapshot deltas.
                    if open_turn_id is not None and turn_id is not None and turn_id != open_turn_id:
                        # Close any open step before closing the turn.
                        if open_step_id is not None:
                            _emit(
                                {
                                    "type": "step_end",
                                    "schema_version": schema_version,
                                    "run_id": run_id,
                                    "ts_ms": ts_ms,
                                    "turn_id": open_turn_id,
                                    "step_id": open_step_id,
                                    "stop_reason": "turn_advanced",
                                }
                            )
                            open_step_id = None
                        _emit(
                            {
                                "type": "turn_end",
                                "schema_version": schema_version,
                                "run_id": run_id,
                                "ts_ms": ts_ms,
                                "turn_id": open_turn_id,
                                "stop_reason": "turn_advanced",
                            }
                        )
                        open_turn_id = None
                        open_step_id = None

                    if open_turn_id is None and turn_id is not None:
                        _emit(
                            {
                                "type": "turn_start",
                                "schema_version": schema_version,
                                "run_id": run_id,
                                "ts_ms": ts_ms,
                                "turn_id": turn_id,
                            }
                        )
                        open_turn_id = turn_id

                    if open_step_id is not None and step_id is not None and step_id != open_step_id:
                        _emit(
                            {
                                "type": "step_end",
                                "schema_version": schema_version,
                                "run_id": run_id,
                                "ts_ms": ts_ms,
                                "turn_id": open_turn_id,
                                "step_id": open_step_id,
                                "stop_reason": "step_advanced",
                            }
                        )
                        open_step_id = None

                    if open_step_id is None and step_id is not None:
                        _emit(
                            {
                                "type": "step_start",
                                "schema_version": schema_version,
                                "run_id": run_id,
                                "ts_ms": ts_ms,
                                "turn_id": open_turn_id,
                                "step_id": step_id,
                            }
                        )
                        open_step_id = step_id

                    # Extract tool events by scanning the whole snapshot.
                    tool_events = correlate_tool_events(
                        detect_tool_events_from_messages(messages),
                        turn_id=turn_id,
                        step_id=step_id,
                    )
                    for tool_index, te in enumerate(tool_events):
                        if te.kind == "tool_call":
                            tc_id = te.tool_call_id or synthesize_tool_call_id(te, turn_id=turn_id, step_id=step_id)
                            key = tc_id or f"{te.tool_name}:{_safe_json(te.args)}"
                            if key in seen_tool_calls:
                                continue
                            seen_tool_calls.add(key)

                            if tc_id is not None and tc_id not in tool_call_started_ms:
                                tool_call_started_ms[tc_id] = ts_ms
                            _emit(
                                {
                                    "type": "tool_call",
                                    "schema_version": schema_version,
                                    "run_id": run_id,
                                    "ts_ms": ts_ms,
                                    "turn_id": turn_id,
                                    "step_id": step_id,
                                    "tool_index": tool_index,
                                    "msg_index": te.msg_index,
                                    "part_index": te.part_index,
                                    "tool_call_id": tc_id,
                                    "tool_name": te.tool_name,
                                    "args": _safe_json(te.args),
                                    "raw": te.raw,
                                }
                            )
                            emitted = True
                        elif te.kind == "tool_result":
                            tr_id = te.tool_call_id or synthesize_tool_call_id(te, turn_id=turn_id, step_id=step_id)
                            key = tr_id or f"{te.tool_name}:{te.content}"
                            if key in seen_tool_results:
                                continue
                            seen_tool_results.add(key)

                            tool_latency_ms = None
                            if tr_id is not None and tr_id in tool_call_started_ms:
                                tool_latency_ms = max(0, ts_ms - tool_call_started_ms[tr_id])
                                tool_latencies.append(tool_latency_ms)
                            _emit(
                                {
                                    "type": "tool_result",
                                    "schema_version": schema_version,
                                    "run_id": run_id,
                                    "ts_ms": ts_ms,
                                    "turn_id": turn_id,
                                    "step_id": step_id,
                                    "tool_index": tool_index,
                                    "msg_index": te.msg_index,
                                    "part_index": te.part_index,
                                    "tool_call_id": tr_id,
                                    "tool_name": te.tool_name,
                                    "content": te.content,
                                    "tool_latency_ms": tool_latency_ms,
                                    **extract_tool_result_fields(te),
                                    "raw": te.raw,
                                }
                            )
                            emitted = True

                    # Extract stop_reason + usage from latest assistant message.
                    if stop_reason is None:
                        stop_reason = last_stop_reason(messages)

                    # Emit assistant content delta.
                    last_ai = None
                    for m in reversed(messages):
                        if isinstance(m, dict) and (m.get("role") in ("assistant", "ai") or m.get("type") in ("assistant", "ai")):
                            last_ai = m
                            break
                    if last_ai is not None:
                        content = last_ai.get("content") if isinstance(last_ai.get("content"), str) else None
                        if content is not None:
                            delta = content[len(last_assistant) :] if content.startswith(last_assistant) else content
                            last_assistant = content
                            _emit(
                                {
                                    "type": "message",
                                    "schema_version": schema_version,
                                    "run_id": run_id,
                                    "ts_ms": ts_ms,
                                    "turn_id": turn_id,
                                    "step_id": step_id,
                                    "role": "assistant",
                                    "delta": delta,
                                    "content": content,
                                }
                            )
                            emitted = True

            if isinstance(chunk, dict) and chunk.get("__interrupt__"):
                interrupted = True
                stats.interrupted = True
                _emit(
                    {
                        "type": "tool_call",
                        "schema_version": schema_version,
                        "run_id": run_id,
                        "ts_ms": ts_ms,
                        "thread_id": agent.thread_id,
                        "state_path": str(agent.config.state_path) if agent.config.state_path else None,
                        "interrupt": _safe_json(chunk.get("__interrupt__")),
                        "resume_hint": "kai resume --continue --approve",
                        "turn_id": last_turn_id,
                        "step_id": last_step_id,
                        "raw": _safe_json(chunk),
                    }
                )
                emitted = True
                break

            if not emitted:
                _emit(
                    {
                        "type": "message",
                        "schema_version": schema_version,
                        "run_id": run_id,
                        "ts_ms": ts_ms,
                        "raw": _safe_json(chunk),
                    }
                )
    except Exception as e:
        ts_ms = now_ms()
        had_error = True
        include_tb = _traceback_enabled(include_traceback)
        _emit(
            {
                "type": "error",
                "schema_version": schema_version,
                "run_id": run_id,
                "ts_ms": ts_ms,
                "model": model,
                "provider": _provider_from_model(model) if model else None,
                "permission_mode": permission_mode,
                "thread_id": agent.thread_id,
                "state_path": str(agent.config.state_path) if agent.config.state_path else None,
                "stop_reason": "error",
                "turn_id": last_turn_id,
                "step_id": last_step_id,
                "message": str(e),
                "error_type": e.__class__.__name__,
                "stats": {
                    "started_ms": started_ms,
                    "ended_ms": ts_ms,
                    "duration_ms": max(0, ts_ms - started_ms),
                    "ttft_ms": ttft_ms,
                    "chunk_count": stats.chunk_count,
                },
                **({"traceback": traceback.format_exc()} if include_tb else {}),
            }
        )

    stats.ended_ms = now_ms()

    # Close any open step/turn deterministically before emitting final result.
    if open_step_id is not None:
        _emit(
            {
                "type": "step_end",
                "schema_version": schema_version,
                "run_id": run_id,
                "ts_ms": stats.ended_ms,
                "turn_id": open_turn_id,
                "step_id": open_step_id,
                "stop_reason": "error" if had_error else ("interrupt" if interrupted else "end_turn"),
            }
        )
        open_step_id = None

    if open_turn_id is not None:
        _emit(
            {
                "type": "turn_end",
                "schema_version": schema_version,
                "run_id": run_id,
                "ts_ms": stats.ended_ms,
                "turn_id": open_turn_id,
                "stop_reason": "error" if had_error else ("interrupt" if interrupted else "end_turn"),
            }
        )
        open_turn_id = None

    output: str | None = None
    message_count: int | None = None
    turn_count: int | None = None
    step_count: int | None = None
    if last_snapshot is not None:
        msgs = last_snapshot.get("messages")
        if isinstance(msgs, list):
            message_count = len(msgs)
            turn_count, step_count = count_turns_steps(msgs)

            u_total = aggregate_usage(msgs)
            token_usage = {
                "prompt_tokens": u_total.prompt_tokens,
                "completion_tokens": u_total.completion_tokens,
                "total_tokens": u_total.total_tokens,
                "cached_input_tokens": u_total.cached_input_tokens,
                "reasoning_tokens": u_total.reasoning_tokens,
            }
            if stop_reason is None:
                stop_reason = last_stop_reason(msgs)
            if msgs:
                last = msgs[-1]
                if isinstance(last, dict):
                    output = last.get("content") if isinstance(last.get("content"), str) else None
                else:
                    output = str(last)

    persisted = bool(agent.config.state_path and agent.config.state_path.exists())

    # Errors always dominate stop_reason so consumers don't treat failed runs as successes.
    if had_error:
        stop_reason = "error"
    elif stop_reason is None:
        stop_reason = "interrupt" if interrupted else "end_turn"

    _emit(
        {
            "type": "result",
            "schema_version": schema_version,
            "run_id": run_id,
            "ts_ms": stats.ended_ms,
            "thread_id": agent.thread_id,
            "state_path": str(agent.config.state_path) if agent.config.state_path else None,
            "model": model,
            "provider": _provider_from_model(model) if model else None,
            "permission_mode": permission_mode,
            "persisted": persisted,
            "interrupted": interrupted,
            "stop_reason": stop_reason,
            "output": output,
            "stats": {
                "duration_ms": stats.duration_ms,
                "ttft_ms": ttft_ms,
                "chunk_count": stats.chunk_count,
                "message_count": message_count,
                "turn_count": turn_count,
                "step_count": step_count,
                "tool_call_count": len(seen_tool_calls),
                "tool_result_count": len(seen_tool_results),
                "tool_count": len(tool_latencies),
                "tool_latency_ms_total": sum(tool_latencies) if tool_latencies else 0,
                "tool_latency_ms_avg": (sum(tool_latencies) / len(tool_latencies)) if tool_latencies else None,
                "tool_latency_ms_max": max(tool_latencies) if tool_latencies else None,
                "token_usage": token_usage,
            },
            "turn_id": (turn_count - 1) if isinstance(turn_count, int) and turn_count > 0 else None,
            "step_id": (step_count - 1) if isinstance(step_count, int) and step_count > 0 else None,
        }
    )

    if had_error:
        return EXIT_ERROR
    return EXIT_INTERRUPT if interrupted else EXIT_SUCCESS


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "resume":
        return _resume_main(argv[1:])

    # Load cwd/.env early so credential checks and default selections work consistently (incl. TUI).
    load_dotenv(root_dir=None)

    parser = argparse.ArgumentParser(
        prog="kai",
        description="Kai Code: deepagents-based coding agent (letta-code-inspired).",
    )

    parser.add_argument(
        "--mode",
        choices=["local", "letta"],
        default="local",
        help="Execution mode: local (deepagents) or letta (Letta server)",
    )
    parser.add_argument("--letta-api-key", help="Letta API key (overrides LETTA_API_KEY)")
    parser.add_argument("--letta-base-url", help="Letta base URL (overrides LETTA_BASE_URL)")
    parser.add_argument("--letta-project", help="Letta project/workspace (optional)")
    parser.add_argument(
        "--base-tools",
        action="store_true",
        help="(letta mode) include Letta base tools on agent creation",
    )
    parser.add_argument(
        "--sleeptime",
        action="store_true",
        help="(letta mode) enable sleeptime on agent creation",
    )
    parser.add_argument(
        "--init-block",
        action="append",
        dest="init_blocks",
        default=None,
        help="(letta mode) add an initial memory block as label=text (repeatable)",
    )

    try:
        version = metadata.version("kai-code")
    except Exception:
        version = "0.0.0"
    parser.add_argument("--version", action="version", version=f"{version} (Kai Code)")

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch interactive TUI mode",
    )

    parser.add_argument("--root", help="Project root (defaults to cwd)")
    parser.add_argument("--new", action="store_true", help="Start a new session")
    parser.add_argument("-c", "--continue", dest="continue_", action="store_true", help="Resume last session")
    parser.add_argument("-a", "--agent", help="Named agent/session (maps to .kai/agents/<name>*.json)")
    parser.add_argument("--state-path", help="Explicit path to the session state JSON")

    parser.add_argument("-m", "--model", help="LangChain model handle (e.g. openai:gpt-4o)")
    parser.add_argument(
        "--toolset",
        "--toolSet",
        dest="toolset",
        choices=["codex", "default", "gemini"],
        help="Toolset-ish selection (affects default model if --model omitted)",
    )

    parser.add_argument(
        "--permission-mode",
        choices=list(VALID_PERMISSION_MODES),
        help="Permission mode: default, acceptEdits, plan, bypassPermissions",
    )

    # Back-compat flags: tri-state so we can distinguish "not provided".
    parser.add_argument(
        "--yolo",
        dest="yolo",
        action="store_true",
        default=None,
        help="Alias for --permission-mode bypassPermissions",
    )
    parser.add_argument(
        "--no-yolo",
        dest="yolo",
        action="store_false",
        default=None,
        help="Alias for --permission-mode default",
    )

    parser.add_argument(
        "--output-format",
        choices=["text", "json", "stream-json"],
        default="text",
        help="Output format for headless mode",
    )

    parser.add_argument(
        "--stream-event-types",
        help="Comma-separated event types to emit for stream-json (e.g. init,message,tool_call,tool_result,error,result)",
    )

    parser.add_argument(
        "--stream-include-traceback",
        action="store_true",
        help="Include a traceback field in stream-json error events (also supports env KAI_STREAM_INCLUDE_TRACEBACK=1)",
    )

    parser.add_argument(
        "--include-traceback",
        action="store_true",
        help="Include a traceback field in JSON error payloads (alias: --stream-include-traceback)",
    )

    parser.add_argument("--skills", default=".skills", help="Skills directory (default: .skills)")
    parser.add_argument(
        "--system-prompt",
        "--system",
        dest="system_prompt",
        help="Additional system prompt text (alias: --system)",
    )
    parser.add_argument(
        "--system-id",
        dest="system_id",
        help="System prompt preset id (e.g. kai-default)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved config/state path and exit (no model call)",
    )

    parser.add_argument(
        "--tools",
        help=(
            "Comma-separated tool names/patterns to enable for this run (filter). "
            "Permissions (allowed/disallowed tools/commands) still apply."
        ),
    )

    parser.add_argument(
        "--allowed-tools",
        "--allowedTools",
        dest="allowed_tools",
        help="Comma-separated fnmatch patterns",
    )
    parser.add_argument(
        "--disallowed-tools",
        "--disallowedTools",
        dest="disallowed_tools",
        help="Comma-separated fnmatch patterns",
    )
    parser.add_argument(
        "--allowed-commands",
        "--allowedCommands",
        dest="allowed_commands",
        help="Comma-separated fnmatch patterns",
    )
    parser.add_argument(
        "--disallowed-commands",
        "--disallowedCommands",
        dest="disallowed_commands",
        help="Comma-separated fnmatch patterns",
    )

    # Prompt: mirror letta headless behavior (args or stdin)
    parser.add_argument("-p", "--prompt", dest="prompt_text", nargs="?", help="Prompt text (or omit to read stdin)")
    # Compatibility with letta-code parsing; treated as a no-op headless trigger.
    parser.add_argument("--run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("prompt_args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    # Launch TUI mode if --interactive flag is provided
    if args.interactive:
        from .tui.app import KaiCodeApp

        root_dir = _resolve_root_dir(args.root)
        load_dotenv(root_dir=root_dir)

        migrate_global_settings(root_dir)
        migrate_project_settings(root_dir)
        settings = load_settings(root_dir)

        # Model selection precedence: CLI --model > CLI --toolset > settings.default_model > settings.default_toolset
        if args.model:
            model = args.model
        elif args.toolset:
            model = _toolset_to_default_model(args.toolset)
        elif settings.default_model:
            model = settings.default_model
        else:
            model = _toolset_to_default_model(settings.default_toolset)

        # Resolve permission mode for yolo setting
        if args.permission_mode:
            permission_mode = args.permission_mode
        elif args.yolo is True:
            permission_mode = "bypassPermissions"
        elif args.yolo is False:
            permission_mode = "default"
        elif settings.permission_mode:
            permission_mode = settings.permission_mode
        else:
            permission_mode = "bypassPermissions"

        mode_res = resolve_permission_mode(mode=permission_mode, base_permissions=None)

        app = KaiCodeApp(
            root_dir=str(root_dir),
            model=model or "default",
            session=args.agent or "default",
            yolo=bool(mode_res.yolo),
        )
        app.run()
        return EXIT_SUCCESS

    from .system_prompts import resolve_system_prompt

    resolved_system_prompt = resolve_system_prompt(
        system_id=getattr(args, "system_id", None),
        extra=args.system_prompt,
    )

    # Apply stream-json filtering early so it works for dry-run schemas too.
    if getattr(args, "stream_event_types", None):
        os.environ["KAI_STREAM_EVENT_TYPES"] = args.stream_event_types

    # letta-code compat: --tools is a tool loading/filtering mechanism, distinct from permissions.
    # We implement this as a per-run tool filter. Permission allow/deny still applies.
    enabled_tools = _parse_csv(getattr(args, "tools", None))

    root_dir = _resolve_root_dir(args.root)
    # Also load root/.env once root is known (does not override existing env vars).
    load_dotenv(root_dir=root_dir)

    if args.mode == "letta":
        from .letta_runner import LettaRunner

        if args.dry_run:
            payload = {
                "type": "dry-run",
                "mode": "letta",
                "root_dir": str(root_dir),
                "agent": args.agent,
                "continue": bool(args.continue_),
                "new": bool(args.new),
                "letta_base_url": args.letta_base_url,
                "letta_project": args.letta_project,
            }
            print(json.dumps(payload, indent=2))
            return EXIT_SUCCESS

        prompt = _read_prompt(args)
        runner = LettaRunner(
            root_dir=root_dir,
            api_key=args.letta_api_key,
            base_url=args.letta_base_url,
            project=args.letta_project,
            model=model if isinstance(model, str) else None,
            system=resolved_system_prompt,
        )
        try:
            if args.new:
                agent_id = runner.create_agent(
                    name=None,
                    include_base_tools=bool(args.base_tools),
                    enable_sleeptime=bool(args.sleeptime),
                    init_blocks=getattr(args, "init_blocks", None),
                )
            else:
                agent_id = runner.resolve_agent_id(
                    agent_id=args.agent,
                    force_new=bool(args.new),
                    should_continue=bool(args.continue_),
                )
        except Exception as e:
            if args.output_format == "json":
                print(
                    json.dumps(
                        {
                            "type": "error",
                            "stop_reason": "error",
                            "error_type": e.__class__.__name__,
                            "message": str(e),
                        },
                        indent=2,
                    )
                )
            else:
                print(f"Error: {e}", file=sys.stderr)
            return EXIT_ERROR

        if args.output_format == "stream-json":
            if args.stream_event_types:
                os.environ["KAI_STREAM_EVENT_TYPES"] = args.stream_event_types

            # Reuse cli emitter to ensure jsonl formatting.
            run_id = uuid.uuid4().hex
            next_event_id = 0
            emit_types = _parse_event_types_csv(os.environ.get("KAI_STREAM_EVENT_TYPES"))
            if emit_types is not None:
                emit_types.add("init")
                emit_types.add("result")

            def _emit(payload: dict[str, Any]) -> None:
                nonlocal next_event_id
                t = payload.get("type")
                if emit_types is None or (isinstance(t, str) and t in emit_types):
                    payload.setdefault("event_id", next_event_id)
                    next_event_id += 1
                    _emit_jsonl(payload)

            return runner.stream_json(
                agent_id=agent_id,
                prompt=prompt,
                run_id=run_id,
                permission_mode=permission_mode,
                permissions=mode_res.permissions,
                enabled_tools=enabled_tools,
                include_traceback=bool(args.stream_include_traceback or args.include_traceback),
                emit=_emit,
            )

        res = runner.run_headless(agent_id=agent_id, prompt=prompt)
        print(res.output)
        return EXIT_SUCCESS

    migrate_global_settings(root_dir)
    migrate_project_settings(root_dir)
    settings = load_settings(root_dir)

    state_path = _resolve_state_path(
        root_dir,
        agent_name=args.agent,
        explicit_state_path=args.state_path,
        force_new=bool(args.new),
        should_continue=bool(args.continue_),
    )

    # For dry-run output, prefer showing the effective enabled-tools filter a run would use,
    # including any persisted session default.
    effective_enabled_tools = enabled_tools
    if effective_enabled_tools is None and state_path.exists():
        try:
            state_obj = json.loads(state_path.read_text())
            if (
                isinstance(state_obj, dict)
                and isinstance(state_obj.get("enabled_tools"), list)
                and all(isinstance(x, str) for x in state_obj.get("enabled_tools"))
            ):
                effective_enabled_tools = list(state_obj["enabled_tools"])
        except Exception:
            pass

    # Model selection precedence:
    # CLI --model > CLI --toolset > settings.default_model > settings.default_toolset
    if args.model:
        model = args.model
    elif args.toolset:
        model = _toolset_to_default_model(args.toolset)
    elif settings.default_model:
        model = settings.default_model
    else:
        model = _toolset_to_default_model(settings.default_toolset)

    # Permissions precedence: CLI explicit patterns override settings.
    permissions = _build_permissions(args)
    if permissions is None:
        permissions = _build_permissions_from_settings(settings)

    # Resolve permission mode precedence:
    # CLI --permission-mode > --yolo/--no-yolo > settings.permission_mode > default
    if args.permission_mode:
        permission_mode = args.permission_mode
    elif args.yolo is True:
        permission_mode = "bypassPermissions"
    elif args.yolo is False:
        permission_mode = "default"
    elif settings.permission_mode:
        permission_mode = settings.permission_mode
    else:
        permission_mode = "bypassPermissions"

    mode_res = resolve_permission_mode(mode=permission_mode, base_permissions=permissions)

    if args.dry_run:
        payload = {
            "type": "dry-run",
            "root_dir": str(root_dir),
            "state_path": str(state_path),
            "agent": args.agent,
            "model": model,
            "toolset": args.toolset,
            "permission_mode": permission_mode,
            "yolo": bool(mode_res.yolo),
            "skills": args.skills,
            "permissions": _safe_json(permissions) if permissions else None,
            "tools": effective_enabled_tools,
        }

        if args.output_format == "stream-json":
            run_id = uuid.uuid4().hex
            _emit_jsonl(
                {
                    "type": "init",
                    "schema_version": 1,
                    "run_id": run_id,
                    "event_id": 0,
                    "ts_ms": now_ms(),
                    "dry_run": True,
                    "thread_id": None,
                    "state_path": str(state_path),
                    "tools": effective_enabled_tools,
                    "config": payload,
                    "model": model,
                    "provider": _provider_from_model(model) if model else None,
                }
            )
            _emit_jsonl(
                {
                    "type": "result",
                    "schema_version": 1,
                    "run_id": run_id,
                    "event_id": 1,
                    "ts_ms": now_ms(),
                    "dry_run": True,
                    "output": None,
                    "stop_reason": "dry_run",
                    "turn_id": None,
                    "step_id": None,
                    "tools": effective_enabled_tools,
                    "stats": {
                        "duration_ms": 0,
                        "ttft_ms": None,
                        "chunk_count": 0,
                        "message_count": None,
                        "turn_count": None,
                        "step_count": None,
                        "tool_call_count": 0,
                        "tool_result_count": 0,
                        "token_usage": {
                            "prompt_tokens": None,
                            "completion_tokens": None,
                            "total_tokens": None,
                            "cached_input_tokens": None,
                            "reasoning_tokens": None,
                        },
                    },
                }
            )
            return EXIT_SUCCESS

        print(json.dumps(payload, indent=2))
        return EXIT_SUCCESS

    # Interactive TUI: if no prompt was provided and stdin is a TTY.
    if args.output_format == "text":
        has_prompt = bool(args.prompt_text) or bool(args.prompt_args) or (not sys.stdin.isatty())
        if not has_prompt:
            from .tui import TuiConfig, run_tui

            return run_tui(
                config=TuiConfig(
                    mode=args.mode,
                    root_dir=root_dir,
                    state_path=Path(state_path),
                    model=model,
                    toolset=args.toolset,
                    permission_mode=permission_mode,
                    skills_dir=args.skills,
                    system_prompt=resolved_system_prompt,
                    letta_api_key=args.letta_api_key,
                    letta_base_url=args.letta_base_url,
                    letta_project=args.letta_project,
                )
            )

    # Only treat -p/--prompt specially; if user didn't pass -p but provided
    # positionals, we still accept them (matching letta headless behavior).
    prompt = _read_prompt(args)

    provider = _provider_from_model(model)
    required_vars = _credentials_env_vars(provider)
    if required_vars and not _has_any_env(required_vars):
        hint = f"Missing credentials for provider '{provider}'. Set one of: {', '.join(required_vars)}."
        hint += " Or pass --model for a different provider."
        print(hint, file=sys.stderr)
        return EXIT_ERROR

    agent = KaiAgent(
        root_dir=root_dir,
        model=model,
        yolo=bool(mode_res.yolo),
        interrupt_on=mode_res.interrupt_on,
        system_prompt=resolved_system_prompt,
        skills_dir=args.skills,
        state_path=state_path,
        permissions=mode_res.permissions,
        enabled_tools=enabled_tools,
    )

    if args.output_format == "stream-json":
        if args.stream_event_types:
            os.environ["KAI_STREAM_EVENT_TYPES"] = args.stream_event_types
        return _stream_json_run(
            agent=agent,
            prompt=prompt,
            run_id=uuid.uuid4().hex,
            permission_mode=permission_mode,
            model=model if isinstance(model, str) else None,
            include_traceback=bool(args.stream_include_traceback or args.include_traceback),
        )

    run_id = uuid.uuid4().hex
    started = now_ms()
    try:
        result = agent.run(prompt)
    except Exception as e:
        ended = now_ms()
        include_tb = _traceback_enabled(bool(args.include_traceback or args.stream_include_traceback))
        if args.output_format == "json":
            print(
                json.dumps(
                    _json_error_payload(
                        run_id=run_id,
                        command="run",
                        model=model if isinstance(model, str) else None,
                        permission_mode=permission_mode,
                        state_path=Path(state_path),
                        thread_id=getattr(agent, "thread_id", None),
                        tools=getattr(agent.config, "enabled_tools", None),
                        err=e,
                        include_traceback=include_tb,
                        started_ms=started,
                        ended_ms=ended,
                    ),
                    indent=2,
                )
            )
            return EXIT_ERROR
        # Text mode: print a concise error.
        print(f"Error: {e}", file=sys.stderr)
        if include_tb:
            print(traceback.format_exc(), file=sys.stderr)
        return EXIT_ERROR
    ended = now_ms()

    # Best-effort stop_reason and token usage from the last assistant message.
    msgs = result.messages
    u_total = aggregate_usage(msgs)
    token_usage = {
        "prompt_tokens": u_total.prompt_tokens,
        "completion_tokens": u_total.completion_tokens,
        "total_tokens": u_total.total_tokens,
        "cached_input_tokens": u_total.cached_input_tokens,
        "reasoning_tokens": u_total.reasoning_tokens,
    }
    stop_reason: str | None = last_stop_reason(msgs)

    is_interrupt = isinstance(result.raw, dict) and bool(result.raw.get("__interrupt__"))
    if stop_reason is None:
        stop_reason = "interrupt" if is_interrupt else "end_turn"

    turn_count, step_count = count_turns_steps(msgs)

    stats = {
        "duration_ms": max(0, ended - started),
        "started_ms": started,
        "ended_ms": ended,
        "permission_mode": permission_mode,
        "message_count": len(result.messages),
        "ttft_ms": None,
        "stop_reason": stop_reason,
        "token_usage": token_usage,
        "turn_count": turn_count,
        "step_count": step_count,
    }

    # Detect HITL interrupt (LangGraph convention)
    if isinstance(result.raw, dict) and result.raw.get("__interrupt__"):
        payload = {
            "type": "interrupt",
            "run_id": run_id,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "tools": getattr(agent.config, "enabled_tools", None),
            "interrupt": _safe_json(result.raw.get("__interrupt__")),
            "stats": stats,
            "stop_reason": "interrupt",
            "resume_hint": "kai resume --continue --approve",
        }
        if args.output_format == "json":
            print(json.dumps(payload, indent=2))
        else:
            print(json.dumps(payload, indent=2), file=sys.stderr)
        return EXIT_INTERRUPT

    if args.output_format == "json":
        payload = {
            "type": "result",
            "run_id": run_id,
            "output": result.output,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "model": model,
            "provider": _provider_from_model(model) if isinstance(model, str) else None,
            "tools": getattr(agent.config, "enabled_tools", None),
            "stop_reason": stop_reason,
            "messages": result.messages,
            "stats": stats,
        }
        print(json.dumps(payload, indent=2))
        return EXIT_SUCCESS

    print(result.output)
    return EXIT_SUCCESS


def _resume_main(argv: list[str]) -> int:
    load_dotenv(root_dir=None)

    parser = argparse.ArgumentParser(
        prog="kai resume",
        description="Resume a human-in-the-loop interrupted run.",
    )

    parser.add_argument("--root", help="Project root (defaults to cwd)")
    parser.add_argument("-c", "--continue", dest="continue_", action="store_true", help="Resume last session")
    parser.add_argument("-a", "--agent", help="Named agent/session")
    parser.add_argument("--state-path", help="Explicit path to the session state JSON")

    parser.add_argument("-m", "--model", help="LangChain model handle (optional override)")
    parser.add_argument(
        "--tools",
        help=(
            "Comma-separated tool names/patterns to enable for this resume (filter). "
            "If omitted, Kai restores enabled tools from the persisted session when available."
        ),
    )
    parser.add_argument(
        "--permission-mode",
        choices=list(VALID_PERMISSION_MODES),
        help="Permission mode during resume (default: default)",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve", action="store_true", help="Approve the pending tool call")
    group.add_argument("--reject", action="store_true", help="Reject the pending tool call")
    group.add_argument(
        "--edit",
        metavar="JSON",
        help="Edit the pending tool call. Provide an edited_action JSON object.",
    )
    group.add_argument(
        "--decisions-json",
        metavar="JSON",
        help="Provide a full decisions JSON array (advanced).",
    )

    parser.add_argument(
        "--output-format",
        choices=["text", "json", "stream-json"],
        default="text",
        help="Output format",
    )

    parser.add_argument(
        "--include-traceback",
        action="store_true",
        help="Include traceback in JSON error payloads (also supports env KAI_STREAM_INCLUDE_TRACEBACK=1)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve session + decision payload and exit (no model call)",
    )

    args = parser.parse_args(argv)
    root_dir = _resolve_root_dir(args.root)
    load_dotenv(root_dir=root_dir)

    migrate_global_settings(root_dir)
    migrate_project_settings(root_dir)
    settings = load_settings(root_dir)

    state_path = _resolve_state_path(
        root_dir,
        agent_name=args.agent,
        explicit_state_path=args.state_path,
        force_new=False,
        should_continue=bool(args.continue_),
    )

    enabled_tools = _parse_csv(getattr(args, "tools", None))

    effective_enabled_tools = enabled_tools
    if effective_enabled_tools is None and state_path.exists():
        try:
            state_obj = json.loads(state_path.read_text())
            if (
                isinstance(state_obj, dict)
                and isinstance(state_obj.get("enabled_tools"), list)
                and all(isinstance(x, str) for x in state_obj.get("enabled_tools"))
            ):
                effective_enabled_tools = list(state_obj["enabled_tools"])
        except Exception:
            pass

    # For resume, default to a mode that supports HITL.
    permission_mode = args.permission_mode or "default"
    permissions = _build_permissions_from_settings(settings)
    mode_res = resolve_permission_mode(mode=permission_mode, base_permissions=permissions)
    if mode_res.yolo:
        raise SystemExit(
            "Error: kai resume requires a permission mode that enables HITL (default or acceptEdits)."
        )

    # Build decisions payload
    decisions: list[dict[str, Any]]
    if args.approve:
        decisions = [{"type": "approve"}]
    elif args.reject:
        decisions = [{"type": "reject"}]
    elif args.edit:
        try:
            edited_action = json.loads(args.edit)
        except Exception:
            raise SystemExit("Error: --edit must be a JSON object")
        if not isinstance(edited_action, dict):
            raise SystemExit("Error: --edit must be a JSON object")
        decisions = [{"type": "edit", "edited_action": edited_action}]
    else:
        try:
            parsed = json.loads(args.decisions_json)
        except Exception:
            raise SystemExit("Error: --decisions-json must be a JSON array")
        if not isinstance(parsed, list) or not all(isinstance(x, dict) for x in parsed):
            raise SystemExit("Error: --decisions-json must be a JSON array of objects")
        decisions = parsed

    if args.dry_run:
        payload = {
            "type": "dry-run",
            "command": "resume",
            "root_dir": str(root_dir),
            "state_path": str(state_path),
            "agent": args.agent,
            "permission_mode": permission_mode,
            "decisions": decisions,
            "tools": effective_enabled_tools,
        }
        if args.output_format == "stream-json":
            run_id = uuid.uuid4().hex
            _emit_jsonl(
                {
                    "type": "init",
                    "schema_version": 1,
                    "run_id": run_id,
                    "event_id": 0,
                    "ts_ms": now_ms(),
                    "dry_run": True,
                    "tools": effective_enabled_tools,
                    "config": payload,
                }
            )
            _emit_jsonl(
                {
                    "type": "result",
                    "schema_version": 1,
                    "run_id": run_id,
                    "event_id": 1,
                    "ts_ms": now_ms(),
                    "dry_run": True,
                    "output": None,
                    "tools": effective_enabled_tools,
                    "stats": {"duration_ms": 0},
                }
            )
            return EXIT_SUCCESS
        print(json.dumps(payload, indent=2))
        return EXIT_SUCCESS

    model = args.model or settings.default_model or _toolset_to_default_model(settings.default_toolset)
    provider = _provider_from_model(model)
    required_vars = _credentials_env_vars(provider)
    if required_vars and not _has_any_env(required_vars):
        hint = f"Missing credentials for provider '{provider}'. Set one of: {', '.join(required_vars)}."
        hint += " Or pass --model for a different provider."
        print(hint, file=sys.stderr)
        return EXIT_ERROR

    agent = KaiAgent(
        root_dir=root_dir,
        model=model,
        yolo=False,
        interrupt_on=mode_res.interrupt_on,
        skills_dir=".skills",  # restored from session state if previously customized
        state_path=state_path,
        permissions=mode_res.permissions,
        enabled_tools=enabled_tools,
    )

    run_id = uuid.uuid4().hex
    started = now_ms()
    try:
        result = agent.resume(decisions)
    except Exception as e:
        ended = now_ms()
        include_tb = _traceback_enabled(bool(args.include_traceback))
        if args.output_format == "json":
            print(
                json.dumps(
                    _json_error_payload(
                        run_id=run_id,
                        command="resume",
                        model=model if isinstance(model, str) else None,
                        permission_mode=permission_mode,
                        state_path=Path(state_path),
                        thread_id=getattr(agent, "thread_id", None),
                        tools=getattr(agent.config, "enabled_tools", None),
                        err=e,
                        include_traceback=include_tb,
                        started_ms=started,
                        ended_ms=ended,
                    ),
                    indent=2,
                )
            )
            return EXIT_ERROR
        print(f"Error: {e}", file=sys.stderr)
        if include_tb:
            print(traceback.format_exc(), file=sys.stderr)
        return EXIT_ERROR
    ended = now_ms()

    if isinstance(result.raw, dict) and result.raw.get("__interrupt__"):
        payload = {
            "type": "interrupt",
            "run_id": run_id,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "tools": getattr(agent.config, "enabled_tools", None),
            "interrupt": _safe_json(result.raw.get("__interrupt__")),
            "stats": {"duration_ms": max(0, ended - started)},
            "stop_reason": "interrupt",
        }
        if args.output_format == "stream-json":
            _emit_jsonl(
                {
                    "type": "init",
                    "schema_version": 1,
                    "run_id": run_id,
                    "event_id": 0,
                    "ts_ms": started,
                    "thread_id": agent.thread_id,
                    "state_path": str(state_path),
                    "tools": getattr(agent.config, "enabled_tools", None),
                    "model": model,
                    "provider": _provider_from_model(model) if isinstance(model, str) else None,
                    "permission_mode": permission_mode,
                }
            )
            _emit_jsonl(
                {
                    "type": "tool_call",
                    "schema_version": 1,
                    "run_id": run_id,
                    "event_id": 1,
                    "ts_ms": ended,
                    "thread_id": agent.thread_id,
                    "state_path": str(state_path),
                    "tools": getattr(agent.config, "enabled_tools", None),
                    "model": model,
                    "provider": _provider_from_model(model) if isinstance(model, str) else None,
                    "permission_mode": permission_mode,
                    "interrupt": payload["interrupt"],
                }
            )
            _emit_jsonl(
                {
                    "type": "result",
                    "schema_version": 1,
                    "run_id": run_id,
                    "event_id": 2,
                    "ts_ms": ended,
                    "thread_id": agent.thread_id,
                    "state_path": str(state_path),
                    "tools": getattr(agent.config, "enabled_tools", None),
                    "model": model,
                    "provider": _provider_from_model(model) if isinstance(model, str) else None,
                    "permission_mode": permission_mode,
                    "interrupted": True,
                    "stop_reason": "interrupt",
                    "output": None,
                    "stats": payload["stats"],
                }
            )
            return EXIT_INTERRUPT

        if args.output_format == "json":
            print(json.dumps(payload, indent=2))
        else:
            print(json.dumps(payload, indent=2), file=sys.stderr)
        return EXIT_INTERRUPT

    if args.output_format == "stream-json":
        _emit_jsonl(
            {
                "type": "init",
                "schema_version": 1,
                "run_id": run_id,
                "event_id": 0,
                "ts_ms": started,
                "thread_id": agent.thread_id,
                "state_path": str(state_path),
                "tools": getattr(agent.config, "enabled_tools", None),
                "model": model,
                "provider": _provider_from_model(model) if isinstance(model, str) else None,
                "permission_mode": permission_mode,
            }
        )
        _emit_jsonl(
            {
                "type": "message",
                "schema_version": 1,
                "run_id": run_id,
                "event_id": 1,
                "ts_ms": ended,
                "thread_id": agent.thread_id,
                "state_path": str(state_path),
                "tools": getattr(agent.config, "enabled_tools", None),
                "model": model,
                "provider": _provider_from_model(model) if isinstance(model, str) else None,
                "permission_mode": permission_mode,
                "role": "assistant",
                "content": result.output,
                "delta": result.output,
            }
        )
        _emit_jsonl(
            {
                "type": "result",
                "schema_version": 1,
                "run_id": run_id,
                "event_id": 2,
                "ts_ms": ended,
                "thread_id": agent.thread_id,
                "state_path": str(state_path),
                "tools": getattr(agent.config, "enabled_tools", None),
                "model": model,
                "provider": _provider_from_model(model) if isinstance(model, str) else None,
                "permission_mode": permission_mode,
                "output": result.output,
                "stats": {"duration_ms": max(0, ended - started)},
                "stop_reason": "end_turn",
            }
        )
        return EXIT_SUCCESS

    if args.output_format == "json":
        payload = {
            "type": "result",
            "run_id": run_id,
            "output": result.output,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "tools": getattr(agent.config, "enabled_tools", None),
            "messages": result.messages,
            "stats": {"duration_ms": max(0, ended - started)},
            "stop_reason": "end_turn",
        }
        print(json.dumps(payload, indent=2))
        return EXIT_SUCCESS

    print(result.output)
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
