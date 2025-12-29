from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import kai_code.cli as cli


@dataclass
class DummyConfig:
    state_path: Path | None


class DummyAgent:
    def __init__(self) -> None:
        self.thread_id = "t_dummy"
        self.config = DummyConfig(state_path=None)

    def stream(self, prompt: str):
        # First snapshot: tool call appears (no id) then later tool result appears.
        yield {
            "messages": [
                {"role": "user", "content": "hi"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "function_call", "name": "execute", "arguments": '{"command":"pwd"}'},
                    ],
                },
            ]
        }
        yield {
            "messages": [
                {"role": "user", "content": "hi"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "function_call", "name": "execute", "arguments": '{"command":"pwd"}'},
                        {"type": "function_response", "name": "execute", "response": {"stdout": "/tmp\n"}},
                    ],
                },
            ]
        }


def main() -> int:
    # Force deterministic clock.
    times = [1000, 1100, 1200, 1300, 1400]

    def fake_now_ms() -> int:
        return times.pop(0) if times else 1400

    old_now = cli.now_ms
    cli.now_ms = fake_now_ms  # type: ignore[assignment]
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli._stream_json_run(
                agent=DummyAgent(),
                prompt="x",
                run_id="r1",
                permission_mode="bypassPermissions",
                model=None,
                include_traceback=False,
            )
        assert code == 0
        lines = [json.loads(l) for l in buf.getvalue().splitlines() if l.strip()]
        tool_results = [l for l in lines if l.get("type") == "tool_result"]
        assert tool_results, "expected a tool_result event"
        assert "tool_latency_ms" in tool_results[-1]
        assert tool_results[-1]["tool_latency_ms"] is not None

        result = [l for l in lines if l.get("type") == "result"][-1]
        stats = result["stats"]
        assert "tool_latency_ms_total" in stats
        assert "tool_latency_ms_avg" in stats
        assert "tool_latency_ms_max" in stats
        assert "tool_count" in stats

        print("ok")
        return 0
    finally:
        cli.now_ms = old_now  # type: ignore[assignment]


if __name__ == "__main__":
    raise SystemExit(main())

