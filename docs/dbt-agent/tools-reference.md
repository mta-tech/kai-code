# DbtAgent Tools Reference

All tools return JSON strings for consistent parsing by the LLM.

---

## Schema Tools

Tools for database introspection via direct SQL queries.

### get_database_schema()

Get the complete database schema including all tables, columns, and descriptions.

```python
def get_database_schema(include_samples: bool = False) -> str
```

**Parameters**:
- `include_samples`: Include sample data rows (default: False)

**Returns**: JSON with:
- `tables`: List of tables with columns, types, descriptions
- `filterable_columns`: Quick reference for low-cardinality columns
- `summary`: Total counts

**Example Output**:
```json
{
  "success": true,
  "database": {
    "dialect": "postgresql",
    "schemas": ["public", "staging"]
  },
  "tables": [
    {
      "name": "orders",
      "schema": "public",
      "full_name": "public.orders",
      "description": "Customer orders",
      "columns": [
        {
          "name": "order_id",
          "type": "INTEGER",
          "primary_key": true
        },
        {
          "name": "status",
          "type": "VARCHAR",
          "filterable": true,
          "allowed_values": ["pending", "completed", "cancelled"]
        }
      ]
    }
  ],
  "filterable_columns": [
    {
      "table": "public.orders",
      "column": "status",
      "values": ["pending", "completed", "cancelled"],
      "hint": "WHERE status IN ('pending', 'completed')"
    }
  ]
}
```

---

### get_table_details()

Get detailed information about a specific table.

```python
def get_table_details(table_name: str) -> str
```

**Parameters**:
- `table_name`: Table name (e.g., "orders" or "public.orders")

**Returns**: JSON with columns, constraints, sample data

**Example Output**:
```json
{
  "success": true,
  "table": {
    "name": "orders",
    "schema": "public",
    "full_name": "public.orders",
    "description": "Customer orders table",
    "columns": [
      {
        "name": "order_id",
        "type": "INTEGER",
        "is_primary_key": true,
        "is_low_cardinality": false
      },
      {
        "name": "customer_id",
        "type": "INTEGER",
        "foreign_key": {
          "references_table": "customers",
          "references_column": "customer_id"
        }
      }
    ],
    "sample_data": [
      {"order_id": 1, "customer_id": 100, "status": "completed"}
    ]
  }
}
```

---

### get_column_cardinality()

Get distinct value count and samples for a column.

```python
def get_column_cardinality(table_name: str, column_name: str) -> str
```

**Parameters**:
- `table_name`: Table name
- `column_name`: Column name

**Returns**: JSON with cardinality info

**Example Output**:
```json
{
  "success": true,
  "table": "orders",
  "column": "status",
  "distinct_count": 3,
  "total_count": 10000,
  "is_low_cardinality": true,
  "sample_values": ["pending", "completed", "cancelled"],
  "value_distribution": {
    "completed": 7500,
    "pending": 2000,
    "cancelled": 500
  }
}
```

---

### get_filterable_columns()

Get columns with known categorical values (low cardinality).

```python
def get_filterable_columns(table_name: str | None = None) -> str
```

**Parameters**:
- `table_name`: Optional filter to specific table

**Returns**: JSON with filterable columns and their allowed values

---

### search_schema()

Search tables and columns using patterns.

```python
def search_schema(
    pattern: str,
    search_in: str = "all",
    case_sensitive: bool = False
) -> str
```

**Parameters**:
- `pattern`: Search pattern with wildcards (`*`, `?`)
- `search_in`: Where to search - "tables", "columns", "descriptions", "all"
- `case_sensitive`: Case-sensitive matching

**Examples**:
```python
search_schema("*customer*")        # Find anything with "customer"
search_schema("*_id", "columns")   # Find ID columns
search_schema("revenue*")          # Find revenue-related items
```

---

## MDL/Semantic Tools

Tools for exploring the semantic layer (MDL manifest).

### get_mdl_manifest()

Get the MDL semantic layer manifest overview.

```python
def get_mdl_manifest() -> str
```

**Returns**: JSON with models, relationships, metrics, views summary

**Example Output**:
```json
{
  "found": true,
  "name": "Sales Analytics",
  "summary": {
    "total_models": 5,
    "total_relationships": 3,
    "total_metrics": 8,
    "total_views": 2
  },
  "models": ["orders", "customers", "products", "order_items", "payments"],
  "relationships": ["orders_customers", "orders_order_items", "order_items_products"],
  "metrics": ["total_revenue", "avg_order_value", "customer_ltv"]
}
```

---

### explore_mdl_model()

Get detailed information about a specific model.

```python
def explore_mdl_model(model_name: str) -> str
```

**Parameters**:
- `model_name`: Name of the model

**Returns**: JSON with columns, calculated fields, relationships

---

### get_mdl_relationships()

Explore relationships between models.

```python
def get_mdl_relationships(model_name: str | None = None) -> str
```

**Parameters**:
- `model_name`: Optional filter to relationships involving this model

**Returns**: JSON with relationship details and join conditions

---

### get_mdl_metrics()

Explore business metrics definitions.

```python
def get_mdl_metrics(metric_name: str | None = None) -> str
```

**Parameters**:
- `metric_name`: Optional specific metric to detail

