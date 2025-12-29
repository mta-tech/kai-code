# Ralph Wiggum API Reference

## Core Classes

### RalphLoopState

Dataclass representing the persistent state of a Ralph loop.

**Location**: `src/kai_code/ralph_loop.py`

```python
@dataclass
class RalphLoopState:
    """Persistent state for Ralph loop."""

    active: bool = False
    prompt: str = ""
    completion_promise: str | None = None
    max_iterations: int | None = None
    current_iteration: int = 0
    started_at: int = 0  # Unix timestamp
    timeout_seconds: int | None = None
    token_limit: int | None = 500_000
    total_tokens: int = 0
    output_log: list[str] = field(default_factory=list)
```

#### Methods

##### `is_timed_out() -> bool`

Check if wall-clock timeout has been exceeded.

**Returns**: True if timeout exceeded, False otherwise

**Example**:
```python
state = RalphLoopState(
    started_at=int(time.time()) - 3600,
    timeout_seconds=1800,
)
if state.is_timed_out():
    print("Timeout exceeded!")
```

##### `check_token_limit(tokens_used: int) -> bool`

Update token count and check if limit exceeded.

**Parameters**:
- `tokens_used`: Number of tokens used in this iteration

**Returns**: True if under limit, False if limit exceeded

**Side Effects**: Updates `total_tokens` field

**Example**:
```python
state = RalphLoopState(token_limit=1000)
if state.check_token_limit(500):
    print("Under limit, continue")
else:
    print("Limit exceeded, stop")
```

##### `to_dict() -> dict[str, Any]`

Convert state to dictionary for JSON serialization.

**Returns**: Dictionary representation of state

##### `from_dict(data: dict[str, Any]) -> RalphLoopState`

Create state from dictionary loaded from JSON.

**Parameters**:
- `data`: Dictionary representation of state

**Returns**: RalphLoopState instance

---

### RalphLoopManager

Main interface for managing Ralph loop lifecycle and state.

**Location**: `src/kai_code/ralph_loop.py`

```python
class RalphLoopManager:
    """Manages Ralph loop lifecycle and state."""

    def __init__(self, root_dir: Path):
        """Initialize Ralph loop manager.

        Args:
            root_dir: Project root directory where .kai/ will be created.
        """
```

#### Properties

- `root_dir: Path` - Project root directory
- `state_path: Path` - Path to `.kai/ralph-loop.json`

#### Methods

##### `start_loop(...)`

Activate Ralph loop with given parameters.

**Signature**:
```python
def start_loop(
    self,
    prompt: str,
    completion_promise: str | None = None,
    max_iterations: int | None = None,
    timeout_seconds: int | None = None,
    token_limit: int | None = 500_000,
) -> None
```

**Parameters**:
- `prompt`: Task prompt to be re-fed each iteration
- `completion_promise`: Exact string to detect completion (optional)
- `max_iterations`: Maximum iterations before stopping (default: 50)
- `timeout_seconds`: Wall-clock timeout in seconds (optional)
- `token_limit`: Maximum total tokens to use (default: 500K)

**Example**:
```python
manager = RalphLoopManager(Path("/project"))
manager.start_loop(
    prompt="Fix all tests",
    completion_promise="TESTS_PASS",
    max_iterations=30,
    timeout_seconds=1800,
    token_limit=500_000,
)
```

##### `is_active() -> bool`

Check if Ralph loop is currently active.

**Returns**: True if loop is active, False otherwise

##### `check_completion(output: str) -> bool`

Check if completion promise appears in agent output.

**Parameters**:
- `output`: Agent output text to check

**Returns**: True if completion promise found, False otherwise

##### `should_continue() -> bool`

Determine if loop should continue based on limits.

**Returns**: True if loop should continue, False if limits reached

**Checks**:
- Max iterations not exceeded
- Timeout not exceeded

##### `increment_iteration() -> None`

Increment iteration counter and save state.

**Side Effects**: Updates `current_iteration` and persists to disk

##### `get_prompt() -> str`

Get current prompt for re-feeding.

**Returns**: The prompt string, or empty string if no active loop

##### `get_state() -> RalphLoopState | None`

Get current loop state.

**Returns**: Current RalphLoopState or None if no active loop

##### `cancel_loop() -> None`

Deactivate Ralph loop.

**Side Effects**: Sets `active=False` and persists to disk

##### `log_output(output: str, max_length: int = 200) -> None`

Log agent output (truncated) for debugging.

**Parameters**:
- `output`: Agent output text
- `max_length`: Maximum length to store (default: 200 chars)

**Behavior**: Keeps only last 10 outputs to avoid memory bloat

##### `update_token_usage(tokens_used: int) -> bool`

Update token count and check limit.

**Parameters**:
- `tokens_used`: Tokens used in this iteration

**Returns**: True if under limit, False if limit exceeded

---

### RalphStopHook

Hook that intercepts agent exit to maintain Ralph loop.

**Location**: `src/kai_code/hooks/ralph_stop_hook.py`

