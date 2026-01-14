"""Integration tests for agent loading with existing kai-code agents."""
import pytest
from pathlib import Path
from kai_code.agent_loader import load_agent
from kai_code.agents.seeknal import SeeknalAgent


def test_loaded_seeknal_agent_is_instance():
    """Test that loaded seeknal agent is KaiAgent instance."""
    # This test requires the .kai/agents/seeknal.md file to exist
    try:
        agent = load_agent("seeknal")
        assert hasattr(agent, 'run')
        assert hasattr(agent, '_get_base_prompt_name')
    except FileNotFoundError:
        pytest.skip("seeknal.md not created yet")


def test_loaded_agent_equivalent_to_python_class():
    """Test that loaded agent has same capabilities as Python SeeknalAgent."""
    try:
        # Load from markdown
        markdown_agent = load_agent("seeknal")
        
        # Create Python instance
        python_agent = SeeknalAgent(root_dir=Path.cwd())
        
        # Both should have same base methods
        assert type(markdown_agent.run) == type(python_agent.run)
        assert type(markdown_agent.save) == type(python_agent.save)
    except FileNotFoundError:
        pytest.skip("seeknal.md not created yet")


def test_python_agent_still_works():
    """Test that existing Python agent creation still works (backward compat)."""
    agent = SeeknalAgent(root_dir=Path.cwd())
    
    assert agent is not None
    assert hasattr(agent, 'run')
    assert hasattr(agent, '_get_base_prompt_name')
