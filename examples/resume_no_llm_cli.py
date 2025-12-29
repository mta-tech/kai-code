from __future__ import annotations

import json
import os
import subprocess
import sys


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["src", env.get("PYTHONPATH", "")]).strip(os.pathsep)
    base = [sys.executable, "-m", "kai_code", "resume", "--approve", "--dry-run"]

    out = subprocess.check_output(base + ["--output-format", "json"], text=True, env=env)
    payload = json.loads(out)
    assert payload["type"] == "dry-run"
    assert payload["command"] == "resume"
    assert payload["decisions"][0]["type"] == "approve"

    out2 = subprocess.check_output(base + ["--output-format", "stream-json"], text=True, env=env)
    lines = [json.loads(line) for line in out2.strip().splitlines()]
    assert lines[0]["type"] == "init"
    assert lines[-1]["type"] == "result"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