```python
class RalphStopHook:
    """Hook that intercepts agent exit to maintain Ralph loop."""

    def __init__(self, manager: RalphLoopManager):
        """Initialize stop hook.

        Args:
            manager: RalphLoopManager instance to check loop state.
        """
```

#### Methods

##### `on_agent_complete(agent: KaiAgent, result: KaiResult) -> tuple[bool, str | None]`

Called when agent attempts to exit.

**Parameters**:
- `agent`: KaiAgent instance that just completed
- `result`: KaiResult from the agent's run

**Returns**: Tuple of `(should_continue, next_prompt)`
- `should_continue`: True to re-feed prompt, False to exit
- `next_prompt`: Prompt for next iteration (if should_continue)

**Logic**:
1. Check if loop is active (return False if not)
2. Log agent output
3. Extract and update token usage
4. Check for completion promise (return False if found)
5. Check token limit (return False if exceeded)
6. Check other safety limits (return False if exceeded)
7. Increment iteration and return True with prompt

**Example**:
```python
hook = RalphStopHook(manager)
should_continue, next_prompt = hook.on_agent_complete(agent, result)

if should_continue:
    result = agent.run(next_prompt)  # Loop continues
```

---

## Command Functions

### ralph_commands.py

Command handlers for TUI/CLI interaction.

**Location**: `src/kai_code/ralph_commands.py`

#### `ralph_loop_command(...)`

Start a Ralph autonomous loop.

**Signature**:
```python
def ralph_loop_command(
    agent: KaiAgent,
    prompt: str,
    completion_promise: str | None = None,
    max_iterations: int | None = None,
    timeout_seconds: int | None = None,
    token_limit: int | None = 500_000,
) -> str
```

**Returns**: Status message indicating loop started

#### `cancel_ralph_command(agent: KaiAgent) -> str`

Cancel active Ralph loop.

**Returns**: Status message indicating loop canceled or not active

#### `ralph_status_command(agent: KaiAgent) -> str`

Show Ralph loop status.

**Returns**: Formatted status information

---

## dbt Integration

### ralph_patterns.py

Pre-configured Ralph patterns for dbt workflows.

**Location**: `src/kai_code/agents/dbt/ralph_patterns.py`

#### `RalphPattern`

Dataclass representing a pre-configured Ralph loop pattern.

```python
@dataclass
class RalphPattern:
    name: str
    description: str
    prompt: str
    completion_promise: str
    max_iterations: int
    timeout_seconds: int | None = None
    token_limit: int = 500_000
```

#### `DBT_RALPH_PATTERNS`

Dictionary of pre-configured dbt patterns.

**Available Patterns**:
- `test-until-pass`: Run dbt tests until all pass (30 iterations)
- `build-models`: Build dbt models incrementally (25 iterations)
- `lint-fix`: Fix sqlfluff violations (20 iterations)
- `test-and-lint`: Fix tests and lint (35 iterations)
- `fix-compilation`: Fix compilation errors (15 iterations)
- `schema-tests`: Add schema tests (40 iterations)
- `docs-generate`: Generate documentation (20 iterations)

#### `start_dbt_ralph_pattern(...)`

Start a pre-configured dbt Ralph pattern.

**Signature**:
```python
def start_dbt_ralph_pattern(
    agent: DbtAgent,
    pattern_name: str,
    custom_prompt: str | None = None,
    **overrides,
) -> str
```

**Parameters**:
- `agent`: DbtAgent instance
- `pattern_name`: Name of pattern to use
- `custom_prompt`: Optional custom prompt to override default
- `**overrides`: Override pattern defaults (e.g., max_iterations=50)

**Returns**: Status message indicating loop started

**Raises**: ValueError if pattern_name not found

**Example**:
```python
from kai_code.agents.dbt.ralph_patterns import start_dbt_ralph_pattern

# Use default pattern
start_dbt_ralph_pattern(agent, "test-until-pass")

# With overrides
start_dbt_ralph_pattern(
    agent,
    "test-until-pass",
    max_iterations=50,
    token_limit=600_000,
)
```

#### `list_dbt_ralph_patterns() -> str`

List all available dbt Ralph patterns.

**Returns**: Formatted list of patterns with descriptions

---

## Logging

### ralph_logger.py

Progress logging and monitoring utilities.

**Location**: `src/kai_code/ralph_logger.py`

#### `log_ralph_start(state: RalphLoopState) -> None`

Log Ralph loop start.

#### `log_ralph_iteration(iteration: int, max_iterations: int | None, tokens_used: int, total_tokens: int) -> None`

Log Ralph loop iteration progress.

#### `log_ralph_completion(reason: str, state: RalphLoopState) -> None`

Log Ralph loop completion.

#### `log_ralph_error(error: Exception, state: RalphLoopState) -> None`

Log Ralph loop error.

#### `write_ralph_metrics(state: RalphLoopState, root_dir: Path) -> None`

Write Ralph loop metrics to file.

