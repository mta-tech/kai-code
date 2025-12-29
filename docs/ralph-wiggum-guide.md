# Ralph Wiggum Autonomous Loop System

## Overview

Ralph Wiggum is an autonomous agent loop system that enables kai-code and kai-dbt agents to work continuously on tasks until completion without human intervention. The system automatically re-feeds prompts, checks completion criteria, and enforces safety limits.

## Key Features

- **Autonomous Operation**: Agents continue working until task completion
- **Self-Referential Improvement**: Each iteration sees previous work (files, git history)
- **Safety Mechanisms**: Iteration limits, timeouts, token budgets
- **Completion Detection**: Automatic task completion via completion promises
- **State Persistence**: Loop state survives process restarts
- **Progress Tracking**: Logging and metrics collection

## Quick Start

### CLI Usage

Start a Ralph loop from the command line:

```bash
# Basic usage
kai --ralph --ralph-promise TESTS_PASS "Fix all failing tests"

# With custom limits
kai --ralph \
    --ralph-promise BUILD_COMPLETE \
    --ralph-max-iterations 30 \
    --ralph-timeout 1800 \
    --ralph-token-limit 300000 \
    "Build all dbt models successfully"
```

### TUI Usage

Start a Ralph loop in the interactive TUI:

```
/ralph-loop "Fix all tests" --promise TESTS_PASS --max-iterations 30
```

Check status:

```
/ralph-status
```

Cancel loop:

```
/cancel-ralph
```

### dbt Patterns

Use pre-configured patterns for common dbt workflows:

```bash
# List available patterns
kai-dbt
> /ralph-patterns

# Start a pattern
> /ralph-pattern test-until-pass
```

Available dbt patterns:
- `test-until-pass`: Run tests until all pass (30 iterations)
- `build-models`: Build models incrementally (25 iterations)
- `lint-fix`: Fix sqlfluff violations (20 iterations)
- `test-and-lint`: Fix both tests and lint (35 iterations)
- `fix-compilation`: Fix compilation errors (15 iterations)
- `schema-tests`: Add and fix schema tests (40 iterations)
- `docs-generate`: Generate documentation (20 iterations)

## How It Works

### The Ralph Loop Cycle

```
1. Agent runs with prompt
2. Agent completes and attempts to exit
3. RalphStopHook intercepts exit
4. Check completion promise in output
5. Check safety limits (iterations, tokens, timeout)
6. If not complete and under limits:
   - Increment iteration counter
   - Re-feed the same prompt
   - Go to step 1
7. If complete or limits reached:
   - Exit loop
```

### Completion Promises

A completion promise is an exact string that signals task completion. When the agent outputs this string, the loop terminates successfully.

**Examples:**
- `TESTS_PASS` - All tests passing
- `BUILD_COMPLETE` - Build finished
- `LINT_CLEAN` - No lint violations
- `ALL_DONE` - General completion

**Best Practice**: Use clear, unique strings that won't appear accidentally in normal output.

### Safety Limits

Ralph enforces multiple safety mechanisms:

1. **Max Iterations** (default: 50)
   - Prevents infinite loops
   - Configurable per loop

2. **Token Limit** (default: 500K)
   - Prevents excessive API costs
   - Tracks cumulative token usage

3. **Timeout** (optional)
   - Wall-clock time limit
   - Useful for time-sensitive tasks

4. **Manual Cancellation**
   - `/cancel-ralph` command
   - Emergency stop

## Configuration

### CLI Flags

```bash
--ralph                    # Enable Ralph loop mode
--ralph-promise STRING     # Completion promise to detect
--ralph-max-iterations N   # Max iterations (default: 50)
--ralph-timeout SECONDS    # Timeout in seconds (optional)
--ralph-token-limit N      # Max total tokens (default: 500000)
```

### Programmatic Usage

```python
from kai_code.agent import KaiAgent

# Create agent
agent = KaiAgent(root_dir="/path/to/project")

# Start Ralph loop
agent.ralph_manager.start_loop(
    prompt="Fix all tests",
    completion_promise="TESTS_PASS",
    max_iterations=30,
    timeout_seconds=1800,  # 30 minutes
    token_limit=500_000,
)

# Run agent (will loop automatically)
result = agent.run("Fix all tests")

# Check status
if agent.ralph_manager.is_active():
    state = agent.ralph_manager.get_state()
    print(f"Iteration {state.current_iteration}/{state.max_iterations}")
    print(f"Tokens used: {state.total_tokens:,}")
```

## Best Practices

### Writing Effective Prompts

**Good prompts:**
- Clear, specific tasks with measurable completion
- Include the completion promise in the prompt
- Specify what "done" looks like

```
"Run 'dbt test' and fix any failures. Continue until all tests pass.
Output TESTS_PASS when complete."
```

**Poor prompts:**
- Vague goals
- No clear completion criteria
- Ambiguous success conditions

```
"Make the project better"  # Too vague
```

### Choosing Iteration Limits

