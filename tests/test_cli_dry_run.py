from __future__ import annotations

import json


def test_dry_run_emits_json(capsys):
    from kai_code.cli import main

    rc = main(["--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["type"] == "dry-run"
    assert "root_dir" in payload
