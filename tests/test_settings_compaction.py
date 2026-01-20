"""Tests for compaction configuration loading."""

import pytest
from pathlib import Path
from kai_code.settings import load_settings, CompactionConfig


def test_default_compaction_config(tmp_path):
    """Default compaction config when no settings present."""
    settings = load_settings(tmp_path)
    assert settings.compaction is None  # No default, explicit only


def test_global_compaction_settings(tmp_path, monkeypatch):
    """Load compaction from global settings."""
    global_dir = tmp_path / ".kai"
    global_dir.mkdir()
    (global_dir / "settings.json").write_text('''{
        "compaction": {
            "enabled": true,
            "threshold": 0.90,
            "recent_window_turns": 15
        }
    }''')

    def mock_global_path():
        return global_dir / "settings.json"

    import kai_code.settings
    monkeypatch.setattr(kai_code.settings, "global_settings_path", mock_global_path)

    settings = load_settings(tmp_path)
    assert settings.compaction is not None
    assert settings.compaction.enabled is True
    assert settings.compaction.threshold == 0.90
    assert settings.compaction.recent_window_turns == 15


def test_project_override_compaction(tmp_path):
    """Project settings override global compaction."""
    # Global settings
    global_dir = tmp_path / ".kai"
    global_dir.mkdir()
    (global_dir / "settings.json").write_text('''{
        "compaction": {
            "enabled": true,
            "threshold": 0.85
        }
    }''')

    # Project settings
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_kai = project_dir / ".kai"
    project_kai.mkdir()
    (project_kai / "settings.json").write_text('''{
        "compaction": {
            "threshold": 0.95
        }
    }''')

    def mock_global_path():
        return global_dir / "settings.json"

    import kai_code.settings
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(kai_code.settings, "global_settings_path", mock_global_path)

    settings = load_settings(project_dir)
    assert settings.compaction is not None
    # Project threshold (0.95) should override global (0.85)
    assert settings.compaction.threshold == 0.95
    monkeypatch.undo()


def test_compaction_config_defaults():
    """CompactionConfig has sensible defaults."""
    config = CompactionConfig()
    assert config.enabled is True
    assert config.threshold == 0.85
    assert config.recent_window_turns == 10
    assert config.min_time_between == 300
    assert config.max_summary_tokens == 1000


def test_compaction_field_level_merge(tmp_path, monkeypatch):
    """Field-level merge preserves all config values across levels."""
    # Global settings with multiple fields
    global_dir = tmp_path / ".kai"
    global_dir.mkdir()
    (global_dir / "settings.json").write_text('''{
        "compaction": {
            "enabled": false,
            "threshold": 0.80,
            "recent_window_turns": 5
        }
    }''')

    # Project settings override only threshold
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_kai = project_dir / ".kai"
    project_kai.mkdir()
    (project_kai / "settings.json").write_text('''{
        "compaction": {
            "threshold": 0.90
        }
    }''')

    def mock_global_path():
        return global_dir / "settings.json"

    import kai_code.settings
    monkeypatch.setattr(kai_code.settings, "global_settings_path", mock_global_path)

    settings = load_settings(project_dir)
    assert settings.compaction is not None
    # Should have enabled=false from global
    assert settings.compaction.enabled is False
    # Should have threshold=0.90 from project (overrides global)
    assert settings.compaction.threshold == 0.90
    # Should have recent_window_turns=5 from global (preserved)
    assert settings.compaction.recent_window_turns == 5
    # Should have defaults for fields not specified anywhere
    assert settings.compaction.min_time_between == 300
    assert settings.compaction.max_summary_tokens == 1000
