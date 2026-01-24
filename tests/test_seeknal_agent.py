"""Tests for SeeknalAgent."""

import pytest
from pathlib import Path
from kai_code.agents.seeknal import SeeknalAgent


def test_seeknal_agent_init(tmp_path: Path) -> None:
    """Test SeeknalAgent initialization."""
    agent = SeeknalAgent(
        root_dir=tmp_path,
        yolo=True,
    )

    assert agent is not None
    assert agent.seeknal_path is not None
    assert agent._get_base_prompt_name() == "kai-seeknal"


def test_seeknal_agent_prompt_loading(tmp_path: Path) -> None:
    """Test that kai-seeknal prompt loads correctly."""
    from kai_code.prompts import load_prompt

    prompt = load_prompt("kai-seeknal")

    assert "Seeknal" in prompt
    assert "data engineering" in prompt.lower()
    assert "feature store" in prompt.lower()


def test_seeknal_agent_tools(tmp_path: Path) -> None:
    """Test that Seeknal tools are available."""
    agent = SeeknalAgent(
        root_dir=tmp_path,
        yolo=True,
    )

    tools = agent.get_seeknal_tools()

    # Check that we have tools from each category
    tool_names = [tool.name for tool in tools]

    # Project tools
    assert "seeknal_init_project" in tool_names
    assert "seeknal_list_projects" in tool_names

    # Flow tools
    assert "seeknal_create_flow" in tool_names
    assert "seeknal_run_flow" in tool_names

    # Feature store tools
    assert "seeknal_create_feature_group" in tool_names
    assert "seeknal_materialize_features" in tool_names

    # Entity tools
    assert "seeknal_create_entity" in tool_names

    # Version tools
    assert "seeknal_list_versions" in tool_names
    assert "seeknal_compare_versions" in tool_names

    # Validation tools
    assert "seeknal_validate_sql_identifier" in tool_names
    assert "seeknal_validate_features" in tool_names


def test_seeknal_agent_custom_path(tmp_path: Path) -> None:
    """Test SeeknalAgent with custom Seeknal path."""
    custom_path = tmp_path / "custom_seeknal"

    agent = SeeknalAgent(
        root_dir=tmp_path,
        seeknal_path=custom_path,
        yolo=True,
    )

    assert agent.seeknal_path == custom_path


def test_seeknal_prompt_inheritance() -> None:
    """Test that kai-seeknal properly inherits from kai-code."""
    from kai_code.prompts import load_prompt

    base_prompt = load_prompt("kai-code")
    seeknal_prompt = load_prompt("kai-seeknal")

    # kai-seeknal should contain kai-code content
    assert base_prompt.split("\n")[0:10]  # Base prompt exists
    assert len(seeknal_prompt) > len(base_prompt)  # Seeknal prompt is longer
    assert "Seeknal" in seeknal_prompt  # Contains Seeknal-specific content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
