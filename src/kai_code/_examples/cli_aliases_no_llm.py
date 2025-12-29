from __future__ import annotations

import json
import os
import subprocess
import sys


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["src", env.get("PYTHONPATH", "")]).strip(os.pathsep)

    # CamelCase permission aliases
    out = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "kai_code",
            "--dry-run",
            "--output-format",
            "json",
            "--allowedTools",
            "ls,read_file",
            "--disallowedCommands",
            "*",
            "-p",
            "hi",
        ],
        text=True,
        env=env,
    )
    payload = json.loads(out)
    perms = payload.get("permissions")
    assert perms is not None
    assert "ls" in (perms.get("allowed_tools") or [])
    assert "*" in (perms.get("disallowed_commands") or [])

    # --tools is an enabled-tools filter (not a permission allowlist)
    out2 = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "kai_code",
            "--dry-run",
            "--output-format",
            "json",
            "--tools",
            "ls,read_file",
            "--allowedTools",
            "execute",
            "-p",
            "hi",
        ],
        text=True,
        env=env,
    )
    payload2 = json.loads(out2)
    assert payload2.get("tools") == ["ls", "read_file"]
    perms2 = payload2.get("permissions")
    assert perms2 is not None
    assert perms2.get("allowed_tools") == ["execute"]

    # --system alias
    out3 = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "kai_code",
            "--dry-run",
            "--output-format",
            "json",
            "--system",
            "You are terse.",
            "-p",
            "hi",
        ],
        text=True,
        env=env,
    )
    payload3 = json.loads(out3)
    assert payload3.get("type") == "dry-run"

    # --toolSet alias
    out4 = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "kai_code",
            "--dry-run",
            "--output-format",
            "json",
            "--toolSet",
            "gemini",
            "-p",
            "hi",
        ],
        text=True,
        env=env,
    )
    payload4 = json.loads(out4)
    assert payload4.get("toolset") == "gemini"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
