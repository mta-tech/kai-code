# Agent Layer: Phase 1 - Core Agent Loading Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable loading kai-code agents from markdown files with YAML frontmatter, compiling them to Python classes at runtime.

**Architecture:** 
- Parse markdown files with YAML frontmatter (following Claude's agent pattern)
- Compile markdown definitions to Python KaiAgent subclasses
- Maintain 100% backward compatibility with existing Python subclasses

**Tech Stack:** Python 3.10+, Pydantic (for validation), PyYAML (frontmatter parsing), existing LangChain/LangGraph infrastructure

---

## Task 1: Create AgentDefinition Data Class

**Files:**
- Create: `src/kai_code/agent_definition.py`
- Test: `tests/agent_loader/test_agent_definition.py`

**Step 1: Write failing tests for AgentDefinition**

Create `tests/agent_loader/test_agent_definition.py`:

```python
"""Tests for AgentDefinition class."""
import pytest
from pathlib import Path
from kai_code.agent_definition import AgentDefinition


def test_parse_agent_with_full_frontmatter(tmp_path):
    """Test parsing agent with complete YAML frontmatter."""
    # Create test agent file
    agent_file = tmp_path / "test-agent.md"
    agent_file.write_text("""---
name: test-agent
description: Test agent for unit testing
tools: Bash, Read, Write
model: sonnet
extends: kai-code
---

# Purpose

You are a test agent.
""")
    
    # Parse the agent
    definition = AgentDefinition(agent_file)
    
    assert definition.name == "test-agent"
    assert definition.description == "Test agent for unit testing"
    assert definition.tools == ["Bash", "Read", "Write"]
    assert definition.model == "sonnet"
    assert definition.extends == "kai-code"
    assert "You are a test agent" in definition.system_prompt


def test_parse_agent_minimal_frontmatter(tmp_path):
    """Test parsing agent with minimal frontmatter (defaults)."""
    agent_file = tmp_path / "minimal-agent.md"
    agent_file.write_text("""---
name: minimal-agent
---

Minimal prompt.
""")
    
    definition = AgentDefinition(agent_file)
    
    assert definition.name == "minimal-agent"
    assert definition.description == ""
    assert definition.tools == []
    assert definition.model is None
    assert definition.extends is None
    assert definition.system_prompt == "Minimal prompt."


def test_parse_agent_without_frontmatter(tmp_path):
    """Test parsing agent without frontmatter (uses filename)."""
    agent_file = tmp_path / "no-frontmatter.md"
    agent_file.write_text("Just the prompt body.")
    
    definition = AgentDefinition(agent_file)
    
    assert definition.name == "no-frontmatter"
    assert definition.metadata == {}
    assert definition.system_prompt == "Just the prompt body."


def test_parse_agent_allowed_tools_field(tmp_path):
    """Test parsing agent with allowed-tools instead of tools."""
    agent_file = tmp_path / "allowed-tools-agent.md"
    agent_file.write_text("""---
name: allowed-tools-agent
allowed-tools: Bash, Read
---

Test.
""")
    
    definition = AgentDefinition(agent_file)
    
    assert definition.allowed_tools == ["Bash", "Read"]
    assert definition.tools == []


def test_invalid_agent_name_format():
    """Test validation rejects invalid agent names."""
    # Agent names must be kebab-case
    with pytest.raises(ValueError, match="kebab-case"):
        AgentDefinition.__init__(None, "InvalidName")
```

**Step 2: Run tests to verify they fail**

```bash
# Create test directory first
mkdir -p tests/agent_loader
touch tests/agent_loader/__init__.py

# Run tests
pytest tests/agent_loader/test_agent_definition.py -v
```

Expected: FAIL with `ModuleNotFoundError: kai_code.agent_definition`

**Step 3: Create AgentDefinition class**

Create `src/kai_code/agent_definition.py`:

```python
"""Agent definition parser for markdown-based agents.

This module provides functionality to parse agent definitions from markdown
files with YAML frontmatter, following Claude's agent definition pattern.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentDefinition:
    """Parsed agent definition from markdown file.
    
    Attributes:
        path: Path to the markdown file
        name: Agent identifier (kebab-case, derived from filename or frontmatter)
        description: Action-oriented description for delegation
        tools: Tool patterns (may include wildcards)
        allowed_tools: Alternative whitelist of tools
        model: Model override or 'inherit'
        extends: Parent agent name for inheritance
        system_prompt: Full system prompt body
        metadata: Raw YAML frontmatter dict
    """
    
    path: Path
    name: str = ""
    description: str = ""
    tools: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    model: str | None = None
    extends: str | None = None
    system_prompt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Parse the markdown file after initialization."""
        if not self.name and self.path:
            self._parse()
    
    def _parse(self) -> None:
        """Parse markdown file with YAML frontmatter."""
        content = self.path.read_text(encoding="utf-8")
        
        # Check for YAML frontmatter
        if content.startswith('---'):
            # Split on ---
            parts = content.split('---', 2)
            if len(parts) >= 3:
                _, fm, body = parts
                self.metadata = yaml.safe_load(fm) or {}
                self.system_prompt = body.strip()
            else:
                # Malformed frontmatter, treat as no frontmatter
                self.metadata = {}
                self.system_prompt = content.strip()
        else:
            self.metadata = {}
            self.system_prompt = content.strip()
        
        # Extract fields from metadata
        self.name = self.metadata.get('name', self.path.stem)
        self.description = self.metadata.get('description', '')
        
        # Handle tools vs allowed-tools
        raw_tools = self.metadata.get('tools', [])
        if isinstance(raw_tools, str):
            # Comma-separated string
            self.tools = [t.strip() for t in raw_tools.split(',')]
        elif isinstance(raw_tools, list):
            self.tools = raw_tools
        else:
            self.tools = []
        
        raw_allowed = self.metadata.get('allowed-tools', [])
        if isinstance(raw_allowed, str):
            self.allowed_tools = [t.strip() for t in raw_allowed.split(',')]
        elif isinstance(raw_allowed, list):
            self.allowed_tools = raw_allowed
        else:
            self.allowed_tools = []
        
        self.model = self.metadata.get('model')
        self.extends = self.metadata.get('extends')
        
        # Validate agent name is kebab-case
        self._validate_name()
    
    def _validate_name(self) -> None:
        """Validate agent name is kebab-case."""
        if not self.name:
            return
        
        # kebab-case: lowercase, hyphens, starts/ends with alphanumeric
        pattern = r'^[a-z][a-z0-9-]*[a-z0-9]$'
        if not re.match(pattern, self.name) and self.name != 'kai-code':
            raise ValueError(
                f"Agent name '{self.name}' must be kebab-case "
                "(lowercase, hyphens, no spaces)"
            )
    
    def validate(self) -> list[str]:
        """Validate definition, returns list of errors (empty if valid).
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check description is present and action-oriented
        if not self.description:
            errors.append("Description is required")
        
        # Check tools or allowed-tools is specified
        if not self.tools and not self.allowed_tools:
            # Not an error - can inherit from parent
            pass
        
        # Check system prompt is present
        if not self.system_prompt:
            errors.append("System prompt body is required")
        
        return errors
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/agent_loader/test_agent_definition.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/kai_code/agent_definition.py tests/agent_loader/test_agent_definition.py
git commit -m "feat(agent-loader): add AgentDefinition class for parsing markdown agents

- Parse markdown files with YAML frontmatter
- Support name, description, tools, model, extends fields
- Validate kebab-case naming convention
- Add comprehensive unit tests

Follows Claude's agent definition pattern."
```

---

## Task 2: Add AgentDefinition to Package Exports

**Files:**
- Modify: `src/kai_code/__init__.py`

**Step 1: Check current exports**

```bash
grep -n "agent" src/kai_code/__init__.py | head -20
```

**Step 2: Add AgentDefinition to exports**

Add to `src/kai_code/__init__.py`:

```python
# Find the __all__ list or create one, and add:
from kai_code.agent_definition import AgentDefinition

__all__ = [
    # ... existing exports ...
    "AgentDefinition",
]
```

**Step 3: Test import**

```bash
python -c "from kai_code import AgentDefinition; print(AgentDefinition)"
```

Expected: No import error

**Step 4: Commit**

```bash
git add src/kai_code/__init__.py
git commit -m "feat(agent-loader): export AgentDefinition from package"
```

---

## Task 3: Create Tool Pattern Loader

**Files:**
- Create: `src/kai_code/tool_loader.py`
- Test: `tests/agent_loader/test_tool_loader.py`

**Step 1: Write failing tests for tool loading**

Create `tests/agent_loader/test_tool_loader.py`:

```python
"""Tests for tool pattern loading."""
import pytest
from kai_code.tool_loader import load_tools_from_patterns


def test_load_builtin_tools_by_name():
    """Test loading tools by exact name."""
    tools = load_tools_from_patterns(["Bash", "Read", "Write"])
    tool_names = [t.name for t in tools]
    
    assert "execute" in tool_names or "Bash" in tool_names
    assert "read_file" in tool_names or "Read" in tool_names


def test_load_tools_with_wildcards():
    """Test loading tools using wildcard patterns."""
    tools = load_tools_from_patterns(["kai_code.agents.seeknal.tools.*"])
    
    # Should load all seeknal tools
    assert len(tools) > 0


def test_load_tools_from_multiple_patterns():
    """Test loading tools from multiple patterns."""
    tools = load_tools_from_patterns([
        "kai_code.agents.seeknal.tools.project_tools",
        "kai_code.agents.seeknal.tools.flow_tools",
    ])
    
    assert len(tools) > 0


def test_empty_pattern_list_returns_empty():
    """Test that empty pattern list returns empty tool list."""
    tools = load_tools_from_patterns([])
    assert tools == []


def test_invalid_tool_pattern_logs_warning(caplog):
    """Test that invalid patterns log warnings but don't crash."""
    with caplog.at_level("WARNING"):
        tools = load_tools_from_patterns(["nonexistent.module.*"])
    
    # Should return empty list, not crash
    assert tools == []
    assert "warning" in caplog.text.lower() or "not found" in caplog.text.lower()
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/agent_loader/test_tool_loader.py -v
```

Expected: FAIL with `ModuleNotFoundError: kai_code.tool_loader`

**Step 3: Implement tool loader**

Create `src/kai_code/tool_loader.py`:

```python
"""Tool loading utilities for agent definitions.

This module provides functionality to load tools from pattern strings,
supporting both exact tool names and import patterns.
"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from kai_code.agent import KaiAgent

logger = logging.getLogger(__name__)


def load_tools_from_patterns(patterns: list[str]) -> list[BaseTool]:
    """Load tools from pattern strings.
    
    Args:
        patterns: List of tool patterns. Can be:
            - Exact tool names (e.g., "Bash", "Read")
            - Import paths (e.g., "kai_code.agents.seeknal.tools.project_tools")
            - Wildcard patterns (e.g., "kai_code.agents.seeknal.tools.*")
    
    Returns:
        List of LangChain tool objects
    """
    if not patterns:
        return []
    
    tools = []
    
    for pattern in patterns:
        try:
            # Try import pattern first
            if '.' in pattern and '*' not in pattern:
                # Exact import path
                module_tools = _load_from_module(pattern)
                tools.extend(module_tools)
            elif '*' in pattern:
                # Wildcard pattern
                module_tools = _load_from_wildcard(pattern)
                tools.extend(module_tools)
            else:
                # Simple tool name - skip for now
                # These are typically handled by the agent itself
                logger.debug(f"Skipping tool name pattern: {pattern}")
        except Exception as e:
            logger.warning(f"Failed to load tools from pattern '{pattern}': {e}")
    
    return tools


def _load_from_module(module_path: str) -> list[BaseTool]:
    """Load tools from a specific module.
    
    Args:
        module_path: Full module path (e.g., "kai_code.agents.seeknal.tools.project_tools")
    
    Returns:
        List of tool objects from the module
    """
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        logger.warning(f"Module not found: {module_path}")
        return []
    
    tools = []
    
    # Look for create_*_tools functions
    for attr_name in dir(module):
        if attr_name.startswith('create_') and attr_name.endswith('_tools'):
            func = getattr(module, attr_name)
            if callable(func):
                try:
                    # Call the function - may need arguments
                    # For Seeknal tools, needs seeknal_path
                    import inspect
                    sig = inspect.signature(func)
                    if len(sig.parameters) > 0:
                        # Skip functions that require arguments
                        # These need to be called by the agent itself
                        continue
                    module_tools = func()
                    if isinstance(module_tools, list):
                        tools.extend(module_tools)
                except Exception as e:
                    logger.debug(f"Could not call {attr_name}: {e}")
    
    return tools


def _load_from_wildcard(pattern: str) -> list[BaseTool]:
    """Load tools from a wildcard pattern.
    
    Args:
        pattern: Pattern with wildcard (e.g., "kai_code.agents.seeknal.tools.*")
    
    Returns:
        List of tool objects from matching modules
    """
    # Extract base path
    base_path = pattern.replace('.*', '')
    
    # Find all modules under that path
    src_path = Path(__file__).parent
    
    # Convert import path to file path
    rel_path = base_path.replace('kai_code.', '').replace('.', '/')
    search_path = src_path / rel_path
    
    if not search_path.exists():
        logger.warning(f"Path not found for pattern: {pattern}")
        return []
    
    tools = []
    
    # Find all Python files
    for py_file in search_path.glob('*.py'):
        if py_file.name.startswith('_'):
            continue
        
        # Convert back to module path
        module_name = f"{base_path}.{py_file.stem}"
        module_tools = _load_from_module(module_name)
        tools.extend(module_tools)
    
    return tools
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/agent_loader/test_tool_loader.py -v
```

Expected: Tests pass (may need to adjust based on actual Seeknal tools structure)

**Step 5: Commit**

```bash
git add src/kai_code/tool_loader.py tests/agent_loader/test_tool_loader.py
git commit -m "feat(agent-loader): add tool pattern loading

- Load tools from import paths
- Support wildcard patterns
- Handle errors gracefully with warnings
- Add unit tests"
```

---

## Task 4: Implement Agent Compilation

**Files:**
- Modify: `src/kai_code/agent_definition.py`
- Test: `tests/agent_loader/test_compilation.py`

**Step 1: Write failing tests for agent compilation**

Create `tests/agent_loader/test_compilation.py`:

```python
"""Tests for agent compilation."""
import pytest
from pathlib import Path
from kai_code.agent_definition import AgentDefinition
from kai_code.agent import KaiAgent


def test_compile_to_agent_class(tmp_path):
    """Test compiling agent definition to Python class."""
    agent_file = tmp_path / "test-agent.md"
    agent_file.write_text("""---
name: test-agent
description: Test agent
tools: Bash, Read
---

You are a test agent.
""")
    
    definition = AgentDefinition(agent_file)
    agent_class = definition.to_agent_class()
    
    # Check class properties
    assert agent_class.__name__ == "TestAgent"
    assert definition.description in agent_class.__doc__
    
    # Check it's a KaiAgent subclass
    assert issubclass(agent_class, KaiAgent)


def test_compiled_agent_has_correct_prompt_method(tmp_path):
    """Test compiled agent has correct _get_base_prompt_name method."""
    agent_file = tmp_path / "prompt-test.md"
    agent_file.write_text("""---
name: prompt-test
description: Test
---

Test prompt.
""")
    
    definition = AgentDefinition(agent_file)
    agent_class = definition.to_agent_class()
    
    # Create instance
    agent = agent_class(root_dir=tmp_path)
    
    # Should return the agent name
    assert agent._get_base_prompt_name() == "prompt-test"


def test_compiled_agent_has_kai_definition_attribute(tmp_path):
    """Test compiled agent has _kai_definition attribute."""
    agent_file = tmp_path / "attr-test.md"
    agent_file.write_text("""---
name: attr-test
description: Test
---

Test.
""")
    
    definition = AgentDefinition(agent_file)
    agent_class = definition.to_agent_class()
    
    # Check attribute exists
    assert hasattr(agent_class, '_kai_definition')
    assert agent_class._kai_definition is definition
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/agent_loader/test_compilation.py -v
```

Expected: FAIL with `AttributeError: 'AgentDefinition' object has no attribute 'to_agent_class'`

**Step 3: Implement to_agent_class method**

Add to `src/kai_code/agent_definition.py` (in AgentDefinition class):

```python
def to_agent_class(self, base_class: type = KaiAgent) -> type:
    """Compile to a Python agent class.
    
    Creates a dynamic KaiAgent subclass from the agent definition.
    The class will use the agent's name as its prompt identifier.
    
    Args:
        base_class: Base class to inherit from (default: KaiAgent)
    
    Returns:
        A Python class that subclasses base_class
    
    Example:
        >>> definition = AgentDefinition(path)
        >>> AgentClass = definition.to_agent_class()
        >>> agent = AgentClass(root_dir=Path.cwd())
    """
    from kai_code.tool_loader import load_tools_from_patterns
    
    # Create class name from agent name
    class_name = ''.join(
        word.title() for word in self.name.replace('-', ' ').split()
    ) + "Agent"
    
    # Define the class namespace
    class_dict = {
        '__doc__': self.description,
        '_kai_definition': self,
    }
    
    # Define _get_base_prompt_name method
    def _get_base_prompt_name(self) -> str:
        return self.name
    
    class_dict['_get_base_prompt_name'] = _get_base_prompt_name
    
    # Define _get_subclass_tools method
    def _get_subclass_tools(self) -> list:
        return load_tools_from_patterns(self.tools)
    
    class_dict['_get_subclass_tools'] = _get_subclass_tools
    
    # Create the class
    agent_class = type(class_name, (base_class,), class_dict)
    
    return agent_class
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/agent_loader/test_compilation.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/kai_code/agent_definition.py tests/agent_loader/test_compilation.py
git commit -m "feat(agent-loader): add agent compilation to Python class

- Implement to_agent_class() method
- Generate dynamic KaiAgent subclasses
- Set class name, docstring, and methods
- Store reference to original definition"
```

---

## Task 5: Create load_agent() Function

**Files:**
- Create: `src/kai_code/agent_loader.py`
- Test: `tests/agent_loader/test_loading.py`

**Step 1: Write failing tests for load_agent**

Create `tests/agent_loader/test_loading.py`:

```python
"""Tests for agent loading."""
import pytest
from pathlib import Path
from kai_code.agent_loader import load_agent, list_agents
from kai_code.agent import KaiAgent


def test_load_agent_by_name(tmp_path):
    """Test loading agent by name from .kai/agents/ directory."""
    # Create agent file
    agents_dir = tmp_path / ".kai" / "agents"
    agents_dir.mkdir(parents=True)
    
    agent_file = agents_dir / "test-agent.md"
    agent_file.write_text("""---
name: test-agent
description: Test agent
---

You are a test agent.
""")
    
    # Load the agent
    agent = load_agent("test-agent", agents_dir=agents_dir, root_dir=tmp_path)
    
    # Check it's a KaiAgent instance
    assert isinstance(agent, KaiAgent)
    assert agent._get_base_prompt_name() == "test-agent"


def test_load_agent_nonexistent_raises_error(tmp_path):
    """Test loading nonexistent agent raises FileNotFoundError."""
    agents_dir = tmp_path / ".kai" / "agents"
    agents_dir.mkdir(parents=True)
    
    with pytest.raises(FileNotFoundError, match="not found"):
        load_agent("nonexistent", agents_dir=agents_dir)


def test_list_agents(tmp_path):
    """Test listing all available agents."""
    agents_dir = tmp_path / ".kai" / "agents"
    agents_dir.mkdir(parents=True)
    
    # Create multiple agent files
    (agents_dir / "agent-one.md").write_text("---\nname: agent-one\n---\n")
    (agents_dir / "agent-two.md").write_text("---\nname: agent-two\n---\n")
    (agents_dir / "not-an-agent.txt").write_text("text file")
    
    agents = list_agents(agents_dir)
    
    assert "agent-one" in agents
    assert "agent-two" in agents
    assert "not-an-agent" not in agents


def test_load_agent_uses_default_directory(tmp_path, monkeypatch):
    """Test load_agent uses .kai/agents by default."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)
    
    # Create default agents directory
    agents_dir = tmp_path / ".kai" / "agents"
    agents_dir.mkdir(parents=True)
    
    agent_file = agents_dir / "default-test.md"
    agent_file.write_text("---\nname: default-test\n---\n")
    
    # Load without specifying directory
    agent = load_agent("default-test", root_dir=tmp_path)
    
    assert isinstance(agent, KaiAgent)
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/agent_loader/test_loading.py -v
```

Expected: FAIL with `ModuleNotFoundError: kai_code.agent_loader`

**Step 3: Implement agent loader**

Create `src/kai_code/agent_loader.py`:

```python
"""Agent loading utilities.

This module provides functions to load and instantiate agents from
markdown definition files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from kai_code.agent import KaiAgent
from kai_code.agent_definition import AgentDefinition


def load_agent(
    name: str,
    agents_dir: Path | str | None = None,
    root_dir: Path | str | None = None,
    **kwargs: Any,
) -> KaiAgent:
    """Load an agent from markdown definition.
    
    Args:
        name: Agent name (kebab-case, matches .md filename without extension)
        agents_dir: Directory containing agent definitions (default: .kai/agents/)
        root_dir: Project root directory (default: current working directory)
        **kwargs: Additional arguments passed to agent constructor
    
    Returns:
        Initialized KaiAgent instance
    
    Raises:
        FileNotFoundError: If agent definition file doesn't exist
    
    Example:
        >>> agent = load_agent('seeknal-data-engineer')
        >>> result = agent.run("Create a feature group")
    """
    # Determine agents directory
    if agents_dir is None:
        # Use default .kai/agents from root_dir or cwd
        if root_dir is None:
            root_dir = Path.cwd()
        else:
            root_dir = Path(root_dir)
        agents_dir = root_dir / ".kai" / "agents"
    else:
        agents_dir = Path(agents_dir)
        if root_dir is None:
            root_dir = Path.cwd()
        else:
            root_dir = Path(root_dir)
    
    # Find agent file
    agent_path = agents_dir / f"{name}.md"
    if not agent_path.exists():
        raise FileNotFoundError(
            f"Agent '{name}' not found at {agent_path}. "
            f"Available agents: {list_agents(agents_dir)}"
        )
    
    # Parse definition
    definition = AgentDefinition(agent_path)
    
    # Handle inheritance
    if definition.extends:
        parent_agent = load_agent(
            definition.extends,
            agents_dir=agents_dir,
            root_dir=root_dir,
        )
        # Could merge tools, prompts, etc. here
        # For now, just use the child's definition
    
    # Compile to class and instantiate
    agent_class = definition.to_agent_class()
    agent = agent_class(root_dir=root_dir, **kwargs)
    
    return agent


def list_agents(agents_dir: Path | str | None = None) -> list[str]:
    """List all available agent definitions.
    
    Args:
        agents_dir: Directory containing agent definitions (default: .kai/agents/)
    
    Returns:
        List of agent names (kebab-case, without .md extension)
    
    Example:
        >>> list_agents()
        ['seeknal', 'seeknal-data-engineer', 'dbt-analyst']
    """
    if agents_dir is None:
        agents_dir = Path.cwd() / ".kai" / "agents"
    else:
        agents_dir = Path(agents_dir)
    
    if not agents_dir.exists():
        return []
    
    agents = []
    for agent_file in agents_dir.glob("*.md"):
        # Skip files starting with underscore
        if agent_file.name.startswith('_'):
            continue
        agents.append(agent_file.stem)
    
    return sorted(agents)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/agent_loader/test_loading.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/kai_code/agent_loader.py tests/agent_loader/test_loading.py
git commit -m "feat(agent-loader): add load_agent() and list_agents() functions

- Load agents from .kai/agents/ directory by name
- List all available agent definitions
- Support custom agents_dir parameter
- Handle inheritance (basic support)
- Raise helpful error for missing agents"
```

---

## Task 6: Integration Test with Existing Agents

**Files:**
- Test: `tests/agent_loader/test_integration.py`

**Step 1: Create markdown definition for SeeknalAgent**

Create `.kai/agents/seeknal.md` (in actual repo, not test):

```markdown
---
name: seeknal
description: Data engineering and feature store specialist using the Seeknal library. Use proactively for data pipeline tasks.
extends: kai-code
tools: kai_code.agents.seeknal.tools.*
model: inherit
color: Blue
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

**Step 2: Write integration tests**

Create `tests/agent_loader/test_integration.py`:

```python
"""Integration tests for agent loading with existing kai-code agents."""
import pytest
from pathlib import Path
from kai_code.agent_loader import load_agent
from kai_code.agents.seeknal import SeeknalAgent


def test_loaded_seeknal_agent_is_instance():
    """Test that loaded seeknal agent is KaiAgent instance."""
    # This test requires the .kai/agents/seeknal.md file to exist
    try:
        agent = load_agent("seeknal")
        assert hasattr(agent, 'run')
        assert hasattr(agent, '_get_base_prompt_name')
    except FileNotFoundError:
        pytest.skip("seeknal.md not created yet")


def test_loaded_agent_equivalent_to_python_class():
    """Test that loaded agent has same capabilities as Python SeeknalAgent."""
    try:
        # Load from markdown
        markdown_agent = load_agent("seeknal")
        
        # Create Python instance
        python_agent = SeeknalAgent(root_dir=Path.cwd())
        
        # Both should have same base methods
        assert type(markdown_agent.run) == type(python_agent.run)
        assert type(markdown_agent.save) == type(python_agent.save)
    except FileNotFoundError:
        pytest.skip("seeknal.md not created yet")


def test_python_agent_still_works():
    """Test that existing Python agent creation still works (backward compat)."""
    agent = SeeknalAgent(root_dir=Path.cwd())
    
    assert agent is not None
    assert hasattr(agent, 'run')
    assert hasattr(agent, '_get_base_prompt_name')
```

**Step 3: Run integration tests**

```bash
pytest tests/agent_loader/test_integration.py -v
```

Expected: Tests pass (seeknal test may be skipped)

**Step 4: Commit**

```bash
git add .kai/agents/seeknal.md tests/agent_loader/test_integration.py
git commit -m "feat(agent-loader): add Seeknal markdown definition and integration tests

- Create .kai/agents/seeknal.md with full agent definition
- Add integration tests for markdown vs Python equivalence
- Verify backward compatibility with Python SeeknalAgent
- Tests may be skipped until file is created"
```

---

## Task 7: Documentation

**Files:**
- Create: `docs/agent-development-guide.md`

**Step 1: Create agent development guide**

Create `docs/agent-development-guide.md`:

```markdown
# Agent Development Guide

This guide explains how to create custom agents using kai-code's agent layer.

## Overview

kai-code supports two approaches for creating agents:

1. **Python API**: Subclass `KaiAgent` for full programmatic control
2. **Markdown Definitions**: Define agents declaratively in `.kai/agents/*.md`

Both approaches produce equivalent `KaiAgent` instances with shared capabilities.

## Quick Start

### Creating a Simple Agent (Markdown)

1. Create `.kai/agents/my-agent.md`:

```markdown
---
name: my-agent
description: My custom agent for specific tasks
tools: Bash, Read, Write
---

# Purpose

You are a specialist agent for...

## Instructions

When invoked, follow these steps:
1. Understand the request
2. Perform the task
3. Report results
```

2. Use the agent:

```python
from kai_code.agent_loader import load_agent

agent = load_agent("my-agent")
result = agent.run("Your task here")
```

### Creating an Agent (Python)

```python
from kai_code.agent import KaiAgent
from pathlib import Path

class MyAgent(KaiAgent):
    def _get_base_prompt_name(self) -> str:
        return "my-agent"
    
    def _get_subclass_tools(self) -> list:
        # Return custom tools
        return super()._get_subclass_tools()

# Use the agent
agent = MyAgent(root_dir=Path.cwd())
result = agent.run("Your task here")
```

## Agent Definition Reference

### YAML Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | kebab-case agent identifier |
| `description` | string | Yes | Action-oriented description for delegation |
| `tools` | list | No | Comma-separated tool names or patterns |
| `allowed-tools` | list | No | Alternative whitelist of tools |
| `model` | string | No | Model override: `sonnet`, `opus`, `haiku`, or `inherit` |
| `extends` | string | No | Parent agent name for inheritance |
| `color` | string | No | Visual indicator for UI |

### System Prompt Sections

Your agent's system prompt should include:

- **# Purpose**: What the agent does
- **## Core Expertise**: Key capabilities
- **## Instructions**: Step-by-step methodology
- **## Critical Behaviors**: Important constraints and patterns
- **## Output Format**: Expected result structure

## Examples

See `.kai/agents/` directory for example agents:
- `seeknal.md` - Data engineering specialist
- `dbt.md` - dbt transformation specialist

## API Reference

### Loading Agents

```python
from kai_code.agent_loader import load_agent, list_agents

# List available agents
agents = list_agents()

# Load by name
agent = load_agent("agent-name")

# Load from custom directory
agent = load_agent("agent-name", agents_dir="/path/to/agents")

# Pass additional arguments
agent = load_agent("agent-name", model="gpt-4o", yolo=True)
```

### AgentDefinition Class

```python
from kai_code.agent_definition import AgentDefinition
from pathlib import Path

# Parse agent file
definition = AgentDefinition(Path(".kai/agents/my-agent.md"))

# Access properties
print(definition.name)
print(definition.description)
print(definition.tools)

# Compile to Python class
AgentClass = definition.to_agent_class()
agent = AgentClass(root_dir=Path.cwd())

# Validate
errors = definition.validate()
if errors:
    print(f"Validation errors: {errors}")
```

## Best Practices

1. **Use kebab-case names**: `my-agent`, not `MyAgent` or `my_agent`
2. **Write action-oriented descriptions**: "Use proactively for X" or "Specialist for Y"
3. **Be specific in instructions**: Clear steps beat vague guidance
4. **Define output format**: Tell users what to expect
5. **Test incrementally**: Start simple, add complexity gradually

## Migration from Python to Markdown

Existing Python agents can be gradually migrated to markdown:

```python
# Before (Python only)
from kai_code.agents.my_agent import MyAgent
agent = MyAgent(root_dir=Path.cwd())

# After (both work)
from kai_code.agent_loader import load_agent
agent = load_agent("my-agent")  # Uses .kai/agents/my-agent.md
```

The Python class continues working - migration is optional.
```

**Step 2: Commit**

```bash
git add docs/agent-development-guide.md
git commit -m "docs(agent-loader): add agent development guide

- Document both Python and markdown approaches
- Provide quick start examples
- Include API reference
- Add best practices and migration guide"
```

---

## Task 8: Run Full Test Suite

**Step 1: Run all new tests**

```bash
pytest tests/agent_loader/ -v
```

Expected: All tests PASS

**Step 2: Run existing tests to verify no breakage**

```bash
pytest tests/ -v --ignore=tests/agent_loader/
```

Expected: All existing tests still PASS (backward compatibility)

**Step 3: Check test coverage**

```bash
pytest tests/agent_loader/ --cov=src/kai_code/agent_definition --cov=src/kai_code/agent_loader --cov=src/kai_code/tool_loader --cov-report=term-missing
```

Expected: Coverage >80% for new modules

**Step 4: Fix any issues**

Address any failing tests or coverage gaps.

**Step 5: Final commit if needed**

```bash
git add .
git commit -m "test(agent-loader): ensure full test coverage and backward compatibility"
```

---

## Summary

This implementation plan creates the foundation for loading kai-code agents from markdown files:

**What was built:**
1. `AgentDefinition` class for parsing markdown with YAML frontmatter
2. Tool pattern loading with wildcard support
3. Agent compilation to Python classes
4. `load_agent()` and `list_agents()` convenience functions
5. Integration with existing SeeknalAgent
6. Comprehensive documentation

**Files created/modified:**
- `src/kai_code/agent_definition.py` (new)
- `src/kai_code/agent_loader.py` (new)
- `src/kai_code/tool_loader.py` (new)
- `tests/agent_loader/` (new directory with tests)
- `.kai/agents/seeknal.md` (new example)
- `docs/agent-development-guide.md` (new documentation)

**Next phases:**
- Phase 2: Prompt system enhancement
- Phase 3: Subagent support
- Phase 4: CLI scaffolding
- Phase 5: Additional documentation
- Phase 6: Migration of all existing agents

**Success criteria for Phase 1:**
- ✅ Can load agents from markdown definitions
- ✅ Compiled agents are functionally equivalent to Python subclasses
- ✅ All existing tests pass (100% backward compatibility)
- ✅ Test coverage >80%
- ✅ Documentation enables agent creation
