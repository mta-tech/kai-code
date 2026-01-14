# Agent Creation Examples: YAML vs Python SDK

This document provides side-by-side examples of creating kai-code agents using both the **YAML/Markdown approach** and the **Python SDK approach**. Both methods produce equivalent agents with the same capabilities.

---

## Table of Contents

1. [Quick Comparison](#quick-comparison)
2. [Example 1: Simple Data Engineer Agent](#example-1-simple-data-engineer-agent)
3. [Example 2: ML Engineer Agent with Inheritance](#example-2-ml-engineer-agent-with-inheritance)
4. [Example 3: Agent with Subagents](#example-3-agent-with-subagents)
5. [Example 4: Custom Tools Agent](#example-4-custom-tools-agent)
6. [When to Use Each Approach](#when-to-use-each-approach)

---

## Quick Comparison

| Aspect | YAML/Markdown Approach | Python SDK Approach |
|--------|----------------------|-------------------|
| **File Location** | `.kai/agents/my-agent.md` | `src/my_project/agents.py` |
| **Best For** | Non-programmers, rapid prototyping, configuration | Complex logic, dynamic behavior, advanced users |
| **Syntax** | YAML frontmatter + Markdown | Python class with methods |
| **Tool Loading** | Declarative list with patterns | Programmatic with factories |
| **Customization** | Limited to YAML fields | Full Python power |
| **Version Control** | Easy to diff (plain text) | Standard Python diff |
| **Testing** | Requires compilation | Direct Python imports |

---

## Example 1: Simple Data Engineer Agent

### YAML/Markdown Approach

**File**: `.kai/agents/data-engineer.md`

```markdown
---
name: data-engineer
description: Specialist for building data pipelines, ETL workflows, and data transformations. Use proactively for data engineering tasks.
extends: kai-code
tools:
  - kai_code.tools.bash
  - kai_code.tools.file_ops
model: inherit
color: Blue
---

# Purpose

You are a Data Engineering Specialist focused on building efficient data pipelines and ETL workflows.

## Core Expertise

You excel at:
- Building ETL/ELT pipelines with modern tools
- Data transformation and validation
- Working with SQL and NoSQL databases
- Pipeline orchestration and scheduling
- Data quality testing and monitoring

## Instructions

When invoked, follow this methodology:

1. **Understand Requirements**: Clarify data sources, transformations, and destinations
2. **Design Pipeline**: Map the data flow with appropriate tools
3. **Implement**: Build pipeline code with proper error handling
4. **Validate**: Test with sample data
5. **Document**: Provide clear setup and usage instructions

## Critical Behaviors

- Always validate data schemas and types
- Handle errors gracefully with logging
- Use idempotent operations where possible
- Document data dependencies clearly
- Consider scalability and performance

## Output Format

Provide:
1. Pipeline architecture overview
2. Step-by-step implementation
3. Configuration files
4. Validation queries/tests
5. Setup and run instructions
```

### Python SDK Approach

**File**: `src/my_project/agents.py`

```python
from kai_code.agent import KaiAgent
from kai_code.tools.bash import bash_tool
from kai_code.tools.file_ops import read_tool, write_tool
from typing import List


class DataEngineerAgent(KaiAgent):
    """Specialist for building data pipelines, ETL workflows, and data transformations.

    Use proactively for data engineering tasks.
    """

    def _get_base_prompt_name(self) -> str:
        return "data-engineer"

    def _get_subclass_tools(self) -> List:
        """Get tools for data engineering tasks."""
        return [
            bash_tool,
            read_tool,
            write_tool,
        ]


# Optionally register for CLI discovery
__all__ = ["DataEngineerAgent"]
```

**Base Prompt File**: `src/kai_code/prompts/data-engineer.md`

```markdown
# Purpose

You are a Data Engineering Specialist focused on building efficient data pipelines and ETL workflows.

## Core Expertise

You excel at:
- Building ETL/ELT pipelines with modern tools
- Data transformation and validation
- Working with SQL and NoSQL databases
- Pipeline orchestration and scheduling
- Data quality testing and monitoring

## Instructions

When invoked, follow this methodology:

1. **Understand Requirements**: Clarify data sources, transformations, and destinations
2. **Design Pipeline**: Map the data flow with appropriate tools
3. **Implement**: Build pipeline code with proper error handling
4. **Validate**: Test with sample data
5. **Document**: Provide clear setup and usage instructions

## Critical Behaviors

- Always validate data schemas and types
- Handle errors gracefully with logging
- Use idempotent operations where possible
- Document data dependencies clearly
- Consider scalability and performance

## Output Format

Provide:
1. Pipeline architecture overview
2. Step-by-step implementation
3. Configuration files
4. Validation queries/tests
5. Setup and run instructions
```

### Usage Comparison

```bash
# YAML Approach: Load directly from markdown
from kai_code.agent_loader import load_agent

agent = load_agent("data-engineer")
result = agent.run("Create a data pipeline for user analytics")

# Python Approach: Import and instantiate
from my_project.agents import DataEngineerAgent

agent = DataEngineerAgent(root_dir=Path.cwd())
result = agent.run("Create a data pipeline for user analytics")
```

---

## Example 2: ML Engineer Agent with Inheritance

### YAML/Markdown Approach

**File**: `.kai/agents/ml-engineer.md`

```markdown
---
name: ml-engineer
description: ML specialist for feature engineering, model training, and MLOps workflows. Use for machine learning tasks.
extends: data-engineer
tools:
  - kai_code.tools.bash
  - kai_code.tools.file_ops
  - kai_code.tools.web_search
model: sonnet
color: Purple
---

# Purpose

You extend the Data Engineer with ML-specific expertise for building production ML systems.

## Additional Expertise

In addition to data engineering, you specialize in:
- Feature engineering for ML models
- Train/test split strategies
- Model versioning and experiment tracking
- MLOps workflows and CI/CD for models
- Model monitoring and drift detection

## ML Methodology

When working on ML tasks:

1. **Define Problem**: Specify prediction target, success metrics
2. **Feature Engineering**: Create and select features
3. **Model Selection**: Choose appropriate algorithms
4. **Training**: Train with proper validation
5. **Evaluation**: Test against holdout data
6. **Deployment**: Package for production serving

## Critical ML Behaviors

- Always create train/validation/test splits
- Track experiments with version control
- Monitor for data drift in production
- Use appropriate metrics for the problem type
- Consider inference latency and cost

## Output Format

Provide:
1. Feature definitions and importance
2. Model architecture and hyperparameters
3. Training script with validation
4. Evaluation metrics and analysis
5. Deployment configuration
```

### Python SDK Approach

**File**: `src/my_project/agents.py`

```python
from kai_code.agent import KaiAgent
from kai_code.tools.bash import bash_tool
from kai_code.tools.file_ops import read_tool, write_tool
from kai_code.tools.web import web_search_tool
from typing import List


class MLEngineerAgent(KaiAgent):
    """ML specialist for feature engineering, model training, and MLOps workflows.

    Use for machine learning tasks.
    """

    def _get_base_prompt_name(self) -> str:
        return "ml-engineer"

    def _get_model_name(self) -> str:
        """Override to use Sonnet for ML tasks."""
        return "sonnet"

    def _get_subclass_tools(self) -> List:
        """Get tools for ML engineering tasks."""
        return [
            bash_tool,
            read_tool,
            write_tool,
            web_search_tool,
        ]


__all__ = ["MLEngineerAgent"]
```

**Base Prompt File**: `src/kai_code/prompts/ml-engineer.md`

```markdown
# Purpose

You extend the Data Engineer with ML-specific expertise for building production ML systems.

# INHERIT: data-engineer

## Additional Expertise

In addition to data engineering, you specialize in:
- Feature engineering for ML models
- Train/test split strategies
- Model versioning and experiment tracking
- MLOps workflows and CI/CD for models
- Model monitoring and drift detection

## ML Methodology

When working on ML tasks:

1. **Define Problem**: Specify prediction target, success metrics
2. **Feature Engineering**: Create and select features
3. **Model Selection**: Choose appropriate algorithms
4. **Training**: Train with proper validation
5. **Evaluation**: Test against holdout data
6. **Deployment**: Package for production serving

## Critical ML Behaviors

- Always create train/validation/test splits
- Track experiments with version control
- Monitor for data drift in production
- Use appropriate metrics for the problem type
- Consider inference latency and cost

## Output Format

Provide:
1. Feature definitions and importance
2. Model architecture and hyperparameters
3. Training script with validation
4. Evaluation metrics and analysis
5. Deployment configuration
```

---

## Example 3: Agent with Subagents

### YAML/Markdown Approach

**File**: `.kai/agents/devops-lead.md`

```markdown
---
name: devops-lead
description: DevOps lead for coordinating infrastructure, deployment, and operations tasks. Delegates to specialized subagents.
extends: kai-code
tools:
  - kai_code.tools.bash
  - kai_code.tools.file_ops
model: inherit
color: Orange
subagents:
  - name: infra-engineer
    description: Infrastructure specialist for cloud resources and Terraform configurations
    agent: infra-engineer

  - name: deploy-specialist
    description: Deployment specialist for CI/CD pipelines and release management
    agent: deploy-specialist
---

# Purpose

You are a DevOps Lead responsible for coordinating infrastructure, deployment, and operations tasks.

## Core Responsibilities

You excel at:
- Infrastructure design and management
- CI/CD pipeline architecture
- Deployment automation
- Monitoring and alerting
- Incident response coordination

## Delegation Strategy

You have access to specialized subagents:
- **infra-engineer**: Use for Terraform, cloud resources, networking
- **deploy-specialist**: Use for CI/CD config, release automation

When a task requires specialized expertise, delegate to the appropriate subagent.

## Instructions

1. **Analyze Request**: Identify task requirements
2. **Delegate**: Assign specialized work to appropriate subagent
3. **Coordinate**: Ensure subagents work together effectively
4. **Synthesize**: Combine results into cohesive solution
5. **Document**: Provide clear implementation guidance

## Output Format

Provide:
1. Task breakdown with assignments
2. Subagent results integrated
3. Deployment steps and verification
4. Monitoring and rollback procedures
```

### Python SDK Approach

**File**: `src/my_project/agents.py`

```python
from kai_code.agent import KaiAgent
from kai_code.subagents import create_subagent_tool
from kai_code.tools.bash import bash_tool
from kai_code.tools.file_ops import read_tool, write_tool
from kai_code.agent_loader import load_agent
from typing import List


class DevOpsLeadAgent(KaiAgent):
    """DevOps lead for coordinating infrastructure, deployment, and operations tasks.

    Delegates to specialized subagents.
    """

    def _get_base_prompt_name(self) -> str:
        return "devops-lead"

    def _get_subclass_tools(self) -> List:
        """Get DevOps tools plus subagent delegation tools."""
        tools = [
            bash_tool,
            read_tool,
            write_tool,
        ]

        # Add subagent tools for delegation
        tools.extend(self._get_subagent_tools())
        return tools

    def _get_subagent_tools(self) -> List:
        """Create tools for delegating to specialized subagents."""
        subagent_tools = []

        # Load subagents
        infra_agent = load_agent("infra-engineer", root_dir=self.config.root_dir)
        deploy_agent = load_agent("deploy-specialist", root_dir=self.config.root_dir)

        # Wrap as callable tools
        subagent_tools.append(
            create_subagent_tool(
                agent=infra_agent,
                name="infra_engineer",
                description="Infrastructure specialist for cloud resources and Terraform configurations",
            )
        )

        subagent_tools.append(
            create_subagent_tool(
                agent=deploy_agent,
                name="deploy_specialist",
                description="Deployment specialist for CI/CD pipelines and release management",
            )
        )

        return subagent_tools


__all__ = ["DevOpsLeadAgent"]
```

---

## Example 4: Custom Tools Agent

### YAML/Markdown Approach

**File**: `.kai/agents/api-tester.md`

```markdown
---
name: api-tester
description: API testing specialist for endpoint validation, load testing, and contract testing. Use for API quality assurance.
extends: kai-code
tools:
  - kai_code.tools.bash
  - kai_code.tools.web_search
  - my_company.tools.http_tools
  - my_company.tools.validation_tools
model: sonnet
color: Red
---

# Purpose

You are an API Testing Specialist focused on ensuring API quality through comprehensive testing.

## Core Expertise

You excel at:
- Endpoint validation and smoke testing
- Load testing and performance analysis
- Contract testing and schema validation
- Security testing for APIs
- Test automation and CI/CD integration

## Testing Methodology

When testing APIs:

1. **Understand API**: Review documentation and contracts
2. **Design Tests**: Create test cases for happy path and edge cases
3. **Execute Tests**: Run functional, load, and security tests
4. **Analyze Results**: Identify performance bottlenecks and bugs
5. **Report**: Document findings with reproduction steps

## Critical Behaviors

- Always test authentication and authorization
- Verify error handling and edge cases
- Check rate limiting and quota enforcement
- Test with realistic data volumes
- Validate response schemas against contracts

## Output Format

Provide:
1. Test plan with coverage analysis
2. Automated test scripts
3. Load test results with metrics
4. Bug reports with reproduction steps
5. Recommendations for improvements
```

**Custom Tools Module**: `src/my_company/tools/http_tools.py`

```python
from langchain_core.tools import tool
import requests
from typing import Dict, Any


@tool("http_get")
def http_get_tool(url: str, headers: dict = None) -> str:
    """Make HTTP GET request and return response.

    Args:
        url: The URL to request
        headers: Optional HTTP headers

    Returns:
        Response body as string
    """
    response = requests.get(url, headers=headers or {})
    return response.text


@tool("http_post")
def http_post_tool(url: str, data: dict = None, json: dict = None) -> str:
    """Make HTTP POST request and return response.

    Args:
        url: The URL to request
        data: Form data to send
        json: JSON data to send

    Returns:
        Response body as string
    """
    response = requests.post(url, data=data, json=json)
    return response.text
```

### Python SDK Approach

**File**: `src/my_project/agents.py`

```python
from kai_code.agent import KaiAgent
from kai_code.tools.bash import bash_tool
from kai_code.tools.web import web_search_tool
from my_company.tools.http_tools import http_get_tool, http_post_tool
from my_company.tools.validation_tools import schema_validator_tool
from typing import List


class APITesterAgent(KaiAgent):
    """API testing specialist for endpoint validation, load testing, and contract testing.

    Use for API quality assurance.
    """

    def _get_base_prompt_name(self) -> str:
        return "api-tester"

    def _get_model_name(self) -> str:
        """Use Sonnet for API testing tasks."""
        return "sonnet"

    def _get_subclass_tools(self) -> List:
        """Get API testing tools."""
        return [
            bash_tool,
            web_search_tool,
            http_get_tool,
            http_post_tool,
            schema_validator_tool,
        ]


__all__ = ["APITesterAgent"]
```

---

## When to Use Each Approach

### Choose YAML/Markdown When:

✅ **You're not a programmer** - Markdown is easier to read and edit
✅ **Rapid prototyping** - Create agents quickly without writing code
✅ **Configuration-driven** - Agent definition is mostly declarative
✅ **Version control friendly** - Easy to see changes in diff
✅ **Team collaboration** - Non-technical stakeholders can review
✅ **Simple tool requirements** - Standard tools or simple patterns

### Choose Python SDK When:

✅ **Complex dynamic behavior** - Need runtime logic or state
✅ **Custom tool factories** - Tools require parameters or initialization
✅ **Advanced subagent patterns** - Dynamic subagent selection or routing
✅ **Integration with existing code** - Need to import other modules
✅ **Testing requirements** - Want to use standard Python test tools
✅ **Performance critical** - Need fine-grained control over execution

### Hybrid Approach

You can use both approaches together:

1. **Start with YAML** - Quickly prototype your agent in markdown
2. **Compile to Python** - Use `kai-code compile-agent` to see the equivalent Python
3. **Customize as needed** - Switch to Python SDK if you need advanced features
4. **Maintain both** - Keep YAML for documentation, Python for power users

---

## Migration Path

### From YAML to Python

```bash
# Compile your YAML agent to Python
kai-code compile-agent .kai/agents/my-agent.md

# Copy the output to src/my_project/agents.py
# Customize as needed
```

### From Python to YAML

1. Extract the prompt content to a markdown file
2. Map Python attributes to YAML fields
3. Convert tool factories to tool patterns
4. Test with `kai-code validate-agent`

See `docs/migration-guide.md` for detailed migration instructions.

---

## Best Practices

### YAML/Markdown Best Practices

1. **Use kebab-case names**: `my-agent` not `MyAgent` or `my_agent`
2. **Write descriptive descriptions**: "Specialist for X. Use for Y tasks."
3. **Leverage inheritance**: Extend base agents to avoid duplication
4. **Organize prompts**: Use clear sections with ## headers
5. **Validate frequently**: Use `kai-code validate-agent` to check syntax

### Python SDK Best Practices

1. **Follow naming conventions**: Class names should be descriptive (`DataEngineerAgent`)
2. **Type hint everything**: Use `List`, `Dict`, `str`, etc. for clarity
3. **Document with docstrings**: Class and method docstrings for API docs
4. **Keep tools focused**: Each tool should do one thing well
5. **Test thoroughly**: Write unit tests for custom tools and agents

### Shared Best Practices

1. **Start simple**: Add complexity only when needed
2. **Version control**: Commit both agent definitions and prompts
3. **Document decisions**: Explain why in comments or docs
4. **Review with users**: Get feedback on agent behavior
5. **Iterate**: Improve based on real usage patterns

---

## Additional Resources

- **Agent Development Guide**: `docs/agent-development-guide.md`
- **Migration Guide**: `docs/migration-guide.md`
- **Subagent Patterns**: `docs/subagent-patterns.md`
- **Tool Authoring**: `docs/tool-authoring.md`
- **Example Agents**: `.kai/agents/examples/`

---

**Need help?** Run `kai-code --help` or see the CLI reference.
