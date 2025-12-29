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
        # A tool_result-like chunk shape that our correlator sees via raw chunk keys.
        yield {
            "messages": [
                {"role": "user", "content": "hi"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "function_call", "name": "execute", "arguments": '{"command":"echo hi"}'},
                        {
                            "type": "function_response",
                            "name": "execute",
                            "response": {
                                "stdout": ["hi\n"],
                                "stderr": "",
                                "exit_code": 0,
                                "status": "success",
                                "command": "echo hi",
                            },
                        },
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
    tool_results = [l for l in lines if l.get("type") == "tool_result"]
    assert tool_results
    tr = tool_results[-1]
    # Extracted fields
    assert tr.get("stdout") is not None
    assert tr.get("stderr") is not None
    assert tr.get("exit_code") == 0
    assert tr.get("status") == "success"
    assert tr.get("command") == "echo hi"
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

