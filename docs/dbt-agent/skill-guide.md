# dbt Skill Development Guide

The dbt skill provides instructions, templates, and examples that customize DbtAgent behavior.

## Skill Location

```
.skills/dbt/
├── SKILL.md              # Main instructions (required)
├── templates/            # Project templates (optional)
├── instructions/         # Business rules (optional)
└── examples/             # Reference code (optional)
```

## SKILL.md Structure

The main skill file that gets embedded in the system prompt:

```markdown
# dbt Data Engineering Agent

## Your Role
[Define the agent's identity and expertise]

## Before Implementation
[Pre-work checklist - what to do before writing code]

## Layer Conventions
[Model naming and organization rules]

## Model Checklist
[Quality checklist for every model]

## Testing Requirements
[What tests are required]

## Common Patterns
[Reusable SQL patterns]
```

### Example SKILL.md

```markdown
# dbt Data Engineering Agent

## Your Role

You are a senior data engineer specializing in dbt. You build production-quality
data pipelines that are tested, documented, and maintainable.

## Before Implementation

Before writing any dbt model:

1. **Explore the database**
   - Call `get_database_schema()` to understand available tables
   - Call `get_filterable_columns()` to identify dimension columns

2. **Check documentation**
   - Read relevant files from `dbt_docs/` using file tools
   - Focus on `01_core_concepts.md` for model types
   - Check `04_testing_strategies.md` for test patterns

3. **Review instructions**
   - Call `get_instructions()` for business rules
   - Check `get_dbt_meta()` for existing model metadata

4. **Understand semantic layer**
   - Call `get_mdl_manifest()` if available
   - Use `get_mdl_join_path()` for relationship info

## Layer Conventions

### Staging Layer (stg_)
- Materialized as `view`
- 1:1 mapping with source tables
- Only cleaning and type casting
- Naming: `stg_{source}__{entity}`

### Intermediate Layer (int_)
- Materialized as `table` or `ephemeral`
- Business logic and transformations
- Not exposed to end users
- Naming: `int_{entity}_{verb}`

### Marts Layer
- Facts (`fct_`): Materialized as `table`, metrics and measures
- Dimensions (`dim_`): Materialized as `table`, descriptive attributes
- Naming: `fct_{entity}` or `dim_{entity}`

### ML Layer (ml_)
- Materialized as `table`
- Feature engineering for ML
- Naming: `ml_{use_case}_features`

## Model Checklist

Every model MUST have:

✓ Config block with materialization
✓ CTEs for organization (source, cleaned, final)
✓ Explicit column selection (no SELECT *)
✓ Data type casting
✓ Descriptive column aliases
✓ Tests in schema.yml (unique, not_null for keys)
✓ Documentation in schema.yml

## Testing Requirements

### Staging Models
- `unique` and `not_null` on primary key
- `relationships` test for foreign keys

### Mart Models
- All staging tests plus:
- `accepted_values` for status/type columns
- Custom data quality tests

## Common Patterns

### Standard CTE Structure
```sql
WITH source AS (
    SELECT * FROM {{ source('schema', 'table') }}
),

cleaned AS (
    SELECT
        CAST(id AS INTEGER) AS entity_id,
        TRIM(LOWER(email)) AS email,
        created_at::DATE AS created_date
    FROM source
    WHERE id IS NOT NULL
),

final AS (
    SELECT * FROM cleaned
)

SELECT * FROM final
```

### Incremental Model Pattern
```sql
{{
    config(
        materialized='incremental',
        unique_key='event_id',
        incremental_strategy='merge'
    )
}}

SELECT *
FROM {{ source('events', 'raw_events') }}

{% if is_incremental() %}
WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})
{% endif %}
```
```

## Templates Directory

Provide starter templates for common use cases:

