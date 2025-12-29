# Configuration Guide

This guide covers all configuration options for Kai Code, including settings files, environment variables, and CLI flags.

## Configuration Hierarchy

Kai Code uses a hierarchical configuration system where settings are merged in order of precedence:

```
CLI Flags / Environment Variables  (highest)
    ↓
Local Settings (.kai/settings.local.json)
    ↓
Project Settings (.kai/settings.json)
    ↓
Global Settings (~/.kai/settings.json)  (lowest)
```

Higher precedence sources override lower ones.

## Settings Files

### Global Settings

Location: `~/.kai/settings.json`

Applied to all projects when running `kai` or `kai-dbt`:

```json
{
  "model": "openai:gpt-4o",
  "permission_mode": "default",
  "theme": "dark"
}
```

### Project Settings

Location: `<project>/.kai/settings.json`

Project-specific settings (should be committed to git):

```json
{
  "model": "anthropic:claude-3-sonnet",
  "allowed_commands": ["python *", "pytest *", "git *"],
  "disallowed_commands": ["rm -rf *"],
  "system_prompt_additions": "This is a Django project using PostgreSQL."
}
```

### Local Settings

Location: `<project>/.kai/settings.local.json`

Personal overrides (do NOT commit to git):

```json
{
  "model": "openai:gpt-4o-mini",
  "yolo": true,
  "debug": true
}
```

## Environment Variables

### API Keys

```bash
# OpenAI
export OPENAI_API_KEY=sk-your-key-here

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Google
export GOOGLE_API_KEY=your-google-key-here
```

### Runtime Configuration

```bash
# Override default model
export KAI_MODEL=openai:gpt-4o

# Enable debug mode
export KAI_DEBUG=1

# Set permission mode
export KAI_PERMISSION_MODE=bypassPermissions
```

## CLI Flags

### Common Flags

| Flag | Description | Example |
|------|-------------|---------|
| `-p`, `--prompt` | Execute single prompt | `kai -p "Explain main.py"` |
| `-y`, `--yes` | Auto-approve all actions | `kai -y` |
| `--new` | Start fresh session | `kai --new` |
| `--agent NAME` | Named agent session | `kai --agent feature-x` |
| `--model MODEL` | Override model | `kai --model anthropic:claude-3-opus` |
| `--permission-mode` | Set permission mode | `kai --permission-mode plan` |
| `--yolo` | Same as `--permission-mode bypassPermissions` | `kai --yolo` |
| `--output-format` | Output format | `kai --output-format json` |
| `--dry-run` | Show config without running | `kai --dry-run` |

### Permission Flags

