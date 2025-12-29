# dbt Agent Tutorial

The dbt Agent (`kai-dbt`) is a specialized AI assistant for data engineering with dbt (data build tool). This tutorial covers installation, configuration, and common workflows.

## Prerequisites

- Python 3.11+
- API key for an LLM provider
- Basic understanding of dbt concepts
- (Optional) An existing dbt project

## Installation

```bash
# Install with dbt support (includes DuckDB and PostgreSQL)
pip install -e '.[dbt]'

# Or specific database only
pip install -e '.[dbt-duckdb]'   # DuckDB only
pip install -e '.[dbt-postgres]' # PostgreSQL only
```

## Quick Start

### Starting kai-dbt

```bash
# Basic start
kai-dbt

# With a DuckDB database
kai-dbt --db analytics.duckdb

# With a dbt profile
kai-dbt --profile my_project --target dev

# Auto-approve mode
kai-dbt -y
```

### Connection Options

| Flag | Description | Example |
|------|-------------|---------|
| `--db` | DuckDB database file | `--db warehouse.duckdb` |
| `--profile` | dbt profile name | `--profile my_project` |
| `--target` | dbt target environment | `--target dev` |
| `--project-dir` | dbt project directory | `--project-dir ./dbt` |

## dbt Slash Commands

kai-dbt provides specialized commands for dbt workflows:

### `/schema` - Explore Database Schema

```
> /schema
```

Shows all tables, views, and their row counts in your database.

### `/model <name>` - Inspect a Model

```
> /model stg_customers
```

Shows:
- Model SQL definition
- Column names and types
- Dependencies (refs)
- Recent test results

### `/dbt run` - Run Models

```
> /dbt run
> /dbt run stg_customers
> /dbt run +marts_sales  # Include upstream deps
```

### `/dbt test` - Run Tests

```
> /dbt test
> /dbt test stg_orders
```

### `/dbt compile` - Compile Models

```
> /dbt compile dim_products
```

Shows the compiled SQL without executing.

## Common Workflows

### 1. Setting Up a New dbt Project

Start an interactive session and ask the agent:

```
You: Help me set up a new dbt project for a sales analytics use case.
     I have customer, order, and product data in DuckDB.
```

The agent will:
1. Create project structure
2. Set up `dbt_project.yml`
3. Configure `profiles.yml`
4. Create staging models

### 2. Creating Staging Models

```
You: Create a staging model for the raw_customers table.
     Apply standard naming conventions and add basic tests.
```

The agent creates:
- `models/staging/stg_customers.sql`
- `models/staging/schema.yml` with tests

### 3. Building Dimensional Models

```
You: Create a dim_customers dimension table from stg_customers.
     Include customer lifetime value calculation.
```

### 4. Data Quality Testing

```
You: Add data quality tests to ensure:
     - customer_id is unique and not null
     - email format is valid
     - order_date is not in the future
```

The agent adds appropriate tests to `schema.yml`.

### 5. Debugging dbt Errors

When you encounter errors:

```
You: I'm getting this error when running stg_orders:
     "column 'user_id' does not exist"
     Help me debug.
```

The agent will:
1. Check the source table schema
2. Identify column name mismatches
3. Suggest fixes

### 6. Exploring Unknown Data

```
> /schema

You: I'm new to this database. What data do we have
     and how might the tables relate to each other?
```

## Example Session

Here's a complete workflow example:

```bash
$ kai-dbt --db sales.duckdb -y
```

```
╭──────────────────────────────────────────────────────────────────╮
│  Kai dbt - Data Engineering Agent                                │
│  Database: sales.duckdb                                          │
╰──────────────────────────────────────────────────────────────────╯

> /schema

Agent: Found 4 tables in sales.duckdb:
       - raw_customers (1,523 rows)
       - raw_orders (45,891 rows)
       - raw_products (342 rows)
       - raw_payments (52,103 rows)

You: Create a complete staging layer for these tables following dbt best practices.

Agent: I'll create staging models with appropriate naming, typing, and tests...
       [Creates stg_customers.sql, stg_orders.sql, stg_products.sql, stg_payments.sql]
       [Creates schema.yml with tests for each model]

> /dbt run

Agent: Running dbt models...
       ✓ stg_customers (1.2s)
       ✓ stg_orders (3.4s)
       ✓ stg_products (0.8s)
       ✓ stg_payments (2.1s)

You: Now create a fact_orders model joining these staging tables.

Agent: Creating fact_orders with order details, customer info, and payment data...
       [Creates models/marts/fact_orders.sql]
       [Updates schema.yml]

> /dbt test

Agent: Running tests...
       ✓ 12 tests passed
       ✗ 1 test failed: stg_orders.order_date_not_in_future

       The test failure shows 3 orders with future dates. Would you like me to
       investigate the source data?
```

