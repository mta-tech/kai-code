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


class BoomAgent:
    def __init__(self, *args, **kwargs) -> None:
        self.thread_id = "t_boom"
        self.config = DummyConfig(state_path=kwargs.get("state_path"))

    def run(self, prompt: str):
        raise RuntimeError("boom")

    def resume(self, decisions):
        raise ValueError("resume boom")


def main() -> int:
    # Patch CLI to avoid credential checks and to use our failing agent.
    old_env = cli._credentials_env_vars
    old_agent = cli.KaiAgent
    cli._credentials_env_vars = lambda provider: []
    cli.KaiAgent = BoomAgent  # type: ignore[assignment]
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["--output-format", "json", "-p", "hi", "--include-traceback"])
        assert code == 1
        payload = json.loads(buf.getvalue())
        assert payload["type"] == "error"
        assert payload["stop_reason"] == "error"
        assert payload["error_type"] == "RuntimeError"
        assert "traceback" in payload
        assert "stats" in payload

        # Metadata fields exist (may be null in this forced no-LLM path).
        for k in ("run_id", "command", "model", "provider", "permission_mode", "thread_id", "state_path"):
            assert k in payload

        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            code2 = cli.main(
                [
                    "resume",
                    "--approve",
                    "--output-format",
                    "json",
                    "--state-path",
                    str(Path(".kai") / "session.json"),
                    "--model",
                    "openai:gpt-4o",
                ]
            )
        assert code2 == 1
        payload2 = json.loads(buf2.getvalue())
        assert payload2["type"] == "error"
        assert payload2["command"] == "resume"
        assert payload2["error_type"] == "ValueError"

        print("ok")
        return 0
    finally:
        cli._credentials_env_vars = old_env
        cli.KaiAgent = old_agent  # type: ignore[assignment]


if __name__ == "__main__":
    raise SystemExit(main())
