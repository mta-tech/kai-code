from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _write_session(path: Path, *, enabled_tools: list[str] | None) -> None:
    payload = {
        "messages": [],
        "thread_id": "t-test",
        "model": None,
        "system_prompt": None,
        "skills_dir": ".skills",
        "enabled_tools": enabled_tools,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["src", env.get("PYTHONPATH", "")]).strip(os.pathsep)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state_path = root / ".kai" / "session.json"
        _write_session(state_path, enabled_tools=["ls", "read_file"])

        # Omitted --tools: should reflect persisted enabled_tools.
        out = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "kai_code",
                "resume",
                "--dry-run",
                "--output-format",
                "json",
                "--state-path",
                str(state_path),
                "--approve",
            ],
            text=True,
            env=env,
        )
        payload = json.loads(out)
        assert payload.get("command") == "resume"
        assert payload.get("tools") == ["ls", "read_file"]

        # Explicit --tools: should override persisted enabled_tools.
        out2 = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "kai_code",
                "resume",
                "--dry-run",
                "--output-format",
                "json",
                "--state-path",
                str(state_path),
                "--approve",
                "--tools",
                "execute",
            ],
            text=True,
            env=env,
        )
        payload2 = json.loads(out2)
        assert payload2.get("tools") == ["execute"]

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

