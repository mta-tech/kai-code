# DbtAgent Design Document

**Date**: 2024-12-22
**Status**: Approved
**Author**: Brainstorming session

---

## Overview

DbtAgent is a specialized kai-code agent for building end-to-end data pipelines using dbt. It extends `KaiAgent` to add dbt-specific capabilities while retaining all generic coding abilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DbtAgent(KaiAgent)                       │
│  - Inherits all KaiAgent capabilities                       │
│  - Auto-loads .skills/dbt/ skill                            │
│  - Injects dbt core concepts into system prompt             │
│  - Registers dbt-specific tools                             │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  dbt Skill    │    │  dbt Tools    │    │  dbt_docs/    │
│  (.skills/)   │    │  (Python)     │    │  (Reference)  │
│               │    │               │    │               │
│ - Workflow    │    │ - Schema      │    │ - Concepts    │
│ - Conventions │    │ - MDL         │    │ - Commands    │
│ - Templates   │    │ - SQL         │    │ - Testing     │
│ - Examples    │    │ - dbt CLI     │    │ - Jinja       │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Key Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Database support | Multi-DB, starting with DuckDB + PostgreSQL | Common starting points, extensible |
| Documentation | Hybrid: core in prompt + tools for dbt_docs/ | Balance speed vs flexibility |
| Use case | Both greenfield and maintenance | Versatile agent |
| Execution | Full dbt CLI, controlled by YOLO mode | Integrates with kai-code permissions |
| Structure | Skill-based + DbtAgent class | Portable + convenient |
| Introspection | dbt commands + direct SQL | Best of both worlds |
| Semantic layer | dbt semantic + custom MDL support | Maximum flexibility |
| Instructions | dbt meta: + dedicated instruction files | Multiple sources |
| Initialization | Templates + interactive scaffolding | Speed + customization |
| Inheritance | Extends KaiAgent | Keeps all generic abilities |

## Tools

### Schema Tools (Direct SQL)

| Tool | Description |
|------|-------------|
| `get_database_schema()` | Full schema with tables, columns, types, descriptions |
| `get_table_details(table)` | Columns, PKs, FKs, sample data for specific table |
| `get_column_cardinality(table, column)` | Distinct values count + sample values |
| `get_filterable_columns(table?)` | Low-cardinality columns with allowed values |
| `search_schema(pattern)` | Grep-like search across tables/columns/descriptions |

### MDL/Semantic Tools

| Tool | Description |
|------|-------------|
| `get_mdl_manifest()` | Overview of semantic models, metrics, relationships |
| `explore_mdl_model(model)` | Model details with columns, calculated fields |
| `get_mdl_relationships(model?)` | Join paths and relationship types |
| `get_mdl_metrics(metric?)` | Business metric definitions |

### Instruction Tools

| Tool | Description |
|------|-------------|
| `get_instructions()` | All custom instructions for the project |
| `get_dbt_meta(model)` | Read meta: properties from schema.yml |

### dbt CLI Tools

| Tool | Description |
|------|-------------|
| `dbt_run(select?, exclude?)` | Run models with selection |
| `dbt_test(select?)` | Run tests with structured results |
| `dbt_compile(model)` | Compile and return generated SQL |
| `dbt_show(model, limit?)` | Preview model output |
| `dbt_list(select?, resource_type?)` | List resources matching criteria |

## Database Adapter

Abstraction layer for database-agnostic introspection:

```python
from abc import ABC, abstractmethod

class DatabaseAdapter(ABC):
    @abstractmethod
    def get_tables(self) -> list[TableInfo]: ...

    @abstractmethod
    def get_columns(self, table: str) -> list[ColumnInfo]: ...

    @abstractmethod
    def get_cardinality(self, table: str, column: str) -> CardinalityInfo: ...

    @abstractmethod
    def execute_query(self, sql: str, limit: int = 100) -> QueryResult: ...


class DuckDBAdapter(DatabaseAdapter): ...
class PostgreSQLAdapter(DatabaseAdapter): ...


def get_adapter(connection_string: str) -> DatabaseAdapter:
    """Factory function to get appropriate adapter."""
    ...
```

## DbtAgent Class

```python
from kai_code import KaiAgent

class DbtAgent(KaiAgent):
    """
    Inherits ALL KaiAgent capabilities:
    - File operations (read, write, edit, glob, grep)
    - Shell execution (execute)
    - Patch application (apply_patch)
    - Skills system (.skills/)
    - YOLO/approval modes
    - Session persistence

    Adds dbt-specific capabilities:
    - Schema introspection tools
    - MDL/semantic layer tools
    - dbt CLI wrapper tools
    - dbt skill auto-loading
    - Database adapter connection
    """

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

        if db_connection:
            self._register_dbt_tools()
```

## Skill Structure

```
.skills/dbt/
├── SKILL.md              # Main skill instructions
├── templates/            # Project templates
│   ├── ecommerce/
│   ├── saas_metrics/
│   └── financial/
├── instructions/         # Business rules
│   └── default.yaml
└── examples/             # Reference implementations
    ├── staging_model.sql
    ├── incremental_model.sql
    └── schema.yml
```

## Agent Workflow

```
1. UNDERSTAND
   ├─ Read dbt_docs/ for relevant concepts
   ├─ get_database_schema() - explore available data
   ├─ get_instructions() - check business rules
   └─ get_mdl_manifest() - understand semantic layer

2. DESIGN
   ├─ Plan layer structure (staging → marts)
   ├─ Identify dependencies (ref graph)
   └─ Select materializations

3. BUILD
   ├─ Create models incrementally
   ├─ dbt_compile() - validate SQL before run
   ├─ dbt_run(--select model) - build one at a time
   └─ dbt_test(--select model) - test immediately

4. VALIDATE
   ├─ dbt_show() - preview results
   ├─ Run full test suite
   └─ Generate documentation
```

## File Structure

```
src/kai_code/
├── agents/
│   ├── __init__.py              # Export DbtAgent
│   └── dbt/
│       ├── __init__.py
│       ├── agent.py             # DbtAgent class
│       ├── adapters.py          # DuckDB/PostgreSQL adapters
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── schema_tools.py
│       │   ├── mdl_tools.py
│       │   ├── instruction_tools.py
│       │   └── dbt_cli_tools.py
│       └── templates/

dbt_docs/                        # Reference documentation (exists)
```

## Implementation Order

1. Database adapters (DuckDB, PostgreSQL)
2. Schema tools (introspection)
3. dbt CLI tools (run, test, compile)
4. DbtAgent class
5. Skill files (SKILL.md, templates)
6. MDL/instruction tools (enhancement)

## Usage Examples

```python
from kai_code.agents import DbtAgent

# Initialize agent
agent = DbtAgent(
    root_dir="/path/to/project",
    db_connection="postgresql://user:pass@localhost/analytics",
    yolo=True,
)

# Pure dbt work
result = agent.run("Create RFM segmentation model")

# Generic coding (inherited from KaiAgent)
result = agent.run("Write a Python script to validate CSV files")

# Mixed workflow
result = agent.run("Create staging models and write pytest to verify row counts")
```

## References

- KAI tools implementation: `~/project/mta/iba/services/KAI/app/modules/autonomous_agent/tools/`
- dbt documentation: `dbt_docs/` folder
- kai-code spec: `spec.md`
