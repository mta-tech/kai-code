from __future__ import annotations

import argparse
import json
import os
import sys
import time
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
    if getattr(args, "prompt_text", None):
        return args.prompt_text
    if getattr(args, "prompt_args", None):
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
    return (root_dir / ".kai" / "session.json").resolve()


def _resolve_state_path_for_resume(
    root_dir: Path,
    *,
    agent_name: str | None,
    explicit_state_path: str | None,
) -> Path:
    """Resolve state path for resume command (must exist)."""
    settings = load_settings(root_dir)

    if explicit_state_path:
        resolved = Path(explicit_state_path).expanduser().resolve()
        if not resolved.exists():
            raise SystemExit(f"Error: State file not found: {resolved}")
        return resolved

    if agent_name:
        agents = dict(settings.agents or {})
        rel = agents.get(agent_name)
        if rel:
            state_path = (root_dir / rel).resolve()
            if state_path.exists():
                return state_path
        raise SystemExit(f"Error: No session found for agent '{agent_name}'")

    # Default: use last session
    if settings.last_session:
        state_path = (root_dir / settings.last_session).resolve()
        if state_path.exists():
            return state_path

    global_last = load_global_last_session()
    if global_last:
        state_path = Path(global_last).expanduser().resolve()
        if state_path.exists():
            return state_path

    raise SystemExit("Error: No interrupted session found to resume. Specify --state-path or --agent.")


def _build_permissions(args: argparse.Namespace) -> PermissionConfig | None:
    allowed_tools = _parse_csv(getattr(args, "allowed_tools", None))
    disallowed_tools = _parse_csv(getattr(args, "disallowed_tools", None))
    allowed_commands = _parse_csv(getattr(args, "allowed_commands", None))
    disallowed_commands = _parse_csv(getattr(args, "disallowed_commands", None))

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


def _print_stream_json(
    agent: KaiAgent,
    prompt: str,
    *,
    run_id: str,
    permission_mode: str,
    model: str | None,
) -> int:
    started = now_ms()
    stats = RunStats(started_ms=started, ended_ms=started)
    init = {
        "type": "init",
        "run_id": run_id,
        "started_ms": started,
        "thread_id": agent.thread_id,
        "state_path": str(agent.config.state_path) if agent.config.state_path else None,
        "model": model,
        "permission_mode": permission_mode,
    }
    print(json.dumps(init))

    last_snapshot: dict[str, Any] | None = None
    interrupted = False

    for chunk in agent.stream(prompt):
        stats.chunk_count += 1
        event = {"type": "chunk", "run_id": run_id, "data": _safe_json(chunk)}
        print(json.dumps(event))

        if isinstance(chunk, dict) and isinstance(chunk.get("messages"), list):
            last_snapshot = chunk

        if isinstance(chunk, dict) and chunk.get("__interrupt__"):
            interrupted = True
            stats.interrupted = True
            interrupt_event = {
                "type": "interrupt",
                "run_id": run_id,
                "thread_id": agent.thread_id,
                "state_path": str(agent.config.state_path) if agent.config.state_path else None,
                "interrupt": _safe_json(chunk.get("__interrupt__")),
            }
            print(json.dumps(interrupt_event))
            break

    stats.ended_ms = now_ms()

    persisted = False
    output: str | None = None
    message_count: int | None = None
    if last_snapshot is not None:
        msgs = last_snapshot.get("messages")
        if isinstance(msgs, list) and msgs:
            message_count = len(msgs)
            last = msgs[-1]
            if isinstance(last, dict):
                output = last.get("content") if isinstance(last.get("content"), str) else None
            else:
                output = str(last)

    # Persistence is handled inside KaiAgent.stream() when possible.
    # If the agent updated its state during streaming, state_path should reflect it.
    if agent.config.state_path is not None and agent.config.state_path.exists():
        persisted = True

    result_event = {
        "type": "result",
        "run_id": run_id,
        "thread_id": agent.thread_id,
        "state_path": str(agent.config.state_path) if agent.config.state_path else None,
        "persisted": persisted,
        "interrupted": interrupted,
        "output": output,
        "stats": {
            "duration_ms": stats.duration_ms,
            "chunk_count": stats.chunk_count,
            "message_count": message_count,
        },
    }
    print(json.dumps(result_event))
    return 2 if interrupted else 0


