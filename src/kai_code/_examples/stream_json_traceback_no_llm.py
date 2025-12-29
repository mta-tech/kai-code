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
        raise RuntimeError("boom")


def main() -> int:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = _stream_json_run(
            agent=DummyAgent(),
            prompt="x",
            run_id="r1",
            permission_mode="bypassPermissions",
            model="openai:gpt-4o",
            include_traceback=True,
        )
    assert code == 1
    lines = [json.loads(l) for l in buf.getvalue().splitlines() if l.strip()]
    assert lines[0]["type"] == "init"
    err = [l for l in lines if l["type"] == "error"][0]
    assert err["error_type"] == "RuntimeError"
    assert "traceback" in err
    assert err["stop_reason"] == "error"
    assert err["model"] == "openai:gpt-4o"
    assert err["provider"] == "openai"
    assert err["permission_mode"] == "bypassPermissions"
    assert "stats" in err
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