```
templates/
├── ecommerce/
│   ├── manifest.yaml       # Template metadata
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   └── models/
│       ├── staging/
│       │   ├── stg_ecommerce__orders.sql
│       │   ├── stg_ecommerce__customers.sql
│       │   └── schema.yml
│       ├── intermediate/
│       │   └── int_customer_orders.sql
│       └── marts/
│           ├── fct_orders.sql
│           ├── dim_customers.sql
│           └── schema.yml
│
├── saas_metrics/
│   └── ... (MRR, churn, cohorts)
│
└── financial/
    └── ... (revenue, cash flow)
```

### manifest.yaml

```yaml
name: ecommerce
description: E-commerce analytics pipeline template
version: 1.0.0

variables:
  - name: source_schema
    description: Schema containing raw tables
    default: raw
  - name: target_schema
    description: Schema for transformed models
    default: analytics

required_sources:
  - orders
  - customers
  - products

models_included:
  staging: 3
  intermediate: 2
  marts: 4
```

## Instructions Directory

Business rules and guidelines in YAML:

```
instructions/
├── default.yaml      # Always-apply rules
├── naming.yaml       # Naming conventions
└── security.yaml     # PII handling rules
```

### default.yaml

```yaml
instructions:
  - condition: Always
    rules: |
      - Use snake_case for all identifiers
      - Include created_at in all staging models
      - Never use SELECT *
    is_default: true

  - condition: When creating fact tables
    rules: |
      - Include surrogate key using dbt_utils.generate_surrogate_key
      - Add row count validation test
    is_default: false

  - condition: When handling PII
    rules: |
      - Hash email addresses in non-production environments
      - Never expose raw phone numbers
      - Tag columns with meta.pii: true
    is_default: false
```

## Examples Directory

Reference implementations:

```
examples/
├── staging_model.sql
├── incremental_model.sql
├── snapshot.sql
├── custom_test.sql
├── macro.sql
└── schema.yml
```

### staging_model.sql

```sql
-- Example staging model following conventions

{{
    config(
        materialized='view',
        tags=['staging', 'daily']
    )
}}

WITH source AS (
    SELECT * FROM {{ source('ecommerce', 'orders') }}
),

cleaned AS (
    SELECT
        -- Primary key
        CAST(order_id AS INTEGER) AS order_id,

        -- Foreign keys
        CAST(customer_id AS INTEGER) AS customer_id,
        CAST(product_id AS INTEGER) AS product_id,

        -- Attributes
        TRIM(UPPER(status)) AS order_status,
        CAST(quantity AS INTEGER) AS quantity,
        CAST(unit_price AS DECIMAL(10, 2)) AS unit_price,
        CAST(discount AS DECIMAL(5, 2)) AS discount_amount,

        -- Calculated
        (quantity * unit_price) - COALESCE(discount, 0) AS line_total,

        -- Timestamps
        CAST(created_at AS TIMESTAMP) AS created_at,
        CAST(updated_at AS TIMESTAMP) AS updated_at

    FROM source
    WHERE order_id IS NOT NULL
)

SELECT * FROM cleaned
```

## Customizing for Your Organization

### 1. Fork the Default Skill

```bash
cp -r ~/.kai/skills/dbt .skills/dbt
```

### 2. Modify SKILL.md

Add your conventions:
- Company-specific naming patterns
- Required metadata fields
- Team ownership rules
- SLA definitions

### 3. Add Custom Instructions

Create domain-specific rules:

```yaml
# instructions/finance.yaml
instructions:
  - condition: When building financial models
    rules: |
      - Use DECIMAL(18, 4) for monetary amounts
      - Always include currency code column
      - Apply SOX compliance tagging
```

### 4. Create Custom Templates

Add templates for your domains:

```
templates/
└── your_domain/
    ├── manifest.yaml
    └── models/
```

### 5. Add Examples

Include real patterns from your codebase:

```
examples/
├── your_incremental_pattern.sql
└── your_testing_pattern.yml
```

## Skill Loading Priority

1. Project-level: `.skills/dbt/` (highest priority)
2. User-level: `~/.kai/skills/dbt/`
3. Built-in: Bundled with kai-code package

Project-level skills override user-level and built-in skills.
