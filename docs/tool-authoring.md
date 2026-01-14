# Tool Authoring Guide

This guide covers how to create and use tools with kai-code agents.

## Overview

Tools are the building blocks that give agents their capabilities. Each tool is a function that the agent can call to perform specific actions. Tools are defined using LangChain's `@tool` decorator and registered with agents through the `_get_subclass_tools()` method.

## Tool Basics

### Creating a Simple Tool

```python
from langchain_core.tools import tool
from pathlib import Path

@tool("read_file")
def read_file(path: str) -> str:
    """Read the contents of a file.

    Args:
        path: Path to the file to read.

    Returns:
        File contents as string.
    """
    return Path(path).read_text()
```

**Key points:**
- Use `@tool` decorator with a unique tool name
- Type hints on parameters are required
- Docstring becomes the tool description (visible to the agent)
- Return type should be JSON-serializable (str, dict, list)

### Tool with Multiple Parameters

```python
@tool("write_file")
def write_file(path: str, content: str) -> str:
    """Write content to a file.

    Args:
        path: Path to the file to write.
        content: Content to write to the file.

    Returns:
        Success message.
    """
    Path(path).write_text(content)
    return f"Successfully wrote {path}"
```

### Tool with Complex Return Types

Tools should return JSON-serializable data. Use structured responses:

```python
import json

@tool("analyze_data")
def analyze_data(file_path: str) -> str:
    """Analyze a data file and return statistics.

    Args:
        file_path: Path to data file.

    Returns:
        JSON string with analysis results.
    """
    # Your analysis logic here
    results = {
        "success": True,
        "row_count": 1000,
        "columns": ["id", "name", "value"],
        "summary": {
            "mean": 42.5,
            "median": 40.0,
            "max": 100
        }
    }
    return json.dumps(results, indent=2)
```

**Best practice:** Always return structured data as JSON string for complex results.

## Tool Factories

When tools need configuration (paths, credentials, etc.), use a **factory function**:

```python
def create_database_tools(connection_string: str) -> list:
    """Create database tools with specific connection.

    Args:
        connection_string: Database connection string.

    Returns:
        List of LangChain tools.
    """

    @tool("db_query")
    def db_query(sql: str) -> str:
        """Execute a SQL query.

        Args:
            sql: SQL query to execute.

        Returns:
            Query results as JSON.
        """
        # Use connection_string from closure
        results = execute_query(connection_string, sql)
        return json.dumps(results)

    @tool("db_list_tables")
    def db_list_tables() -> str:
        """List all tables in the database.

        Returns:
            JSON list of table names.
        """
        tables = list_tables(connection_string)
        return json.dumps({"tables": tables})

    return [db_query, db_list_tables]
```

**Why factories?**
- Encapsulate configuration (paths, credentials)
- Create related tool groups
- Support multiple instances with different configs
- Keep tool definitions clean

## Registering Tools with Agents

### Option 1: Python Agent (Recommended for Advanced Users)

Override `_get_subclass_tools()` method:

```python
# src/kai_code/agents/my_agent/agent.py
from kai_code.agent import KaiAgent
from .tools import create_my_tools

class MyAgent(KaiAgent):
    def _get_base_prompt_name(self) -> str:
        return "kai-my-agent"

    def _get_subclass_tools(self) -> list:
        from kai_code.tools import get_base_tools

        # Get base KaiAgent tools (Bash, Read, Write, etc.)
        base_tools = get_base_tools()

        # Add your custom tools
        custom_tools = create_my_tools(config_path="/path/to/config")

        return base_tools + custom_tools
```

### Option 2: Markdown Agent (Recommended for Most Users)

Specify tool patterns in YAML frontmatter:

```markdown
---
name: my-agent
description: My custom agent
tools:
  - kai_code.tools.bash
  - kai_code.tools.read
  - kai_code.tools.write
  - my_package.tools.my_tools
  - my_package.tools.*
model: inherit
---

# Purpose

You are a specialist agent...
```

