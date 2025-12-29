from __future__ import annotations

import json
import os
import subprocess
import sys


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["src", env.get("PYTHONPATH", "")]).strip(os.pathsep)
    base = [sys.executable, "-m", "kai_code", "--new", "-p", "Hello", "--dry-run"]

    out = subprocess.check_output(base + ["--output-format", "json"], text=True, env=env)
    payload = json.loads(out)
    assert payload["type"] == "dry-run"
    assert "state_path" in payload

    out2 = subprocess.check_output(base + ["--output-format", "stream-json"], text=True, env=env)
    lines = [json.loads(line) for line in out2.strip().splitlines()]
    assert lines[0]["type"] == "init"
    assert lines[-1]["type"] == "result"
    assert "stats" in lines[-1]
    assert "ttft_ms" in lines[-1]["stats"]
    assert "token_usage" in lines[-1]["stats"]
    assert "turn_count" in lines[-1]["stats"]
    assert "step_count" in lines[-1]["stats"]
    assert "turn_id" in lines[-1]
    assert "step_id" in lines[-1]

    # tool/message events (if present in non-dry-run runs) include turn_id/step_id.
    # In dry-run mode we only guarantee init/result.

    # Event type filter should still include init+result.
    out4 = subprocess.check_output(
        base + ["--output-format", "stream-json", "--stream-event-types", "tool_call"],
        text=True,
        env=env,
    )
    lines4 = [json.loads(line) for line in out4.strip().splitlines()]
    assert lines4[0]["type"] == "init"
    assert lines4[-1]["type"] == "result"

    # dry-run should not require a prompt
    out3 = subprocess.check_output([sys.executable, "-m", "kai_code", "--dry-run"], text=True, env=env)
    payload3 = json.loads(out3)
    assert payload3["type"] == "dry-run"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
