# DbtAgent Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User Request                                │
│                   "Create customer segmentation model"                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DbtAgent(KaiAgent)                            │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Inherited from KaiAgent                         │ │
│  │  • File operations (read, write, edit, glob, grep)                 │ │
│  │  • Shell execution (execute)                                       │ │
│  │  • Patch application (apply_patch)                                 │ │
│  │  • Skills system loading                                           │ │
│  │  • YOLO/approval permission modes                                  │ │
│  │  • Session persistence (.kai/)                                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      DbtAgent Extensions                           │ │
│  │  • Database adapter connection                                     │ │
│  │  • dbt-specific tools registration                                 │ │
│  │  • Auto-loading of dbt skill                                       │ │
│  │  • dbt core concepts in system prompt                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│   dbt Skill       │   │   dbt Tools       │   │   dbt_docs/       │
│   (.skills/dbt/)  │   │   (Python)        │   │   (Reference)     │
│                   │   │                   │   │                   │
│ • SKILL.md        │   │ • Schema Tools    │   │ • Core concepts   │
│ • Workflow rules  │   │ • MDL Tools       │   │ • Commands ref    │
│ • Conventions     │   │ • Instruction     │   │ • Testing guide   │
│ • Templates       │   │ • dbt CLI         │   │ • Jinja macros    │
│ • Examples        │   │                   │   │ • Best practices  │
└───────────────────┘   └───────────────────┘   └───────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Database Adapter Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  DuckDBAdapter  │  │ PostgreSQLAdapter│  │  Future Adapters │         │
│  │                 │  │                 │  │                 │         │
│  │ • get_tables()  │  │ • get_tables()  │  │ • Snowflake     │         │
│  │ • get_columns() │  │ • get_columns() │  │ • BigQuery      │         │
│  │ • get_cardinal  │  │ • get_cardinal  │  │ • Redshift      │         │
│  │ • execute_query │  │ • execute_query │  │ • Databricks    │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Data Warehouse                               │
│                    (DuckDB, PostgreSQL, Snowflake, etc.)                │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. DbtAgent Class

**Location**: `src/kai_code/agents/dbt/agent.py`

The main agent class that extends KaiAgent:

```python
class DbtAgent(KaiAgent):
    def __init__(
        self,
        root_dir: str,
        model: str = "openai:gpt-4o",
        db_connection: str | None = None,
        dbt_project_dir: str | None = None,
        dbt_profiles_dir: str | None = None,
        **kwargs
    ):
        super().__init__(root_dir=root_dir, model=model, **kwargs)

        self.db_connection = db_connection
        self.dbt_project_dir = dbt_project_dir or root_dir
        self.dbt_profiles_dir = dbt_profiles_dir

        # Initialize database adapter
        if db_connection:
            self.adapter = get_adapter(db_connection)
            self._register_dbt_tools()

        # Inject dbt core concepts into system prompt
        self._inject_dbt_prompt()
```

**Responsibilities**:
- Initialize database adapter based on connection string
- Register dbt-specific tools
- Inject dbt knowledge into system prompt
- Auto-load dbt skill from `.skills/dbt/`

### 2. Database Adapters

**Location**: `src/kai_code/agents/dbt/adapters.py`

Abstract base class and implementations for database introspection:

```python
class DatabaseAdapter(ABC):
    @abstractmethod
    def get_tables(self) -> list[TableInfo]:
        """Get all tables with metadata."""

    @abstractmethod
    def get_columns(self, table: str) -> list[ColumnInfo]:
        """Get columns for a specific table."""

    @abstractmethod
    def get_cardinality(self, table: str, column: str) -> CardinalityInfo:
        """Get distinct value count and samples."""

    @abstractmethod
    def execute_query(self, sql: str, limit: int = 100) -> QueryResult:
        """Execute read-only SQL query."""
```

**Adapter Selection**:

```python
def get_adapter(connection_string: str) -> DatabaseAdapter:
    if connection_string.endswith((".duckdb", ".db")):
        return DuckDBAdapter(connection_string)
    elif "duckdb:///" in connection_string:
        return DuckDBAdapter(connection_string.replace("duckdb:///", ""))
    elif connection_string.startswith("postgresql://"):
        return PostgreSQLAdapter(connection_string)
    else:
        raise ValueError(f"Unsupported database: {connection_string}")
```

### 3. Tools Layer

**Location**: `src/kai_code/agents/dbt/tools/`

Four categories of tools:

#### Schema Tools (`schema_tools.py`)
```python
def create_schema_tools(adapter: DatabaseAdapter) -> list[Tool]:
    return [
        get_database_schema,    # Full schema overview
        get_table_details,      # Specific table info
        get_column_cardinality, # Distinct values
        get_filterable_columns, # Low-cardinality columns
        search_schema,          # Pattern search
    ]
```