**Tool patterns:**
- Exact path: `my_package.tools.my_tools` (imports `create_my_tools()`)
- Wildcard: `my_package.tools.*` (imports all `create_*_tools()` functions)

## Tool Naming Conventions

Follow these conventions for consistency:

### Function Names

Use `verb_noun` pattern:

```python
# Good
@tool("seeknal_init_project")
@tool("db_query")
@tool("file_read")

# Avoid
@tool("init")        # Too vague
@tool("project")     # Noun, not verb
@tool("do_query")    # Unnecessary "do"
```

### Tool Names (Decorator Argument)

Use `service_action` or `domain_action` pattern:

```python
# Domain-specific tools
@tool("seeknal_init_project")   # service_action
@tool("db_query")               # domain_action

# Generic tools
@tool("read_file")              # verb_noun
@tool("write_file")             # verb_noun
```

### Docstrings

Write clear, action-oriented descriptions:

```python
# Good
@tool("db_query")
def db_query(sql: str) -> str:
    """Execute a SQL query and return results.

    Args:
        sql: SQL query to execute.

    Returns:
        Query results as JSON string with rows and columns.
    """

# Too brief
@tool("db_query")
def db_query(sql: str) -> str:
    """Run query."""  # Doesn't explain what it does

# Too verbose
@tool("db_query")
def db_query(sql: str) -> str:
    """
    This function executes a SQL query against the database.
    It takes a SQL string as input and returns the results.
    The database connection is managed internally.
    Args: sql (str): The SQL query
    Returns: str: JSON results
    """  # Docstring should be concise for agent
```

## Error Handling

Always handle errors gracefully and return structured error responses:

```python
@tool("api_call")
def api_call(endpoint: str) -> str:
    """Make an API call to external service.

    Args:
        endpoint: API endpoint URL.

    Returns:
        JSON response or error message.
    """
    try:
        response = requests.get(endpoint, timeout=30)
        response.raise_for_status()
        return json.dumps({
            "success": True,
            "data": response.json()
        })
    except requests.Timeout:
        return json.dumps({
            "success": False,
            "error": "Request timed out after 30 seconds",
            "suggestion": "Try again or check endpoint availability"
        })
    except requests.RequestException as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "suggestion": "Check endpoint URL and network connectivity"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "suggestion": "Contact support with error details"
        })
```

**Error response structure:**
```python
{
    "success": False,
    "error": "Clear error message",
    "suggestion": "How to fix the issue"  # Optional but helpful
}
```

## Tool Organization

### Directory Structure

```
src/kai_code/agents/my_agent/
├── agent.py              # Agent class
├── tools/
│   ├── __init__.py       # Tool exports
│   ├── database_tools.py # DB-related tools
│   ├── file_tools.py     # File-related tools
│   └── api_tools.py      # API-related tools
```

### Tool Module (`__init__.py`)

```python
# src/kai_code/agents/my_agent/tools/__init__.py
from .database_tools import create_database_tools
from .file_tools import create_file_tools
from .api_tools import create_api_tools

__all__ = [
    "create_database_tools",
    "create_file_tools",
    "create_api_tools",
]
```

### Naming Tool Factories

All tool factory functions should be named `create_*_tools`:

```python
# Good
def create_database_tools(config: dict) -> list:
    """Create database tools."""
    ...

def create_file_tools(base_path: Path) -> list:
    """Create file tools."""
    ...

# Avoid
def get_db_tools():      # Use "create_" prefix
def database_tools():    # Missing "create_" prefix
def tools():             # Not descriptive
```

This allows wildcard imports to work correctly:

```python
# In agent definition or YAML:
tools: kai_code.agents.my_agent.tools.*
# Finds: create_database_tools, create_file_tools, create_api_tools
```

## Tool Testing

Always test tools independently:

