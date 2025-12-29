# Custom Agents Guide

This guide explains how to create specialized agents by extending the base `KaiAgent` class.

## Overview

Kai Code's agent architecture is designed for extensibility. The base `KaiAgent` provides core functionality, while specialized agents (like `DbtAgent`) add domain-specific capabilities.

## Architecture

```
KaiAgent (base)
    │
    ├── Core tools (ls, read_file, write_file, etc.)
    ├── Session management
    ├── Permission system
    └── LangGraph workflow

DbtAgent (extends KaiAgent)
    │
    ├── Inherits all KaiAgent functionality
    ├── dbt-specific tools (schema, model inspection)
    ├── Database adapters (DuckDB, PostgreSQL)
    └── Custom system prompt
```

## Creating a Custom Agent

### Step 1: Create the Agent Class

```python
# src/kai_code/agents/my_agent/agent.py
from kai_code.agent import KaiAgent
from langchain_core.tools import tool

class MyAgent(KaiAgent):
    """A specialized agent for my use case."""

    def __init__(
        self,
        root_dir: str = ".",
        model: str = None,
        yolo: bool = False,
        custom_option: str = None,  # Your custom options
        **kwargs
    ):
        self.custom_option = custom_option
        super().__init__(root_dir=root_dir, model=model, yolo=yolo, **kwargs)

    def _get_base_prompt_name(self) -> str:
        """Return the name of the prompt file to load."""
        return "my-agent"  # Loads prompts/my-agent.md

    def get_custom_tools(self):
        """Return additional tools for this agent."""
        return [
            self._my_custom_tool(),
            self._another_tool(),
        ]

    def _my_custom_tool(self):
        @tool("my_tool")
        def my_tool(arg: str) -> str:
            """Description of what this tool does.

            Args:
                arg: Description of the argument

            Returns:
                The result
            """
            # Implementation
            return f"Processed: {arg}"

        return my_tool

    def _another_tool(self):
        @tool("another_tool")
        def another_tool(data: dict) -> str:
            """Another specialized tool."""
            return str(data)

        return another_tool
```

### Step 2: Create the System Prompt

```markdown
<!-- src/kai_code/prompts/my-agent.md -->
# INHERIT: kai-code

## My Agent Capabilities

You are a specialized agent for [your domain]. You have access to:

### Custom Tools

- `my_tool`: Does X when given Y
- `another_tool`: Handles Z

### Guidelines

1. Always do A before B
2. When encountering C, prefer D
3. Output format should be E

### Example Workflow

1. User asks to do X
2. First, call `my_tool` to gather information
3. Then, apply changes using file operations
4. Finally, validate the result
```

### Step 3: Create the CLI

```python
# src/kai_code/agents/my_agent/cli.py
import argparse
import sys
from .agent import MyAgent
from kai_code.rich_main import run_interactive_loop

def cli_main():
    parser = argparse.ArgumentParser(
        description="My specialized agent"
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Auto-approve all actions"
    )
    parser.add_argument(
        "--model",
        help="LLM model to use"
    )
    parser.add_argument(
        "--custom-option",
        help="My custom option"
    )
    parser.add_argument(
        "-p", "--prompt",
        help="Run a single prompt"
    )

    args = parser.parse_args()

    agent = MyAgent(
        root_dir=".",
        model=args.model,
        yolo=args.yes,
        custom_option=args.custom_option
    )

    if args.prompt:
        # Headless mode
        result = agent.run(args.prompt)
        print(result.output)
        sys.exit(0)
    else:
        # Interactive mode
        run_interactive_loop(agent)

if __name__ == "__main__":
    cli_main()
```

### Step 4: Register the CLI Entry Point

```toml
# pyproject.toml
[project.scripts]
kai = "kai_code.rich_main:cli_main"
kai-dbt = "kai_code.agents.dbt.cli:cli_main"
my-agent = "kai_code.agents.my_agent.cli:cli_main"  # Add this
```

## Tool Development

### Tool Anatomy

```python
from langchain_core.tools import tool

@tool("tool_name")
def my_tool(
    required_arg: str,
    optional_arg: int = 10
) -> str:
    """Short description of the tool.

    Longer description explaining when and how to use this tool.
    The LLM uses this docstring to decide when to invoke the tool.

    Args:
        required_arg: What this argument is for
        optional_arg: What this optional argument does (default: 10)

    Returns:
        Description of what's returned

    Raises:
        ValueError: When input is invalid
    """
    # Implementation
    if not required_arg:
        raise ValueError("required_arg cannot be empty")

    result = process(required_arg, optional_arg)
    return f"Result: {result}"
```

### Tool Best Practices

1. **Clear docstrings**: The LLM relies on them to know when to use tools
2. **Type hints**: Enable proper parameter parsing
3. **Error handling**: Return helpful error messages
4. **Focused scope**: One tool = one clear purpose
5. **Consistent returns**: String output works best

### Complex Tool Example

