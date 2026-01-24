# Kai Seeknal Agent

A specialized AI agent for data engineering and data science using the [Seeknal library](https://github.com/mta-tech/seeknal).

## Overview

Kai Seeknal is a specialized version of Kai Code that focuses on:
- **Feature Store Management**: Create, version, and serve features for ML models
- **Data Pipeline Orchestration**: Build multi-engine data flows (DuckDB + Spark)
- **Entity Management**: Define join keys and relationships
- **Feature Engineering**: Transformations, aggregations, and validators
- **Offline/Online Stores**: Batch processing and real-time serving
- **Data Validation**: SQL injection prevention and path security

## Installation

The SeeknalAgent is included in the `kai-code` package. Ensure you have it installed:

```bash
pip install kai-code
```

## Quick Start

### Command Line Interface

```bash
# Launch interactive CLI
kai-seeknal

# Run with initial prompt
kai-seeknal "Create a feature group named user_features"

# Auto-approve mode (dangerous)
kai-seeknal -y "Create a project named ml_features"

# Specify custom Seeknal path
kai-seeknal --seeknal-path /path/to/seeknal "List all projects"
```

### Python API

```python
from pathlib import Path
from kai_code.agents.seeknal import SeeknalAgent

# Initialize agent
agent = SeeknalAgent(
    root_dir=Path.cwd(),
    seeknal_path=Path.home() / "project" / "mta" / "signal",
    yolo=True,  # Auto-approve actions
)

# Run a task
result = agent.run("Create a new project named 'ml_features'")
print(result.output)

# Save session
agent.save()
```

## Features

### 1. Project Management

```python
# Create a new project
agent.run("Create project 'analytics' with description 'Customer analytics pipeline'")

# List all projects
agent.run("List all Seeknal projects")

# Delete a project
agent.run("Delete project 'old_project'")
```

### 2. Entity Management

```python
# Create an entity
agent.run("Create entity 'user' with join keys 'user_id'")

# Get entity details
agent.run("Show details for entity 'user'")
```

### 3. Feature Store Operations

```python
# Create a feature group
agent.run("""
    Create feature group 'user_features' with entity 'user',
    event_time_col 'created_at', in project 'analytics'
""")

# Materialize features to offline store
agent.run("Materialize feature group 'user_features' starting from 2024-01-01")

# List feature groups
agent.run("List all feature groups")

# Delete feature group
agent.run("Delete feature group 'old_features'")
```

### 4. Data Pipelines (Flows)

```python
# Create a data pipeline
agent.run("""
    Create a flow named 'transform_data' that reads from PARQUET file
    'data/raw.parquet' and runs a DuckDB task to select user_id,
    count(*) as purchase_count
""")

# Run a flow
agent.run("Run flow 'transform_data'")

# List flows
agent.run("List all flows")
```

### 5. Version Management

```python
# List all versions of a feature group
agent.run("List all versions of feature group 'user_features'")

# Show specific version
agent.run("Show version 2 of feature group 'user_features'")

# Compare versions
agent.run("Compare version 1 and 2 of feature group 'user_features'")

# Materialize specific version (rollback)
agent.run("Materialize version 1 of feature group 'user_features'")
```

### 6. Data Validation

```python
# Validate SQL identifiers
agent.run("Validate SQL identifier 'user_features'")

# Validate table names
agent.run("Validate table name 'raw.customers'")

# Validate column names
agent.run("Validate column name 'customer_id'")

# Validate file paths
agent.run("Validate file path '~/.seeknal/feature_store'")

# Validate features in feature group
agent.run("Validate features in feature group 'user_features' with mode 'fail'")
```

## Architecture

### Agent Structure

```
SeeknalAgent
├── Inherits: KaiAgent (all base capabilities)
├── Prompt: kai-seeknal.md (inherits from kai-code.md)
└── Tools:
    ├── Project Tools: init, list, get, delete projects
    ├── Flow Tools: create, run, list flows
    ├── Feature Store Tools: create, write, read, delete feature groups
    ├── Entity Tools: create, list, get entities
    ├── Version Tools: list, show, compare versions
    └── Validation Tools: validate SQL, tables, columns, paths, features
```

### Prompt Inheritance

The `kai-seeknal.md` prompt inherits from `kai-code.md`, adding:

- Seeknal-specific role and expertise
- Data engineering best practices
- Feature store patterns
- Security and validation guidelines
- Engine selection recommendations (DuckDB vs Spark)
- Production deployment strategies

### Engine Selection

The agent helps you choose the right engine:

| Engine | Use Case | Dataset Size | Setup |
|--------|----------|--------------|-------|
| **DuckDB** | Default choice | <100M rows | Pure Python, pip install |
| **Spark** | Big data, distributed | >100M rows | JVM, Spark installation |

## Security Best Practices

The agent enforces Seeknal security guidelines:

1. **SQL Injection Prevention**: Always validates SQL identifiers
2. **Path Security**: Validates file paths, warns about insecure locations
3. **No `/tmp` Usage**: Recommends `~/.seeknal/` or cloud storage
4. **Input Validation**: Validates all user inputs before database operations

## Configuration

### Command Line Arguments

```
kai-seeknal [OPTIONS] [PROMPT]

Options:
  -y, --yes              Auto-approve all tool actions
  --no-splash            Skip startup banner
  --seeknal-path PATH    Path to Seeknal library
  -m, --model MODEL      LLM model to use
  --ralph                Enable Ralph autonomous loop
  --ralph-promise STR    Completion promise for Ralph
  --ralph-max-iterations N  Max Ralph iterations (default: 50)
  --ralph-timeout SEC    Wall-clock timeout
  --ralph-token-limit N  Max tokens (default: 500000)
  -v, --version          Show version
  --help-commands        Show available slash commands
```

### Environment Variables

- `SEEKNAL_BASE_CONFIG_PATH`: Base directory for Seeknal config
- `SEEKNAL_USER_CONFIG_PATH`: User config file path
- `TURSO_DATABASE_URL`: Turso database URL (for production)
- `TURSO_AUTH_TOKEN`: Turso authentication token

## Examples

### Complete Feature Engineering Workflow

```python
from pathlib import Path
from kai_code.agents.seeknal import SeeknalAgent

agent = SeeknalAgent(
    root_dir=Path.cwd(),
    yolo=True,
)

# 1. Create project
agent.run("Create project 'churn_prediction'")

# 2. Create entity
agent.run("Create entity 'customer' with join keys 'customer_id'")

# 3. Create feature group
agent.run("""
    Create feature group 'customer_activity' with entity 'customer',
    event_time_col 'activity_date', in project 'churn_prediction'
""")

# 4. Build data pipeline
agent.run("""
    Create flow 'process_activity' that reads from PARQUET file
    'data/activities.parquet' and runs DuckDB task to aggregate
    customer activity metrics
""")

# 5. Materialize features
agent.run("Materialize feature group 'customer_activity' starting from 2024-01-01")

# 6. Validate features
agent.run("Validate features in feature group 'customer_activity'")

agent.save()
```

### Version Rollback Workflow

```python
# 1. List versions to identify the target
agent.run("List all versions of feature group 'user_features'")

# 2. Compare versions to understand changes
agent.run("Compare version 2 and 1 of feature group 'user_features'")

# 3. Rollback to previous version
agent.run("Materialize version 1 of feature group 'user_features'")
```

## Testing

Run tests for SeeknalAgent:

```bash
# Run all SeeknalAgent tests
pytest tests/test_seeknal_agent.py -v

# Run specific test
pytest tests/test_seeknal_agent.py::test_seeknal_agent_tools -v
```

## Troubleshooting

### Import Errors

If you get import errors for Seeknal:

```bash
# Check Seeknal is installed
python -c "import seeknal; print(seeknal.__version__)"

# Verify Seeknal path
ls ~/project/mta/signal/src/seeknal
```

### CLI Not Found

If `kai-seeknal` command is not found:

```bash
# Reinstall kai-code
pip install -e .

# Or use Python module directly
python -m kai_code.agents.seeknal.cli
```

### Database Connection Issues

If you get database connection errors:

```bash
# Check SQLite database
ls ~/.seeknal/seeknal.db

# For Turso, verify environment variables
echo $TURSO_DATABASE_URL
echo $TURSO_AUTH_TOKEN
```

## Contributing

When contributing to Kai Seeknal:

1. Follow the existing code style (type hints, docstrings)
2. Add tests for new features
3. Update documentation
4. Use Seeknal's validation functions for security
5. Prefer DuckDB over Spark for new features (unless dealing with big data)

## License

Apache-2.0 (same as kai-code)

## Resources

- [Kai Code Documentation](https://github.com/kai-code/kai-code)
- [Seeknal Documentation](https://github.com/mta-tech/seeknal)
- [Seeknal Agent Prompt](src/kai_code/prompts/kai-seeknal.md)
- [Example Usage](examples/seeknal_agent_demo.py)
