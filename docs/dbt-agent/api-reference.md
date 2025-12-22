# DbtAgent API Reference

## DbtAgent Class

```python
from kai_code.agents import DbtAgent
```

### Constructor

```python
DbtAgent(
    root_dir: str | Path,
    model: str = "openai:gpt-4o",
    db_connection: str | None = None,
    dbt_project_dir: str | Path | None = None,
    dbt_profiles_dir: str | Path | None = None,
    yolo: bool = True,
    system_prompt: str | None = None,
    skills_dir: str = ".skills",
    state_path: str | Path | None = None,
    **kwargs
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `root_dir` | `str \| Path` | required | Project root directory. All paths are relative to this. |
| `model` | `str` | `"openai:gpt-4o"` | LLM model handle (LangChain format) |
| `db_connection` | `str \| None` | `None` | Database connection string for introspection |
| `dbt_project_dir` | `str \| Path \| None` | `None` | dbt project directory (defaults to root_dir) |
| `dbt_profiles_dir` | `str \| Path \| None` | `None` | profiles.yml location (defaults to ~/.dbt) |
| `yolo` | `bool` | `True` | If False, require approval for dbt commands |
| `system_prompt` | `str \| None` | `None` | Additional system prompt (appended to base) |
| `skills_dir` | `str` | `".skills"` | Skills directory relative to root_dir |
| `state_path` | `str \| Path \| None` | `None` | Session state file (defaults to .kai/session.json) |

#### Connection String Formats

```python
# DuckDB (file)
db_connection = "analytics.duckdb"
db_connection = "duckdb:///path/to/analytics.duckdb"

# PostgreSQL
db_connection = "postgresql://user:password@host:5432/database"
db_connection = "postgresql://user:password@host/database?sslmode=require"

# Future support
db_connection = "snowflake://user:password@account/database/schema"
db_connection = "bigquery://project/dataset"
```

### Methods

#### run()

```python
def run(self, prompt: str) -> KaiResult
```

Execute a prompt and return the result.

**Parameters**:
- `prompt`: The task or question for the agent

**Returns**: `KaiResult` with output, messages, and raw state

**Example**:
```python
result = agent.run("Create a staging model for the orders table")
print(result.output)
```

#### stream()

```python
def stream(self, prompt: str) -> Iterator[StreamEvent]
```

Execute a prompt with streaming output.

**Parameters**:
- `prompt`: The task or question for the agent

**Yields**: `StreamEvent` objects with incremental output

**Example**:
```python
for event in agent.stream("Build the customer analytics pipeline"):
    if event.type == "message":
        print(event.content, end="")
```

#### reset()

```python
def reset(self) -> None
```

Clear conversation history and reset state.

**Example**:
```python
agent.reset()
result = agent.run("Start fresh with a new project")
```

#### fork()

```python
def fork(self, state_path: str | Path) -> DbtAgent
```

Create a copy of the agent with a different state file.

**Parameters**:
- `state_path`: Path for the new agent's state

**Returns**: New `DbtAgent` instance

**Example**:
```python
experiment = agent.fork("/tmp/experiment_state.json")
result = experiment.run("Try an alternative approach")
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `adapter` | `DatabaseAdapter` | Database adapter instance |
| `dbt_project_dir` | `Path` | dbt project directory |
| `dbt_profiles_dir` | `Path` | profiles.yml directory |
| `db_connection` | `str` | Database connection string |

---

## DatabaseAdapter Classes

### Base Class

```python
from kai_code.agents.dbt.adapters import DatabaseAdapter
```

```python
class DatabaseAdapter(ABC):
    @abstractmethod
    def get_tables(self) -> list[TableInfo]: ...

    @abstractmethod
    def get_columns(self, table: str) -> list[ColumnInfo]: ...

    @abstractmethod
    def get_cardinality(self, table: str, column: str) -> CardinalityInfo: ...

    @abstractmethod
    def execute_query(self, sql: str, limit: int = 100) -> QueryResult: ...

    @abstractmethod
    def close(self) -> None: ...
```

### DuckDBAdapter

```python
from kai_code.agents.dbt.adapters import DuckDBAdapter

adapter = DuckDBAdapter("analytics.duckdb")
```

### PostgreSQLAdapter

```python
from kai_code.agents.dbt.adapters import PostgreSQLAdapter

adapter = PostgreSQLAdapter("postgresql://user:pass@localhost/db")
```

### Factory Function

```python
from kai_code.agents.dbt.adapters import get_adapter

adapter = get_adapter("postgresql://user:pass@localhost/db")
```

---

## Data Classes

### TableInfo

```python
@dataclass
class TableInfo:
    name: str
    schema: str
    full_name: str  # schema.table
    description: str | None
    column_count: int
    row_count: int | None
```

### ColumnInfo

```python
@dataclass
class ColumnInfo:
    name: str
    data_type: str
    description: str | None
    is_nullable: bool
    is_primary_key: bool
    foreign_key: ForeignKeyInfo | None
    is_low_cardinality: bool
    categories: list[str] | None  # For low-cardinality columns
```

### ForeignKeyInfo

```python
@dataclass
class ForeignKeyInfo:
    reference_table: str
    reference_column: str
```

### CardinalityInfo

```python
@dataclass
class CardinalityInfo:
    table: str
    column: str
    distinct_count: int
    total_count: int
    sample_values: list[Any]
    is_low_cardinality: bool  # < 50 distinct values
```

### QueryResult

```python
@dataclass
class QueryResult:
    success: bool
    columns: list[str]
    rows: list[dict]
    row_count: int
    truncated: bool
    error: str | None
```

### KaiResult

```python
@dataclass
class KaiResult:
    output: str              # Final assistant response
    messages: list[dict]     # Conversation history
    raw: dict                # Raw LangGraph state
```

---

## Exceptions

```python
from kai_code.agents.dbt.exceptions import (
    DbtAgentError,
    DatabaseConnectionError,
    DbtExecutionError,
    AdapterNotFoundError,
)
```

| Exception | Description |
|-----------|-------------|
| `DbtAgentError` | Base exception for DbtAgent |
| `DatabaseConnectionError` | Failed to connect to database |
| `DbtExecutionError` | dbt command failed |
| `AdapterNotFoundError` | No adapter for connection string |

---

## Usage Examples

### Basic Usage

```python
from kai_code.agents import DbtAgent

agent = DbtAgent(
    root_dir="/path/to/project",
    db_connection="postgresql://localhost/analytics",
)

result = agent.run("List all available tables and their descriptions")
print(result.output)
```

### With DuckDB

```python
agent = DbtAgent(
    root_dir=".",
    db_connection="warehouse.duckdb",
    yolo=True,
)

result = agent.run("Create staging models for all source tables")
```

### Approval Mode

```python
agent = DbtAgent(
    root_dir=".",
    db_connection="postgresql://prod@localhost/analytics",
    yolo=False,  # Require approval for dbt commands
)

result = agent.run("Run the full pipeline")
# Agent will pause for approval before dbt run
```

### Custom System Prompt

```python
agent = DbtAgent(
    root_dir=".",
    db_connection="analytics.duckdb",
    system_prompt="""
    Additional guidelines:
    - Always use incremental models for fact tables
    - Follow our naming convention: {layer}_{domain}__{entity}
    - Include row counts in all test descriptions
    """,
)
```

### Streaming

```python
agent = DbtAgent(root_dir=".", db_connection="analytics.duckdb")

for event in agent.stream("Build customer segmentation"):
    if event.type == "tool_call":
        print(f"Using tool: {event.tool_name}")
    elif event.type == "message":
        print(event.content, end="", flush=True)
```
