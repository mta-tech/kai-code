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
from kai_code.agent import KaiResult


@dataclass
class DummyConfig:
    state_path: Path | None


class InterruptAgent:
    def __init__(self, *args, **kwargs) -> None:
        self.thread_id = "t_interrupt"
        self.config = DummyConfig(state_path=kwargs.get("state_path"))

    def run(self, prompt: str):
        return KaiResult(output="", messages=[], raw={"__interrupt__": [{"tool": "execute"}]})

    def stream(self, prompt: str):
        yield {"__interrupt__": [{"tool": "execute"}]}


def main() -> int:
    old_env = cli._credentials_env_vars
    old_agent = cli.KaiAgent
    cli._credentials_env_vars = lambda provider: []
    cli.KaiAgent = InterruptAgent  # type: ignore[assignment]
    try:
        # dry-run => 0
        code0 = cli.main(["--dry-run", "--output-format", "json", "-p", "hi"])
        assert code0 == 0

        # interrupt (non-stream json) => 2 and stop_reason interrupt
        buf = io.StringIO()
        with redirect_stdout(buf):
            code2 = cli.main(["--output-format", "json", "-p", "hi"])
        assert code2 == 2
        payload = json.loads(buf.getvalue())
        assert payload["type"] == "interrupt"
        assert payload["stop_reason"] == "interrupt"

        # interrupt (stream-json) => 2 (we'll run direct stream mode)
        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            code2s = cli.main(["--output-format", "stream-json", "-p", "hi"])
        assert code2s == 2

        print("ok")
        return 0
    finally:
        cli._credentials_env_vars = old_env
        cli.KaiAgent = old_agent  # type: ignore[assignment]


if __name__ == "__main__":
    raise SystemExit(main())