- **Quick fixes**: 10-15 iterations
- **Standard tasks**: 20-30 iterations
- **Complex features**: 40-50 iterations
- **Large refactors**: 50+ iterations (monitor costs)

### Token Budgets

- **Small tasks**: 100K-200K tokens (~$1-2)
- **Medium tasks**: 300K-500K tokens (~$3-5)
- **Large tasks**: 500K-1M tokens (~$5-10)

*Costs based on Sonnet 3.5 pricing as of 2024*

### When to Use Ralph

**✅ Excellent for:**
- Fixing failing tests iteratively
- Building features with TDD
- Fixing lint/format errors
- Building dbt models incrementally
- Any task with clear completion criteria

**❌ Avoid for:**
- Production debugging (too risky)
- Tasks requiring human judgment
- One-shot operations
- Unclear success criteria
- Exploratory work

## Monitoring and Debugging

### View Loop Status

```bash
# In TUI
/ralph-status

# Programmatically
state = agent.ralph_manager.get_state()
print(f"Active: {state.active}")
print(f"Iteration: {state.current_iteration}/{state.max_iterations}")
print(f"Tokens: {state.total_tokens:,}/{state.token_limit:,}")
print(f"Prompt: {state.prompt}")
```

### Check Metrics

Ralph logs metrics to `.kai/ralph-metrics.json`:

```json
[
  {
    "timestamp": 1704394800,
    "elapsed_seconds": 456,
    "iterations": 12,
    "total_tokens": 45000,
    "completion_promise": "TESTS_PASS",
    "max_iterations": 30,
    "prompt": "Fix all tests..."
  }
]
```

### Logs

Ralph logs progress to the kai-code logger:

```
⟳ Ralph iteration 1/30 (tokens: 1,234)
⟳ Ralph iteration 2/30 (tokens: 2,456)
✓ Ralph loop completed: completion promise found
```

### Common Issues

**Loop doesn't start:**
- Check that `--ralph` flag is set
- Verify agent is properly initialized

**Loop never completes:**
- Check completion promise spelling
- Ensure prompt instructs agent to output promise
- Verify promise appears in agent output

**Loop stops early:**
- Check iteration limit
- Check token limit
- Check for timeout
- Look for error messages

**Too many iterations:**
- Task might be too complex
- Prompt might be unclear
- Consider breaking into smaller tasks

## Architecture

### Components

```
┌─────────────────────┐
│   KaiAgent.run()    │
│                     │
│  ┌───────────────┐  │
│  │ Agent Logic   │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │ RalphStopHook │  │ ← Intercepts exit
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │   Check:      │  │
│  │ - Completion  │  │
│  │ - Limits      │  │
│  └───────┬───────┘  │
│          │          │
│     Continue?       │
│      ┌──┴──┐        │
│     Yes    No       │
│      │      └──► Exit
│      │             │
│  Re-feed prompt    │
│      │             │
│      └─────────────┘
└─────────────────────┘
```

### State Management

Ralph state is persisted to `.kai/ralph-loop.json`:

```json
{
  "active": true,
  "prompt": "Fix all tests",
  "completion_promise": "TESTS_PASS",
  "max_iterations": 30,
  "current_iteration": 5,
  "started_at": 1704394800,
  "timeout_seconds": 1800,
  "token_limit": 500000,
  "total_tokens": 12500,
  "output_log": [
    "Fixing test_user.py...",
    "Fixing test_auth.py..."
  ]
}
```

## API Reference

### RalphLoopManager

Main interface for Ralph loop control.

```python
class RalphLoopManager:
    def __init__(self, root_dir: Path)

    def start_loop(
        self,
        prompt: str,
        completion_promise: str | None = None,
        max_iterations: int | None = 50,
        timeout_seconds: int | None = None,
        token_limit: int = 500_000,
    ) -> None

    def is_active(self) -> bool
    def check_completion(self, output: str) -> bool
    def should_continue(self) -> bool
    def increment_iteration(self) -> None
    def cancel_loop(self) -> None
    def get_state(self) -> RalphLoopState | None
    def get_prompt(self) -> str
```

### RalphStopHook

Hook that intercepts agent exit.

```python
class RalphStopHook:
    def __init__(self, manager: RalphLoopManager)

    def on_agent_complete(
        self,
        agent: KaiAgent,
        result: KaiResult
    ) -> tuple[bool, str | None]
```

### dbt Patterns

```python
from kai_code.agents.dbt.ralph_patterns import (
    start_dbt_ralph_pattern,
    list_dbt_ralph_patterns,
    DBT_RALPH_PATTERNS,
)

# Start a pattern
start_dbt_ralph_pattern(agent, "test-until-pass")

# With overrides
start_dbt_ralph_pattern(
    agent,
    "test-until-pass",
    max_iterations=50,
    token_limit=600_000,
)

# List patterns
print(list_dbt_ralph_patterns())
```

## Examples

### Example 1: Fix Failing Tests

```bash
kai --ralph \
    --ralph-promise "TESTS_PASS" \
    --ralph-max-iterations 25 \
    "Run pytest and fix all failing tests. Output TESTS_PASS when done."
```

