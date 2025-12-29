# System Prompts Improvement Plan

**Date:** 2024-12-22
**Status:** Ready for Implementation
**Scope:** Core improvements + kai-dbt specific enhancements

## Overview

Improve kai-code and kai-dbt system prompts based on Claude Code's best practices. Create a markdown-based prompt system with lazy loading and selective inheritance.

## Design Decisions

| Decision | Choice |
|----------|--------|
| Architecture | Markdown files in `src/kai_code/prompts/` |
| Loading | Lazy loading (load on first use) |
| File Structure | Single file per agent |
| Assembly | Selective inheritance (dbt inherits core, can override) |
| Examples | Rich examples (2-3 per major section) |
| Variables | Static only (no interpolation) |

## Tasks

### Task 1: Create prompts directory structure

Create the new prompts directory:

```
src/kai_code/prompts/
├── __init__.py
├── kai-code.md
└── kai-dbt.md
```

**Files:**
- `src/kai_code/prompts/__init__.py` - Empty init for package

**Tests:** None (directory creation)

---

### Task 2: Create kai-code.md system prompt

Create comprehensive system prompt with 8 sections (~800-1000 lines):

**Section 1: Identity & Role**
- "You are Kai Code, a software engineering agent"
- CLI tool context
- GitHub-flavored markdown output

**Section 2: Tone & Style Guidelines**
- No emojis unless requested
- Concise responses for CLI
- Professional objectivity
- No excessive praise ("You're absolutely right")
- Planning without time estimates

**Section 3: Tool Usage Policies**
- Prefer specialized tools over bash (Read vs cat, Edit vs sed)
- Parallel tool calls when independent
- Sequential when dependent
- Use absolute paths
- Never use bash for file operations

**Section 4: Over-Engineering Prevention**
- Only make requested changes
- Don't add features beyond what's asked
- Don't refactor surrounding code
- Don't add error handling for impossible scenarios
- Don't create abstractions for one-time operations
- Three similar lines > premature abstraction

**Section 5: Task Management**
- Use TodoWrite for 3+ step tasks
- Mark in_progress before starting
- Mark completed immediately after
- Examples of when to use/not use

**Section 6: Git Safety Protocol**
- Never update git config
- Never force push without explicit request
- Never skip hooks
- Amend rules (only when conditions met)
- Commit message format with HEREDOC
- PR creation workflow

**Section 7: Code Quality Rules**
- Read before modifying
- Avoid OWASP top 10 vulnerabilities
- Delete unused code completely
- No backwards-compatibility hacks

**Section 8: Planning Guidelines**
- Concrete steps without time estimates
- Break into actionable items
- Focus on what, not when

**Files:**
- `src/kai_code/prompts/kai-code.md`

**Tests:** `tests/prompts/test_kai_code_prompt.py`

---

### Task 3: Create kai-dbt.md system prompt

Create dbt-specific prompt with 8 sections (~400-500 lines):

**Section 1: Layer Conventions**
- staging/ (stg_): Views, 1:1 with source, cleaning only
- intermediate/ (int_): Tables, business logic
- marts/ (fct_, dim_): Tables, analytics-ready
- Examples for each layer

**Section 2: Schema Exploration Workflow**
- Always run get_database_schema() first
- Understand source data before modeling
- Check column types and nullability
- Identify relationships
- Example workflow

**Section 3: Model Quality Checklist**
- Config block with materialization
- CTEs for organization
- Explicit column selection (no SELECT *)
- Data type casting
- ref() for dependencies
- Example model template

**Section 4: dbt Command Safety**
- Warn before --full-refresh
- Explain destructive operations
- Safe defaults for dbt run
- Test before production
- Example safe vs risky commands

**Section 5: SQL Best Practices**
- No SELECT *
- Explicit JOIN conditions
- Proper aggregation patterns
- Window functions guidance
- CTEs over subqueries
- Examples

