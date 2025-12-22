# DbtAgent Developer Guide

DbtAgent is a specialized kai-code agent for building end-to-end data pipelines using dbt (data build tool).

## Overview

DbtAgent extends `KaiAgent` to add dbt-specific capabilities while retaining all generic coding abilities:

- **Inherited from KaiAgent**: File operations, shell execution, patch application, skills system, YOLO/approval modes, session persistence
- **Added by DbtAgent**: Schema introspection, MDL/semantic layer tools, dbt CLI wrappers, project templates

## Quick Start

```python
from kai_code.agents import DbtAgent

# Initialize agent with database connection
agent = DbtAgent(
    root_dir="/path/to/dbt/project",
    db_connection="postgresql://user:pass@localhost/analytics",
    yolo=True,  # Allow dbt execution without approval
)

# Run dbt tasks
result = agent.run("Create a customer segmentation model using RFM analysis")

# Generic coding still works
result = agent.run("Write a Python script to validate the source CSV files")
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System design and component overview |
| [API Reference](api-reference.md) | DbtAgent class and method documentation |
| [Tools Reference](tools-reference.md) | All dbt-specific tools |
| [Skill Guide](skill-guide.md) | Customizing the dbt skill |
| [Examples](examples.md) | Usage examples and patterns |

## Key Concepts

### Database Adapters

DbtAgent uses database adapters for direct SQL introspection:

```python
# Automatic adapter selection based on connection string
agent = DbtAgent(
    root_dir=".",
    db_connection="duckdb:///analytics.duckdb",  # Uses DuckDBAdapter
)

agent = DbtAgent(
    root_dir=".",
    db_connection="postgresql://localhost/db",  # Uses PostgreSQLAdapter
)
```

### Hybrid Documentation

The agent uses a hybrid approach for dbt knowledge:

1. **Core concepts** embedded in system prompt (fast access)
2. **Detailed docs** in `dbt_docs/` accessed via file tools (comprehensive)

### Tool Categories

| Category | Purpose |
|----------|---------|
| Schema Tools | Database introspection (tables, columns, cardinality) |
| MDL Tools | Semantic layer exploration (models, metrics, relationships) |
| Instruction Tools | Business rules and guidelines |
| dbt CLI Tools | Wrapped dbt commands with structured output |

## Project Structure

```
src/kai_code/
├── agents/
│   ├── __init__.py          # Exports DbtAgent
│   └── dbt/
│       ├── __init__.py
│       ├── agent.py          # DbtAgent class
│       ├── adapters.py       # Database adapters
│       └── tools/
│           ├── schema_tools.py
│           ├── mdl_tools.py
│           ├── instruction_tools.py
│           └── dbt_cli_tools.py

.skills/dbt/                   # Skill files (copied to projects)
├── SKILL.md
├── templates/
└── examples/

dbt_docs/                      # Reference documentation
├── 01_core_concepts.md
├── 02_project_structure.md
└── ...
```

## Supported Databases

| Database | Adapter | Status |
|----------|---------|--------|
| DuckDB | `DuckDBAdapter` | Primary |
| PostgreSQL | `PostgreSQLAdapter` | Primary |
| Snowflake | `SnowflakeAdapter` | Planned |
| BigQuery | `BigQueryAdapter` | Planned |

## Next Steps

1. Read [Architecture](architecture.md) for system design
2. Check [API Reference](api-reference.md) for class details
3. See [Examples](examples.md) for common patterns
