# DbtAgent Usage Examples

## Basic Usage

### Initialize Agent

```python
from kai_code.agents import DbtAgent

# With PostgreSQL
agent = DbtAgent(
    root_dir="/path/to/dbt/project",
    db_connection="postgresql://user:pass@localhost:5432/analytics",
)

# With DuckDB
agent = DbtAgent(
    root_dir="/path/to/dbt/project",
    db_connection="warehouse.duckdb",
)

# With custom dbt paths
agent = DbtAgent(
    root_dir="/path/to/project",
    db_connection="postgresql://localhost/db",
    dbt_project_dir="/path/to/dbt",
    dbt_profiles_dir="/custom/profiles",
)
```

### Simple Prompts

```python
# Explore database
result = agent.run("What tables are available and what do they contain?")

# Create a model
result = agent.run("Create a staging model for the orders table")

# Run tests
result = agent.run("Run all tests and summarize the results")

# Debug an issue
result = agent.run("The int_customer_orders model is failing. Diagnose and fix it.")
```

---

## Greenfield Project

### Create New dbt Project

```python
agent = DbtAgent(
    root_dir="/path/to/new/project",
    db_connection="postgresql://localhost/raw_data",
    yolo=True,
)

result = agent.run("""
Initialize a new dbt project for e-commerce analytics.

Source tables available:
- raw.orders (order_id, customer_id, order_date, status, total)
- raw.customers (customer_id, email, name, created_at)
- raw.products (product_id, name, category, price)
- raw.order_items (order_item_id, order_id, product_id, quantity, price)

Create:
1. Staging models for all source tables
2. Intermediate model joining orders with customers
3. Fact table for order metrics
4. Dimension table for customers with order stats
""")
```

### Interactive Project Setup

```python
# Agent will ask clarifying questions
result = agent.run("""
Help me set up a dbt project for customer analytics.
I want to track customer lifetime value and churn risk.
""")

# Follow-up with more details
result = agent.run("""
The data is in PostgreSQL. We have these tables:
- users (user_id, email, signup_date)
- subscriptions (sub_id, user_id, plan, start_date, end_date)
- payments (payment_id, user_id, amount, date)
""")
```

---

## Existing Project Maintenance

### Add New Model

```python
agent = DbtAgent(
    root_dir="/existing/dbt/project",
    db_connection="postgresql://localhost/analytics",
)

result = agent.run("""
Add a new model for customer segmentation based on RFM analysis.

RFM segments:
- Champions: High recency, high frequency, high monetary
- Loyal: Medium recency, high frequency
- At Risk: Low recency, high past frequency
- Lost: Very low recency, any frequency
""")
```

### Fix Failing Tests

```python
result = agent.run("""
The test `unique_fct_orders_order_id` is failing.
Investigate and fix the issue.
""")
```

### Optimize Slow Model

```python
result = agent.run("""
The model `fct_daily_metrics` takes 15 minutes to run.
Analyze and optimize it. Consider:
- Converting to incremental
- Adding clustering keys
- Optimizing joins
""")
```

---

## Mixed Workflows

### dbt + Python Validation

```python
result = agent.run("""
1. Create staging models for the orders and customers tables
2. Write a Python script that validates the row counts match the source
3. Run the validation and report results
""")
```

### dbt + Documentation

```python
result = agent.run("""
1. Review all models in the marts/ folder
2. Ensure each model has complete documentation in schema.yml
3. Add any missing descriptions
4. Generate the dbt docs
""")
```

### dbt + Data Quality

```python
result = agent.run("""
Implement data quality checks:
1. Add dbt-expectations tests for the orders model
2. Create a singular test that checks for orphan records
3. Add source freshness tests
4. Run all tests and create a summary report
""")
```

---

## Streaming Output

### Progress Monitoring

```python
agent = DbtAgent(
    root_dir=".",
    db_connection="postgresql://localhost/db",
)

for event in agent.stream("Build the entire analytics pipeline"):
    if event.type == "tool_call":
        print(f"\n🔧 Using: {event.tool_name}")
        if event.tool_name.startswith("dbt_"):
            print(f"   Command: dbt {event.args.get('select', 'all')}")

    elif event.type == "tool_result":
        result = json.loads(event.content)
        if result.get("success"):
            print(f"   ✅ Success")
        else:
            print(f"   ❌ Error: {result.get('error')}")

    elif event.type == "message":
        print(event.content, end="", flush=True)
```

