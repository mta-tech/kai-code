# Subagent Delegation Patterns

This guide covers advanced patterns for using subagents with kai-code's agent layer.

## Overview

Subagents follow the **deepagents delegation pattern** - specialized agents are exposed as callable tools that main agents can invoke for specific tasks. This enables:

- **Specialization**: Each subagent focuses on a specific domain
- **Composability**: Complex tasks are broken into smaller, manageable pieces
- **Isolation**: Subagents execute in isolated contexts with fresh state
- **Scalability**: Easy to add new specialized capabilities

## Basic Subagent Usage

### Defining Subagents in Agent Configuration

```markdown
---
name: data-pipeline-manager
description: Orchestrates data pipeline tasks
subagents:
  - name: data-engineer
    description: Builds data pipelines and feature stores
    agent: data-engineer
  - name: ml-engineer
    description: Handles feature engineering for ML
    agent: ml-engineer
---

# Purpose

You orchestrate data pipeline tasks by delegating to specialized subagents...
```

### How Delegation Works

When the main agent needs specialized help:

```
User Request → Main Agent Analyzes
                      ↓
              "This needs data pipeline work"
                      ↓
              Invoke data-engineer subagent
                      ↓
              Subagent executes in isolation
                      ↓
              Results flow back to main agent
                      ↓
              Main agent synthesizes final response
```

## Advanced Patterns

### Pattern 1: Hierarchical Specialization

Create a hierarchy of increasingly specialized subagents:

```markdown
---
name: analytics-orchestrator
description: Orchestrates all analytics work
subagents:
  # Level 1: Domain specialists
  - name: data-engineer
    description: Data pipeline and feature store specialist
    agent: data-engineer

  - name: ml-engineer
    description: ML feature engineering specialist
    agent: ml-engineer

  - name: bi-analyst
    description: Business intelligence and reporting specialist
    agent: bi-analalyzer

  # Level 2: Sub-specialists (used by data-engineer)
  - name: etl-specialist
    description: ETL workflow specialist
    agent: etl-specialist

  - name: validation-engineer
    description: Data quality validation specialist
    agent: validation-engineer
---
```

The `data-engineer` subagent can itself have subagents, creating a delegation hierarchy.

### Pattern 2: Parallel Execution

For independent tasks, create multiple subagents that can work in parallel:

```markdown
---
name: parallel-processor
description: Processes independent tasks in parallel
subagents:
  - name: csv-processor
    description: Processes CSV data files
    agent: csv-processor

  - name: json-processor
    description: Processes JSON data files
    agent: json-processor

  - name: xml-processor
    description: Processes XML data files
    agent: xml-processor
---

# Instructions

When given multiple data files to process:
1. Identify file types (CSV, JSON, XML)
2. Delegate each file to the appropriate specialist subagent
3. Collect results from all subagents
4. Synthesize combined summary
```

### Pattern 3: Sequential Pipeline

Create a pipeline where subagents hand off work:

```markdown
---
name: etl-orchestrator
description: Orchestrates ETL pipeline stages
subagents:
  - name: extractor
    description: Extracts data from source systems
    agent: data-extractor

  - name: transformer
    description: Transforms and cleans data
    agent: data-transformer

  - name: loader
    description: Loads data into target systems
    agent: data-loader
---

# Instructions

When building an ETL pipeline:
1. Use **extractor** to pull data from sources
2. Use **transformer** to clean and transform
3. Use **loader** to load into destination
4. Verify data integrity at each stage
```

### Pattern 4: Fallback Pattern

Provide a generalist subagent as fallback when specialists fail:

```markdown
---
name: fault-tolerant-processor
description: Handles tasks with fallback logic
subagents:
  - name: sql-optimizer
    description: Specialized SQL query optimizer
    agent: sql-optimizer

  - name: general-query-writer
    description: General query writing fallback
    agent: query-writer
---

# Instructions

When asked to write SQL queries:
1. First try **sql-optimizer** for optimized queries
2. If optimization fails or is not applicable, use **general-query-writer**
3. Always explain which subagent handled the task
```

## Subagent Configuration Options

### Minimal Configuration

```yaml
subagents:
  - name: specialist
    agent: specialist
```

Uses the specialist agent's default description.

### Full Configuration

```yaml
subagents:
  - name: data-engineer
    description: |
      Senior data engineering specialist with 10+ years experience.
      Expert in Python, SQL, data modeling, and ETL pipelines.
      Proactively suggests optimizations and best practices.
    agent: data-engineer
    tools:
      include:
        - kai_code.tools.bash
        - kai_code.tools.read
        - kai_code.agents.seeknal.tools.feature_store_tools
    trigger:
      keywords: [pipeline, etl, feature, data, extract]
      tool_patterns: [create_project, create_flow]
```

## Creating Subagent Agents

### Option 1: Python Class

