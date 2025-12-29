from __future__ import annotations

import json
import os
import subprocess
import sys


def _parse_jsonl(text: str) -> list[dict]:
    return [json.loads(line) for line in text.strip().splitlines() if line.strip()]


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["src", env.get("PYTHONPATH", "")]).strip(os.pathsep)

    tools = "ls,read_file"

    # Run dry-run JSON should include tools.
    out = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "kai_code",
            "--dry-run",
            "--output-format",
            "json",
            "--tools",
            tools,
            "-p",
            "hi",
        ],
        text=True,
        env=env,
    )
    payload = json.loads(out)
    assert payload["type"] == "dry-run"
    assert payload.get("tools") == ["ls", "read_file"]

    # Run dry-run stream-json init/result should include tools.
    out2 = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "kai_code",
            "--dry-run",
            "--output-format",
            "stream-json",
            "--tools",
            tools,
            "-p",
            "hi",
        ],
        text=True,
        env=env,
    )
    lines = _parse_jsonl(out2)
    assert lines[0]["type"] == "init"
    assert lines[0].get("tools") == ["ls", "read_file"]
    assert lines[-1]["type"] == "result"
    assert lines[-1].get("tools") == ["ls", "read_file"]

    # Resume dry-run stream-json should include tools as well.
    out3 = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "kai_code",
            "resume",
            "--approve",
            "--dry-run",
            "--output-format",
            "stream-json",
            "--tools",
            "execute",
        ],
        text=True,
        env=env,
    )
    lines2 = _parse_jsonl(out3)
    assert lines2[0]["type"] == "init"
    assert lines2[0].get("config", {}).get("tools") == ["execute"]
    assert lines2[-1]["type"] == "result"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