```python
# tests/agents/my_agent/tools/test_database_tools.py
import pytest
from kai_code.agents.my_agent.tools import create_database_tools

def test_db_query_tool():
    """Test database query tool."""
    tools = create_database_tools(":memory:")

    # Find the tool by name
    query_tool = next(t for t in tools if t.name == "db_query")

    # Invoke the tool
    result = query_tool.invoke("SELECT 1 AS value")

    # Parse JSON response
    import json
    data = json.loads(result)

    assert data["success"] is True
    assert data["rows"] == [{"value": 1}]

def test_db_query_error_handling():
    """Test error handling in query tool."""
    tools = create_database_tools(":memory:")
    query_tool = next(t for t in tools if t.name == "db_query")

    # Invalid SQL
    result = query_tool.invoke("INVALID SQL")
    data = json.loads(result)

    assert data["success"] is False
    assert "error" in data
```

## Advanced Tool Patterns

### Async Tools

For I/O-bound operations, use async tools:

```python
from langchain_core.tools import tool

@tool("fetch_url")
async def fetch_url(url: str) -> str:
    """Fetch content from a URL asynchronously.

    Args:
        url: URL to fetch.

    Returns:
        URL content as string.
    """
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            text = await response.text()
            return text
```

### Tools with State

Some tools need to maintain state across invocations:

```python
class DataProcessor:
    """Tool class with internal state."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache = {}

    @tool("process_data")
    def process_data(self, data_id: str) -> str:
        """Process data with caching.

        Args:
            data_id: Data identifier.

        Returns:
            Processing results.
        """
        if data_id in self.cache:
            return json.dumps({
                "cached": True,
                "result": self.cache[data_id]
            })

        result = self._process(data_id)
        self.cache[data_id] = result
        return json.dumps({"cached": False, "result": result})

def create_processing_tools(cache_dir: Path) -> list:
    """Create stateful processing tools."""
    processor = DataProcessor(cache_dir)
    return [processor.process_data]
```

### Tools with File System Access

Always validate and sanitize paths:

```python
@tool("read_config")
def read_config(path: str, base_dir: str = "/safe/dir") -> str:
    """Read a config file safely.

    Args:
        path: Config file path (relative to base_dir).
        base_dir: Base directory for safety.

    Returns:
        Config file contents.
    """
    from pathlib import Path

    base = Path(base_dir).resolve()
    target = (base / path).resolve()

    # Security check: ensure target is within base_dir
    if not str(target).startswith(str(base)):
        return json.dumps({
            "success": False,
            "error": "Access denied: path outside base directory"
        })

    if not target.exists():
        return json.dumps({
            "success": False,
            "error": f"File not found: {path}"
        })

    return target.read_text()
```

## Tool Performance

### Timeouts

Always use timeouts for external operations:

```python
import subprocess
import signal

@tool("run_command")
def run_command(command: str, timeout: int = 30) -> str:
    """Run a shell command with timeout.

    Args:
        command: Command to run.
        timeout: Timeout in seconds (default 30).

    Returns:
        Command output.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return json.dumps({
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": f"Command timed out after {timeout} seconds"
        })
```

### Caching

Cache expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def _expensive_lookup(key: str) -> dict:
    """Cached lookup operation."""
    # Expensive computation here
    return {"result": f"value_for_{key}"}

@tool("cached_lookup")
def cached_lookup(key: str) -> str:
    """Perform cached lookup.

    Args:
        key: Lookup key.

    Returns:
        Cached result.
    """
    result = _expensive_lookup(key)
    return json.dumps({"key": key, "result": result})
