# Migration Guide: Python to Markdown Agent Definitions

This guide helps you migrate existing Python agent subclasses to markdown-based agent definitions while maintaining full backward compatibility.

## Overview

Kai-code now supports **dual paths** for creating agents:

| Path | Best For | Complexity |
|------|----------|------------|
| **Python Subclass** | Advanced users, complex logic, dynamic tools | High |
| **Markdown Definition** | Most users, static configuration, quick iteration | Low |

Both paths produce **equivalent agents** with the same capabilities. Migration is **optional** - Python subclasses continue to work fully.

## When to Migrate

**Good candidates for markdown migration:**
- Agents with static tool sets (no complex initialization logic)
- Agents that override only `_get_base_prompt_name()` and `_get_subclass_tools()`
- Projects that benefit from easy configuration editing
- Teams wanting faster iteration cycles

**Keep as Python:**
- Agents with complex initialization logic
- Agents that compute tool sets dynamically
- Agents with custom `__init__` parameters beyond standard KaiAgent args
- Agents requiring runtime state or configuration

## Migration Steps

### Step 1: Analyze Your Python Agent

Examine your existing agent class:

```python
# src/my_package/agents/my_agent.py
from kai_code.agent import KaiAgent
from pathlib import Path

class MyAgent(KaiAgent):
    """My custom agent."""

    def __init__(self, root_dir, **kwargs):
        super().__init__(root_dir=root_dir, **kwargs)
        self.custom_config = kwargs.get('custom_config', 'default')

    def _get_base_prompt_name(self) -> str:
        return "kai-my-agent"

    def _get_subclass_tools(self) -> list:
        from my_package.tools import create_my_tools
        return create_my_tools(self.custom_config)
```

**Key attributes to note:**
1. Base prompt name (from `_get_base_prompt_name()`)
2. Tool factory functions and their arguments
3. Custom initialization parameters
4. Additional methods beyond the two overrides

### Step 2: Create Markdown Definition

Create `.kai/agents/my-agent.md`:

```markdown
---
name: my-agent
description: My custom agent. Use proactively for specific tasks.
extends: kai-my-agent
tools: my_package.tools.my_tools
model: inherit
color: Blue
---

# Purpose

You are a **My Custom Agent**...

## Core Expertise

You excel at...
```

**Mapping Python to YAML:**

| Python Attribute | YAML Field | Value |
|------------------|------------|-------|
| `_get_base_prompt_name()` | `extends` | `"kai-my-agent"` |
| Tools from `_get_subclass_tools()` | `tools` | `"my_package.tools.my_tools"` |
| Class docstring | `description` | Action-oriented description |

### Step 3: Handle Tool Factories with Parameters

If your tool factory requires parameters (like paths or config), you have two options:

#### Option A: Environment Variables

**Python (original):**
```python
def _get_subclass_tools(self) -> list:
    config = self.custom_config  # From __init__
    return create_my_tools(config)
```

**Markdown (migrated):**
```markdown
---
tools: my_package.tools.my_tools
---
```

Then modify the tool factory to read from environment:

```python
# my_package/tools.py
import os

def create_my_tools() -> list:
    """Create my tools."""
    config = os.getenv('MY_AGENT_CONFIG', 'default')
    return _create_with_config(config)
```

#### Option B: Create Parameterized Tool Module

Create a wrapper that pre-configures tools:

```python
# my_package/tools/my_agent_tools.py
from my_package.tools import create_my_tools
from pathlib import Path

def create_my_agent_tools() -> list:
    """Create tools for my-agent with hardcoded config."""
    config_path = Path.home() / '.my-agent-config'
    return create_my_tools(config_path)
```

Then reference this in markdown:

```markdown
---
tools: my_package.tools.my_agent_tools
---
```

### Step 4: Create or Verify Base Prompt

Ensure your base prompt file exists at `src/kai_code/prompts/kai-my-agent.md`:

```markdown
# INHERIT: kai-code

# My Agent Base Prompt

You are a specialized agent for...

## Core Expertise

You excel at...

## Instructions

When working on tasks...
```

**If the prompt doesn't exist:** Create it with content from your Python agent's documentation and behavior patterns.

### Step 5: Test Equivalence

Verify both paths produce equivalent behavior:

```python
# test_migration.py
from kai_code.agent_loader import load_agent
from my_package.agents.my_agent import MyAgent
from pathlib import Path

# Python path
python_agent = MyAgent(root_dir=Path.cwd())

# Markdown path
markdown_agent = load_agent('my-agent')

# Compare base prompts
assert python_agent._get_base_prompt_name() == "kai-my-agent"
# markdown_agent uses agent name which loads same prompt

# Compare tool counts
python_tools = len(python_agent._get_subclass_tools())
markdown_tools = len(markdown_agent._get_subclass_tools())
assert python_tools == markdown_tools

# Test basic functionality
test_prompt = "List your available tools"
python_response = python_agent.run(test_prompt)
markdown_response = markdown_agent.run(test_prompt)
# Both should produce similar results
```

