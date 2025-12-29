from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from typing import Any


def _safe_json(obj: Any) -> Any:
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


@dataclass
class ToolEvent:
    kind: str  # "tool_call" | "tool_result"
    tool_name: str | None
    tool_call_id: str | None
    args: Any | None
    content: str | None
    raw: Any
    msg_index: int | None = None
    part_index: int | None = None


def extract_tool_result_fields(event: ToolEvent) -> dict[str, Any]:
    """Best-effort structured extraction from a tool result raw payload.

    Returns additive fields such as stdout/stderr/exit_code/status/command.
    Does not remove existing content/raw.
    """
    raw = event.raw
    if not isinstance(raw, dict):
        return {}

    out: dict[str, Any] = {}

    # Common patterns (letta-style and general tool wrappers)
    status = raw.get("status")
    if isinstance(status, str):
        out["status"] = status

    exit_code = _get_any(raw, "exit_code", "code")
    if isinstance(exit_code, int):
        out["exit_code"] = exit_code

    command = _get_any(raw, "command", "cmd")
    if isinstance(command, str):
        out["command"] = command

    stdout = raw.get("stdout")
    if isinstance(stdout, str):
        out["stdout"] = stdout
    elif isinstance(stdout, list):
        out["stdout"] = "".join(str(x) for x in stdout)

    stderr = raw.get("stderr")
    if isinstance(stderr, str):
        out["stderr"] = stderr
    elif isinstance(stderr, list):
        out["stderr"] = "".join(str(x) for x in stderr)

    # Some tool wrappers embed under toolReturn/tool_return
    tr = _get_any(raw, "toolReturn", "tool_return")
    if isinstance(tr, dict):
        if "stdout" not in out and isinstance(tr.get("stdout"), str):
            out["stdout"] = tr["stdout"]
        if "stderr" not in out and isinstance(tr.get("stderr"), str):
            out["stderr"] = tr["stderr"]
        if "status" not in out and isinstance(tr.get("status"), str):
            out["status"] = tr["status"]

    # Google function_response nests fields under response
    resp = raw.get("response")
    if isinstance(resp, dict):
        if "stdout" not in out:
            stdout2 = resp.get("stdout")
            if isinstance(stdout2, str):
                out["stdout"] = stdout2
            elif isinstance(stdout2, list):
                out["stdout"] = "".join(str(x) for x in stdout2)
        if "stderr" not in out:
            stderr2 = resp.get("stderr")
            if isinstance(stderr2, str):
                out["stderr"] = stderr2
            elif isinstance(stderr2, list):
                out["stderr"] = "".join(str(x) for x in stderr2)
        if "exit_code" not in out and isinstance(resp.get("exit_code"), int):
            out["exit_code"] = resp["exit_code"]
        if "status" not in out and isinstance(resp.get("status"), str):
            out["status"] = resp["status"]
        if "command" not in out and isinstance(resp.get("command"), str):
            out["command"] = resp["command"]

    return out


def _maybe_json(s: Any) -> Any:
    if not isinstance(s, str):
        return None
    t = s.strip()
    if not t or (not t.startswith("{") and not t.startswith("[")):
        return None
    try:
        return json.loads(t)
    except Exception:
        return None


