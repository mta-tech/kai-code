# Agent Development Guide

This guide explains how to create custom agents using kai-code's agent layer.

## Overview

kai-code supports two approaches for creating agents:

1. **Python API**: Subclass `KaiAgent` for full programmatic control
2. **Markdown Definitions**: Define agents declaratively in `.kai/agents/*.md`

Both approaches produce equivalent `KaiAgent` instances with shared capabilities.

## Quick Start

### Creating a Simple Agent (Markdown)

1. Create `.kai/agents/my-agent.md`:

```markdown
---
name: my-agent
description: My custom agent for specific tasks
tools: Bash, Read, Write
---

# Purpose

You are a specialist agent for...

## Instructions

When invoked, follow these steps:
1. Understand the request
2. Perform the task
3. Report results
```

2. Use the agent:

```python
from kai_code.agent_loader import load_agent

agent = load_agent("my-agent")
result = agent.run("Your task here")
```

### Creating an Agent (Python)

```python
from kai_code.agent import KaiAgent
from pathlib import Path

class MyAgent(KaiAgent):
    def _get_base_prompt_name(self) -> str:
        return "my-agent"

    def _get_subclass_tools(self) -> list:
        # Return custom tools
        return super()._get_subclass_tools()

# Use the agent
agent = MyAgent(root_dir=Path.cwd())
result = agent.run("Your task here")
```

## Agent Definition Reference

### YAML Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | kebab-case agent identifier |
| `description` | string | Yes | Action-oriented description for delegation |
| `tools` | list | No | Comma-separated tool names or patterns |
| `allowed-tools` | list | No | Alternative whitelist of tools |
| `model` | string | No | Model override: `sonnet`, `opus`, `haiku`, or `inherit` |
| `extends` | string | No | Parent agent name for inheritance |
| `color` | string | No | Visual indicator for UI |

### System Prompt Sections

Your agent's system prompt should include:

- **# Purpose**: What the agent does
- **## Core Expertise**: Key capabilities
- **## Instructions**: Step-by-step methodology
- **## Critical Behaviors**: Important constraints and patterns
- **## Output Format**: Expected result structure

## Examples

See `.kai/agents/` directory for example agents:
- `seeknal.md` - Data engineering specialist
- `dbt.md` - dbt transformation specialist

## Subagent Delegation

Agents can delegate tasks to specialized subagents using the deepagents pattern.

### Defining Subagents

Add subagents to your agent's YAML frontmatter:

```markdown
---
name: data-pipeline-manager
description: Orchestrates data pipeline tasks
subagents:
  - name: data-engineer
    description: Builds data pipelines and feature stores
    agent: data-engineer
  - name: ml-engineer
    description: Handles feature engineering for ML
    agent: ml-engineer
---

# Purpose

You orchestrate data pipeline tasks by delegating to specialized subagents...
```

### How Subagents Work

When the main agent loads, each subagent is wrapped as a LangChain tool:

```python
# Internally, this happens automatically:
from kai_code.subagents import create_subagent_tool

subagent_tool = create_subagent_tool(
    agent=load_agent("data-engineer"),  # Subagent class
    name="data-engineer",
    description="Builds data pipelines and feature stores",
    root_dir=Path.cwd(),
)
```

When the main agent needs to perform a specialized task, it can call the subagent tool:

```
User: "Build a data pipeline for customer analytics"

Main Agent Decision → invoke("data-engineer", "Build pipeline...")
    ↓
Data Engineer Subagent executes task
    ↓
Returns result to main agent
    ↓
Main agent synthesizes final response
```

### Creating Subagent Agents

Subagents are just regular agents defined in `.kai/agents/`:

```markdown
---
name: data-engineer
description: Data engineering specialist
extends: kai-code
tools: kai_code.agents.seeknal.tools.*
---

# Purpose

You are a Data Engineering Specialist focused on building
efficient data pipelines...

## Core Expertise

You excel at:
- Building multi-engine data flows (DuckDB and Spark)
- Designing feature store schemas
- Data pipeline orchestration
```

### Subagent Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Tool name for the subagent |
| `description` | string | Description of what the subagent does |
| `agent` | string | Agent name (loads from `.kai/agents/`) or class |

### Manual Subagent Tool Creation

For advanced use cases, create subagent tools programmatically:

```python
from kai_code.subagents import create_subagent_tool
from kai_code.agent_loader import load_agent
from pathlib import Path

# Load subagent class
DataEngineer = load_agent("data-engineer")

# Wrap as tool
tool = create_subagent_tool(
    agent=DataEngineer,
    name="data-engineer",
    description="Handles data pipelines and feature stores",
    root_dir=Path.cwd(),
    model="sonnet",  # Optional model override
)

# Add to main agent's tools
main_agent_tools = [tool, ...]
```

## API Reference

### Loading Agents

```python
from kai_code.agent_loader import load_agent, list_agents

# List available agents
agents = list_agents()

# Load by name
agent = load_agent("agent-name")

# Load from custom directory
agent = load_agent("agent-name", agents_dir="/path/to/agents")

# Pass additional arguments
agent = load_agent("agent-name", model="gpt-4o", yolo=True)
```

### AgentDefinition Class

```python
from kai_code.agent_definition import AgentDefinition
from pathlib import Path

# Parse agent file
definition = AgentDefinition(Path(".kai/agents/my-agent.md"))

# Access properties
print(definition.name)
print(definition.description)
print(definition.tools)

# Compile to Python class
AgentClass = definition.to_agent_class()
agent = AgentClass(root_dir=Path.cwd())

# Validate
errors = definition.validate()
if errors:
    print(f"Validation errors: {errors}")
```

## Best Practices

1. **Use kebab-case names**: `my-agent`, not `MyAgent` or `my_agent`
2. **Write action-oriented descriptions**: "Use proactively for X" or "Specialist for Y"
3. **Be specific in instructions**: Clear steps beat vague guidance
4. **Define output format**: Tell users what to expect
5. **Test incrementally**: Start simple, add complexity gradually

## Migration from Python to Markdown

Existing Python agents can be gradually migrated to markdown:

```python
# Before (Python only)
from kai_code.agents.my_agent import MyAgent
agent = MyAgent(root_dir=Path.cwd())

# After (both work)
from kai_code.agent_loader import load_agent
agent = load_agent("my-agent")  # Uses .kai/agents/my-agent.md
```

The Python class continues working - migration is optional.