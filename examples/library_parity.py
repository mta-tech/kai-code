"""Minimal usage flows for the exported library-style API surface."""

from __future__ import annotations

import json
from pathlib import Path

from kai_code import (
    create_agent,
    createAgent,
    format_available_models,
    formatAvailableModels,
    get_client,
    getClient,
    get_default_model,
    getDefaultModel,
    handle_headless_command,
    handleHeadlessCommand,
    resolve_model,
    resolveModel,
    update_agent_llm_config,
    updateAgentLLMConfig,
    updateAgentSystemPrompt,
)


def main() -> None:
    root = Path(".").resolve()

    # model helpers
    print("default_model", get_default_model())
    print("default_model_ts", getDefaultModel())
    print("available_models\n" + format_available_models())
    print("available_models_ts\n" + formatAvailableModels())
    print("resolve_model(gpt-4o)", resolve_model("gpt-4o"))
    print("resolve_model_ts(gpt-4o)", resolveModel("gpt-4o"))

    # client factory
    client = get_client(root_dir=root)
    _ = getClient(root_dir=root)
    agent = client.open_agent(model=resolve_model("gpt-4o") or "openai:gpt-4o")
    print("client_agent_state_path", agent.config.state_path)

    # create agent wrapper
    created = create_agent(root_dir=root, model="openai:gpt-4o")
    _ = createAgent(root_dir=root, model="openai:gpt-4o")
    print("create_agent_provenance", created.provenance)

    # modify wrapper
    agent2 = update_agent_llm_config(created.agent, "openai:gpt-4o")
    _ = updateAgentLLMConfig(created.agent, "openai:gpt-4o")
    print("updated_model_agent_state_path", agent2.config.state_path)

    # update system prompt (persists into state file)
    _ = updateAgentSystemPrompt(created.agent, "You are a helpful coding agent.")

    # headless wrapper (no model call)
    rc = handle_headless_command(["--new", "-p", "hello", "--dry-run", "--output-format", "json"])
    _ = handleHeadlessCommand(["--new", "-p", "hello", "--dry-run", "--output-format", "json"])
    print(json.dumps({"headless_exit_code": rc}))


if __name__ == "__main__":
    main()
