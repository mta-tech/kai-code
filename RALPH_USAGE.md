# Ralph Mode Usage Guide

## Native Ralph Commands (Recommended)

The kai-code and kai-dbt Rich CLIs have **built-in Ralph support** via native commands.

### Using Ralph in kai-dbt

**Start a Ralph loop:**
```bash
kai-dbt
> /ralph-loop "build five business metrics from green_tripdata_2023-05.parquet" --promise METRICS_COMPLETE --max-iterations 30
```

**Check Ralph status:**
```bash
> /ralph-status
```

**Cancel Ralph loop:**
```bash
> /cancel-ralph
```

### CLI Usage

**Start kai-dbt with Ralph mode:**
```bash
kai-dbt --ralph --ralph-promise "METRICS_COMPLETE" "build five business metrics"
```

**Start kai-code with Ralph mode:**
```bash
kai --ralph --ralph-promise "TESTS_PASS" "fix all failing tests"
```

## Important Notes

1. **Use `/ralph-loop` NOT `/ralph-wiggum:ralph-loop`**
   - `/ralph-loop` = Native command (works in Rich CLI)
   - `/ralph-wiggum:ralph-loop` = Plugin command (for other contexts)

2. **Completion Promise Format**
   - Use simple strings: `TESTS_PASS`, `METRICS_COMPLETE`, `BUILD_DONE`
   - No need for XML tags in the promise parameter
   - The agent outputs `<promise>TEXT</promise>` to signal completion

3. **Command Syntax**
```bash
/ralph-loop "<prompt>" [--promise <text>] [--max-iterations <n>] [--timeout <s>] [--token-limit <n>]
```

## Example Session

```bash
# Start kai-dbt
kai-dbt

# Navigate to project
kai-dbt> cd green_trips

# Start Ralph loop
kai-dbt> /ralph-loop "build staging and metrics models for green taxi data" --promise BUILD_COMPLETE --max-iterations 25

⟳ Ralph autonomous loop started!
Prompt: build staging and metrics models for green taxi data
Completion promise: BUILD_COMPLETE
Max iterations: 25
Token limit: 500,000

# Ralph will now work autonomously until:
# - It outputs <promise>BUILD_COMPLETE</promise>
# - Hits max iterations (25)
# - Exceeds token limit (500K)

# Check status anytime
kai-dbt> /ralph-status

# Cancel if needed
kai-dbt> /cancel-ralph
```

## Available Ralph Commands

| Command | Description |
|---------|-------------|
| `/ralph-loop` | Start autonomous loop with prompt and options |
| `/ralph-status` or `/ralph` | Show current loop status |
| `/cancel-ralph` | Stop active Ralph loop |

## Flags for /ralph-loop

| Flag | Default | Description |
|------|---------|-------------|
| `--promise` | None | Completion string to detect (optional) |
| `--max-iterations` | 50 | Maximum iterations before stopping |
| `--timeout` | None | Wall-clock timeout in seconds |
| `--token-limit` | 500,000 | Maximum total tokens |
