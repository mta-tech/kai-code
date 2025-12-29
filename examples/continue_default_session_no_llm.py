from __future__ import annotations

import json
import os
import subprocess
import sys


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["src", env.get("PYTHONPATH", "")]).strip(os.pathsep)
    # First run: default session (no --new, no --agent) should become resumable.
    out1 = subprocess.check_output(
        [sys.executable, "-m", "kai_code", "--dry-run", "-p", "hi"],
        text=True,
        env=env,
    )
    p1 = json.loads(out1)
    assert p1["type"] == "dry-run"

    # Second run: --continue should resolve without error.
    out2 = subprocess.check_output(
        [sys.executable, "-m", "kai_code", "--dry-run", "--continue", "-p", "hi"],
        text=True,
        env=env,
    )
    p2 = json.loads(out2)
    assert p2["type"] == "dry-run"
    assert p2["state_path"] == p1["state_path"]

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