### Real-time Logging

```python
import logging
logging.basicConfig(level=logging.INFO)

for event in agent.stream("Create and test staging models"):
    if event.type == "message":
        # Final response
        print(event.content)
```

---

## Permission Modes

### Approval Required

```python
agent = DbtAgent(
    root_dir=".",
    db_connection="postgresql://prod@localhost/analytics",
    yolo=False,  # Require approval
)

result = agent.run("Deploy the updated models to production")
# Agent will pause before running dbt commands
# User must approve each dbt run/test
```

### Plan Mode (Read-Only)

```python
from kai_code import PermissionMode

agent = DbtAgent(
    root_dir=".",
    db_connection="postgresql://localhost/db",
    permission_mode=PermissionMode.PLAN,
)

result = agent.run("What changes would you make to optimize this pipeline?")
# Agent can only read files and compile models
# Cannot run dbt run, dbt test, or modify files
```

---

## Error Handling

### Graceful Recovery

```python
try:
    result = agent.run("Run the full pipeline")
except DbtExecutionError as e:
    print(f"dbt command failed: {e}")
    # Agent may have already diagnosed the issue
    print(f"Suggestion: {e.suggestion}")

except DatabaseConnectionError as e:
    print(f"Cannot connect to database: {e}")
```

### Retry with Context

```python
result = agent.run("Create the customer metrics model")

if "error" in result.output.lower():
    # Provide more context and retry
    result = agent.run("""
    The previous attempt failed. Here's additional context:
    - The customer_id column is in the public schema
    - Use LEFT JOIN for optional relationships
    - Date format is YYYY-MM-DD

    Please try again with this information.
    """)
```

---

## Advanced Patterns

### Multi-Database Workflow

```python
# Extract from production
prod_agent = DbtAgent(
    root_dir=".",
    db_connection="postgresql://readonly@prod:5432/analytics",
    yolo=False,
)

schema_info = prod_agent.run("Export the schema for orders and customers tables")

# Develop locally
dev_agent = DbtAgent(
    root_dir=".",
    db_connection="dev.duckdb",
    yolo=True,
)

dev_agent.run(f"""
Create local development models based on this production schema:
{schema_info.output}
""")
```

### Template-Based Generation

```python
agent = DbtAgent(root_dir=".", db_connection="analytics.duckdb")

result = agent.run("""
Use the ecommerce template to generate:
1. All staging models
2. The standard intermediate models
3. Core fact and dimension tables

Customize for our specific source tables:
- Source schema: raw_data
- Target schema: analytics
""")
```

### Batch Operations

```python
models_to_create = [
    "stg_users",
    "stg_events",
    "stg_transactions",
    "int_user_events",
    "fct_user_activity",
]

for model in models_to_create:
    result = agent.run(f"Create and test the {model} model")
    print(f"✅ {model}: {result.output[:100]}...")

    if "error" in result.output.lower():
        print(f"⚠️  Issue with {model}, stopping batch")
        break
```

---

## Integration Examples

### CI/CD Pipeline

```python
# In your CI script
import sys
from kai_code.agents import DbtAgent

agent = DbtAgent(
    root_dir=".",
    db_connection=os.environ["DBT_DATABASE_URL"],
    yolo=True,
)

result = agent.run("""
Run the CI checks:
1. dbt compile --select state:modified+
2. dbt run --select state:modified+
3. dbt test --select state:modified+
4. Report any failures
""")

if "failed" in result.output.lower():
    print(result.output)
    sys.exit(1)
```

### Slack Bot Integration

```python
def handle_slack_message(message: str, channel: str):
    agent = DbtAgent(
        root_dir="/dbt/project",
        db_connection=os.environ["DATABASE_URL"],
        yolo=False,  # Always require approval for Slack requests
    )

    result = agent.run(message)

    return {
        "channel": channel,
        "text": result.output,
    }
```

### Jupyter Notebook

```python
# In a Jupyter cell
from kai_code.agents import DbtAgent

agent = DbtAgent(
    root_dir=".",
    db_connection="analytics.duckdb",
)

# Interactive exploration
agent.run("Show me the top 10 customers by revenue")
```

```python
# Follow-up questions maintain context
agent.run("Create a model that segments these customers")
```

```python
# View the generated SQL
agent.run("Show me the compiled SQL for the model you just created")
```
