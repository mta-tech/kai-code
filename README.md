# Kai Code

**Kai Code** is a Python library for running **local coding agents** against project directories. Built on top of LangChain's `deepagents`, it provides intelligent AI assistants for software engineering and data engineering tasks.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Intelligent Code Agents**: AI-powered assistants that understand your codebase
- **Multiple LLM Support**: Works with OpenAI, Anthropic Claude, Google Gemini, and OpenRouter
- **Auto-Compact**: Automatically compresses conversation history at 85% context usage
- **Permission System**: Fine-grained control over what the agent can do
- **Human-in-the-Loop**: Approval workflows for sensitive operations
- **Session Persistence**: Resume conversations across restarts
- **Token Usage Indicator**: Color-coded warnings when approaching context limits
- **Auto-Update**: Update kai-code directly from GitHub without reinstallation
- **Extensible**: Create custom agents with specialized capabilities

## Agents

| Agent | CLI Command | Description |
|-------|-------------|-------------|
| **KaiAgent** | `kai-code` | General-purpose coding agent for software engineering |
| **DbtAgent** | `kai-dbt` | Specialized data engineering agent for dbt projects |

## Quick Start

### Installation

```bash
# Basic installation
pip install -e .

# With OpenAI support
pip install -e '.[openai]'
export OPENAI_API_KEY=your-key-here

# With Anthropic Claude support
pip install -e '.[anthropic]'
export ANTHROPIC_API_KEY=your-key-here

# With Google Gemini support
pip install -e '.[google-genai]'
export GOOGLE_API_KEY=your-key-here

# With OpenRouter support
pip install -e '.[openrouter]'
export OPENROUTER_API_KEY=your-key-here

# With dbt support (includes DuckDB and PostgreSQL)
pip install -e '.[dbt]'
```

### Basic Usage

#### Interactive CLI

```bash
# Start interactive session
kai-code

# With auto-approve mode (no confirmations)
kai-code -y

# Start new session
kai-code --new
```

#### Programmatic Usage

```python
from kai_code import KaiAgent

agent = KaiAgent(root_dir=".", model="openai:gpt-4o", yolo=True)
result = agent.run("Summarize this repository and propose improvements.")
print(result.output)
```

#### Headless Mode

```bash
# Single prompt
kai-code -p "Explain the architecture of this project"

# From stdin
echo "Add unit tests for utils.py" | kai-code -p

# With JSON output
kai-code -p "List all functions" --output-format json
```

## CLI Reference

### Main Commands

| Command | Description |
|---------|-------------|
| `kai-code` | Start the general-purpose coding agent |
| `kai-dbt` | Start the dbt-specialized data engineering agent |
| `kai-basic` | Legacy CLI (basic mode) |

### Common Flags

| Flag | Description |
|------|-------------|
| `-p`, `--prompt` | Execute a single prompt |
| `-y`, `--yes` | Auto-approve all actions (YOLO mode) |
| `--new` | Start a fresh session |
| `--agent NAME` | Use/create a named agent session |
| `--model MODEL` | Specify the LLM model |
| `--output-format` | Output format: `text`, `json`, `stream-json` |
| `--dry-run` | Show configuration without running |
| `--no-compact` | Disable auto-compaction |
| `--compact-threshold PCT` | Set compaction threshold (0.0-1.0) |

### Slash Commands

Available in interactive mode:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/exit` or `/quit` | Exit the session |
| `/new` | Start a new conversation |
| `/model <name>` | Switch the AI model |
| `/models [refresh]` | List or refresh available models |
| `/tokens [show\|hide]` | Show or hide token usage indicator |
| `/history` | Show conversation history |
| `/clear` | Clear conversation history |
| `/skills` | Show available skills |
| `/tasks` | Show background tasks |
| `/quickstart` | Show quick start guide |
| `/version` | Show version information |
| `/brainstorm [topic]` | Start a design session |
| `/ralph start` | Start autonomous Ralph mode |
| `/ralph status` | Check Ralph loop status |
| `/ralph stop` | Stop Ralph loop |
| `/update` | Update kai-code from GitHub |
| `/update check` | Check if updates are available |
| `/update status` | Show installation status |
| `/export-settings [file]` | Export settings to a file |
| `/import-settings <file>` | Import settings from a file |
| `/compact status` | Show auto-compact status |
| `/compact now` | Manually trigger compaction |
| `/compact enable` | Enable auto-compaction |
| `/compact disable` | Disable auto-compaction |

### dbt-Specific Commands (kai-dbt)

| Command | Description |
|---------|-------------|
| `/schema` | Show database schema summary |
| `/model <name>` | Show model details and columns |
| `/dbt run [model]` | Run dbt models |
| `/dbt test [model]` | Run dbt tests |
| `/dbt compile [model]` | Compile dbt models |

## Configuration

### Settings Hierarchy

Kai uses a 3-tier settings hierarchy (highest precedence last):

1. **Global**: `~/.kai/settings.json`
2. **Project**: `<project>/.kai/settings.json`
3. **Local**: `<project>/.kai/settings.local.json`

CLI flags and environment variables take highest precedence.

### Example Settings

```json
{
  "model": "openai:gpt-4o",
  "permission_mode": "default",
  "max_tokens": 4096
}
```

### Permission Modes

| Mode | Description |
|------|-------------|
| `default` | Approvals for execute, write, edit, and patch operations |
| `acceptEdits` | Approve execute only, allow file edits |
| `plan` | Read-only mode (no writes or execution) |
| `bypassPermissions` | YOLO mode - allow all operations |

```bash
# Use permission mode
kai-code --permission-mode plan