def _parse_decisions(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Parse resume decisions from CLI arguments.

    Supports:
    - --approve: Approve the pending tool call
    - --reject: Reject the pending tool call
    - --edit <json>: Edit the pending tool call with custom arguments

    Returns a list of decision dicts following LangGraph HITL conventions.
    """
    approve = getattr(args, "approve", False)
    reject = getattr(args, "reject", False)
    edit_json = getattr(args, "edit", None)

    decision_count = sum([bool(approve), bool(reject), bool(edit_json)])
    if decision_count == 0:
        raise SystemExit(
            "Error: Must specify one of --approve, --reject, or --edit <json>.\n"
            "Examples:\n"
            "  kai resume --approve\n"
            "  kai resume --reject\n"
            '  kai resume --edit \'{"args": {"command": "echo hello"}}\''
        )
    if decision_count > 1:
        raise SystemExit("Error: Can only specify one of --approve, --reject, or --edit.")

    if approve:
        return [{"type": "approve"}]
    if reject:
        return [{"type": "reject"}]
    if edit_json:
        try:
            edit_data = json.loads(edit_json)
        except json.JSONDecodeError as e:
            raise SystemExit(f"Error: Invalid JSON for --edit: {e}")
        if not isinstance(edit_data, dict):
            raise SystemExit("Error: --edit JSON must be an object (dict)")
        return [{"type": "edit", "edited_action": edit_data}]

    # Should not reach here
    raise SystemExit("Error: No decision specified")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments shared between run and resume commands."""
    parser.add_argument("--root", help="Project root (defaults to cwd)")
    parser.add_argument("-a", "--agent", help="Named agent/session (maps to .kai/agents/<name>*.json)")
    parser.add_argument("--state-path", help="Explicit path to the session state JSON")
    parser.add_argument("-m", "--model", help="LangChain model handle (e.g. openai:gpt-4o)")
    parser.add_argument(
        "--toolset",
        choices=["codex", "default", "gemini"],
        help="Toolset-ish selection (affects default model if --model omitted)",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json", "stream-json"],
        default="text",
        help="Output format for headless mode",
    )
    parser.add_argument("--skills", default=".skills", help="Skills directory (default: .skills)")
    parser.add_argument("--system-prompt", help="Additional system prompt text")


def _cmd_run(args: argparse.Namespace) -> int:
    """Execute the 'run' subcommand (default behavior)."""
    root_dir = _resolve_root_dir(args.root)

    migrate_global_settings(root_dir)
    migrate_project_settings(root_dir)
    settings = load_settings(root_dir)

    state_path = _resolve_state_path(
        root_dir,
        agent_name=args.agent,
        explicit_state_path=args.state_path,
        force_new=bool(getattr(args, "new", False)),
        should_continue=bool(getattr(args, "continue_", False)),
    )

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
    yolo_flag = getattr(args, "yolo", None)
    permission_mode_arg = getattr(args, "permission_mode", None)

    if permission_mode_arg:
        permission_mode = permission_mode_arg
    elif yolo_flag is True:
        permission_mode = "bypassPermissions"
    elif yolo_flag is False:
        permission_mode = "default"
    elif settings.permission_mode:
        permission_mode = settings.permission_mode
    else:
        permission_mode = "bypassPermissions"

    mode_res = resolve_permission_mode(mode=permission_mode, base_permissions=permissions)

    # Only treat -p/--prompt specially; if user didn't pass -p but provided
    # positionals, we still accept them (matching letta headless behavior).
    prompt = _read_prompt(args)

    if getattr(args, "dry_run", False):
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
        }

        if args.output_format == "stream-json":
            run_id = uuid.uuid4().hex
            init = {
                "type": "init",
                "run_id": run_id,
                "thread_id": None,
                "state_path": str(state_path),
                "dry_run": True,
                "config": payload,
            }
            print(json.dumps(init))
            result = {
                "type": "result",
                "run_id": run_id,
                "dry_run": True,
                "output": None,
                "stats": {"duration_ms": 0, "chunk_count": 0},
            }
            print(json.dumps(result))
            return 0

        print(json.dumps(payload, indent=2))
        return 0

    provider = _provider_from_model(model)
    required_vars = _credentials_env_vars(provider)
    if required_vars and not _has_any_env(required_vars):
        hint = f"Missing credentials for provider '{provider}'. Set one of: {', '.join(required_vars)}."
        hint += " Or pass --model for a different provider."
        print(hint, file=sys.stderr)
        return 1

    agent = KaiAgent(
        root_dir=root_dir,
        model=model,
        yolo=bool(mode_res.yolo),
        interrupt_on=mode_res.interrupt_on,
        system_prompt=args.system_prompt,
        skills_dir=args.skills,
        state_path=state_path,
        permissions=mode_res.permissions,
    )

    if args.output_format == "stream-json":
        return _print_stream_json(
            agent,
            prompt,
            run_id=uuid.uuid4().hex,
            permission_mode=permission_mode,
            model=model if isinstance(model, str) else None,
        )

    run_id = uuid.uuid4().hex
    started = now_ms()
    result = agent.run(prompt)
    ended = now_ms()
    stats = {
        "duration_ms": max(0, ended - started),
        "started_ms": started,
        "ended_ms": ended,
        "permission_mode": permission_mode,
        "message_count": len(result.messages),
    }

    # Detect HITL interrupt (LangGraph convention)
    if isinstance(result.raw, dict) and result.raw.get("__interrupt__"):
        payload = {
            "type": "interrupt",
            "run_id": run_id,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "interrupt": _safe_json(result.raw.get("__interrupt__")),
            "stats": stats,
        }
        if args.output_format == "json":
            print(json.dumps(payload, indent=2))
        else:
            print(json.dumps(payload, indent=2), file=sys.stderr)
        return 2

    if args.output_format == "json":
        payload = {
            "type": "result",
            "run_id": run_id,
            "output": result.output,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "messages": result.messages,
            "stats": stats,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(result.output)
    return 0


def _cmd_resume(args: argparse.Namespace) -> int:
    """Execute the 'resume' subcommand to continue an interrupted run."""
    root_dir = _resolve_root_dir(args.root)

    migrate_global_settings(root_dir)
    migrate_project_settings(root_dir)
    settings = load_settings(root_dir)

    state_path = _resolve_state_path_for_resume(
        root_dir,
        agent_name=args.agent,
        explicit_state_path=args.state_path,
    )

    # Check for checkpoint file
    checkpoint_path = state_path.parent / "checkpoints.pkl"
    if not checkpoint_path.exists():
        raise SystemExit(
            f"Error: No checkpoint file found at {checkpoint_path}.\n"
            "This session may not have been interrupted, or checkpoints were not enabled.\n"
            "Checkpoints require running with --permission-mode default or acceptEdits (not bypassPermissions)."
        )

    # Parse the decision from CLI args
    decisions = _parse_decisions(args)

    # Model selection precedence (same as run)
    if args.model:
        model = args.model
    elif args.toolset:
        model = _toolset_to_default_model(args.toolset)
    elif settings.default_model:
        model = settings.default_model
    else:
        model = _toolset_to_default_model(settings.default_toolset)

    # Permissions (same as run)
    permissions = _build_permissions(args)
    if permissions is None:
        permissions = _build_permissions_from_settings(settings)

    # For resume, we need yolo=False to use the checkpointer
    mode_res = resolve_permission_mode(mode="default", base_permissions=permissions)

    # Handle --dry-run before credential check
    if getattr(args, "dry_run", False):
        payload = {
            "type": "dry-run",
            "command": "resume",
            "root_dir": str(root_dir),
            "state_path": str(state_path),
            "checkpoint_path": str(checkpoint_path),
            "agent": args.agent,
            "model": model,
            "decision": decisions[0]["type"] if decisions else None,
            "skills": args.skills,
            "permissions": _safe_json(permissions) if permissions else None,
        }

        if args.output_format == "stream-json":
            run_id = uuid.uuid4().hex
            init = {
                "type": "init",
                "run_id": run_id,
                "state_path": str(state_path),
                "dry_run": True,
                "config": payload,
            }
            print(json.dumps(init))
            result = {
                "type": "result",
                "run_id": run_id,
                "dry_run": True,
                "output": None,
                "stats": {"duration_ms": 0},
            }
            print(json.dumps(result))
            return 0

        print(json.dumps(payload, indent=2))
        return 0

    provider = _provider_from_model(model)
    required_vars = _credentials_env_vars(provider)
    if required_vars and not _has_any_env(required_vars):
        hint = f"Missing credentials for provider '{provider}'. Set one of: {', '.join(required_vars)}."
        hint += " Or pass --model for a different provider."
        print(hint, file=sys.stderr)
        return 1

    agent = KaiAgent(
        root_dir=root_dir,
        model=model,
        yolo=False,  # Must be False to use checkpoints
        interrupt_on=mode_res.interrupt_on,
        system_prompt=args.system_prompt,
        skills_dir=args.skills,
        state_path=state_path,
        permissions=mode_res.permissions,
    )

    run_id = uuid.uuid4().hex
    started = now_ms()

    if args.output_format == "stream-json":
        init = {
            "type": "init",
            "run_id": run_id,
            "started_ms": started,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "model": model if isinstance(model, str) else None,
            "resume_decision": decisions[0]["type"] if decisions else None,
        }
        print(json.dumps(init))

    result = agent.resume(decisions)
    ended = now_ms()

    stats = {
        "duration_ms": max(0, ended - started),
        "started_ms": started,
        "ended_ms": ended,
        "message_count": len(result.messages),
        "resumed": True,
        "decision": decisions[0]["type"] if decisions else None,
    }

    # Check if we hit another interrupt
    if isinstance(result.raw, dict) and result.raw.get("__interrupt__"):
        payload = {
            "type": "interrupt",
            "run_id": run_id,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "interrupt": _safe_json(result.raw.get("__interrupt__")),
            "stats": stats,
        }
        if args.output_format == "json":
            print(json.dumps(payload, indent=2))
        elif args.output_format == "stream-json":
            interrupt_event = {
                "type": "interrupt",
                "run_id": run_id,
                "thread_id": agent.thread_id,
                "state_path": str(state_path),
                "interrupt": _safe_json(result.raw.get("__interrupt__")),
            }
            print(json.dumps(interrupt_event))
            result_event = {
                "type": "result",
                "run_id": run_id,
                "thread_id": agent.thread_id,
                "state_path": str(state_path),
                "interrupted": True,
                "output": result.output,
                "stats": stats,
            }
            print(json.dumps(result_event))
        else:
            print(json.dumps(payload, indent=2), file=sys.stderr)
        return 2

    if args.output_format == "json":
        payload = {
            "type": "result",
            "run_id": run_id,
            "output": result.output,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "messages": result.messages,
            "stats": stats,
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.output_format == "stream-json":
        result_event = {
            "type": "result",
            "run_id": run_id,
            "thread_id": agent.thread_id,
            "state_path": str(state_path),
            "interrupted": False,
            "output": result.output,
            "stats": stats,
        }
        print(json.dumps(result_event))
        return 0

    print(result.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kai",
        description="Kai Code: deepagents-based coding agent (letta-code-inspired).",
    )

    try:
        version = metadata.version("kai-code")
    except Exception:
        version = "0.0.0"
    parser.add_argument("--version", action="version", version=f"{version} (Kai Code)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- 'run' subcommand (default behavior) ---
    run_parser = subparsers.add_parser(
        "run",
        help="Run the agent with a prompt",
        description="Run the agent with a prompt. This is the default command.",
    )
    _add_common_args(run_parser)
    run_parser.add_argument("--new", action="store_true", help="Start a new session")
    run_parser.add_argument("-c", "--continue", dest="continue_", action="store_true", help="Resume last session")
    run_parser.add_argument(
        "--permission-mode",
        choices=list(VALID_PERMISSION_MODES),
        help="Permission mode: default, acceptEdits, plan, bypassPermissions",
    )
    run_parser.add_argument(
        "--yolo",
        dest="yolo",
        action="store_true",
        default=None,
        help="Alias for --permission-mode bypassPermissions",
    )
    run_parser.add_argument(
        "--no-yolo",
        dest="yolo",
        action="store_false",
        default=None,
        help="Alias for --permission-mode default",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved config/state path and exit (no model call)",
    )
    run_parser.add_argument("--allowed-tools", help="Comma-separated fnmatch patterns")
    run_parser.add_argument("--disallowed-tools", help="Comma-separated fnmatch patterns")
    run_parser.add_argument("--allowed-commands", help="Comma-separated fnmatch patterns")
    run_parser.add_argument("--disallowed-commands", help="Comma-separated fnmatch patterns")
    run_parser.add_argument("-p", "--prompt", dest="prompt_text", nargs="?", help="Prompt text (or omit to read stdin)")
    run_parser.add_argument("--run", action="store_true", help=argparse.SUPPRESS)
    run_parser.add_argument("prompt_args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    run_parser.set_defaults(func=_cmd_run)

    # --- 'resume' subcommand ---
    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume an interrupted run with a decision (approve/reject/edit)",
        description=(
            "Resume an interrupted agent run. Use this after the agent exits with code 2.\n\n"
            "The agent must have been run with HITL mode enabled (--permission-mode default or acceptEdits)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  kai resume --approve                    # Approve the pending tool call\n"
            "  kai resume --reject                     # Reject and skip the pending tool call\n"
            '  kai resume --edit \'{"args": ...}\'       # Edit the tool call arguments\n'
            "  kai resume --approve --agent myagent    # Resume a specific named agent\n"
            "  kai resume --approve --state-path .kai/session.json\n"
        ),
    )
    _add_common_args(resume_parser)

    # Decision flags (mutually exclusive - one is required)
    decision_group = resume_parser.add_mutually_exclusive_group(required=True)
    decision_group.add_argument(
        "--approve",
        action="store_true",
        help="Approve the pending tool call and continue execution",
    )
    decision_group.add_argument(
        "--reject",
        action="store_true",
        help="Reject the pending tool call and skip it",
    )
    decision_group.add_argument(
        "--edit",
        metavar="JSON",
        help='Edit the tool call with modified arguments (JSON object, e.g. \'{"args": {"command": "ls"}}\')',
    )
    resume_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved config and exit without calling the model",
    )
    resume_parser.set_defaults(func=_cmd_resume)

    # Handle backwards compatibility BEFORE parsing
    # If first arg doesn't look like a known subcommand or flag, prepend 'run'
    if argv is None:
        argv = sys.argv[1:]

    known_subcommands = {"run", "resume"}
    known_global_flags = {"-h", "--help", "--version"}

    if argv:
        first_arg = argv[0]
        # If first arg is not a known subcommand or global flag, treat as 'run' invocation
        if first_arg not in known_subcommands and first_arg not in known_global_flags:
            argv = ["run"] + list(argv)
    else:
        # No args at all - default to 'run' (will prompt for input or read stdin)
        argv = ["run"]

    args = parser.parse_args(argv)

    # Execute the appropriate command
    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
