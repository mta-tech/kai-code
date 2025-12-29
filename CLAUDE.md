# CLAUDE.md - Project Context for AI Assistants

This file provides context for AI assistants working on the kai-code project.

## Project Overview

**kai-code** is a Python library for running local coding agents, built on LangChain's `deepagents`. It provides:

- **KaiAgent**: General-purpose coding agent (`kai` CLI)
- **DbtAgent**: Specialized data engineering agent (`kai-dbt` CLI)

## Directory Structure

```
src/kai_code/
├── agent.py              # KaiAgent - base agent class
├── agents/
│   └── dbt/
│       ├── agent.py      # DbtAgent - extends KaiAgent
│       ├── cli.py        # kai-dbt CLI entry point
│       ├── banner.py     # ASCII banner and startup info
│       ├── config.py     # Configuration loading
│       ├── commands.py   # Slash command handler
│       ├── adapters/     # Database adapters (DuckDB, PostgreSQL)
│       └── tools/        # dbt-specific tools
├── prompts/
│   ├── __init__.py       # Prompt loader with inheritance
│   ├── kai-code.md       # Base system prompt
│   └── kai-dbt.md        # dbt prompt (inherits kai-code)
├── rich_*.py             # Rich CLI components (main UI)
├── rich_ui/              # Rich UI application
├── tools/                # Shared tools (web, skills)
├── memory/               # Memory management
├── skills/               # Skill definitions
└── ralph_*.py            # Ralph Wiggum autonomous loop
```

## Key Concepts

### Agent Architecture

```python
# Base agent - uses kai-code.md prompt
class KaiAgent:
    def _get_base_prompt_name(self) -> str:
        return "kai-code"

# Specialized agent - uses kai-dbt.md (inherits kai-code)
class DbtAgent(KaiAgent):
    def _get_base_prompt_name(self) -> str:
        return "kai-dbt"
```

### Prompt System

Prompts are markdown files in `src/kai_code/prompts/` with inheritance:

```markdown
# kai-dbt.md
# INHERIT: kai-code

(dbt-specific content here)
```

Load prompts:
```python
from kai_code.prompts import load_prompt
prompt = load_prompt("kai-dbt")  # Returns kai-code + kai-dbt content
```

### CLI Patterns

Both CLIs use the Rich CLI framework:
- ASCII banner on startup
- Slash commands for quick actions
- Auto-approve mode (`-y` or `--yes`)
- Session state persistence in `.kai/`

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/prompts/ -v
python -m pytest tests/agents/dbt/ -v

# No-LLM verification (safe for CI)
python verify_no_llm.py
```

## Common Tasks

### Adding a New Agent

1. Create agent class extending `KaiAgent`
2. Override `_get_base_prompt_name()` to return your prompt name
3. Create `src/kai_code/prompts/your-agent.md` with `# INHERIT: kai-code`
4. Add agent-specific tools in `get_*_tools()` method

### Modifying System Prompts

Edit the markdown files in `src/kai_code/prompts/`:
- `kai-code.md` - Base prompt for all agents
- `kai-dbt.md` - dbt-specific additions

### Adding dbt Tools

Add tools in `src/kai_code/agents/dbt/tools/`:
```python
from langchain_core.tools import tool

@tool("tool_name")
def my_tool(arg: str) -> str:
    """Tool description."""
    return result
```

Register in `DbtAgent.get_dbt_tools()`.

## Code Style

- Type hints required
- Docstrings for public APIs
- Tests for new functionality
- Keep it simple - avoid over-engineering

## Key Files to Know

| File | Purpose |
|------|---------|
| `agent.py` | Base KaiAgent with `_build_graph()` |
| `prompts/__init__.py` | Prompt loader with caching |
| `prompts/kai-code.md` | Base system prompt |
| `prompts/kai-dbt.md` | dbt-specific prompt |
| `agents/dbt/agent.py` | DbtAgent implementation |
| `agents/dbt/cli.py` | kai-dbt CLI entry point |
| `rich_main.py` | Main kai CLI entry point |
| `rich_config.py` | Colors, ASCII banners, settings |
| `ralph_loop.py` | Ralph Wiggum autonomous loop |