```python
# src/kai_code/agents/my_domain/specialist.py
from kai_code.agent import KaiAgent

class SpecialistAgent(KaiAgent):
    def _get_base_prompt_name(self) -> str:
        return "specialist"

    def _get_subclass_tools(self) -> list:
        from my_package.tools import get_specialist_tools
        return super()._get_subclass_tools() + get_specialist_tools()
```

### Option 2: Markdown Definition

```markdown
---
name: specialist
description: Domain specialist for specific tasks
extends: kai-code
tools: my_package.tools.*
---

# Purpose

You are a specialist agent for...

## Core Expertise

You excel at...
```

Both approaches work. The markdown definition is simpler for most cases.

## Best Practices

### 1. Clear Naming

Subagent names should clearly indicate their specialty:

```yaml
# Good
- name: data-engineer
- name: ml-feature-engineer
- name: bi-report-writer

# Avoid
- name: helper
- name: agent1
- name: specialist
```

### 2. Action-Oriented Descriptions

Descriptions should tell the main agent WHEN to use the subagent:

```yaml
# Good
description: "Use proactively for data pipeline and feature store tasks"

# Less useful
description: "Data engineering agent"
```

### 3. Appropriate Granularity

Balance between too coarse and too fine:

```yaml
# Too coarse - one giant subagent
- name: data-specialist
  description: "Does all data things"

# Too fine - overly narrow
- name: csv-reader
  description: "Reads CSV files"
- name: csv-writer
  description: "Writes CSV files"

# Just right
- name: data-engineer
  description: "Builds data pipelines and feature stores"
```

### 4. Avoid Circular Dependencies

Don't create circular subagent relationships:

```yaml
# DON'T DO THIS - circular dependency
# orchestrator.yaml
subagents:
  - name: specialist
    agent: specialist

# specialist.yaml
subagents:
  - name: orchestrator
    agent: orchestrator
```

### 5. Document Subagent Contracts

Clearly document what each subagent expects and returns:

```markdown
---
name: data-validator
description: |
  Validates data quality and generates reports.

  Use when you need to:
  - Check data quality metrics
  - Validate against schema
  - Generate data quality reports

  Input: Dataset location or query
  Output: Validation report with pass/fail status
---
```

## Troubleshooting

### Subagent Not Invoked

If a subagent is never called by the main agent:

1. Check the description is clear about when to use it
2. Ensure the subagent's name and purpose are in the main agent's prompt
3. Consider adding trigger keywords to guide the main agent

### Subagent Returns Errors

If a subagent fails:

1. Check the subagent's tools are properly configured
2. Verify the subagent has access to required resources
3. Check for circular dependencies
4. Review the subagent's prompt for clarity

### Performance Issues

If subagent delegation is slow:

1. Reduce the number of subagents (use composites)
2. Add caching for repeated operations
3. Consider if the task should be handled by the main agent instead
4. Profile to identify bottlenecks

## Examples

### Example 1: E-Commerce Data Pipeline

```markdown
---
name: ecommerce-analytics
description: Orchestrates e-commerce analytics
subagents:
  - name: customer-analyst
    description: Analyzes customer behavior and metrics
    agent: customer-analyst

  - name: product-analyst
    description: Analyzes product performance
    agent: product-analyst

  - name: inventory-specialist
    description: Manages inventory and forecasting
    agent: inventory-specialist
---
```

### Example 2: Multi-Region Deployment

```markdown
---
name: global-deployer
description: Orchestrates multi-region deployments
subagents:
  - name: aws-deployer
    description: AWS deployment specialist
    agent: aws-deployer

  - name: gcp-deployer
    description: GCP deployment specialist
    agent: gcp-deployer

  - name: azure-deployer
    description: Azure deployment specialist
    agent: azure-deployer
---
```

### Example 3: Code Review Pipeline

```markdown
---
name: code-review-orchestrator
description: Orchestrates code review process
subagents:
  - name: security-reviewer
    description: Security and vulnerability specialist
    agent: security-reviewer

  - name: performance-reviewer
    description: Performance optimization specialist
    agent: performance-reviewer

  - name: style-reviewer
    description: Code style and best practices specialist
    agent: style-reviewer

  - name: test-coverage-reviewer
    description: Test coverage analysis specialist
    agent: test-coverage-reviewer
---
```

## Manual Subagent Creation

For advanced use cases, create subagent tools programmatically:

```python
from kai_code.subagents import create_subagent_tool
from kai_code.agent_loader import load_agent
from pathlib import Path

# Load subagent class
DataEngineer = load_agent("data-engineer")

# Wrap as tool
tool = create_subagent_tool(
    agent=DataEngineer,
    name="data-engineer",
    description="Builds data pipelines and feature stores",
    root_dir=Path.cwd(),
    model="sonnet",  # Optional model override
)

# Add to main agent's tools
main_agent_tools = [tool, ...]
```

This is useful when you need to:
- Dynamically create subagents at runtime
- Pass custom configuration
- Mix agent-defined and manually-created tools
