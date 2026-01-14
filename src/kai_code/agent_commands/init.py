"""Agent initialization command for kai-code."""

from pathlib import Path
from typing import Optional

# Default agent templates
BASE_TEMPLATE = """---
name: {name}
description: {description}
extends: kai-code
tools: kai_code.tools.bash, kai_code.tools.read, kai_code.tools.write, kai_code.tools.edit
model: inherit
color: Blue
---

# Purpose

You are a **Custom Agent** - a specialized AI assistant for this project.

## Core Expertise

You excel at:
- Reading and understanding code
- Writing new code and tests
- Debugging and fixing issues
- Following project conventions

## Instructions

When working on tasks, follow this methodology:

1. **Understand**: Clarify requirements and constraints
2. **Plan**: Break down the task into steps
3. **Execute**: Implement the solution step by step
4. **Verify**: Test that the solution works
5. **Document**: Add comments and documentation as needed

## Project-Specific Guidelines

Add your project's conventions and patterns here:

- Coding standards
- Architecture patterns
- Testing requirements
- Deployment processes

## Critical Behaviors

- Think before acting: Read existing code before making changes
- Test changes: Run tests after modifications
- Minimize changes: Only change what's necessary
- Ask for clarification: When requirements are unclear
"""

DATA_ENGINEER_TEMPLATE = """---
name: {name}
description: {description}
extends: kai-code
tools:
  - kai_code.tools.bash
  - kai_code.tools.read
  - kai_code.tools.write
  - kai_code.tools.edit
model: inherit
color: Green
---

# Purpose

You are a **Data Engineering Specialist** focused on building efficient data pipelines, ETL workflows, and data transformations.

## Core Expertise

You excel at:
- **ETL/ELT Pipelines**: Extract, transform, and load data between systems
- **Data Transformation**: Clean, normalize, and enrich datasets
- **Workflow Orchestration**: Design and implement data flow processes
- **Database Operations**: SQL queries, schema design, and optimization
- **Data Validation**: Ensure data quality and integrity
- **Performance**: Optimize for throughput and latency

## Instructions

When building data pipelines, follow this methodology:

1. **Understand Requirements**: Identify data sources, destinations, and transformation rules
2. **Design Architecture**: Map the data flow and choose appropriate tools
3. **Implement Pipeline**: Build with validation and error handling
4. **Validate and Test**: Test with sample data and verify data quality
5. **Monitor**: Add logging and monitoring for production use

## Critical Behaviors

- **Validate inputs**: Check schema, types, and constraints
- **Handle errors gracefully**: Fail loudly but recoverably
- **Log everything**: Track data lineage and issues
- **Test thoroughly**: Use realistic data samples
"""

API_DEVELOPER_TEMPLATE = """---
name: {name}
description: {description}
extends: kai-code
tools:
  - kai_code.tools.bash
  - kai_code.tools.read
  - kai_code.tools.write
  - kai_code.tools.edit
model: inherit
color: Purple
---

# Purpose

You are an **API Development Specialist** focused on building robust REST APIs, web services, and backend applications.

## Core Expertise

You excel at:
- **REST API Design**: Resource modeling and endpoint design
- **Framework Implementation**: FastAPI, Flask, Django REST Framework
- **Authentication & Authorization**: JWT, OAuth2, API keys
- **Database Integration**: ORMs, query optimization, transactions
- **API Documentation**: OpenAPI/Swagger, request/response schemas
- **Testing**: Unit tests, integration tests, API testing

## Instructions

When building APIs, follow this methodology:

1. **Design the API**: Define resources, endpoints, and schemas
2. **Implement Framework**: Set up FastAPI/Flask with proper structure
3. **Add Authentication**: Implement JWT or OAuth2
4. **Database Integration**: Connect to database with ORM
5. **Validation**: Add input validation and error handling
6. **Documentation**: Generate OpenAPI/Swagger docs
7. **Testing**: Write comprehensive tests

## Critical Behaviors

- Use appropriate HTTP status codes
- Validate input data rigorously
- Handle errors gracefully with structured responses
- Follow RESTful conventions
- Document all endpoints
- Test thoroughly before deploying
"""

