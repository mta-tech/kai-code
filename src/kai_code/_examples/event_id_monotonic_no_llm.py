from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kai_code.cli import _stream_json_run


@dataclass
class DummyConfig:
    state_path: Path | None


class DummyAgent:
    def __init__(self) -> None:
        self.thread_id = "t_dummy"
        self.config = DummyConfig(state_path=None)

    def stream(self, prompt: str):
        # Emit multiple events in a single run via snapshot-derived events.
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
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = _stream_json_run(
            agent=DummyAgent(),
            prompt="x",
            run_id="r1",
            permission_mode="bypassPermissions",
            model=None,
            include_traceback=False,
        )
    assert code == 0
    lines = [json.loads(l) for l in buf.getvalue().splitlines() if l.strip()]
    event_ids = [l["event_id"] for l in lines]
    assert len(event_ids) == len(set(event_ids)), "event_id must be unique"
    assert event_ids == sorted(event_ids), "event_id must be monotonic increasing"
    # Often we start at 0.
    assert event_ids[0] == 0
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