**Output**: Appends to `.kai/ralph-metrics.json`

---

## KaiAgent Integration

The KaiAgent class is extended with Ralph functionality.

### New Properties

```python
@property
def ralph_manager(self) -> RalphLoopManager:
    """The Ralph loop manager for autonomous operation."""
    return self._ralph_manager
```

### Modified Methods

#### `run(prompt: str) -> KaiResult`

The run method now integrates with Ralph:

```python
def run(self, prompt: str) -> KaiResult:
    """Run the agent with the given prompt.

    If a Ralph loop is active, this method will re-feed the prompt
    recursively until the loop completes or safety limits are reached.
    """
    # ... agent execution ...

    result = KaiResult(output=output, messages=messages, raw=state)

    # Check Ralph stop hook - enables autonomous loops
    should_continue, next_prompt = self._ralph_hook.on_agent_complete(self, result)

    if should_continue and next_prompt:
        # Ralph loop continues - recursively re-feed the prompt
        return self.run(next_prompt)

    return result
```

---

## CLI Integration

### New CLI Flags

```bash
--ralph                    # Enable Ralph autonomous loop mode
--ralph-promise STRING     # Exact string to detect completion
--ralph-max-iterations N   # Maximum iterations (default: 50)
--ralph-timeout SECONDS    # Wall-clock timeout in seconds
--ralph-token-limit N      # Maximum total tokens (default: 500K)
```

### Usage Example

```bash
kai --ralph \
    --ralph-promise "TESTS_PASS" \
    --ralph-max-iterations 30 \
    --ralph-timeout 1800 \
    --ralph-token-limit 300000 \
    "Fix all failing tests. Output TESTS_PASS when done."
```

---

## TUI Commands

### Registered Commands

```python
{
    "ralph-loop": Command(
        name="ralph-loop",
        description="Start Ralph autonomous loop",
        requires_arg=True,
    ),
    "cancel-ralph": Command(
        name="cancel-ralph",
        description="Cancel active Ralph loop",
        aliases=["ralph-cancel", "stop-ralph"],
    ),
    "ralph-status": Command(
        name="ralph-status",
        description="Show Ralph loop status",
        aliases=["ralph"],
    ),
}
```

### Command Syntax

```
/ralph-loop <prompt> [--promise <text>] [--max-iterations <n>] [--timeout <s>] [--token-limit <n>]
/cancel-ralph
/ralph-status
```

---

## State Persistence

### File Location

Ralph state is persisted to:
```
<root_dir>/.kai/ralph-loop.json
```

### File Format

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
    "Fixing test_auth.py...",
    "..."
  ]
}
```

### Metrics File

Metrics are appended to:
```
<root_dir>/.kai/ralph-metrics.json
```

Format:
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

---

## Type Definitions

### KaiResult

```python
@dataclass(frozen=True)
class KaiResult:
    output: str
    messages: list[dict[str, Any]]
    raw: dict[str, Any]
```

---

## Constants

### Default Values

```python
DEFAULT_MAX_ITERATIONS = 50
DEFAULT_TOKEN_LIMIT = 500_000
MAX_OUTPUT_LOG_SIZE = 10
OUTPUT_LOG_TRUNCATE_LENGTH = 200
```

---

## Error Handling

### Exceptions

Ralph uses standard Python exceptions:

- `ValueError`: Invalid pattern name or parameters
- `FileNotFoundError`: State file issues
- `json.JSONDecodeError`: Corrupted state file
- `TimeoutError`: Not raised, checked via `is_timed_out()`

### Error Recovery

Ralph is designed to be resilient:

1. **Corrupted state file**: Starts fresh
2. **Process crash**: State restored on restart
3. **Token limit**: Graceful shutdown
4. **Timeout**: Graceful shutdown
5. **Max iterations**: Graceful shutdown

---

## Testing

### Test Files

- `tests/test_ralph_loop.py`: Unit tests (32 tests)
- `tests/e2e/test_ralph_e2e.py`: E2E tests (10 tests)

### Running Tests

```bash
# Unit tests only
pytest tests/test_ralph_loop.py -v

# E2E tests only
pytest tests/e2e/test_ralph_e2e.py -v

# All Ralph tests
pytest tests/test_ralph_loop.py tests/e2e/test_ralph_e2e.py -v
```

---

## Thread Safety

⚠️ **Warning**: Ralph is not thread-safe. Do not run multiple Ralph loops concurrently in the same process on the same root directory.

For parallel execution, use separate processes with different root directories.

---

## Performance Considerations

### Memory Usage

- State file: ~1-5 KB
- Output log: Limited to last 10 entries, truncated to 200 chars each
- In-memory state: Minimal (<1 MB)

### Disk I/O

State is persisted to disk:
- On loop start
- After each iteration
- On loop completion
- On cancellation

Use SSD storage for best performance.

### Token Efficiency

Ralph is token-efficient:
- No additional context overhead
- Prompts are re-used exactly
- Agent sees previous work through files, not conversation history
