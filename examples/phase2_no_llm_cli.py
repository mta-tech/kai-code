from __future__ import annotations

import json
import subprocess
import sys


def main() -> int:
    base = [sys.executable, "-m", "kai_code", "--new", "-p", "Hello", "--dry-run"]

    out = subprocess.check_output(base + ["--output-format", "json"], text=True)
    payload = json.loads(out)
    assert payload["type"] == "dry-run"
    assert "state_path" in payload

    out2 = subprocess.check_output(base + ["--output-format", "stream-json"], text=True)
    lines = [json.loads(line) for line in out2.strip().splitlines()]
    assert lines[0]["type"] == "init"
    assert lines[-1]["type"] == "result"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
