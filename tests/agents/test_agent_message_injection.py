"""Tests for _add_system_message method on KaiAgent."""

import pytest
from pathlib import Path
from kai_code.agent import KaiAgent
from langchain_core.messages import SystemMessage


def test_add_system_message_to_graph():
    agent = KaiAgent(root_dir=Path.cwd())
    agent.run("Hello")  # Initialize the graph

    initial_msg_count = len(agent._graph.state['messages'])

    agent._add_system_message("Test notification")

    new_msg_count = len(agent._graph.state['messages'])
    assert new_msg_count == initial_msg_count + 1

    last_message = agent._graph.state['messages'][-1]
    assert last_message.content == "Test notification"
    assert last_message.type == "system"
