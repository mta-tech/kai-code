# Kai-Code Example Agents

This directory contains example agent definitions that demonstrate different patterns and use cases for building custom agents with kai-code.

## Available Examples

### [`base-agent.md`](./base-agent.md)
A minimal template for building custom agents. Use this as a starting point for creating your own agents.

**Best for**: Learning the agent definition structure

### [`data-engineer.md`](./data-engineer.md)
Data engineering specialist for building ETL pipelines, data transformations, and workflows.

**Best for**: Data pipeline projects, ETL workflows, data processing tasks

### [`api-developer.md`](./api-developer.md)
API and backend development specialist for building REST APIs and web services.

**Best for**: Backend development, API projects, server-side applications

### [`ml-engineer.md`](./ml-engineer.md)
Machine learning engineer for building models, feature engineering, and ML pipelines.

**Best for**: ML projects, data science, model development

## How to Use These Examples

### 1. Copy and Customize

```bash
# Copy an example to your agents directory
cp .kai/agents/examples/data-engineer.md .kai/agents/my-agent.md

# Edit to customize
vim .kai/agents/my-agent.md
```

### 2. Update Key Fields

```yaml
---
name: my-agent                    # Update with your agent name
description: Your description     # Describe when to use this agent
extends: kai-code                  # Or another base agent
tools:                            # List tools your agent needs
  - kai_code.tools.bash
  - kai_code.tools.read
  - kai_code.tools.write
model: inherit                     # Or specify: sonnet, opus, haiku
color: Blue                        # For UI display
---
```

### 3. Customize the Prompt

Edit the sections below the YAML frontmatter:
- **Purpose**: Describe what your agent does
- **Core Expertise**: List agent's specializations
- **Instructions**: Add methodology and patterns
- **Critical Behaviors**: Define constraints and best practices
- **Output Format**: Specify expected outputs

### 4. Test Your Agent

```bash
# Load and run your agent
kai-code run my-agent "Your task here"

# Or use programmatically
python -c "
from kai_code.agent_loader import load_agent
agent = load_agent('my-agent')
result = agent.run('Your task here')
print(result)
"
```

## Agent Definition Structure

Each agent definition has:

### YAML Frontmatter
Metadata that configures the agent:
- `name`: Unique identifier (kebab-case)
- `description`: When to use this agent
- `extends`: Base prompt to inherit from
- `tools`: Tools available to the agent
- `model`: LLM model to use
- `color`: UI display color

### Markdown Body
The agent's system prompt:
- **Purpose**: What the agent does
- **Core Expertise**: Key capabilities
- **Instructions**: How to approach tasks
- **Critical Behaviors**: Constraints and patterns
- **Output Format**: Expected deliverables
- **Examples**: Code samples and patterns

## Common Patterns

### General-Purpose Agent
```yaml
extends: kai-code
tools: kai_code.tools.*
```

### Domain-Specific Agent
```yaml
extends: kai-code
tools:
  - kai_code.tools.bash
  - kai_code.tools.read
  - kai_code.tools.write
  - my_package.domain_tools
```

### Agent with Subagents
```yaml
extends: kai-code
tools: kai_code.tools.*
subagents:
  - name: specialist
    agent: specialist-agent
    description: When to delegate to this specialist
```

## Best Practices

1. **Start Simple**: Begin with `base-agent.md` template
2. **Be Specific**: Clear descriptions help agents choose when to use yours
3. **Provide Context**: Include examples and patterns in the prompt
4. **Constrain Tools**: Only include necessary tools for the domain
5. **Test Iteratively**: Validate agent behavior before extensive customization
6. **Version Control**: Track agent definitions in git

## Learning Path

1. **Start**: Read `base-agent.md` to understand structure
2. **Explore**: Review domain-specific examples relevant to your work
3. **Customize**: Copy and modify an example for your use case
4. **Test**: Run your agent with typical tasks
5. **Refine**: Adjust based on results

## Additional Resources

- **Agent Development Guide**: `docs/agent-development-guide.md`
- **Tool Authoring**: `docs/tool-authoring.md`
- **Subagent Patterns**: `docs/subagent-patterns.md`
- **Design Document**: `docs/plans/2025-01-14-agent-layer-design.md`

## Need Help?

1. Check the documentation in `docs/`
2. Review existing agents: `.kai/agents/seeknal.md`, `.kai/agents/dbt.md`
3. Examine source code: `src/kai_code/agents/`
4. Run tests: `pytest tests/agent_loader/ -v`