**Returns**: JSON with metric definitions, dimensions, measures

---

### get_mdl_join_path()

Find the join path between two models.

```python
def get_mdl_join_path(from_model: str, to_model: str) -> str
```

**Parameters**:
- `from_model`: Starting model
- `to_model`: Target model

**Returns**: JSON with join path and conditions

**Example Output**:
```json
{
  "found": true,
  "path_type": "direct",
  "from_model": "orders",
  "to_model": "customers",
  "relationship": {
    "name": "orders_customers",
    "join_type": "MANY_TO_ONE",
    "condition": "orders.customer_id = customers.customer_id"
  },
  "sql_hint": "JOIN customers ON orders.customer_id = customers.customer_id"
}
```

---

## Instruction Tools

Tools for retrieving business rules and guidelines.

### get_instructions()

Get all custom instructions for the project.

```python
def get_instructions() -> str
```

**Returns**: JSON with instructions from `.skills/dbt/instructions/`

**Example Output**:
```json
{
  "success": true,
  "instructions": [
    {
      "condition": "Always",
      "rules": "Use snake_case for all model names",
      "is_default": true
    },
    {
      "condition": "When creating fact tables",
      "rules": "Include created_at and updated_at columns",
      "is_default": false
    }
  ]
}
```

---

### get_dbt_meta()

Read meta properties from schema.yml files.

```python
def get_dbt_meta(model_name: str) -> str
```

**Parameters**:
- `model_name`: Name of the dbt model

**Returns**: JSON with meta properties from schema.yml

**Example Output**:
```json
{
  "success": true,
  "model": "fct_orders",
  "meta": {
    "owner": "data-team",
    "pii": false,
    "refresh_frequency": "daily",
    "sla": "6am EST"
  }
}
```

---

## dbt CLI Tools

Wrapped dbt commands with structured output parsing.

### dbt_run()

Run dbt models.

```python
def dbt_run(
    select: str | None = None,
    exclude: str | None = None,
    full_refresh: bool = False
) -> str
```

**Parameters**:
- `select`: Model selection (e.g., "+my_model", "tag:staging")
- `exclude`: Models to exclude
- `full_refresh`: Force full refresh of incremental models

**Returns**: JSON with run results

**Example Output**:
```json
{
  "success": true,
  "models_run": 5,
  "models": [
    {"name": "stg_orders", "status": "success", "rows": 1000},
    {"name": "stg_customers", "status": "success", "rows": 500}
  ],
  "warnings": [],
  "duration_seconds": 12.5
}
```

**Error Output**:
```json
{
  "success": false,
  "error_type": "compilation",
  "message": "column 'order_id' does not exist",
  "failed_models": ["stg_orders"],
  "suggestion": "Check column names in source table"
}
```

---

### dbt_test()

Run dbt tests.

```python
def dbt_test(select: str | None = None) -> str
```

**Parameters**:
- `select`: Test selection

**Returns**: JSON with test results

**Example Output**:
```json
{
  "success": true,
  "tests_run": 15,
  "passed": 15,
  "failed": 0,
  "warnings": 0,
  "tests": [
    {"name": "unique_orders_order_id", "status": "pass"},
    {"name": "not_null_orders_customer_id", "status": "pass"}
  ]
}
```

---

### dbt_compile()

Compile a model and return the generated SQL.

```python
def dbt_compile(model_name: str) -> str
```

**Parameters**:
- `model_name`: Model to compile

**Returns**: JSON with compiled SQL

**Example Output**:
```json
{
  "success": true,
  "model": "stg_orders",
  "compiled_sql": "SELECT\n  order_id,\n  customer_id,\n  order_date\nFROM raw.orders\nWHERE order_date >= '2024-01-01'"
}
```

---

### dbt_show()

Preview model output.

```python
def dbt_show(model_name: str, limit: int = 10) -> str
```

**Parameters**:
- `model_name`: Model to preview
- `limit`: Number of rows (default: 10)

**Returns**: JSON with sample data

**Example Output**:
```json
{
  "success": true,
  "model": "fct_orders",
  "columns": ["order_id", "customer_id", "total_amount"],
  "rows": [
    {"order_id": 1, "customer_id": 100, "total_amount": 99.99},
    {"order_id": 2, "customer_id": 101, "total_amount": 149.99}
  ],
  "row_count": 10,
  "total_rows": 5000
}
```

---

### dbt_list()

List dbt resources.

```python
def dbt_list(
    select: str | None = None,
    resource_type: str | None = None
) -> str
```

**Parameters**:
- `select`: Selection criteria
- `resource_type`: Filter by type (model, test, source, seed, snapshot)

**Returns**: JSON with resource list

**Example Output**:
```json
{
  "success": true,
  "resources": [
    {"name": "stg_orders", "type": "model", "path": "models/staging/stg_orders.sql"},
    {"name": "stg_customers", "type": "model", "path": "models/staging/stg_customers.sql"}
  ],
  "count": 2
}
```

---

## Tool Response Patterns

All tools follow consistent response patterns:

### Success Response
```json
{
  "success": true,
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "error_type": "compilation|runtime|connection",
  "suggestion": "How to fix"
}
```

### Not Found Response
```json
{
  "found": false,
  "error": "Resource not found",
  "available": ["list", "of", "alternatives"]
}
```
