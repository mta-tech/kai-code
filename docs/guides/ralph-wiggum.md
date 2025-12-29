# Ralph Wiggum Guide

Ralph Wiggum mode is an autonomous loop system that enables iterative, self-improving task completion. Named after the Simpsons character, it represents an agent that works independently, checking in occasionally until a task is complete.

## Overview

Ralph mode creates a feedback loop where:
1. The agent receives a task
2. It works on the task iteratively
3. Each iteration builds on previous work
4. The loop continues until completion criteria are met

## Quick Start

### Starting Ralph Mode

```bash
kai
> /ralph start "Refactor the authentication module to use JWT"
```

### Monitoring Progress

```bash
> /ralph status
```

### Stopping the Loop

```bash
> /ralph stop
```

## Commands

| Command | Description |
|---------|-------------|
| `/ralph start <task>` | Start autonomous loop with given task |
| `/ralph status` | Check current loop status |
| `/ralph stop` | Stop the current loop |
| `/ralph pause` | Pause the loop (resume with start) |
| `/ralph log` | View recent loop activity |

## How It Works

### The Loop Cycle

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  1. Receive Task                                    │
│     ↓                                               │
│  2. Analyze Current State                           │
│     ↓                                               │
│  3. Plan Next Steps                                 │
│     ↓                                               │
│  4. Execute Actions                                 │
│     ↓                                               │
│  5. Evaluate Progress                               │
│     ↓                                               │
│  6. Check Completion Criteria                       │
│     ↓                                               │
│  ├─→ Complete? → Exit Loop                          │
│  └─→ Not Complete? → Back to Step 2                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### State Persistence

Ralph mode maintains state across iterations:

```
.kai/ralph/
├── loop-state.json     # Current loop state
├── iterations.log      # Iteration history
└── checkpoints/        # Recovery points
```

## Configuration

### In Settings

```json
{
  "ralph": {
    "max_iterations": 50,
    "iteration_delay": 2,
    "checkpoint_interval": 5,
    "auto_stop_on_error": true
  }
}
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `max_iterations` | 50 | Maximum iterations before stopping |
| `iteration_delay` | 2 | Seconds between iterations |
| `checkpoint_interval` | 5 | Iterations between checkpoints |
| `auto_stop_on_error` | true | Stop on unrecoverable errors |

## Use Cases

### 1. Large Refactoring Tasks

```bash
> /ralph start "Migrate all JavaScript files to TypeScript"
```

The agent will:
- Identify all `.js` files
- Convert them one by one
- Fix type errors iteratively
- Run tests after each batch
- Continue until all files are converted

### 2. Documentation Generation

```bash
> /ralph start "Add docstrings to all public functions in src/"
```

The agent will:
- Scan for undocumented functions
- Add docstrings progressively
- Validate format consistency
- Continue until coverage is complete

### 3. Bug Hunting

```bash
> /ralph start "Find and fix all uses of deprecated API calls"
```

The agent will:
- Search for deprecated patterns
- Fix each occurrence
- Verify fixes don't break tests
- Report progress

### 4. Code Quality Improvement

```bash
> /ralph start "Improve test coverage to 80%"
```

The agent will:
- Identify uncovered code
- Write tests for untested functions
- Run coverage reports
- Iterate until target is reached

## Best Practices

### 1. Clear Task Definitions

**Good:**
```bash
> /ralph start "Add input validation to all API endpoints in src/api/"
```

**Bad:**
```bash
> /ralph start "Improve the code"
```

### 2. Set Reasonable Limits

```json
{
  "ralph": {
    "max_iterations": 30,
    "iteration_delay": 5
  }
}
```

### 3. Use Checkpoints

Enable checkpointing for long tasks:

```json
{
  "ralph": {
    "checkpoint_interval": 3
  }
}
```

Recover from a checkpoint:
```bash
> /ralph resume
```

### 4. Monitor Progress

Check status regularly:
```bash
> /ralph status
```

View iteration log:
```bash
> /ralph log
```

### 5. Define Exit Criteria

Include measurable completion criteria in your task:

```bash
> /ralph start "Reduce code duplication until sonar reports < 5% duplication"
```

## Integration with CI/CD

### Headless Ralph Mode

Run Ralph in CI:

```bash
# In your CI script
kai -y -p "/ralph start 'Run linting and fix all issues' --max-iterations 20"
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Task completed successfully |
| 1 | Error during execution |
| 2 | Max iterations reached |
| 3 | Stopped by user |

### Example GitHub Action

```yaml
name: Ralph Code Improvement
on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly Monday 2am

jobs:
  improve:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install kai-code
        run: pip install -e '.[openai]'

      - name: Run Ralph
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          kai -y -p "/ralph start 'Fix all lint warnings' --max-iterations 10"

      - name: Create PR
        if: success()
        run: |
          git checkout -b ralph-improvements
          git add .
          git commit -m "Ralph: Automated code improvements"
          gh pr create --title "Ralph: Automated improvements" --body "Automated by Ralph Wiggum"
```

## Troubleshooting

### Loop Not Progressing

If the loop seems stuck:

1. Check status: `/ralph status`
2. View recent log: `/ralph log`
3. Consider if task is too vague
4. Stop and restart with clearer criteria

### Too Many Iterations

Set stricter limits:

```bash
> /ralph start "Fix tests" --max-iterations 10
```

Or in settings:

```json
{
  "ralph": {
    "max_iterations": 20
  }
}
```

### Recovering from Errors

If the loop stops due to an error:

1. Check the log: `/ralph log`
2. Fix the underlying issue
3. Resume: `/ralph resume`

### Stopping a Runaway Loop

```bash
> /ralph stop
```

Or in headless mode, send SIGINT (Ctrl+C).

## Advanced Usage

### Custom Completion Criteria

In your task, specify explicit completion criteria:

```bash
> /ralph start "
Add error handling to all database operations.
Complete when:
- All try/catch blocks are in place
- Error messages are user-friendly
- Logs include stack traces
- Tests pass for error cases
"
```

### Combining with Brainstorming

Use brainstorming first, then Ralph for execution:

```bash
> /brainstorm authentication refactor
# Review and approve the design

> /ralph start "Implement the approved authentication design from docs/plans/"
```

### Parallel Ralph Instances

Run multiple named sessions:

```bash
# Terminal 1
kai --agent ralph-frontend
> /ralph start "Update all React components to use hooks"

# Terminal 2
kai --agent ralph-backend
> /ralph start "Add API rate limiting to all endpoints"
```

## Limitations

1. **Not suitable for:**
   - Tasks requiring human judgment at each step
   - Changes that need immediate review
   - Security-sensitive modifications

2. **Works best with:**
   - Well-defined, measurable tasks
   - Repetitive operations across files
   - Iterative improvement goals

3. **Resource considerations:**
   - Each iteration uses API tokens
   - Long loops can be expensive
   - Set reasonable iteration limits

## Next Steps

- **[Getting Started Tutorial](../tutorials/getting-started.md)** - Basic usage
- **[Configuration Guide](configuration.md)** - All settings
- **[Custom Agents Guide](custom-agents.md)** - Extend functionality