# YOLO shortcut
kai-code --yolo
```

## Human-in-the-Loop (HITL)

When `yolo=False`, the agent pauses for approval on sensitive operations:

```python
agent = KaiAgent(root_dir=".", model="openai:gpt-4o", yolo=False)

# If interrupted, resume with decisions:
result = agent.resume([{"type": "approve"}])
```

### CLI Resume

```bash
# Run without auto-approve
kai-code --no-yolo -p "Run tests"

# When interrupted (exit code 2), approve pending action
kai-code resume --continue --approve

# Or reject
kai-code resume --continue --reject
```

## Advanced Features

### Brainstorming Mode

Start a collaborative design session:

```bash
kai-code
> /brainstorm user authentication system
```

The `/brainstorm` command guides you through:
1. **Understanding** - Clarifying questions about your idea
2. **Exploring** - Alternative approaches with trade-offs
3. **Designing** - Incremental design validation
4. **Documentation** - Writes design to `docs/plans/`
5. **Implementation** - Optional implementation plan

### Ralph Mode (Autonomous Loop)

Ralph Wiggum mode enables autonomous, iterative task completion:

```bash
kai-code
> /ralph start "Refactor the auth module"
```

See [Ralph Wiggum Guide](docs/guides/ralph-wiggum.md) for details.

### Custom Agents

Create specialized agents by extending `KaiAgent`:

```python
from kai_code.agent import KaiAgent

class MyAgent(KaiAgent):
    def _get_base_prompt_name(self) -> str:
        return "my-custom-prompt"  # loads prompts/my-custom-prompt.md

    def get_my_tools(self):
        # Add custom tools
        return [my_tool_1, my_tool_2]
```

### Prompt System

Prompts are markdown files with inheritance:

```markdown
# my-custom-prompt.md
# INHERIT: kai-code

(Your custom prompt additions here)
```

```python
from kai_code.prompts import load_prompt

# Load with inheritance
prompt = load_prompt("my-custom-prompt")
```

### Auto-Update

Kai can update itself directly from GitHub:

```bash
# Check for updates (interactive)
kai-code
> /update check

# Show installation status
kai-code
> /update status

# Apply updates (interactive)
kai-code
> /update
```

The auto-update system handles both editable (development) installs and regular pip installations:
- **Editable installs**: Uses `git pull` to update
- **Regular installs**: Uses `pip install --upgrade` to update

### Auto-Compact Configuration

Auto-compact automatically compresses conversation history when approaching context limits:

```json
{
  "compaction": {
    "enabled": true,
    "threshold": 0.85,
    "recent_window_turns": 10,
    "min_time_between": 300,
    "max_summary_tokens": 1000
  }
}
```

**Settings:**
- `enabled`: Enable/disable auto-compaction
- `threshold`: Context usage percentage (0.0-1.0) to trigger
- `recent_window_turns`: Number of recent turns to always keep verbatim
- `min_time_between`: Minimum seconds between compactions (default: 300)
- `max_summary_tokens`: Target size for each summary

### Token Usage Indicator

When using models with context limits, Kai displays token usage in real-time:

- **Green** (< 80%): Safe, plenty of context remaining
- **Yellow** (80-95%): Approaching limit
- **Red** (>= 95%): Near limit, consider truncating history

The indicator appears in the status bar during interactive sessions.

## Project Structure

```
kai-code/
├── src/kai_code/
│   ├── agent.py              # Base KaiAgent class
│   ├── agents/
│   │   ├── dbt/              # DbtAgent and dbt tools
│   │   └── seeknal/          # SeeknalAgent (data engineering)
│   ├── prompts/              # System prompts (markdown)
│   ├── rich_*.py             # Rich CLI components
│   ├── rich_ui/              # Rich UI application
│   ├── tasks/                # Background task management
│   ├── tools/                # Shared tools
│   ├── memory/               # Memory management
│   ├── skills/               # Skill definitions
│   ├── update.py             # Auto-update functionality
│   └── models.json           # Available model configurations
├── docs/
│   ├── tutorials/            # Step-by-step tutorials
│   ├── guides/               # In-depth guides
│   └── api/                  # API reference
├── examples/                 # Example scripts
└── tests/                    # Test suite
```

## Development

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific tests
python -m pytest tests/prompts/ -v

# No-LLM verification (safe for CI)
python verify_no_llm.py
```

### Smoke Test

```bash
python -m kai_code.smoke
```

## Stream JSON Output

For programmatic consumption, use `--output-format stream-json`:

```bash
kai-code -p "Hello" --output-format stream-json
```

Events emitted:
- `init`: Run metadata
- `message`: Assistant response deltas
- `tool_call`: Tool invocations (HITL interrupts)
- `tool_result`: Tool results
- `error`: Exceptions
- `result`: Final summary with stats

See [Stream JSON Schema](docs/stream-json-schema.md) for full reference.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error |
| `2` | Interrupt (HITL approval required) |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m pytest tests/ -v`
5. Submit a pull request

## License

Apache-2.0 - See [LICENSE](LICENSE) for details.

## Documentation

- [Getting Started Tutorial](docs/tutorials/getting-started.md)
- [dbt Agent Tutorial](docs/tutorials/dbt-agent.md)
- [Configuration Guide](docs/guides/configuration.md)
- [Custom Agents Guide](docs/guides/custom-agents.md)
- [Ralph Wiggum Guide](docs/guides/ralph-wiggum.md)
- [API Reference](docs/api/README.md)
