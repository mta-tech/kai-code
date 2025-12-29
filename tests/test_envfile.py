from __future__ import annotations

import os
from pathlib import Path

from kai_code.envfile import load_env_file


def test_load_env_file_sets_vars_without_overriding(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / ".env"
    p.write_text(
        """
        # comment
        FOO=bar
        export BAZ='qux'
        SPACED = "hello world"
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("FOO", "already")

    assert load_env_file(p, override=False) is True
    assert os.environ["FOO"] == "already"
    assert os.environ["BAZ"] == "qux"
    assert os.environ["SPACED"] == "hello world"