#### MDL Tools (`mdl_tools.py`)
```python
def create_mdl_tools(root_dir: Path) -> list[Tool]:
    return [
        get_mdl_manifest,       # Semantic layer overview
        explore_mdl_model,      # Model details
        get_mdl_relationships,  # Join paths
        get_mdl_metrics,        # Business metrics
    ]
```

#### Instruction Tools (`instruction_tools.py`)
```python
def create_instruction_tools(root_dir: Path) -> list[Tool]:
    return [
        get_instructions,       # Custom business rules
        get_dbt_meta,           # schema.yml meta properties
    ]
```

#### dbt CLI Tools (`dbt_cli_tools.py`)
```python
def create_dbt_cli_tools(project_dir: Path, profiles_dir: Path) -> list[Tool]:
    return [
        dbt_run,      # Run models
        dbt_test,     # Run tests
        dbt_compile,  # Compile SQL
        dbt_show,     # Preview data
        dbt_list,     # List resources
    ]
```

### 4. Skill System

**Location**: `.skills/dbt/`

The dbt skill provides:

```
.skills/dbt/
├── SKILL.md              # Main instructions (embedded in prompt)
│
├── templates/            # Project templates
│   ├── ecommerce/
│   │   ├── manifest.yaml
│   │   ├── dbt_project.yml
│   │   └── models/
│   ├── saas_metrics/
│   └── financial/
│
├── instructions/         # Business rules
│   └── default.yaml
│
└── examples/             # Reference code
    ├── staging_model.sql
    ├── incremental_model.sql
    └── schema.yml
```

### 5. Documentation Layer

**Location**: `dbt_docs/`

Reference documentation accessible via file tools:

```
dbt_docs/
├── README.md                    # Overview and learning path
├── 01_core_concepts.md          # Models, sources, materializations
├── 02_project_structure.md      # Project organization
├── 03_commands_reference.md     # CLI commands
├── 04_testing_strategies.md     # Testing patterns
├── 05_jinja_macros.md           # Jinja templating
├── 06_production_best_practices.md
├── 07_getting_started_example.md
└── 08_agent_development_guide.md
```

## Data Flow

### Request Processing

```
1. User Request
   │
   ▼
2. DbtAgent.run(prompt)
   │
   ├─► System prompt includes:
   │   • KaiAgent base prompt
   │   • dbt core concepts (from SKILL.md)
   │   • Available tools list
   │
   ▼
3. LLM decides tool usage
   │
   ├─► Schema tools → DatabaseAdapter → SQL → Results
   ├─► MDL tools → File read → Parse → Results
   ├─► dbt CLI tools → subprocess → Parse output → Results
   └─► File tools (inherited) → Filesystem → Results
   │
   ▼
4. LLM processes results, may loop
   │
   ▼
5. Final response to user
```

### Agent Workflow (Embedded in Skill)

```
UNDERSTAND
├── Read dbt_docs/ for concepts
├── get_database_schema()
├── get_instructions()
└── get_mdl_manifest()
        │
        ▼
DESIGN
├── Plan layer structure
├── Identify dependencies
└── Select materializations
        │
        ▼
BUILD (iterative)
├── Create model file
├── dbt_compile() - validate
├── dbt_run(--select model)
└── dbt_test(--select model)
        │
        ▼
VALIDATE
├── dbt_show() - preview
├── Full test suite
└── Generate documentation
```

## Permission Integration

DbtAgent respects kai-code's permission system:

| Mode | dbt Behavior |
|------|--------------|
| `yolo=True` | All dbt commands execute without approval |
| `yolo=False` | `dbt run`, `dbt test` require approval |
| `permission_mode='plan'` | Only `dbt compile`, `dbt list` allowed |
| `permission_mode='acceptEdits'` | Model creation allowed, execution needs approval |

## Extension Points

### Adding New Database Adapter

```python
class SnowflakeAdapter(DatabaseAdapter):
    def __init__(self, connection_string: str):
        # Parse connection string
        # Initialize snowflake connector

    def get_tables(self) -> list[TableInfo]:
        # Query INFORMATION_SCHEMA

    # ... implement other methods

# Register in get_adapter()
def get_adapter(connection_string: str) -> DatabaseAdapter:
    # ... existing adapters ...
    elif connection_string.startswith("snowflake://"):
        return SnowflakeAdapter(connection_string)
```

### Adding New Tools

```python
# In tools/__init__.py
def create_all_tools(agent: DbtAgent) -> list[Tool]:
    tools = []
    tools.extend(create_schema_tools(agent.adapter))
    tools.extend(create_mdl_tools(agent.root_dir))
    tools.extend(create_instruction_tools(agent.root_dir))
    tools.extend(create_dbt_cli_tools(agent.dbt_project_dir, agent.dbt_profiles_dir))

    # Add custom tools here
    tools.extend(create_custom_tools(agent))

    return tools
```

### Customizing Skill

Modify `.skills/dbt/SKILL.md` to:
- Add company-specific conventions
- Define custom layer patterns
- Include domain-specific examples
