# Agent Prompt System Guide

This guide explains how agent definitions integrate with kai-code's prompt system.

## Overview

kai-code has two sources for prompts:

1. **`src/kai_code/prompts/`** - Traditional prompt files with `# INHERIT:` directive
2. **`.kai/agents/`** - Agent definitions with YAML frontmatter `extends:` field

Both sources are unified through the prompt loader, allowing seamless inheritance and composition.

## Prompt Inheritance

### Traditional Prompts (`src/kai_code/prompts/`)

Use the `# INHERIT:` directive:

```markdown
# INHERIT: kai-code

## Specialized Content

Your specialized instructions here...
```

### Agent Definitions (`.kai/agents/*.md`)

Use YAML frontmatter:

```markdown
---
name: my-agent
description: My specialized agent
extends: kai-code
---

# Purpose

Your specialized instructions here...
```

Both approaches produce the same result: the base prompt (kai-code) is prepended to your specialized content.

## How It Works

### Loading Flow

```
load_prompt("my-agent")
    ↓
get_prompt_path("my-agent")
    ↓
Searches:
  1. src/kai_code/prompts/my-agent.md
  2. .kai/agents/my-agent.md
    ↓
_load_prompt_with_chain()
    ↓
Parse extends field (YAML or # INHERIT:)
    ↓
Recursively load parent prompt
    ↓
Merge: parent + child
    ↓
Return combined prompt
```

### Agent Compilation

When an agent definition is compiled to a Python class:

```python
class CompiledAgent(KaiAgent):
    def _get_base_prompt_name(self) -> str:
        return "my-agent"  # Triggers prompt system loading
```

The prompt system automatically:
1. Finds the agent definition file
2. Parses the `extends` field
3. Loads and merges the parent prompt
4. Returns the combined system prompt

## Examples

### Base Agent (kai-code)

```markdown
---
name: kai-code
description: General-purpose coding agent
tools: kai_code.tools.*
---

# Purpose

You are Kai, a general-purpose coding agent...

## Core Expertise

You excel at:
- Reading, writing, and editing code
- Running tests and debugging
- Git operations
...
```

### Specialized Agent (seeknal)

```markdown
---
name: seeknal
description: Data engineering specialist
extends: kai-code
tools: kai_code.agents.seeknal.tools.*
---

# Purpose

You are a Data Engineering Specialist...

## Core Expertise

You excel at:
- Building multi-engine data flows
- Designing feature store schemas
...
```

When loaded, `seeknal` gets:
1. kai-code's base prompt (general coding expertise)
2. Seeknal's specialized content (data engineering focus)

## Prompt Metadata

Get metadata about any prompt:

```python
from kai_code.prompts import get_prompt_metadata

metadata = get_prompt_metadata("seeknal")
# {
#     "path": "/path/to/.kai/agents/seeknal.md",
#     "inherits": "kai-code",
#     "lines": "51"
# }
```

## Best Practices

### 1. Use `extends` for Base Behavior

Don't repeat common instructions - extend a base prompt:

```markdown
---
extends: kai-code
---

# Specialized Purpose

Only include what's unique to your agent.
```

### 2. Keep Prompts Focused

Your agent's prompt should add specific expertise, not replace the base.

### 3. Use Descriptive Names

```yaml
name: data-quality-checker    # Good
description: Proactively validate data quality
```

### 4. Specify Tools Appropriately

```yaml
# For agents that extend kai-code's tools:
tools: kai_code.tools.*

# For specialized tools:
tools: kai_code.agents.mydomain.tools.*

# For specific tool selection:
allowed-tools: Bash, Read, Write
```

## Migration Guide

### From Python-Only Agents

If you have a Python agent class:

```python
class MyAgent(KaiAgent):
    def _get_base_prompt_name(self) -> str:
        return "my-custom-prompt"
```

Create an agent definition:

1. Create `.kai/agents/my-custom-prompt.md`:

```markdown
---
name: my-custom-prompt
description: My specialized agent
extends: kai-code
---

# Purpose

Your specialized content...
```

2. The Python class will now use the merged prompt automatically.

### From Traditional Prompts

If you have `src/kai_code/prompts/my-agent.md` with `# INHERIT: kai-code`:

You can migrate to `.kai/agents/my-agent.md`:

```markdown
---
name: my-agent
description: My specialized agent
extends: kai-code
---

# Purpose

Your specialized content...
```

The behavior remains identical - both sources are handled by the same prompt loader.

## API Reference

### Loading Prompts

```python
from kai_code.prompts import load_prompt, list_prompts, get_prompt_path

# Load a prompt (with inheritance applied)
prompt = load_prompt("seeknal")

# List all available prompts (from both sources)
prompts = list_prompts()  # ["kai-code", "kai-dbt", "seeknal", ...]

# Get the file path
path = get_prompt_path("seeknal")  # Path to .kai/agents/seeknal.md
```

### Clearing Cache

```python
from kai_code.prompts import clear_cache

# Clear cache during development
clear_cache()
```

## Troubleshooting

### Prompt Not Found

```
FileNotFoundError: Prompt 'my-agent' not found. Available prompts: [...]
```

Check:
1. File exists in `src/kai_code/prompts/my-agent.md` OR `.kai/agents/my-agent.md`
2. Filename is kebab-case
3. File is not hidden (doesn't start with `_`)

### Inheritance Not Working

If specialized content appears but base content doesn't:

1. Check `extends:` field is correctly set in YAML frontmatter
2. Verify parent prompt exists
3. Check for circular inheritance (A extends B extends A)

### Duplicate Prompt Names

If you have both `src/kai_code/prompts/foo.md` and `.kai/agents/foo.md`:

- `prompts/` is checked first
- Rename one to avoid conflicts