| Flag | Description |
|------|-------------|
| `--allowed-tools` | Comma-separated list of allowed tools |
| `--disallowed-tools` | Comma-separated list of disallowed tools |
| `--allowed-commands` | Glob patterns for allowed shell commands |
| `--disallowed-commands` | Glob patterns for disallowed shell commands |
| `--tools` | Tool enablement filter (what's available) |

### Output Flags

| Flag | Description |
|------|-------------|
| `--output-format text` | Human-readable output (default) |
| `--output-format json` | JSON output |
| `--output-format stream-json` | JSONL streaming output |
| `--include-traceback` | Include tracebacks in JSON errors |
| `--stream-event-types` | Filter streamed event types |

## All Settings Options

### Core Settings

```json
{
  "model": "openai:gpt-4o",           // LLM model to use
  "max_tokens": 4096,                  // Max tokens in response
  "temperature": 0.7,                  // Response randomness (0-1)
  "yolo": false,                       // Auto-approve all actions
  "permission_mode": "default",        // Permission mode
  "debug": false                       // Enable debug output
}
```

### Model Configuration

```json
{
  "model": "openai:gpt-4o",
  "model_config": {
    "api_base": "https://custom-endpoint.com/v1",
    "api_key_env": "CUSTOM_API_KEY",
    "timeout": 60
  }
}
```

### Permission Settings

```json
{
  "permission_mode": "default",
  "allowed_tools": ["ls", "read_file", "glob", "grep"],
  "disallowed_tools": ["execute"],
  "allowed_commands": ["python *", "pytest *", "git *"],
  "disallowed_commands": ["rm -rf *", "sudo *"]
}
```

### Session Settings

```json
{
  "session_dir": ".kai",               // Session storage directory
  "persist_session": true,             // Save session between runs
  "resume_enabled": true               // Allow resuming interrupted sessions
}
```

### UI Settings

```json
{
  "theme": "dark",                     // dark, light, auto
  "show_banner": true,                 // Show ASCII banner on start
  "colors": {
    "primary": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red"
  }
}
```

## Permission Modes

### `default`

Standard mode with human-in-the-loop approvals:
- Asks permission for: `execute`, `write_file`, `edit_file`, `apply_patch`
- Auto-approves: `ls`, `read_file`, `glob`, `grep`

### `acceptEdits`

Trust file edits, approve command execution:
- Asks permission for: `execute`
- Auto-approves: All file operations

### `plan`

Read-only exploration mode:
- Denies: `write_file`, `edit_file`, `apply_patch`, `execute`
- Auto-approves: All read operations

### `bypassPermissions`

Full auto-approve (YOLO mode):
- Auto-approves: Everything

## Tool Configuration

### Tool Enablement vs Permission

**Enablement** (`--tools`): What tools are available for the session
**Permission** (`--allowed-tools`): What tools can run without approval

A tool must be both enabled AND permitted to run automatically.

```bash
# Enable only specific tools
kai --tools "ls,read_file,glob,grep"

# Allow specific tools without approval
kai --allowed-tools "ls,read_file" --permission-mode default
```

### Available Tools

| Tool | Description |
|------|-------------|
| `ls` | List directory contents |
| `read_file` | Read file contents |
| `write_file` | Create/overwrite files |
| `edit_file` | Edit existing files |
| `glob` | Find files by pattern |
| `grep` | Search file contents |
| `execute` | Run shell commands |
| `apply_patch` | Apply diff patches |

## Model Configuration

### Supported Providers

#### OpenAI

```bash
kai --model openai:gpt-4o
kai --model openai:gpt-4o-mini
kai --model openai:gpt-4-turbo
```

#### Anthropic

```bash
kai --model anthropic:claude-3-opus
kai --model anthropic:claude-3-sonnet
kai --model anthropic:claude-3-haiku
```

#### Google

```bash
kai --model google:gemini-pro
kai --model google:gemini-1.5-pro
```

### Custom Endpoints

For Azure OpenAI or other compatible APIs:

```json
{
  "model": "openai:gpt-4",
  "model_config": {
    "api_base": "https://your-resource.openai.azure.com/",
    "api_version": "2024-02-15-preview",
    "api_key_env": "AZURE_OPENAI_API_KEY"
  }
}
```

## Session Management

### Session Storage

Sessions are stored in `.kai/` by default:

```
.kai/
├── session.json        # Current session state
├── checkpoints/        # HITL checkpoints
└── settings.local.json # Local settings
```

### Named Sessions

Create isolated sessions for different tasks:

```bash
# Create/resume named session
kai --agent feature-auth

# Different agent for different feature
kai --agent feature-payment
```

### Clearing Sessions

```bash
# Start fresh
kai --new

# Or manually
rm -rf .kai/session.json
```

## Debugging

### Enable Debug Mode

```bash
# Via CLI
kai --debug

# Via environment
export KAI_DEBUG=1

# Via settings
{"debug": true}
```

### Debug Output

Debug mode shows:
- Full LLM prompts and responses
- Tool call details
- Permission checks
- Error tracebacks

### Dry Run

Preview configuration without running:

```bash
kai --dry-run --output-format json -p "Test"
```

Shows:
- Resolved settings
- Active model
- Permission mode
- Enabled tools

## Best Practices

### 1. Use Global Settings for Defaults

Set your preferred model and basic settings globally:

```json
// ~/.kai/settings.json
{
  "model": "openai:gpt-4o",
  "permission_mode": "default"
}
```

### 2. Project-Specific Permissions

Lock down permissions in shared projects:

```json
// .kai/settings.json
{
  "allowed_commands": ["python *", "pytest *", "git *"],
  "disallowed_commands": ["rm -rf *"]
}
```

### 3. Personal Overrides in Local Settings

Keep personal preferences out of version control:

```json
// .kai/settings.local.json (add to .gitignore)
{
  "model": "openai:gpt-4o-mini",
  "yolo": true
}
```

### 4. Use Named Agents for Parallel Work

```bash
# Feature work
kai --agent feature-x -p "Implement feature X"

# Bug fix (separate context)
kai --agent bug-123 -p "Fix bug 123"
```

### 5. Read-Only Exploration First

Use plan mode when exploring unfamiliar code:

```bash
kai --permission-mode plan
> Explain the authentication flow in this project
```