def _get_any(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d:
            return d.get(k)
    return None


def _stable_hash(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        payload = str(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def synthesize_tool_call_id(event: ToolEvent, *, turn_id: int | None, step_id: int | None) -> str | None:
    """Return a stable tool_call_id.

    Some providers omit tool call ids. We synthesize a deterministic id based on:
    - grouping (turn_id/step_id)
    - message/part index within the snapshot
    - tool_name + args/content (hashed)
    """
    if event.tool_call_id:
        return event.tool_call_id

    msg_index = event.msg_index
    part_index = event.part_index

    # If we don't have stable indices, fall back to hashing tool_name+args/content.
    payload = {
        "kind": event.kind,
        "tool_name": event.tool_name,
        "args": event.args,
        "content": event.content,
    }
    h = _stable_hash(payload)
    return f"kai_{turn_id}_{step_id}_{msg_index}_{part_index}_{h}"


def correlate_tool_events(events: list[ToolEvent], *, turn_id: int | None, step_id: int | None) -> list[ToolEvent]:
    """Assign stable tool_call_id values and correlate tool_result -> tool_call.

    For providers that omit ids (common with Anthropic/Google shapes), we:
    - synthesize ids for tool_call events
    - assign missing tool_result ids to the most recent unmatched tool_call

    This is done within the *snapshot order* so repeated snapshots yield the
    same correlation.
    """
    unmatched: list[str] = []
    out: list[ToolEvent] = []
    for e in events:
        if e.kind == "tool_call":
            tc_id = synthesize_tool_call_id(e, turn_id=turn_id, step_id=step_id)
            out.append(
                ToolEvent(
                    kind=e.kind,
                    tool_name=e.tool_name,
                    tool_call_id=tc_id,
                    args=e.args,
                    content=e.content,
                    raw=e.raw,
                    msg_index=e.msg_index,
                    part_index=e.part_index,
                )
            )
            if tc_id:
                unmatched.append(tc_id)
            continue

        if e.kind == "tool_result":
            tr_id = e.tool_call_id
            # If the tool result already includes an id, treat it as completing
            # that pending call so later id-less results don't get misassigned.
            if tr_id is not None and unmatched:
                for i in range(len(unmatched) - 1, -1, -1):
                    if unmatched[i] == tr_id:
                        unmatched.pop(i)
                        break
            if tr_id is None and unmatched:
                tr_id = unmatched.pop()
            if tr_id is None:
                tr_id = synthesize_tool_call_id(e, turn_id=turn_id, step_id=step_id)

            out.append(
                ToolEvent(
                    kind=e.kind,
                    tool_name=e.tool_name,
                    tool_call_id=tr_id,
                    args=e.args,
                    content=e.content,
                    raw=e.raw,
                    msg_index=e.msg_index,
                    part_index=e.part_index,
                )
            )
            continue

        out.append(e)
    return out


def _detect_tool_events_from_message(msg: Any, *, msg_index: int | None) -> list[ToolEvent]:
    """Extract tool_call/tool_result events from a LangChain-style message.

    deepagents/LangGraph may surface tools via:
    - message.additional_kwargs.tool_calls (OpenAI-style)
    - message.tool_calls / message.tool_call_chunks
    - ToolMessage-like dicts with tool_call_id
    - message.content containing JSON

    This is best-effort and designed to be safe: if unknown, return [].
    """
    if msg is None:
        return []
    if not isinstance(msg, dict):
        # Try model_dump-like
        if hasattr(msg, "model_dump"):
            try:
                msg = msg.model_dump()
            except Exception:
                return []
        elif hasattr(msg, "dict"):
            try:
                msg = msg.dict()
            except Exception:
                return []
        else:
            return []
    if not isinstance(msg, dict):
        return []

    role = msg.get("role") or msg.get("type")
    content = msg.get("content") if isinstance(msg.get("content"), str) else None

    events: list[ToolEvent] = []

    # Tool calls embedded in assistant message
    tool_calls = None
    if isinstance(msg.get("tool_calls"), list):
        tool_calls = msg.get("tool_calls")
    else:
        ak = msg.get("additional_kwargs")
        if isinstance(ak, dict) and isinstance(ak.get("tool_calls"), list):
            tool_calls = ak.get("tool_calls")

    # Google/others: single function_call shape (best-effort)
    if tool_calls is None:
        ak = msg.get("additional_kwargs")
        if isinstance(ak, dict) and isinstance(ak.get("function_call"), dict):
            tool_calls = [{"id": None, "function": ak.get("function_call")}]

    if tool_calls:
        for i, tc in enumerate(tool_calls):
            if not isinstance(tc, dict):
                continue
            tc_id = tc.get("id") if isinstance(tc.get("id"), str) else None
            name = None
            args = None
            fn = tc.get("function")
            if isinstance(fn, dict):
                name = fn.get("name") if isinstance(fn.get("name"), str) else None
                args_raw = fn.get("arguments")
                args = _maybe_json(args_raw) if args_raw is not None else None
                if args is None:
                    args = args_raw
            events.append(
                ToolEvent(
                    kind="tool_call",
                    tool_name=name,
                    tool_call_id=tc_id,
                    args=args,
                    content=None,
                    raw=_safe_json(tc),
                    msg_index=msg_index,
                    part_index=i,
                )
            )

    # Anthropic/Google: content blocks/parts (best-effort)
    content_val = msg.get("content")
    if isinstance(content_val, list):
        for part_i, part in enumerate(content_val):
            if not isinstance(part, dict):
                continue
            ptype = part.get("type")

            # Anthropic tool_use
            if ptype in ("tool_use", "tool-use"):
                tc_id = _get_any(part, "id", "tool_use_id")
                name = _get_any(part, "name")
                args = _get_any(part, "input")
                events.append(
                    ToolEvent(
                        kind="tool_call",
                        tool_name=name if isinstance(name, str) else None,
                        tool_call_id=tc_id if isinstance(tc_id, str) else None,
                        args=args,
                        content=None,
                        raw=_safe_json(part),
                        msg_index=msg_index,
                        part_index=part_i,
                    )
                )

            # Google function_call parts
            fc = part.get("function_call") if isinstance(part.get("function_call"), dict) else None
            if ptype == "function_call" and isinstance(part.get("name"), str):
                fc = part
            if isinstance(fc, dict) and isinstance(_get_any(fc, "name"), str):
                name = _get_any(fc, "name")
                args = _get_any(fc, "arguments", "args")
                if isinstance(args, str):
                    parsed = _maybe_json(args)
                    args = parsed if parsed is not None else args
                events.append(
                    ToolEvent(
                        kind="tool_call",
                        tool_name=name if isinstance(name, str) else None,
                        tool_call_id=None,
                        args=args,
                        content=None,
                        raw=_safe_json(part),
                        msg_index=msg_index,
                        part_index=part_i,
                    )
                )

            # Anthropic tool_result
            if ptype in ("tool_result", "tool-result"):
                tc_id = _get_any(part, "tool_use_id", "tool_call_id", "id")
                tcontent = _get_any(part, "content")
                if isinstance(tcontent, list):
                    tcontent = "".join(
                        x.get("text", "") if isinstance(x, dict) else str(x) for x in tcontent
                    )
                events.append(
                    ToolEvent(
                        kind="tool_result",
                        tool_name=None,
                        tool_call_id=tc_id if isinstance(tc_id, str) else None,
                        args=None,
                        content=tcontent if isinstance(tcontent, str) else (None if tcontent is None else str(tcontent)),
                        raw=_safe_json(part),
                        msg_index=msg_index,
                        part_index=part_i,
                    )
                )

            # Google function_response part (best-effort tool result)
            if ptype == "function_response":
                name = _get_any(part, "name")
                resp = _get_any(part, "response")
                events.append(
                    ToolEvent(
                        kind="tool_result",
                        tool_name=name if isinstance(name, str) else None,
                        tool_call_id=None,
                        args=None,
                        content=_safe_json(resp) if resp is not None else None,
                        raw=_safe_json(part),
                        msg_index=msg_index,
                        part_index=part_i,
                    )
                )

    # Tool result messages
    if role in ("tool", "tool_result") or msg.get("tool_call_id"):
        tc_id = msg.get("tool_call_id") if isinstance(msg.get("tool_call_id"), str) else None
        name = msg.get("name") if isinstance(msg.get("name"), str) else None
        events.append(
            ToolEvent(
                kind="tool_result",
                tool_name=name,
                tool_call_id=tc_id,
                args=None,
                content=content,
                raw=_safe_json(msg),
                msg_index=msg_index,
                part_index=None,
            )
        )

    return events


def detect_tool_events_from_message(msg: Any) -> list[ToolEvent]:
    return _detect_tool_events_from_message(msg, msg_index=None)


def detect_tool_events_from_messages(messages: Any) -> list[ToolEvent]:
    """Scan a whole messages list and extract tool events in order."""
    if not isinstance(messages, list):
        return []
    out: list[ToolEvent] = []
    for i, m in enumerate(messages):
        out.extend(_detect_tool_events_from_message(m, msg_index=i))
    return out


@dataclass
class UsageStats:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None


def _coerce_int(v: Any) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().isdigit():
        try:
            return int(v.strip())
        except Exception:
            return None
    return None


def extract_usage_and_stop_reason(message: Any) -> tuple[UsageStats, str | None]:
    """Best-effort token usage + stop_reason from a LangChain message dict/object."""
    if message is None:
        return UsageStats(), None
    if not isinstance(message, dict):
        if hasattr(message, "model_dump"):
            try:
                message = message.model_dump()
            except Exception:
                return UsageStats(), None
        elif hasattr(message, "dict"):
            try:
                message = message.dict()
            except Exception:
                return UsageStats(), None
        else:
            return UsageStats(), None
    if not isinstance(message, dict):
        return UsageStats(), None

    stop_reason = None
    rm = message.get("response_metadata")
    if isinstance(rm, dict):
        sr = rm.get("stop_reason") or rm.get("finish_reason")
        if isinstance(sr, str) and sr:
            stop_reason = sr

    usage = message.get("usage_metadata")
    stats = UsageStats()
    if isinstance(usage, dict):
        # LangChain often uses input/output/total naming.
        stats.prompt_tokens = _coerce_int(usage.get("input_tokens") or usage.get("prompt_tokens"))
        stats.completion_tokens = _coerce_int(usage.get("output_tokens") or usage.get("completion_tokens"))
        stats.total_tokens = _coerce_int(usage.get("total_tokens"))

        stats.cached_input_tokens = _coerce_int(
            usage.get("cache_read_input_tokens")
            or usage.get("cached_input_tokens")
            or usage.get("input_tokens_cached")
        )
        stats.reasoning_tokens = _coerce_int(usage.get("reasoning_tokens"))

    # Fallback: provider-specific usage in response_metadata
    if isinstance(rm, dict):
        u = rm.get("usage")
        if isinstance(u, dict):
            if stats.prompt_tokens is None:
                stats.prompt_tokens = _coerce_int(_get_any(u, "input_tokens", "prompt_tokens"))
            if stats.completion_tokens is None:
                stats.completion_tokens = _coerce_int(_get_any(u, "output_tokens", "completion_tokens"))
            if stats.total_tokens is None:
                stats.total_tokens = _coerce_int(_get_any(u, "total_tokens"))
        tu = rm.get("token_usage")
        if isinstance(tu, dict):
            if stats.prompt_tokens is None:
                stats.prompt_tokens = _coerce_int(_get_any(tu, "prompt_tokens", "input_tokens"))
            if stats.completion_tokens is None:
                stats.completion_tokens = _coerce_int(_get_any(tu, "completion_tokens", "output_tokens"))
            if stats.total_tokens is None:
                stats.total_tokens = _coerce_int(_get_any(tu, "total_tokens"))

    return stats, stop_reason


def aggregate_usage(messages: Any) -> UsageStats:
    """Aggregate token usage across all assistant messages (best-effort)."""
    if not isinstance(messages, list):
        return UsageStats()
    total = UsageStats()

    def _add(field: str, v: int | None) -> None:
        if v is None:
            return
        cur = getattr(total, field)
        setattr(total, field, v if cur is None else cur + v)

    for m in messages:
        u, _ = extract_usage_and_stop_reason(m)
        _add("prompt_tokens", u.prompt_tokens)
        _add("completion_tokens", u.completion_tokens)
        _add("total_tokens", u.total_tokens)
        _add("cached_input_tokens", u.cached_input_tokens)
        _add("reasoning_tokens", u.reasoning_tokens)
    return total


def last_stop_reason(messages: Any) -> str | None:
    """Return the last non-empty stop_reason observed (best-effort)."""
    if not isinstance(messages, list):
        return None
    for m in reversed(messages):
        _, sr = extract_usage_and_stop_reason(m)
        if sr:
            return sr
    return None


def count_turns_steps(messages: Any) -> tuple[int | None, int | None]:
    """Best-effort counters based on message roles.

    - turns: number of user messages
    - steps: number of assistant messages
    """
    if not isinstance(messages, list):
        return None, None
    turns = 0
    steps = 0
    for m in messages:
        if not isinstance(m, dict):
            if hasattr(m, "model_dump"):
                try:
                    m = m.model_dump()
                except Exception:
                    continue
            elif hasattr(m, "dict"):
                try:
                    m = m.dict()
                except Exception:
                    continue
            else:
                continue
        if not isinstance(m, dict):
            continue
        role = m.get("role") or m.get("type")
        if role in ("user", "human"):
            turns += 1
        if role in ("assistant", "ai"):
            steps += 1
    return turns, steps