```

## Common Tool Patterns

### CLI Wrapper Tools

Wrap external CLI tools:

```python
def create_cli_tools(binary_path: Path) -> list:
    """Create CLI wrapper tools.

    Args:
        binary_path: Path to CLI binary.

    Returns:
        List of CLI tools.
    """

    @tool("cli_status")
    def cli_status() -> str:
        """Get CLI status."""
        result = subprocess.run(
            [str(binary_path), "status"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return json.dumps({
            "success": result.returncode == 0,
            "output": result.stdout
        })

    @tool("cli_run")
    def cli_run(command: str) -> str:
        """Run a CLI command."""
        result = subprocess.run(
            [str(binary_path), command],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )
        return json.dumps({
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        })

    return [cli_status, cli_run]
```

### Data Transformation Tools

```python
@tool("transform_csv_to_json")
def transform_csv_to_json(csv_path: str, json_path: str) -> str:
    """Transform CSV file to JSON format.

    Args:
        csv_path: Path to input CSV file.
        json_path: Path to output JSON file.

    Returns:
        Transformation result.
    """
    import pandas as pd

    try:
        df = pd.read_csv(csv_path)
        df.to_json(json_path, orient="records", indent=2)

        return json.dumps({
            "success": True,
            "rows": len(df),
            "output": json_path
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "suggestion": "Check CSV file format and paths"
        })
```

### Validation Tools

```python
@tool("validate_schema")
def validate_schema(data: str, schema: str) -> str:
    """Validate data against a JSON schema.

    Args:
        data: JSON data to validate.
        schema: JSON schema for validation.

    Returns:
        Validation result.
    """
    import json
    from jsonschema import validate, ValidationError

    try:
        data_obj = json.loads(data)
        schema_obj = json.loads(schema)

        validate(instance=data_obj, schema=schema_obj)

        return json.dumps({
            "valid": True,
            "message": "Data is valid"
        })
    except ValidationError as e:
        return json.dumps({
            "valid": False,
            "error": e.message,
            "path": list(e.path)
        })
    except json.JSONDecodeError as e:
        return json.dumps({
            "valid": False,
            "error": f"Invalid JSON: {str(e)}"
        })
```

## Best Practices Summary

### Do's
- ✅ Use type hints on all parameters
- ✅ Return JSON-serializable data (str, dict, list)
- ✅ Write clear, concise docstrings
- ✅ Handle errors gracefully with structured responses
- ✅ Use timeouts for external operations
- ✅ Validate input (paths, data, etc.)
- ✅ Use factory functions for configured tools
- ✅ Follow naming conventions (`create_*_tools`)
- ✅ Test tools independently
- ✅ Return structured JSON responses

### Don'ts
- ❌ Return complex objects (Pydantic models, etc.)
- ❌ Write verbose docstrings (agent sees them)
- ❌ Ignore error handling
- ❌ Block indefinitely (no timeouts)
- ❌ Trust user input without validation
- ❌ Use global state
- ❌ Create overly complex tools
- ❌ Mix concerns (one tool = one purpose)

## Examples

See existing tool implementations for reference:

- **Seeknal tools**: `src/kai_code/agents/seeknal/tools/`
  - `project_tools.py` - Project management tools
  - `flow_tools.py` - Data flow tools
  - `feature_store_tools.py` - Feature store tools

- **Dbt tools**: `src/kai_code/agents/dbt/tools/`
  - `dbt_cli_tools.py` - dbt CLI wrapper tools
  - `schema_tools.py` - Schema validation tools

- **Base tools**: `src/kai_code/tools/`
  - Common tools used by all agents

## Troubleshooting

### Tool Not Found

If tools aren't loading:

1. Check factory function name is `create_*_tools`
2. Verify module path is correct in YAML
3. Ensure tools are returned as list
4. Check for import errors

### Tool Returns Wrong Type

If agent can't parse tool results:

1. Ensure return type is JSON-serializable
2. Convert complex objects to JSON string
3. Use `json.dumps()` for structured data
4. Return simple strings for text output

### Tool Not Called by Agent

If agent doesn't use your tool:

1. Check tool description is clear
2. Verify docstring explains when to use it
3. Ensure tool name is descriptive
4. Test agent with explicit tool invocation

### Tool Performance Issues

If tools are slow:

1. Add timeouts to external operations
2. Use caching for expensive lookups
3. Consider async for I/O-bound work
4. Profile to find bottlenecks

---

**Need help?** See `docs/agent-development-guide.md` for agent creation, or `docs/subagent-patterns.md` for advanced patterns.