### Step 6: Update Usage (Optional)

**Old usage (still works):**
```python
from my_package.agents.my_agent import MyAgent

agent = MyAgent(root_dir=Path.cwd())
result = agent.run("Do something")
```

**New usage (optional):**
```python
from kai_code.agent_loader import load_agent

agent = load_agent('my-agent')
result = agent.run("Do something")
```

**Both continue to work** - migration doesn't break existing code.

## Complete Migration Example

### Before: Python Agent

```python
# src/my_company/agents/data_agent.py
from kai_code.agent import KaiAgent
from pathlib import Path

class DataAgent(KaiAgent):
    """Data engineering specialist for my company."""

    def __init__(self, root_dir, data_dir=None, **kwargs):
        super().__init__(root_dir=root_dir, **kwargs)
        self.data_dir = Path(data_dir or root_dir / 'data')

    def _get_base_prompt_name(self) -> str:
        return "kai-data-agent"

    def _get_subclass_tools(self) -> list:
        from my_company.tools import (
            create_database_tools,
            create_file_tools,
            create_validation_tools
        )

        tools = []
        tools.extend(create_database_tools())
        tools.extend(create_file_tools(self.data_dir))
        tools.extend(create_validation_tools())
        return tools
```

### After: Markdown Definition

**Step 1: Create base prompt**

```markdown
# src/kai_code/prompts/kai-data-agent.md
# INHERIT: kai-code

# Data Engineering Agent

You are a Data Engineering Specialist...

## Core Expertise

You excel at:
- Building data pipelines
- Database operations
- Data validation
...
```

**Step 2: Create agent definition**

```markdown
# .kai/agents/data-agent.md
---
name: data-agent
description: Data engineering specialist. Use proactively for pipeline, database, and validation tasks.
extends: kai-data-agent
tools:
  - kai_code.tools.bash
  - kai_code.tools.read
  - kai_code.tools.write
  - my_company.tools.database_tools
  - my_company.tools.file_tools
  - my_company.tools.validation_tools
model: inherit
color: Green
---

# Purpose

You are a **Data Engineering Specialist**...

## Additional Configuration

Data directory: {{DATA_DIR | default('./data')}}
```

**Step 3: Handle parameterized tools**

If `create_file_tools` needs `data_dir` parameter:

```python
# my_company/tools/file_tools.py
import os
from pathlib import Path

def create_file_tools(data_dir: str | Path = None) -> list:
    """Create file tools.

    Args:
        data_dir: Data directory path. If None, uses DATA_DIR env var.

    Returns:
        List of file tools.
    """
    if data_dir is None:
        data_dir = os.getenv('DATA_DIR', './data')
    data_dir = Path(data_dir)

    # Create tools with data_dir
    ...
```

Now both paths work without custom `__init__`.

## Complex Cases

### Case 1: Dynamic Tool Selection

**Python (original):**
```python
class SmartAgent(KaiAgent):
    def _get_subclass_tools(self) -> list:
        tools = get_base_tools()

        # Conditional tool loading
        if self._has_database():
            tools.extend(create_db_tools())

        if self._has_api_access():
            tools.extend(create_api_tools())

        return tools
```

**Options:**
1. **Keep as Python** - Dynamic logic is complex
2. **Always include tools** - Agent decides when to use them
3. **Create multiple agents** - One for DB, one for API, combine with subagents

### Case 2: Runtime State

**Python (original):**
```python
class StatefulAgent(KaiAgent):
    def __init__(self, root_dir, state_file, **kwargs):
        super().__init__(root_dir=root_dir, **kwargs)
        self.state = self._load_state(state_file)

    def _save_state(self):
        # Save internal state
        pass
```

**Options:**
1. **Keep as Python** - State management is complex
2. **Use MemoryManager** - Built-in memory system
3. **File-based state** - Tools handle persistence

### Case 3: Custom Methods

**Python (original):**
```python
class ExtendedAgent(KaiAgent):
    def custom_method(self, arg):
        """Custom functionality."""
        return process(arg)

    def _get_subclass_tools(self) -> list:
        # Uses custom_method
        return [create_tool_using_custom(self.custom_method)]
```

**Options:**
1. **Keep as Python** - Custom methods needed
2. **Extract to tools** - Move logic to standalone tool factory
3. **Mix approaches** - Python for complex, markdown for simple

