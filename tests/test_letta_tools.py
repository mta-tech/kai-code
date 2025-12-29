from __future__ import annotations

from pathlib import Path


def test_build_default_tools_has_core_names(tmp_path: Path):
    from kai_code.letta_tools import build_default_tools

    (tmp_path / "x.txt").write_text("hello")
    tools = build_default_tools(root_dir=tmp_path)
    names = {t.name for t in tools}
    assert {"ls", "read_file", "glob", "grep", "write_file", "edit_file", "execute", "apply_patch"}.issubset(
        names
    )
