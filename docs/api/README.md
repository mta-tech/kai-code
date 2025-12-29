# API Reference

This section provides detailed API documentation for Kai Code's Python interfaces.

## Core Classes

### KaiAgent

The base agent class for all Kai Code agents.

```python
from kai_code import KaiAgent
```

#### Constructor

```python
KaiAgent(
    root_dir: str = ".",
    model: str = None,
    yolo: bool = False,
    permissions: PermissionConfig = None,
    system_prompt: str = None,
    **kwargs
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `root_dir` | str | "." | Working directory for the agent |
| `model` | str | None | LLM model (e.g., "openai:gpt-4o") |
| `yolo` | bool | False | Auto-approve all actions |
| `permissions` | PermissionConfig | None | Permission configuration |
| `system_prompt` | str | None | Override system prompt |

#### Methods

##### run()

Execute a prompt and return the result.

```python
result = agent.run(prompt: str) -> AgentResult
```

**Parameters:**
- `prompt`: The user prompt to execute

**Returns:** `AgentResult` with:
- `output`: Final response text
- `stats`: Execution statistics
- `interrupted`: Whether HITL approval is needed

##### resume()

Resume an interrupted session.

```python
result = agent.resume(decisions: list[dict]) -> AgentResult
```

**Parameters:**
- `decisions`: List of approval decisions (e.g., `[{"type": "approve"}]`)

**Returns:** `AgentResult`

##### get_tools()

Get all available tools.

```python
tools = agent.get_tools() -> list[Tool]
```

#### Example

```python
from kai_code import KaiAgent, PermissionConfig

# Create agent with custom permissions
perms = PermissionConfig(
    allowed_tools=["ls", "read_file", "glob", "grep"],
    allowed_commands=["python *", "pytest *"]
)

agent = KaiAgent(
    root_dir="./my-project",
    model="openai:gpt-4o",
    permissions=perms,
    yolo=False
)

# Run a task
result = agent.run("Explain the project structure")
print(result.output)

# If interrupted, resume with approval
if result.interrupted:
    result = agent.resume([{"type": "approve"}])
    print(result.output)
```

---

### DbtAgent

Specialized agent for dbt data engineering.

```python
from kai_code.agents.dbt import DbtAgent
```

#### Constructor

```python
DbtAgent(
    root_dir: str = ".",
    model: str = None,
    yolo: bool = False,
    db_path: str = None,
    profile: str = None,
    target: str = None,
    **kwargs
)
```

**Additional Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | str | None | Path to DuckDB database |
| `profile` | str | None | dbt profile name |
| `target` | str | None | dbt target environment |

#### Example

```python
from kai_code.agents.dbt import DbtAgent

agent = DbtAgent(
    root_dir="./dbt_project",
    model="openai:gpt-4o",
    db_path="warehouse.duckdb",
    yolo=True
)

result = agent.run("Show me the schema of the orders table")
print(result.output)
```

---

### PermissionConfig

Configure agent permissions.

```python
from kai_code import PermissionConfig
```

#### Constructor

```python
PermissionConfig(
    allowed_tools: list[str] = None,
    disallowed_tools: list[str] = None,
    allowed_commands: list[str] = None,
    disallowed_commands: list[str] = None
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `allowed_tools` | list[str] | Tools that can run without approval |
| `disallowed_tools` | list[str] | Tools that are blocked |
| `allowed_commands` | list[str] | Glob patterns for allowed shell commands |
| `disallowed_commands` | list[str] | Glob patterns for blocked shell commands |

#### Example

```python
from kai_code import PermissionConfig

# Read-only configuration
readonly_perms = PermissionConfig(
    allowed_tools=["ls", "read_file", "glob", "grep"],
    disallowed_tools=["write_file", "edit_file", "execute", "apply_patch"]
)

# Restricted commands
safe_perms = PermissionConfig(
    allowed_commands=["python *", "pytest *", "git status", "git diff"],
    disallowed_commands=["rm *", "sudo *", "git push *"]
)
```

---

## Prompt System

### load_prompt()

Load a system prompt with inheritance support.

```python
from kai_code.prompts import load_prompt

prompt = load_prompt(name: str) -> str
```

**Parameters:**
- `name`: Prompt name (without .md extension)

**Returns:** Full prompt text including inherited content

**Example:**

```python
from kai_code.prompts import load_prompt

# Load base prompt
base = load_prompt("kai-code")

# Load dbt prompt (includes kai-code via inheritance)
dbt = load_prompt("kai-dbt")
```

---

## Client Helpers

### get_client()

Get a client wrapper for the agent.

```python
from kai_code import get_client

client = get_client(root_dir: str = ".") -> KaiClient
```

### create_agent()

Create an agent with simplified configuration.

```python
from kai_code import create_agent

agent = create_agent(
    root_dir: str = ".",
    model: str = None
) -> KaiAgent
```

### handle_headless_command()

Execute CLI commands programmatically.

```python
from kai_code import handle_headless_command

result = handle_headless_command(args: list[str]) -> int
```

**Example:**

```python
from kai_code import handle_headless_command

# Run a headless command
exit_code = handle_headless_command([
    "--new",
    "-p", "Hello world",
    "--output-format", "json"
])
```

---

## Result Types

### AgentResult

Returned by `agent.run()` and `agent.resume()`.

```python
class AgentResult:
    output: str           # Final response text
    stats: dict           # Execution statistics
    interrupted: bool     # True if HITL approval needed
    thread_id: str        # Session thread ID
    state_path: str       # Path to session state
```

**Stats dictionary:**

```python
{
    "stop_reason": "end_turn",  # end_turn, interrupt, error
    "ttft_ms": 1234,            # Time to first token
    "token_usage": {
        "input": 1000,
        "output": 500
    },
    "turn_count": 3,
    "step_count": 5
}
```

---

## Tool Definitions

### Available Tools

| Tool | Description |
|------|-------------|
| `ls` | List directory contents |
| `read_file` | Read file contents |
| `write_file` | Create or overwrite a file |
| `edit_file` | Edit an existing file |
| `glob` | Find files matching a pattern |
| `grep` | Search file contents |
| `execute` | Execute shell commands |
| `apply_patch` | Apply a diff patch |

### Creating Custom Tools

```python
from langchain_core.tools import tool

@tool("my_custom_tool")
def my_custom_tool(arg1: str, arg2: int = 10) -> str:
    """Tool description for the LLM.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value
    """
    return f"Result: {arg1}, {arg2}"
```

---

## Stream Events

For `--output-format stream-json`:

### Event Types

| Type | Description |
|------|-------------|
| `init` | Run metadata |
| `message` | Assistant response deltas |
| `tool_call` | Tool invocation |
| `tool_result` | Tool result |
| `error` | Exception |
| `result` | Final summary |

### Event Structure

```json
{
  "event_id": 1,
  "type": "message",
  "content": "Hello...",
  "delta": "...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

See [Stream JSON Schema](../stream-json-schema.md) for full details.

---

## Configuration Loading

### load_settings()

Load merged settings from all sources.

```python
from kai_code.settings import load_settings

settings = load_settings(root_dir: str = ".") -> dict
```

### Settings Priority

1. CLI flags (highest)
2. Local settings (`.kai/settings.local.json`)
3. Project settings (`.kai/settings.json`)
4. Global settings (`~/.kai/settings.json`) (lowest)
