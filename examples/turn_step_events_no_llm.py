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
        # Snapshot 1: user turn appears
        yield {"messages": [{"role": "user", "content": "hi"}]}
        # Snapshot 2: assistant step appears
        yield {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "ok"},
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
    types = [l["type"] for l in lines]
    assert types[0] == "init"
    assert types[-1] == "result"

    # Lifecycle events are present and ordered before result.
    assert "turn_start" in types
    assert "turn_end" in types
    assert "step_start" in types
    assert "step_end" in types

    ts = [i for i, t in enumerate(types) if t == "turn_start"][0]
    te = [i for i, t in enumerate(types) if t == "turn_end"][0]
    ss = [i for i, t in enumerate(types) if t == "step_start"][0]
    se = [i for i, t in enumerate(types) if t == "step_end"][0]
    ri = len(types) - 1
    assert ts < te < ri
    assert ss < se < ri

    # IDs are consistent.
    turn_start = lines[ts]
    assert turn_start["turn_id"] == 0
    step_start = lines[ss]
    assert step_start["turn_id"] == 0
    assert step_start["step_id"] == 0

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

