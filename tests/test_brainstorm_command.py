from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kai_code.rich_commands import handle_command, _handle_brainstorm


def test_brainstorm_command_recognized() -> None:
    agent = MagicMock()
    result = handle_command("/brainstorm", agent)
    assert result is not None
    assert result != "exit"


def test_brainstorm_with_topic_includes_topic() -> None:
    agent = MagicMock()
    result = handle_command("/brainstorm user authentication", agent)
    assert result is not None
    assert "user authentication" in result


def test_brainstorm_without_topic_prompts_for_idea() -> None:
    agent = MagicMock()
    result = handle_command("/brainstorm", agent)
    assert result is not None
    assert "brainstorm" in result.lower()


def test_brainstorm_skill_content_included() -> None:
    agent = MagicMock()
    result = handle_command("/brainstorm test idea", agent)
    assert result is not None
    assert "One question at a time" in result


def test_brainstorm_includes_design_output_path() -> None:
    agent = MagicMock()
    result = handle_command("/brainstorm", agent)
    assert result is not None
    assert "docs/plans/" in result


def test_brainstorm_handler_returns_none_when_skill_missing(
    tmp_path: Path, monkeypatch
) -> None:
    import kai_code.rich_commands as rc

    original_file = rc.__file__
    monkeypatch.setattr(rc, "__file__", str(tmp_path / "fake.py"))

    result = _handle_brainstorm("/brainstorm test")
    assert result is None

    monkeypatch.setattr(rc, "__file__", original_file)


def test_skill_file_exists() -> None:
    skill_path = (
        Path(__file__).parent.parent
        / "src"
        / "kai_code"
        / "skills"
        / "brainstorming"
        / "SKILL.md"
    )
    assert skill_path.exists(), f"Skill file not found at {skill_path}"


def test_skill_has_required_sections() -> None:
    skill_path = (
        Path(__file__).parent.parent
        / "src"
        / "kai_code"
        / "skills"
        / "brainstorming"
        / "SKILL.md"
    )
    content = skill_path.read_text()

    assert "Understanding" in content or "understand" in content.lower()
    assert "Exploring" in content or "approach" in content.lower()
    assert "Design" in content
    assert "docs/plans/" in content