## Database Adapters

kai-dbt supports multiple databases through adapters:

### DuckDB (Default)

Best for local development and file-based analytics:

```bash
kai-dbt --db analytics.duckdb
```

```python
# Programmatic usage
from kai_code.agents.dbt import DbtAgent

agent = DbtAgent(
    root_dir=".",
    db_path="analytics.duckdb",
    model="openai:gpt-4o"
)
```

### PostgreSQL

For production data warehouses:

```bash
# Using dbt profile
kai-dbt --profile my_warehouse --target prod
```

Configure in `~/.dbt/profiles.yml`:

```yaml
my_warehouse:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: analyst
      password: "{{ env_var('PG_PASSWORD') }}"
      database: analytics
      schema: dbt_dev
```

## Working with Sources

### Defining Sources

Ask the agent to create source definitions:

```
You: Create a sources.yml for our raw tables in the 'raw' schema
```

Creates `models/staging/sources.yml`:

```yaml
version: 2

sources:
  - name: raw
    database: analytics
    schema: raw
    tables:
      - name: customers
        description: Raw customer data
        columns:
          - name: id
            description: Primary key
            tests:
              - unique
              - not_null
      - name: orders
        description: Raw order data
```

### Using Sources in Models

```sql
-- stg_customers.sql
select
    id as customer_id,
    first_name,
    last_name,
    email,
    created_at
from {{ source('raw', 'customers') }}
```

## Creating Custom Macros

Ask the agent to create reusable macros:

```
You: Create a macro for calculating days since an event,
     handling null dates gracefully
```

Creates `macros/date_utils.sql`:

```sql
{% macro days_since(date_column) %}
    case
        when {{ date_column }} is null then null
        else datediff('day', {{ date_column }}, current_date)
    end
{% endmacro %}
```

## Documentation Generation

### Generate Model Docs

```
You: Generate comprehensive documentation for all models
     in the marts folder
```

The agent updates `schema.yml` with descriptions for:
- Models
- Columns
- Tests

## Best Practices

### Project Structure

```
dbt_project/
├── dbt_project.yml
├── models/
│   ├── staging/           # 1:1 with sources
│   │   ├── sources.yml
│   │   ├── stg_*.sql
│   │   └── schema.yml
│   ├── intermediate/      # Business logic
│   │   ├── int_*.sql
│   │   └── schema.yml
│   └── marts/             # Final tables
│       ├── dim_*.sql
│       ├── fact_*.sql
│       └── schema.yml
├── macros/
├── tests/
└── seeds/
```

### Naming Conventions

| Layer | Prefix | Example |
|-------|--------|---------|
| Staging | `stg_` | `stg_customers` |
| Intermediate | `int_` | `int_customer_orders` |
| Dimensions | `dim_` | `dim_customers` |
| Facts | `fact_` | `fact_orders` |
| Metrics | `metric_` | `metric_daily_sales` |

### Testing Strategy

Always test:
- Primary keys: `unique`, `not_null`
- Foreign keys: `relationships`
- Business rules: custom tests
- Data freshness: `freshness` on sources

## Troubleshooting

### "Database file not found"

```bash
# Check the path
kai-dbt --db ./data/analytics.duckdb

# Create if needed
duckdb analytics.duckdb "SELECT 1"
```

### "dbt profile not found"

Ensure `~/.dbt/profiles.yml` exists and contains your profile:

```yaml
your_profile_name:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: analytics.duckdb
```

### "Model compilation error"

```
You: I'm getting a Jinja compilation error in my model.
     Here's the error: [paste error]
```

The agent will identify syntax issues and suggest fixes.

## What's Next?

- **[Custom Agents Guide](../guides/custom-agents.md)** - Extend DbtAgent
- **[Configuration Guide](../guides/configuration.md)** - Advanced settings
- **[API Reference](../api/dbt-agent.md)** - Programmatic usage
