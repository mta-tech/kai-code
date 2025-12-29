# Kai Code

**Kai Code** is a Python library for running **local coding agents** against project directories. Built on top of LangChain's `deepagents`, it provides intelligent AI assistants for software engineering and data engineering tasks.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Intelligent Code Agents**: AI-powered assistants that understand your codebase
- **Multiple LLM Support**: Works with OpenAI, Anthropic Claude, and Google Gemini
- **Permission System**: Fine-grained control over what the agent can do
- **Human-in-the-Loop**: Approval workflows for sensitive operations
- **Session Persistence**: Resume conversations across restarts
- **Extensible**: Create custom agents with specialized capabilities

## Agents

| Agent | CLI Command | Description |
|-------|-------------|-------------|
| **KaiAgent** | `kai` | General-purpose coding agent for software engineering |
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

# With dbt support (includes DuckDB and PostgreSQL)
pip install -e '.[dbt]'
```

### Basic Usage

#### Interactive CLI

```bash
# Start interactive session
kai

# With auto-approve mode (no confirmations)
kai -y

# Start new session
kai --new
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
kai -p "Explain the architecture of this project"

# From stdin
echo "Add unit tests for utils.py" | kai -p

# With JSON output
kai -p "List all functions" --output-format json
```

## CLI Reference

### Main Commands

| Command | Description |
|---------|-------------|
| `kai` | Start the general-purpose coding agent |
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

### Slash Commands

Available in interactive mode:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/exit` or `/quit` | Exit the session |
| `/new` | Start a new conversation |
| `/model <name>` | Switch the AI model |
| `/history` | Show conversation history |
| `/brainstorm [topic]` | Start a design session |
| `/ralph start` | Start autonomous Ralph mode |
| `/ralph status` | Check Ralph loop status |
| `/ralph stop` | Stop Ralph loop |

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
kai --permission-mode plan

# YOLO shortcut
kai --yolo
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
kai --no-yolo -p "Run tests"

# When interrupted (exit code 2), approve pending action
kai resume --continue --approve

# Or reject
kai resume --continue --reject
```

## Advanced Features

### Brainstorming Mode

Start a collaborative design session:

```bash
kai
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
kai
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

## Project Structure

```
kai-code/
├── src/kai_code/
│   ├── agent.py              # Base KaiAgent class
│   ├── agents/
│   │   └── dbt/              # DbtAgent and dbt tools
│   ├── prompts/              # System prompts (markdown)
│   ├── rich_*.py             # Rich CLI components
│   ├── tools/                # Shared tools
│   ├── memory/               # Memory management
│   └── skills/               # Skill definitions
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
kai -p "Hello" --output-format stream-json
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
