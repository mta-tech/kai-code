# Kai-Code as Universal Agent Layer - Design Document

**Date**: 2025-01-14
**Status**: Design
**Author**: Design exploration via brainstorming

## Executive Summary

This document outlines the design for evolving kai-code into a universal agent layer library. Users will be able to create domain-specific AI agents through **two complementary approaches**:

1. **Python API**: Subclass `KaiAgent` with custom prompts and tools (for developers)
2. **Markdown Configuration**: Define agents declaratively in markdown files, compiles to Python at runtime (for accessibility)

Both approaches produce equivalent agents with shared interface and composability.

---

## Table of Contents

1. [Vision Summary](#vision-summary)
2. [Architecture](#architecture)
3. [Agent Definition via Markdown](#agent-definition-via-markdown)
4. [Subagent Model](#subagent-model)
5. [CLI Scaffolding](#cli-scaffolding)
6. [Implementation Planning](#implementation-planning)
7. [API Reference](#api-reference)
8. [Testing Strategy](#testing-strategy)
9. [Backward Compatibility](#backward-compatibility)
10. [Success Criteria](#success-criteria)

---

## Vision Summary

kai-code becomes a library for creating domain-specific AI agents through **dual paths** that converge at runtime:

```
                    ┌─────────────────────────────────────────┐
                    │           KaiAgent (Base)               │
                    │  - File ops, shell, patches             │
                    │  - Session persistence                  │
                    │  - YOLO/approval modes                  │
                    │  - Skills system                        │
                    │  - Prompt inheritance                   │
                    └─────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
          ┌─────────────────────┐         ┌──────────────────────┐
          │   Python Path       │         │    Markdown Path     │
          │                     │         │                      │
          │ class MyAgent       │         │ # .kai/agents/*.md   │
          │   (KaiAgent):       │         │ name: my-agent       │
          │   ...               │         │ prompt: ...          │
          └─────────────────────┘         │ tools: ...           │
                    │                     └──────────────────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │   Runtime Agent Instance  │
                        │   (both paths converge)   │
                        └──────────────────────────┘
```

**Key insight**: Markdown config is syntax sugar that compiles to a Python subclass at runtime.

### Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| User experience | Python API + Markdown config | Accessibility + power |
| Agent scope | Project-specific (like SeeknalAgent) | Deep domain integration |
| Key benefits | Both shared interface + composability | Flexibility |
| YAML/Markdown | Markdown with YAML frontmatter | Matches Claude's pattern |
| Agent relationship | YAML compiles to Python | Unified model |
| CLI coexistence | Domain CLIs coexist with kai-code | Gradual migration |

---

## Architecture

### Current State (Already Works)

```
                    ┌─────────────────────────────────────┐
                    │         KaiAgent (Base)             │
                    │  - File ops, shell, patches         │
                    │  - Session persistence              │
                    │  - YOLO/approval modes              │
                    │  - Skills system                    │
                    │  - Prompt inheritance               │
                    └─────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
          ┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
          │  SeeknalAgent   │ │  DbtAgent    │ │  [YourAgent] │
          │  - kai-seeknal  │ │  - kai-dbt   │ │  - custom    │
          │    prompt       │ │    prompt    │ │    prompt    │
          │  - Feature      │ │  - dbt       │ │  - domain    │
          │    store tools  │ │    tools     │ │    tools     │
          └─────────────────┘ └──────────────┘ └──────────────┘
```

The architecture already supports the pattern. What's needed:
1. Better documentation/templates
2. Code improvements (agent loading from markdown)
3. CLI scaffolding for easy agent creation
4. Subagent composition support

### Target State

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Agent (kai-code)                    │
│                                                             │
│  User: "Build a data pipeline and train an ML model"        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Decision Router                                    │   │
│  │  - Analyze request                                  │   │
│  │  - Identify tasks                                   │   │
│  │  - Delegate to subagents                            │   │
│  └─────────────────────────────────────────────────────┘   │
│           │                      │                          │
│           ▼                      ▼                          │
│  ┌──────────────┐        ┌──────────────┐                 │
│  │ data-engineer│        │  ml-engineer │                 │
│  │   subagent   │        │   subagent   │                 │
│  └──────────────┘        └──────────────┘                 │
│           │                      │                          │
│           └──────────┬───────────┘                          │
│                      ▼                                     │
│         ┌─────────────────────────┐                        │
│         │   Result Synthesis      │                        │
│         └─────────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Definition via Markdown

kai-code adopts Claude's markdown-based agent definition pattern. Agents are defined in `.kai/agents/*.md` files with YAML frontmatter.

### Agent Definition Structure

```markdown
---
name: seeknal-data-engineer
description: Specialist for building data pipelines, feature stores, and ETL workflows with Seeknal. Use proactively for data engineering tasks.
tools: kai_code.agents.seeknal.tools.*, Bash, Read, Write
model: sonnet
---

# Purpose

You are a Data Engineering Specialist focused on building efficient data pipelines and feature stores using the Seeknal library.

## Core Expertise

You excel at:
- Building multi-engine data flows (DuckDB and Spark)
- Designing feature store schemas for ML models
- Entity relationship modeling
- Data pipeline orchestration
- Engine selection and optimization

## Instructions

When invoked, follow this methodology:

1. **Understand Requirements**: Clarify the data pipeline goals, data sources, and target use cases
2. **Engine Selection**: Choose DuckDB for <100M rows, Spark for larger datasets
3. **Design Schema**: Create entities with appropriate join keys and feature groups
4. **Build Pipeline**: Use Flow tools to orchestrate data transformation
5. **Validate**: Ensure SQL injection protection and path security
6. **Materialize**: Build features to offline store for batch serving

## Critical Behaviors

- Always validate SQL identifiers using Seeknal's validation functions
- Warn about security risks (e.g., /tmp usage, SQL injection)
- Prefer DuckDB unless Spark is explicitly needed
- Document pipeline dependencies and data sources
- Handle errors gracefully with clear messages

## Output Format

Provide:
1. Pipeline architecture overview
2. Engine selection rationale
3. Entity and feature group definitions
4. Flow configuration with source/destination
5. Materialization commands
6. Validation results
```

### YAML Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | kebab-case agent identifier |
| `description` | string | Yes | Action-oriented description for automatic delegation. Use phrases like "Use proactively for..." or "Specialist for..." |
| `tools` | list | No | Comma-separated tool names. If omitted, inherits all parent tools |
| `allowed-tools` | list | No | Alternative to `tools` - whitelist of tools |
| `model` | string | No | Model override: `sonnet`, `opus`, `haiku`, or `inherit` |
| `color` | string | No | Visual indicator: `Red`, `Blue`, `Green`, etc. |
| `extends` | string | No | Parent agent name to inherit from |

### Agent Inheritance

```markdown
---
name: seeknal-ml-engineer
description: ML feature engineering specialist for Seeknal feature stores
extends: seeknal-data-engineer
tools: kai_code.agents.seeknal.tools.feature_store_tools, kai_code.agents.seeknal.tools.entity_tools
---

# Purpose

You extend the Data Engineer with ML-specific expertise...

## Additional Expertise

In addition to data engineering, you specialize in:
- Feature engineering for ML models
- Train/test split strategies
- Feature versioning for experiment tracking
- Entity relationship design for prediction tasks
...
```

### Loading Agents at Runtime

```python
# src/kai_code/agent_loader.py
from pathlib import Path
from typing import Any
import yaml

class AgentDefinition:
    """Agent definition loaded from markdown file."""
    
    def __init__(self, path: Path):
        self.path = path
        self._parse()
    
    def _parse(self):
        """Parse markdown file with YAML frontmatter."""
        content = self.path.read_text()
        
        # Split frontmatter and content
        if content.startswith('---'):
            _, fm, body = content.split('---', 2)
            self.metadata = yaml.safe_load(fm)
        else:
            self.metadata = {}
            body = content
        
        self.name = self.metadata.get('name', self.path.stem)
        self.description = self.metadata.get('description', '')
        self.tools = self.metadata.get('tools', [])
        self.allowed_tools = self.metadata.get('allowed-tools', [])
        self.model = self.metadata.get('model', 'inherit')
        self.extends = self.metadata.get('extends')
        self.system_prompt = body.strip()
    
    def to_agent_class(self, base_class: type = KaiAgent) -> type:
        """Compile to a Python agent class."""
        
        class CompiledAgent(base_class):
            def _get_base_prompt_name(self) -> str:
                return self.name
            
            def _get_subclass_tools(self) -> list:
                return self._load_tools()
            
            def _load_tools(self) -> list:
                # Import tools based on patterns
                from kai_code.tools import load_tools_from_patterns
                return load_tools_from_patterns(self.tools)
        
        # Set class metadata
        CompiledAgent.__name__ = f'{self.name.title()}Agent'
        CompiledAgent.__doc__ = self.description
        CompiledAgent._kai_definition = self
        
        return CompiledAgent


def load_agent(name: str, agents_dir: Path = None) -> KaiAgent:
    """Load an agent by name from .kai/agents/ directory."""
    if agents_dir is None:
        agents_dir = Path.cwd() / '.kai' / 'agents'
    
    agent_path = agents_dir / f'{name}.md'
    if not agent_path.exists():
        raise FileNotFoundError(f"Agent '{name}' not found at {agent_path}")
    
    definition = AgentDefinition(agent_path)
    
    # Handle inheritance
    if definition.extends:
        parent_def = load_agent(definition.extends, agents_dir)
        # Merge prompts, tools, etc.
    
    # Compile to class and instantiate
    agent_class = definition.to_agent_class()
    return agent_class(root_dir=Path.cwd())
```

---

## Subagent Model

Subagents follow the **deepagents delegation pattern** - specialized agents are exposed as callable tools that the main agent can invoke for specific tasks.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Agent (kai-code)                    │
│                                                             │
│  User: "Build a data pipeline and train an ML model"        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Decision Router                                    │   │
│  │  - Analyze request                                  │   │
│  │  - Identify tasks                                   │   │
│  │  - Delegate to subagents                            │   │
│  └─────────────────────────────────────────────────────┘   │
│           │                      │                          │
│           ▼                      ▼                          │
│  ┌──────────────┐        ┌──────────────┐                 │
│  │ data-engineer│        │  ml-engineer │                 │
│  │   subagent   │        │   subagent   │                 │
│  └──────────────┘        └──────────────┘                 │
│           │                      │                          │
│           └──────────┬───────────┘                          │
│                      ▼                                     │
│         ┌─────────────────────────┐                        │
│         │   Result Synthesis      │                        │
│         └─────────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### YAML Configuration for Subagents

```yaml
# .kai/agents/seeknal.yaml
name: seeknal

# Subagent delegation model
subagents:
  # Data engineering specialist
  - name: data-engineer
    description: "Handles data pipelines, feature stores, and ETL workflows"
    
    # Agent specification (can reference another YAML or Python class)
    agent:
      type: yaml                    # or 'python'
      ref: ./data-engineer.yaml     # path to subagent config
    
    # Tools available to this subagent
    tools:
      include: 
        - kai_code.agents.seeknal.tools.project_tools
        - kai_code.agents.seeknal.tools.flow_tools
        - kai_code.agents.seeknal.tools.feature_store_tools
    
    # Prompt specialization
    prompt:
      base: kai-seeknal
      override: |
        Focus on:
        - Building efficient data pipelines
        - DuckDB vs Spark engine selection
        - Feature store best practices
        - Data validation and security
        
    # Routing trigger (when to use this subagent)
    trigger:
      keywords: [pipeline, etl, feature, data, extract, transform]
      tool_patterns: [create_project, create_flow, materialize]
    
    # Execution mode
    mode: tool                     # 'tool' = exposed as tool, 'router' = automatic routing
  
  # ML engineer specialist  
  - name: ml-engineer
    description: "Handles feature engineering for ML models"
    
    agent:
      type: python
      ref: kai_code.agents.seeknal.MLEngineerAgent
    
    tools:
      include:
        - kai_code.agents.seeknal.tools.feature_store_tools
        - kai_code.agents.seeknal.tools.entity_tools
        - kai_code.agents.seeknal.tools.version_tools
    
    prompt:
      base: kai-seeknal
      override: |
        Focus on:
        - Feature engineering for ML
        - Entity relationship design
        - Feature versioning and rollback
        - Train/test split patterns
        
    trigger:
      keywords: [ml, model, training, prediction, feature, entity]
      tool_patterns: [create_entity, feature_version]
    
    mode: tool
```

### Python Subagent Definition

```python
# src/kai_code/agents/seeknal/subagents.py
from typing import Any
from kai_code.agent import KaiAgent

class DataEngineerAgent(KaiAgent):
    """Specialized subagent for data engineering tasks."""
    
    def _get_base_prompt_name(self) -> str:
        return "kai-seeknal-data-eng"
    
    def get_data_engineer_tools(self) -> list:
        from kai_code.agents.seeknal.tools import (
            create_project_tools,
            create_flow_tools,
            create_feature_store_tools,
        )
        seeknal_path = self._seeknal_path
        return [
            *create_project_tools(seeknal_path),
            *create_flow_tools(seeknal_path),
            *create_feature_store_tools(seeknal_path),
        ]
    
    def _get_subclass_tools(self) -> list:
        return self.get_data_engineer_tools()


class MLEngineerAgent(KaiAgent):
    """Specialized subagent for ML feature engineering."""
    
    def _get_base_prompt_name(self) -> str:
        return "kai-seeknal-ml"
    
    def get_ml_tools(self) -> list:
        from kai_code.agents.seeknal.tools import (
            create_feature_store_tools,
            create_entity_tools,
            create_version_tools,
        )
        seeknal_path = self._seeknal_path
        return [
            *create_feature_store_tools(seeknal_path),
            *create_entity_tools(seeknal_path),
            *create_version_tools(seeknal_path),
        ]
    
    def _get_subclass_tools(self) -> list:
        return self.get_ml_tools()
```

### Subagent Tool Wrapper (deepagents pattern)

```python
# src/kai_code/subagents.py
from langchain_core.tools import tool
from typing import Any

def create_subagent_tool(
    agent: KaiAgent,
    name: str,
    description: str,
) -> Any:
    """Wrap a subagent as a callable tool (deepagents delegation pattern)."""
    
    @tool(name)
    def subagent_tool(task: str) -> str:
        """Delegate task to specialized subagent.
        
        Args:
            task: Detailed description of the task to delegate.
            
        Returns:
            Result from the subagent execution.
        """
        # Create fresh subagent instance
        subagent = agent.__class__(
            root_dir=agent.config.root_dir,
            model=agent.config.model,
            yolo=agent.config.yolo,
        )
        
        # Run the task
        result = subagent.run(task)
        return result.output
    
    subagent_tool.description = description
    return subagent_tool


def load_subagents(agent_config: dict) -> list:
    """Load subagents from configuration and wrap as tools."""
    tools = []
    
    for subagent_def in agent_config.get("subagents", []):
        # Load subagent (from YAML or Python)
        subagent = _load_subagent(subagent_def["agent"])
        
        # Wrap as tool
        tool = create_subagent_tool(
            agent=subagent,
            name=subagent_def["name"],
            description=subagent_def.get("description", ""),
        )
        tools.append(tool)
    
    return tools
```

### Usage Example

```python
# User interaction with main agent
agent = load_agent_from_yaml(".kai/agents/seeknal.yaml")

# User asks a complex task spanning multiple domains
result = agent.run("""
    Build a data pipeline that:
    1. Extracts user activity from Parquet files
    2. Creates feature groups for churn prediction
    3. Sets up entity relationships
    4. Materializes features for training
""")

# Main agent analyzes and delegates:
# - "data-engineer" subagent handles pipeline setup (1-2)
# - "ml-engineer" subagent handles entity/features (3-4)
# - Main agent synthesizes results
```

---

## CLI Scaffolding

The `kai-code` CLI should include commands to scaffold new agents, following conventions similar to `npm init`, `cargo new`, or `django-admin startproject`.

### CLI Commands

```bash
# Create a new agent interactively
kai-code init-agent

# Create with specific name
kai-code init-agent my-data-agent

# Create from template
kai-code init-agent my-agent --template data-engineer

# List available templates
kai-code list-templates

# Generate Python class from markdown agent
kai-code compile-agent .kai/agents/my-agent.md

# Validate agent definition
kai-code validate-agent .kai/agents/my-agent.md
```

### Interactive Flow

```bash
$ kai-code init-agent

? Agent name (kebab-case): my-ml-agent
? Description: ML pipeline specialist for scikit-learn workflows
? Parent agent (optional): kai-code
? Model preference: 
  ◉ inherit (use parent's model)
  ○ sonnet
  ○ opus
  ○ haiku
? Tools to include (space to select, enter to finish):
  ◯ Bash
  ⬡ Read
  ⬡ Write
  ⬡ Edit
  ◯ Grep
  ◯ Glob
  ⬡ WebSearch
? Color for UI:
  ◉ Blue
  ○ Green
  ○ Purple
  ○ Cyan

✓ Created .kai/agents/my-ml-agent.md
✓ Created src/my_project/agents/my_ml_agent.py (optional)
✓ Added to .gitignore

Next steps:
1. Edit .kai/agents/my-ml-agent.md to customize the system prompt
2. Run: kai-code run my-ml-agent "your task here"
3. Or compile to Python: kai-code compile-agent .kai/agents/my-ml-agent.md
```

### Agent Templates

Built-in templates provide starting points for common agent types:

```bash
$ kai-code list-templates

Available agent templates:
  base           - General-purpose coding agent (inherits KaiAgent)
  data-engineer  - Data pipeline and ETL specialist
  ml-engineer    - ML feature engineering specialist
  dbt-analyst    - dbt transformation specialist
  api-developer  - API/endpoint development specialist
  tester         - Test generation specialist
  reviewer       - Code review specialist
  custom         - Blank template with guidance
```

### Template: `data-engineer`

```markdown
---
name: {{name}}
description: {{description}}
extends: kai-code
tools: Bash, Read, Write, Edit, Grep, Glob, WebSearch
model: inherit
color: Blue
---

# Purpose

You are a Data Engineering Specialist focused on building efficient data pipelines and ETL workflows.

## Core Expertise

You excel at:
- Building data pipelines with modern tools
- ETL/ELT workflow design
- Data transformation and validation
- Working with databases (SQL, NoSQL)
- Pipeline orchestration and scheduling

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
1. Pipeline architecture diagram
2. Step-by-step implementation
3. Configuration files
4. Validation queries/tests
5. Setup and run instructions
```

### Template Implementation

```python
# src/kai_code/cli/init_agent.py
import click
from pathlib import Path
from typing import Optional
import yaml
from jinja2 import Template

# Template definitions
TEMPLATES = {
    "base": "base_agent.md.j2",
    "data-engineer": "data_engineer.md.j2",
    "ml-engineer": "ml_engineer.md.j2",
    "dbt-analyst": "dbt_analyst.md.j2",
    "api-developer": "api_developer.md.j2",
    "tester": "tester.md.j2",
    "reviewer": "reviewer.md.j2",
    "custom": "custom.md.j2",
}

@click.command()
@click.argument("name", required=False)
@click.option("--template", "-t", type=click.Choice(list(TEMPLATES.keys())), 
              default="custom", help="Agent template to use")
@click.option("--description", "-d", help="Agent description")
@click.option("--extends", "-e", help="Parent agent to inherit from")
@click.option("--tools", help="Comma-separated list of tools")
@click.option("--output-dir", "-o", type=Path, default=Path(".kai/agents"),
              help="Output directory for agent file")
@click.option("--compile", is_flag=True, help="Also compile to Python class")
def init_agent(name, template, description, extends, tools, output_dir, compile):
    """Create a new kai-code agent definition."""
    
    # Interactive mode if no name provided
    if not name:
        name = _prompt_name()
        description = description or _prompt_description()
        template = _prompt_template()
        extends = extends or _prompt_extends()
        tools = tools or _prompt_tools()
    
    # Load and render template
    template_path = Path(__file__).parent / "templates" / TEMPLATES[template]
    template_content = template_path.read_text()
    jinja_template = Template(template_content)
    content = jinja_template.render(
        name=name,
        description=description or f"Specialist agent for {name}",
        extends=extends or "kai-code",
        tools=tools or "Bash, Read, Write, Edit",
        model="inherit",
    )
    
    # Write agent file
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    agent_path = output_dir / f"{name}.md"
    agent_path.write_text(content)
    
    click.secho(f"✓ Created {agent_path}", fg="green")
    
    # Optionally compile to Python
    if compile:
        _compile_agent(agent_path)
    
    # Print next steps
    _print_next_steps(name, agent_path)
```

### Template Directory Structure

```
src/kai_code/
├── cli/
│   ├── templates/
│   │   ├── base_agent.md.j2
│   │   ├── data_engineer.md.j2
│   │   ├── ml_engineer.md.j2
│   │   ├── dbt_analyst.md.j2
│   │   ├── api_developer.md.j2
│   │   ├── tester.md.j2
│   │   ├── reviewer.md.j2
│   │   └── custom.md.j2
│   └── init_agent.py
```

---

## Implementation Planning

Implementation should be phased to allow incremental adoption without breaking existing functionality.

### Phase 1: Core Agent Loading (Foundation)

**Goal**: Enable loading agents from markdown files without changing existing KaiAgent behavior.

```
Week 1-2: Core Agent Loader
├── AgentDefinition class
│   ├── Parse markdown with YAML frontmatter
│   ├── Validate metadata
│   └── Extract system prompt
├── Agent compilation
│   ├── to_agent_class() method
│   ├── Tool pattern loading
│   └── Inheritance handling
└── Tests
    ├── Unit tests for parsing
    ├── Compilation tests
    └── Integration with existing agents
```

**Key Files**:
- `src/kai_code/agent_loader.py` (new)
- `src/kai_code/agent_definition.py` (new)
- `tests/agent_loader/test_definition.py` (new)
- `tests/agent_loader/test_compilation.py` (new)

**Acceptance Criteria**:
- Can load SeeknalAgent from markdown definition
- Compiled agent is functionally equivalent to Python subclass
- All existing tests pass
- No breaking changes to KaiAgent API

### Phase 2: Prompt System Enhancement

**Goal**: Support markdown-based prompts alongside existing `.md` files.

```
Week 3: Agent Definition Prompts
├── Extend prompt loader
│   ├── Load from .kai/agents/*.md
│   ├── Support inheritance in agent definitions
│   └── Merge with existing prompt system
└── Documentation
    ├── How agent definitions work
    └── Migration guide from prompts/
```

**Key Files**:
- `src/kai_code/prompts/__init__.py` (modify)
- `src/kai_code/agent_definition.py` (extend)
- `docs/agent-definition-guide.md` (new)

**Acceptance Criteria**:
- Agent definitions can reference base prompts
- Prompt inheritance works across markdown agents
- Backward compatible with existing prompt files

### Phase 3: Subagent Support

**Goal**: Implement deepagents-style subagent delegation.

```
Week 4-5: Subagent Infrastructure
├── Subagent tool wrapper
│   ├── create_subagent_tool()
│   ├── Execution isolation
│   └── Result synthesis
├── Subagent loading
│   ├── Load from agent definition
│   ├── Nested agent support
│   └── Circular dependency detection
└── Testing
    ├── Subagent invocation tests
    ├── Result synthesis tests
    └── Error handling tests
```

**Key Files**:
- `src/kai_code/subagents.py` (new)
- `src/kai_code/agent.py` (modify - add subagent support)
- `tests/subagents/test_delegation.py` (new)

**Acceptance Criteria**:
- Main agent can delegate to subagents
- Subagents execute in isolated context
- Results flow back to main agent
- Deepagents pattern is followed

### Phase 4: CLI Scaffolding

**Goal**: Provide `kai-code init-agent` command for easy agent creation.

```
Week 6: Agent Scaffolding CLI
├── Template system
│   ├── Jinja2 templates
│   ├── Built-in agent templates
│   └── Custom template support
├── Interactive CLI
│   ├── kai-code init-agent
│   ├── kai-code compile-agent
│   └── kai-code validate-agent
└── Documentation
    ├── CLI reference
    └── Template authoring guide
```

**Key Files**:
- `src/kai_code/cli/init_agent.py` (new)
- `src/kai_code/cli/compile_agent.py` (new)
- `src/kai_code/cli/validate_agent.py` (new)
- `src/kai_code/cli/templates/*.md.j2` (new)
- `docs/agent-scaffolding.md` (new)

**Acceptance Criteria**:
- `kai-code init-agent` creates valid agent definitions
- `kai-code compile-agent` generates working Python code
- `kai-code validate-agent` catches common errors
- Templates cover common use cases

### Phase 5: Documentation & Examples

**Goal**: Comprehensive documentation for agent creators.

```
Week 7: Documentation & Examples
├── Core documentation
│   ├── Agent definition reference
│   ├── Subagent guide
│   ├── Tool authoring guide
│   └── Best practices
├── Example agents
│   ├── data-engineer agent
│   ├── ml-engineer agent
│   ├── api-developer agent
│   └── Custom agent tutorial
└── Migration guide
    ├── From Python subclass to markdown
    └── From CLI args to agent definition
```

**Key Files**:
- `docs/agent-development-guide.md` (new)
- `docs/subagent-patterns.md` (new)
- `docs/tool-authoring.md` (new)
- `.kai/agents/example-*` (new examples)
- `examples/agent-development/` (new)

**Acceptance Criteria**:
- New users can create agents without reading source code
- Example agents demonstrate all features
- Migration path from existing code is clear

### Phase 6: Migration of Existing Agents

**Goal**: Migrate SeeknalAgent and DbtAgent to hybrid model.

```
Week 8: Migration
├── SeeknalAgent migration
│   ├── Create .kai/agents/seeknal.md
│   ├── Keep Python class for compatibility
│   └── Test parity
├── DbtAgent migration
│   ├── Create .kai/agents/dbt.md
│   ├── Keep Python class for compatibility
│   └── Test parity
└── Documentation
    ├── Migration checklist
    └── Breaking changes (none planned)
```

**Key Files**:
- `.kai/agents/seeknal.md` (new)
- `.kai/agents/seeknal-data-eng.md` (new)
- `.kai/agents/seeknal-ml.md` (new)
- `.kai/agents/dbt.md` (new)
- `src/kai_code/agents/seeknal/agent.py` (modify - add loading)
- `src/kai_code/agents/dbt/agent.py` (modify - add loading)

**Acceptance Criteria**:
- Both Python and markdown paths work
- Feature parity between approaches
- Documentation shows both methods

### Implementation Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                    Implementation Timeline                  │
├─────────────────────────────────────────────────────────────┤
│ Phase 1: Core Agent Loader           ████████ (Week 1-2)   │
│ Phase 2: Prompt Enhancement          ████     (Week 3)     │
│ Phase 3: Subagent Support            ████████ (Week 4-5)   │
│ Phase 4: CLI Scaffolding             ██████   (Week 6)     │
│ Phase 5: Documentation               ████████ (Week 7)     │
│ Phase 6: Migration                   ████     (Week 8)     │
└─────────────────────────────────────────────────────────────┘

Dependencies:
  Phase 2 depends on Phase 1 (needs agent loading)
  Phase 3 depends on Phase 1 (needs agent compilation)
  Phase 4 depends on Phase 1 (needs compilation target)
  Phase 5 depends on Phases 1-4 (docs final features)
  Phase 6 depends on Phases 1-5 (migrate when complete)
```

---

## API Reference

### Agent Loading API

```python
# src/kai_code/agent_loader.py

def load_agent(
    name: str,
    agents_dir: Path | str | None = None,
    root_dir: Path | str | None = None,
    **kwargs
) -> KaiAgent:
    """Load an agent from markdown definition.
    
    Args:
        name: Agent name (kebab-case, matches .md filename)
        agents_dir: Directory containing agent definitions (default: .kai/agents/)
        root_dir: Project root directory (default: current working directory)
        **kwargs: Additional arguments passed to agent constructor
        
    Returns:
        Initialized KaiAgent instance
        
    Example:
        >>> agent = load_agent('seeknal-data-engineer')
        >>> result = agent.run("Create a feature group")
    """

def list_agents(agents_dir: Path | str | None = None) -> list[str]:
    """List all available agent definitions.
    
    Returns:
        List of agent names (kebab-case)
    """

class AgentDefinition:
    """Parsed agent definition from markdown file."""
    
    @property
    def name(self) -> str:
        """Agent identifier (kebab-case)."""
        
    @property
    def description(self) -> str:
        """Action-oriented description for delegation."""
        
    @property
    def tools(self) -> list[str]:
        """Tool patterns (may include wildcards)."""
        
    @property
    def model(self) -> str | None:
        """Model override or 'inherit'."""
        
    @property
    def extends(self) -> str | None:
        """Parent agent name."""
        
    @property
    def system_prompt(self) -> str:
        """Full system prompt body."""
        
    def to_agent_class(base_class: type = KaiAgent) -> type:
        """Compile to Python agent class."""
        
    def validate() -> list[str]:
        """Validate definition, returns list of errors (empty if valid)."""
```

### Subagent API

```python
# src/kai_code/subagents.py

def create_subagent_tool(
    agent: KaiAgent,
    name: str,
    description: str
) -> Any:
    """Wrap a subagent as a callable tool.
    
    Creates a LangChain tool that delegates tasks to the specified subagent.
    Follows deepagents delegation pattern.
    
    Args:
        agent: Subagent instance to wrap
        name: Tool name for the subagent
        description: When to use this subagent
        
    Returns:
        LangChain tool object
    """

def load_subagents(
    agent_config: dict | AgentDefinition,
    parent_agent: KaiAgent
) -> list:
    """Load and wrap subagents from configuration.
    
    Args:
        agent_config: Agent definition with subagents field
        parent_agent: Parent agent instance
        
    Returns:
        List of subagent tools
    """
```

### CLI API

```bash
# Agent management
kai-code init-agent [NAME] [OPTIONS]
kai-code list-agents
kai-code validate-agent AGENT_FILE
kai-code compile-agent AGENT_FILE

# Agent execution
kai-code run AGENT_NAME "PROMPT"
kai-code run --agent .kai/agents/my-agent.md "PROMPT"

# Template management
kai-code list-templates
kai-code new-template NAME
```

---

## Testing Strategy

### Unit Tests

```python
# tests/agent_loader/test_definition.py
def test_parse_agent_with_frontmatter():
    """Test parsing agent with YAML frontmatter."""
    
def test_parse_agent_without_frontmatter():
    """Test parsing agent without frontmatter (defaults)."""
    
def test_parse_agent_with_inheritance():
    """Test parsing agent with extends field."""
    
def test_parse_agent_invalid_name():
    """Test validation rejects invalid agent names."""
    
def test_agent_to_python_class():
    """Test compilation to Python class."""
    
def test_agent_validation_empty_description():
    """Test validation catches missing description."""
```

### Integration Tests

```python
# tests/agent_loader/test_loading.py
def test_load_agent_from_markdown():
    """Test loading and running agent from markdown."""
    
def test_loaded_agent_equivalent_to_python():
    """Test markdown agent is functionally equivalent to Python subclass."""
    
def test_agent_inheritance_chain():
    """Test agent inherits from parent correctly."""
    
def test_agent_tools_pattern_expansion():
    """Test tool patterns are expanded correctly."""
```

### Subagent Tests

```python
# tests/subagents/test_delegation.py
def test_subagent_tool_invocation():
    """Test subagent can be invoked as tool."""
    
def test_subagent_result_synthesis():
    """Test results flow back to main agent."""
    
def test_subagent_isolation():
    """Test subagent has isolated context."""
    
def test_nested_subagents():
    """Test subagent can have its own subagents."""
```

### CLI Tests

```python
# tests/cli/test_init_agent.py
def test_init_agent_creates_file():
    """Test init-agent creates markdown file."""
    
def test_init_agent_interactive():
    """Test interactive mode works."""
    
def test_init_agent_from_template():
    """Test template-based creation."""
    
def test_compile_agent_generates_python():
    """Test compile-agent generates valid Python."""
    
def test_validate_agent_catches_errors():
    """Test validate-agent finds problems."""
```

### E2E Tests

```python
# tests/e2e/test_agent_workflow.py
def test_full_agent_creation_workflow():
    """Test: init -> edit -> validate -> compile -> run"""
    
def test_seeknal_agent_migration():
    """Test SeeknalAgent works from markdown definition."""
    
def test_subagent_delegation_e2e():
    """Test end-to-end subagent delegation."""
```

---

## Backward Compatibility

**Zero Breaking Changes Policy:**

All existing code must continue working without modifications:

```python
# Existing code - MUST CONTINUE WORKING
from kai_code.agents.seeknal import SeeknalAgent
from kai_code.agents.dbt import DbtAgent
from kai_code.agent import KaiAgent

agent = SeeknalAgent(root_dir=Path.cwd())
result = agent.run("some task")
```

**Migration Path:**

Users can migrate gradually at their own pace:

| Phase | Capability | User Action Required |
|--------|-----------|---------------------|
| Current | Python subclass only | None |
| Phase 1 | Markdown agents available | Optional: Try `load_agent()` |
| Phase 3 | Subagents supported | Optional: Use subagents |
| Phase 4 | CLI scaffolding | Optional: Use `init-agent` |
| Phase 6 | Both paths equal | Optional: Migrate when ready |

**For existing Python subclass users:**
```python
# Current: Python subclass
from kai_code.agents.seeknal import SeeknalAgent
agent = SeeknalAgent(root_dir=Path.cwd())

# Option 1: Continue using Python (no changes)
# Still works, fully supported

# Option 2: Migrate to markdown (when ready)
from kai_code.agent_loader import load_agent
agent = load_agent('seeknal')  # Loads from .kai/agents/seeknal.md
```

**For new users:**
```bash
# Start directly with markdown
kai-code init-agent my-agent --template data-engineer
kai-code run my-agent "your task here"
```

---

## Success Criteria

The implementation is successful when:

### Technical Criteria
- [ ] All existing tests pass (100% backward compatibility)
- [ ] New code has >80% test coverage
- [ ] SeeknalAgent can be loaded from markdown with feature parity
- [ ] DbtAgent can be loaded from markdown with feature parity
- [ ] Subagent delegation works following deepagents pattern
- [ ] CLI scaffolding creates working agents
- [ ] Documentation enables agent creation without reading source code

### User Experience Criteria
- [ ] New users can create agents in <10 minutes using CLI
- [ ] Non-programmers can create agents using markdown
- [ ] Programmers have full power via Python subclassing
- [ ] Both approaches are documented equally well
- [ ] Migration from Python to markdown is optional and clear

### Design Goals
- [ ] Shared interface: All agents are KaiAgent instances
- [ ] Composability: Subagents can be mixed and matched
- [ ] Accessibility: Markdown path for non-programmers
- [ ] Power: Python path for advanced use cases

---

## Appendix: Related Files

- Claude Agent SDK: https://platform.claude.com/docs/en/agent-sdk/python
- Claude Agent Definitions: `~/.claude/agents/*.md`
- Current SeeknalAgent: `src/kai_code/agents/seeknal/agent.py`
- Current DbtAgent: `src/kai_code/agents/dbt/agent.py`
- Prompt System: `src/kai_code/prompts/__init__.py`

---

**End of Design Document**