```python
@tool("analyze_data")
def analyze_data(
    file_path: str,
    analysis_type: str = "summary",
    include_stats: bool = True
) -> str:
    """Analyze data from a file.

    Use this tool when you need to understand the contents and
    structure of a data file (CSV, JSON, Parquet).

    Args:
        file_path: Path to the data file
        analysis_type: Type of analysis - "summary", "schema", "quality"
        include_stats: Whether to include statistical summaries

    Returns:
        Analysis results as formatted text
    """
    import pandas as pd

    try:
        # Load data based on file type
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.json'):
            df = pd.read_json(file_path)
        elif file_path.endswith('.parquet'):
            df = pd.read_parquet(file_path)
        else:
            return f"Unsupported file type: {file_path}"

        result = []

        if analysis_type in ("summary", "schema"):
            result.append(f"Columns: {list(df.columns)}")
            result.append(f"Rows: {len(df)}")
            result.append(f"Types:\n{df.dtypes.to_string()}")

        if include_stats and analysis_type == "summary":
            result.append(f"\nStatistics:\n{df.describe().to_string()}")

        if analysis_type == "quality":
            null_counts = df.isnull().sum()
            result.append(f"Null counts:\n{null_counts.to_string()}")

        return "\n".join(result)

    except Exception as e:
        return f"Error analyzing file: {e}"
```

## Prompt Inheritance

### How It Works

Prompts can inherit from parent prompts using the `# INHERIT:` directive:

```markdown
# my-agent.md
# INHERIT: kai-code

(Your additions here)
```

The prompt loader (`kai_code.prompts.load_prompt`) will:
1. Load the parent prompt (`kai-code.md`)
2. Append your additions
3. Return the combined prompt

### Loading Prompts Programmatically

```python
from kai_code.prompts import load_prompt

# Load a specific prompt
prompt = load_prompt("my-agent")  # Returns full text including inherited content

# Load base prompt
base = load_prompt("kai-code")
```

### Multiple Inheritance Levels

```
kai-code.md           (base)
    ↓
my-domain.md          (INHERIT: kai-code)
    ↓
my-specialized.md     (INHERIT: my-domain)
```

## Extending DbtAgent

### Example: Adding Custom Database Support

```python
from kai_code.agents.dbt import DbtAgent
from kai_code.agents.dbt.adapters import DatabaseAdapter

class SnowflakeAdapter(DatabaseAdapter):
    """Adapter for Snowflake database."""

    def __init__(self, connection_string: str):
        self.conn_str = connection_string
        self._conn = None

    def connect(self):
        import snowflake.connector
        self._conn = snowflake.connector.connect(...)

    def get_schema(self):
        # Return schema information
        pass

    def execute(self, query: str):
        # Execute SQL query
        pass

class SnowflakeDbtAgent(DbtAgent):
    """DbtAgent with Snowflake support."""

    def __init__(self, connection_string: str, **kwargs):
        super().__init__(**kwargs)
        self.adapter = SnowflakeAdapter(connection_string)

    def _get_base_prompt_name(self):
        return "kai-dbt-snowflake"  # Custom prompt with Snowflake-specific guidance
```

## Testing Your Agent

### Unit Tests

```python
# tests/agents/my_agent/test_agent.py
import pytest
from kai_code.agents.my_agent import MyAgent

def test_agent_creation():
    agent = MyAgent(root_dir=".", yolo=True)
    assert agent is not None

def test_custom_tools():
    agent = MyAgent(root_dir=".")
    tools = agent.get_custom_tools()
    assert len(tools) > 0

    # Check tool names
    tool_names = [t.name for t in tools]
    assert "my_tool" in tool_names

def test_tool_execution():
    agent = MyAgent(root_dir=".")
    my_tool = agent._my_custom_tool()

    result = my_tool.invoke({"arg": "test"})
    assert "Processed: test" in result
```

### Integration Tests

```python
def test_agent_run():
    agent = MyAgent(root_dir=".", yolo=True)
    result = agent.run("Use my_tool with 'hello'")

    assert result.output is not None
    assert "hello" in result.output.lower()
```

## Package Structure

Recommended structure for your custom agent:

```
src/kai_code/agents/my_agent/
├── __init__.py          # Export MyAgent
├── agent.py             # MyAgent class
├── cli.py               # CLI entry point
├── tools/               # Custom tools
│   ├── __init__.py
│   ├── my_tool.py
│   └── another_tool.py
├── adapters/            # If needed (like DbtAgent)
│   ├── __init__.py
│   └── my_adapter.py
└── config.py            # Configuration helpers

src/kai_code/prompts/
└── my-agent.md          # System prompt
```

## Next Steps

- **[Configuration Guide](configuration.md)** - Agent configuration options
- **[API Reference](../api/kai-agent.md)** - Full KaiAgent API
- **[dbt Agent Tutorial](../tutorials/dbt-agent.md)** - See DbtAgent implementation