**Section 6: Testing Strategy**
- unique tests for primary keys
- not_null for required fields
- relationships for foreign keys
- accepted_values for enums
- Custom tests when needed
- Example schema.yml

**Section 7: Source-to-Mart Workflow**
- Step 1: Define sources in sources.yml
- Step 2: Create staging models
- Step 3: Build intermediate logic
- Step 4: Create mart tables
- Example walkthrough

**Section 8: Error Handling**
- Compilation errors vs runtime errors
- Common dbt errors and fixes
- Debug workflow
- Example error scenarios

**Files:**
- `src/kai_code/prompts/kai-dbt.md`

**Tests:** `tests/prompts/test_kai_dbt_prompt.py`

---

### Task 4: Create prompt loader with selective inheritance

Create `__init__.py` with lazy loading and selective inheritance support:

```python
def load_prompt(name: str) -> str:
    """Load prompt by name with inheritance support.

    Args:
        name: Prompt name ("kai-code", "kai-dbt")

    Returns:
        Full prompt string with inheritance applied
    """
```

**Features:**
- Lazy loading (load markdown on first use)
- Caching (don't reload same file)
- Selective inheritance via `# INHERIT: kai-code` marker
- Override sections via `# OVERRIDE: section-name` marker
- `get_prompt_path()` for file location
- `list_prompts()` for discovery

**Files:**
- `src/kai_code/prompts/__init__.py`

**Tests:** `tests/prompts/test_prompt_loader.py`

---

### Task 5: Update KaiAgent to use new prompt system

Modify `src/kai_code/agent.py`:

1. Import from `kai_code.prompts`
2. Load "kai-code" prompt in `_build_graph()`
3. Combine with user-provided system_prompt
4. Maintain backwards compatibility

**Files:**
- `src/kai_code/agent.py`

**Tests:** `tests/test_agent_prompts.py`

---

### Task 6: Update DbtAgent to use new prompt system

Modify `src/kai_code/agents/dbt/agent.py`:

1. Remove `_build_dbt_system_prompt()` method
2. Load "kai-dbt" prompt (which inherits from kai-code)
3. Combine with user-provided system_prompt

**Files:**
- `src/kai_code/agents/dbt/agent.py`

**Tests:** `tests/agents/dbt/test_dbt_agent_prompts.py`

---

### Task 7: Update system_prompts.py for backwards compatibility

Keep `resolve_system_prompt()` working but use new prompt loader internally:

```python
def resolve_system_prompt(*, system_id: str | None, extra: str | None) -> str | None:
    # Map old IDs to new prompts
    # "kai-default" -> load_prompt("kai-code")
```

**Files:**
- `src/kai_code/system_prompts.py`

**Tests:** `tests/test_system_prompts_compat.py`

---

### Task 8: Run all tests and commit

1. Run pytest for all new tests
2. Run existing tests to verify no regressions
3. Commit with descriptive message

**Commands:**
```bash
pytest tests/prompts/ -v
pytest tests/ -v
```

---

## File Summary

**New Files:**
- `src/kai_code/prompts/__init__.py` - Prompt loader
- `src/kai_code/prompts/kai-code.md` - Core system prompt
- `src/kai_code/prompts/kai-dbt.md` - dbt system prompt
- `tests/prompts/__init__.py` - Test package
- `tests/prompts/test_prompt_loader.py` - Loader tests
- `tests/prompts/test_kai_code_prompt.py` - Content tests
- `tests/prompts/test_kai_dbt_prompt.py` - dbt content tests

**Modified Files:**
- `src/kai_code/agent.py` - Use new prompts
- `src/kai_code/agents/dbt/agent.py` - Use new prompts
- `src/kai_code/system_prompts.py` - Backwards compat

## Success Criteria

1. All tests pass
2. `load_prompt("kai-code")` returns ~800+ line prompt
3. `load_prompt("kai-dbt")` returns kai-code + dbt sections
4. Existing `resolve_system_prompt()` still works
5. KaiAgent uses new comprehensive prompt
6. DbtAgent uses inherited dbt prompt