## Hybrid Approach

You can maintain **both** Python and Markdown definitions:

```python
# src/my_package/agents/my_agent.py
from kai_code.agent import KaiAgent

class MyAgent(KaiAgent):
    """My custom agent - Python path."""

    def _get_base_prompt_name(self) -> str:
        return "kai-my-agent"

    def _get_subclass_tools(self) -> list:
        from my_package.tools import create_my_tools
        return create_my_tools()
```

```markdown
# .kai/agents/my-agent.md
---
name: my-agent
description: My custom agent
extends: kai-my-agent
tools: my_package.tools.my_tools
model: inherit
---
```

**Usage:**

```python
# Both work and are equivalent
from my_package.agents.my_agent import MyAgent
from kai_code.agent_loader import load_agent

python_agent = MyAgent(root_dir=Path.cwd())
markdown_agent = load_agent('my-agent')

# Same capabilities, same behavior
```

**Benefits of hybrid:**
- Gradual migration
- Test markdown before removing Python
- Keep Python for complex features, use markdown for simple variants
- Support both usage patterns in your team

## Verification Checklist

After migration, verify:

- [ ] Base prompt exists and loads correctly
- [ ] Agent definition file parses without errors
- [ ] `load_agent('my-agent')` returns a KaiAgent instance
- [ ] Tool count matches Python version
- [ ] Agent responds to test prompts appropriately
- [ ] Existing code using Python class still works
- [ ] Documentation is updated
- [ ] Tests pass for both paths

## Rollback Plan

If issues arise after migration:

1. **Immediate rollback**: Continue using Python class
2. **Investigate**: Check logs for specific issues
3. **Fix**: Update markdown definition or base prompt
4. **Retry**: Test markdown path again
5. **Keep hybrid**: Maintain both if各有优势

## Common Issues

### Issue: Tools Not Loading

**Symptom:** Agent has fewer tools than expected

**Diagnosis:**
```python
agent = load_agent('my-agent')
print(f"Tools: {len(agent._get_subclass_tools())}")
```

**Fixes:**
- Check tool factory is named `create_*_tools`
- Verify module path is correct
- Check for import errors in tool module
- Ensure factory is in `__all__`

### Issue: Prompt Not Found

**Symptom:** `FileNotFoundError: Prompt 'kai-my-agent' not found`

**Fixes:**
- Create prompt file at `src/kai_code/prompts/kai-my-agent.md`
- Or use existing prompt: `extends: kai-code`
- Check prompt name matches exactly

### Issue: Different Behavior

**Symptom:** Markdown agent behaves differently than Python

**Fixes:**
- Compare prompts (they should be identical)
- Check tool lists match
- Verify base prompt inheritance
- Test with identical prompts

## Best Practices

1. **Test Before Deleting**: Keep Python version until markdown is verified
2. **Document Changes**: Update README and docs with new usage
3. **Version Control**: Commit markdown before removing Python
4. **Team Communication**: Let team know about migration
5. **Gradual Migration**: Start with simple agents, keep complex ones as Python
6. **Keep Hybrids When Useful**: No rule says you must choose one

## Decision Tree

```
Does your agent need to migrate?
│
├─ Does it have complex __init__ logic?
│  └─ Yes → Keep as Python (or refactor first)
│  └─ No → Continue
│
├─ Are tools dynamically selected based on runtime state?
│  └─ Yes → Keep as Python (or use subagents)
│  └─ No → Continue
│
├─ Do you have custom methods beyond the two overrides?
│  └─ Yes → Keep as Python (or extract to tools)
│  └─ No → Continue
│
└─ Is tool factory simple (just passes config)?
   └─ Yes → Good candidate for markdown
   └─ No → Consider refactoring or keep as Python
```

## Examples

See existing migrations:

- **SeeknalAgent**: `.kai/agents/seeknal.md` extends `kai-seeknal`
- **DbtAgent**: `.kai/agents/dbt.md` extends `kai-dbt`

Both maintain Python classes with full feature parity.

## Summary

**Key points:**
- Migration is **optional** - Python agents continue to work
- Best for agents with **static tool sets** and **simple initialization**
- Use **environment variables** for configuration instead of `__init__` params
- **Hybrid approach** lets you support both paths
- **Test thoroughly** before removing Python version

**Remember:** The goal is **flexibility**, not forced migration. Use whichever path (or both) works best for your use case.

---

**Need help?** See:
- `docs/agent-development-guide.md` - Agent creation guide
- `docs/tool-authoring.md` - Tool creation patterns
- `.kai/agents/examples/` - Example agent templates
