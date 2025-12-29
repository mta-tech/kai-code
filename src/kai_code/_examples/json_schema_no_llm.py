from __future__ import annotations

import json
import os
import subprocess
import sys


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["src", env.get("PYTHONPATH", "")]).strip(os.pathsep)
    out = subprocess.check_output(
        [sys.executable, "-m", "kai_code", "--dry-run", "-p", "hi", "--output-format", "json"],
        text=True,
        env=env,
    )
    payload = json.loads(out)
    assert payload["type"] == "dry-run"

    # Non-dry-run json can't be verified without credentials, but we can verify
    # the interrupt schema in dry-run doesn't crash.
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