### Example 2: Build dbt Models

```bash
kai-dbt
> /ralph-pattern build-models
```

### Example 3: Custom Task

```python
from kai_code.agent import KaiAgent

agent = KaiAgent(root_dir=".")

agent.ralph_manager.start_loop(
    prompt="Refactor the authentication module to use async/await. "
           "Update all tests. Output REFACTOR_COMPLETE when done.",
    completion_promise="REFACTOR_COMPLETE",
    max_iterations=40,
    timeout_seconds=3600,  # 1 hour
)

result = agent.run(agent.ralph_manager.get_prompt())
```

## Cost Analysis

### Real-World Example

From production usage (source: ghuntley.com/ralph):
- Task: Build complex feature from scratch
- Iterations: ~50
- Total tokens: ~450K
- Cost: $297 (for a $50K project)
- ROI: 168x

### Calculating Costs

```python
# Estimate costs (Sonnet 3.5 pricing)
INPUT_PRICE = 3.00 / 1_000_000   # $3 per million tokens
OUTPUT_PRICE = 15.00 / 1_000_000  # $15 per million tokens

def estimate_cost(iterations, avg_input, avg_output):
    total_input = iterations * avg_input
    total_output = iterations * avg_output

    cost = (total_input * INPUT_PRICE) + (total_output * OUTPUT_PRICE)
    return cost

# Example: 30 iterations, 5K input, 2K output per iteration
cost = estimate_cost(30, 5000, 2000)
print(f"Estimated cost: ${cost:.2f}")  # ~$1.35
```

## Troubleshooting

### Loop Runs Forever

**Symptom**: Loop continues indefinitely
**Solutions**:
- Check completion promise is in agent output
- Verify promise spelling matches exactly
- Add iteration limit as safety
- Review prompt clarity

### Loop Stops Too Early

**Symptom**: Task incomplete but loop exits
**Solutions**:
- Check token limit not exceeded
- Verify timeout not reached
- Check max iterations not too low
- Look for errors in logs

### High Token Usage

**Symptom**: Consuming more tokens than expected
**Solutions**:
- Reduce context in each iteration
- Use more specific prompts
- Set lower token limit
- Monitor with /ralph-status

### State Not Persisting

**Symptom**: Loop state lost on restart
**Solutions**:
- Check `.kai/` directory permissions
- Verify state file not corrupted
- Ensure proper shutdown (not kill -9)

## Advanced Topics

### Custom Patterns

Create your own Ralph patterns:

```python
from dataclasses import dataclass
from kai_code.agents.dbt.ralph_patterns import RalphPattern

MY_PATTERN = RalphPattern(
    name="custom-workflow",
    description="My custom workflow",
    prompt="Do custom task. Output CUSTOM_DONE when complete.",
    completion_promise="CUSTOM_DONE",
    max_iterations=20,
    token_limit=300_000,
)

# Use it
agent.ralph_manager.start_loop(
    prompt=MY_PATTERN.prompt,
    completion_promise=MY_PATTERN.completion_promise,
    max_iterations=MY_PATTERN.max_iterations,
    token_limit=MY_PATTERN.token_limit,
)
```

### Multiple Agents

Run Ralph loops across multiple agents:

```python
agents = [
    KaiAgent(root_dir="project1"),
    KaiAgent(root_dir="project2"),
]

for agent in agents:
    agent.ralph_manager.start_loop(
        prompt="Fix tests",
        completion_promise="TESTS_PASS",
        max_iterations=20,
    )
    agent.run(agent.ralph_manager.get_prompt())
```

### Integration with CI/CD

```yaml
# .github/workflows/ralph-fix-tests.yml
name: Ralph Auto-Fix Tests

on:
  push:
    branches: [main]

jobs:
  auto-fix:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Ralph to fix tests
        run: |
          kai --ralph \
              --ralph-promise "TESTS_PASS" \
              --ralph-max-iterations 15 \
              --ralph-token-limit 200000 \
              "Run tests and fix failures. Output TESTS_PASS when done."
      - name: Commit fixes
        run: |
          git config user.name "Ralph Bot"
          git add .
          git commit -m "fix: auto-fix tests via Ralph"
          git push
```

## FAQ

**Q: How is this different from agentic loops?**
A: Ralph is specifically designed for completion-driven tasks with automatic re-feeding and safety limits.

**Q: Can I use Ralph with other agents?**
A: Yes, any agent that extends KaiAgent inherits Ralph functionality.

**Q: What happens if I lose connection?**
A: State is persisted to disk. Resume with the same command.

**Q: How do I know my task is suitable for Ralph?**
A: If you can define clear completion criteria and the task is iterative, it's suitable.

**Q: Can Ralph run in parallel?**
A: Each agent runs its own Ralph loop independently.

**Q: How do I estimate iteration count?**
A: Start conservative (20-30), monitor first run, adjust based on actual usage.

## References

- Original concept: https://ghuntley.com/ralph/
- Claude Code plugin: https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-wiggum
- kai-code documentation: /docs/README.md
