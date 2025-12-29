# Getting Started with Kai Code

This tutorial will guide you through installing, configuring, and using Kai Code for your first AI-assisted coding session.

## Prerequisites

- Python 3.11 or higher
- An API key for at least one supported LLM provider:
  - OpenAI (GPT-4, GPT-4o)
  - Anthropic (Claude)
  - Google (Gemini)

## Installation

### Step 1: Clone or Install

```bash
# Clone the repository
git clone https://github.com/yourusername/kai-code.git
cd kai-code

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with your preferred LLM provider
pip install -e '.[openai]'      # For OpenAI
pip install -e '.[anthropic]'   # For Anthropic Claude
pip install -e '.[google-genai]' # For Google Gemini
```

### Step 2: Configure API Keys

Create a `.env` file in your project root:

```bash
# For OpenAI
OPENAI_API_KEY=sk-your-openai-key-here

# For Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# For Google
GOOGLE_API_KEY=your-google-key-here
```

Or export them directly:

```bash
export OPENAI_API_KEY=sk-your-openai-key-here
```

## Your First Session

### Starting Interactive Mode

```bash
kai
```

You'll see a welcome banner and prompt:

```
╭──────────────────────────────────────────────────────────────────╮
│  Kai Code - AI Coding Assistant                                   │
│  Model: openai:gpt-4o                                             │
│  Session: default                                                 │
╰──────────────────────────────────────────────────────────────────╯

You:
```

### Your First Prompt

Try asking the agent to analyze your project:

```
You: Summarize this project and list the main files
```

The agent will:
1. Scan your project structure
2. Read relevant files
3. Provide a summary

### Using Slash Commands

Type `/help` to see available commands:

```
You: /help
```

Common commands:
- `/new` - Start a fresh conversation
- `/model gpt-4o` - Switch to a different model
- `/history` - Show conversation history
- `/exit` - Exit the session

## Auto-Approve Mode (YOLO)

For faster workflows, enable auto-approve mode:

```bash
# From CLI
kai -y

# Or use the flag
kai --yes
```

In this mode, the agent won't ask for confirmation before:
- Reading files
- Writing files
- Executing commands

**Warning**: Use with caution in production environments!

## Headless Mode

Run single prompts without interactive mode:

```bash
# Single prompt
kai -p "Create a hello world Python script"

# From stdin
echo "Add error handling to main.py" | kai -p

# Get JSON output
kai -p "List all functions in this project" --output-format json
```

## Understanding Permissions

Kai Code has a permission system to control what the agent can do:

### Permission Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `default` | Asks for approval on sensitive operations | Normal development |
| `acceptEdits` | Only asks for command execution | Trusted file editing |
| `plan` | Read-only, no modifications | Safe exploration |
| `bypassPermissions` | No restrictions (YOLO) | Fast iteration |

```bash
# Start in plan mode (read-only)
kai --permission-mode plan

# Start in YOLO mode
kai --yolo
```

### Tool Filtering

Limit which tools the agent can use:

```bash
# Only allow reading operations
kai --tools "ls,read_file,glob,grep"

# Disable certain commands
kai --disallowed-commands "rm *,git push"
```

## Session Management

### Named Sessions

Create separate sessions for different tasks:

```bash
# Create a session for a specific feature
kai --agent feature-auth

# Continue working on it later
kai --agent feature-auth
```

### Starting Fresh

```bash
# New session (clears history)
kai --new
```

### Resume Interrupted Work

If a session is interrupted (HITL approval needed):

```bash
# Check the pending action and approve
kai resume --continue --approve

# Or reject the pending action
kai resume --continue --reject
```

## Configuration Files

Kai Code uses a hierarchy of configuration files:

### 1. Global Settings (`~/.kai/settings.json`)

```json
{
  "model": "openai:gpt-4o",
  "permission_mode": "default"
}
```

### 2. Project Settings (`<project>/.kai/settings.json`)

```json
{
  "model": "anthropic:claude-3-sonnet",
  "allowed_commands": ["python *", "pytest *", "git *"]
}
```

### 3. Local Settings (`<project>/.kai/settings.local.json`)

Personal overrides (don't commit this):

```json
{
  "yolo": true
}
```

## What's Next?

Now that you've got the basics:

1. **[dbt Agent Tutorial](dbt-agent.md)** - Learn data engineering with kai-dbt
2. **[Configuration Guide](../guides/configuration.md)** - Deep dive into settings
3. **[Custom Agents Guide](../guides/custom-agents.md)** - Create your own agents
4. **[Ralph Wiggum Guide](../guides/ralph-wiggum.md)** - Autonomous task loops

## Troubleshooting

### "No API key found"

Make sure you've set your API key:

```bash
export OPENAI_API_KEY=your-key-here
# or create a .env file
```

### "Model not found"

Check your model name format:

```bash
# Correct formats
kai --model openai:gpt-4o
kai --model anthropic:claude-3-sonnet
kai --model google:gemini-pro
```

### "Permission denied" for file operations

Either:
1. Run with `-y` or `--yolo` for auto-approve
2. Or approve when prompted

### Session state issues

Clear and start fresh:

```bash
kai --new
```

Or remove the session file:

```bash
rm -rf .kai/session.json
```