ML_ENGINEER_TEMPLATE = """---
name: {name}
description: {description}
extends: kai-code
tools:
  - kai_code.tools.bash
  - kai_code.tools.read
  - kai_code.tools.write
  - kai_code.tools.edit
model: inherit
color: Orange
---

# Purpose

You are a **Machine Learning Engineer** focused on building, training, and deploying machine learning models and ML pipelines.

## Core Expertise

You excel at:
- **Feature Engineering**: Creating and selecting features for models
- **Model Development**: Training and evaluating ML models
- **Data Preprocessing**: Cleaning, transforming, and splitting data
- **Model Evaluation**: Cross-validation, metrics, and analysis
- **ML Pipelines**: Building reproducible ML workflows
- **Deployment**: Serving models in production
- **Experiment Tracking**: Logging experiments and results

## Instructions

When working on ML tasks, follow this methodology:

1. **Understand the Problem**: Define task type and success metrics
2. **Explore Data**: Analyze data quality and patterns
3. **Preprocess**: Clean, transform, and split data
4. **Build Models**: Train and evaluate multiple approaches
5. **Validate**: Use cross-validation and test sets
6. **Deploy**: Export model and create serving interface
7. **Monitor**: Track model performance in production

## Critical Behaviors

- Always split data before preprocessing (avoid leakage)
- Use appropriate evaluation metrics
- Track all experiments and hyperparameters
- Validate assumptions about data
- Test thoroughly before deployment
- Monitor model performance over time
"""


def get_template(template_name: str) -> str:
    """Get template content by name.

    Args:
        template_name: Name of template ('base', 'data-engineer', 'api-developer', 'ml-engineer')

    Returns:
        Template content string.

    Raises:
        ValueError: If template name is unknown.
    """
    templates = {
        "base": BASE_TEMPLATE,
        "data-engineer": DATA_ENGINEER_TEMPLATE,
        "api-developer": API_DEVELOPER_TEMPLATE,
        "ml-engineer": ML_ENGINEER_TEMPLATE,
    }

    if template_name not in templates:
        raise ValueError(
            f"Unknown template: {template_name}. "
            f"Available templates: {', '.join(templates.keys())}"
        )

    return templates[template_name]


def validate_agent_name(name: str) -> bool:
    """Validate agent name follows kebab-case convention.

    Args:
        name: Agent name to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not name:
        return False

    # Must be kebab-case (lowercase, hyphens, numbers)
    if not all(c.islower() or c.isdigit() or c == "-" for c in name):
        return False

    # Must start and end with alphanumeric
    if name[0] == "-" or name[-1] == "-":
        return False

    # No consecutive hyphens
    if "--" in name:
        return False

    return True


def init_agent(
    name: str,
    description: str | None = None,
    template: str = "base",
    extends: str | None = None,
    tools: str | None = None,
    model: str = "inherit",
    color: str = "Blue",
    output_dir: str = ".kai/agents",
) -> Path:
    """Initialize a new kai-code agent from template.

    Args:
        name: Agent name (kebab-case, e.g., 'my-agent').
        description: Agent description (action-oriented).
        template: Template to use ('base', 'data-engineer', 'api-developer', 'ml-engineer').
        extends: Parent agent to inherit from (overrides template).
        tools: Comma-separated list of tool patterns (overrides template).
        model: Model preference ('inherit', 'sonnet', 'opus', 'haiku').
        color: UI color for the agent.
        output_dir: Directory to create agent file (default: .kai/agents).

    Returns:
        Path to the created agent file.

    Raises:
        ValueError: If agent name is invalid or template is unknown.
        FileExistsError: If agent file already exists.
    """
    # Validate agent name
    if not validate_agent_name(name):
        raise ValueError(
            f"Invalid agent name '{name}'. "
            "Agent names must be kebab-case (lowercase, numbers, hyphens, "
            "cannot start/end with hyphen, no consecutive hyphens). "
            "Examples: 'my-agent', 'data-pipeline-v2', 'api-server'"
        )

    # Get template content
    template_content = get_template(template)

    # Set defaults
    if description is None:
        description = f"Custom agent for {name.replace('-', ' ')}"

    # Render template
    content = template_content.format(
        name=name,
        description=description,
    )

    # Allow overriding fields from template
    if extends or tools or model != "inherit" or color != "Blue":
        import re

        # Parse and replace fields
        if extends:
            content = re.sub(
                r"extends: [^\n]+",
                f"extends: {extends}",
                content
            )

        if tools:
            # Format tools as YAML list
            tool_list = "\n  - ".join(tools.split(","))
            content = re.sub(
                r"tools: [^\n]*\n(?:  - [^\n]*\n)*",
                f"tools:\n  - {tool_list}\n",
                content
            )

        if model != "inherit":
            content = re.sub(r"model: [^\n]+", f"model: {model}", content)

        if color != "Blue":
            content = re.sub(r"color: [^\n]+", f"color: {color}", content)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create agent file
    agent_file = output_path / f"{name}.md"

    if agent_file.exists():
        raise FileExistsError(
            f"Agent file already exists: {agent_file}. "
            "Use a different name or remove the existing file first."
        )

    agent_file.write_text(content)

    return agent_file


def list_templates() -> dict[str, str]:
    """List available agent templates.

    Returns:
        Dictionary mapping template names to descriptions.
    """
    return {
        "base": "General-purpose coding agent (inherits from kai-code)",
        "data-engineer": "Data pipeline and ETL specialist",
        "api-developer": "API and backend development specialist",
        "ml-engineer": "Machine learning and data science specialist",
    }
