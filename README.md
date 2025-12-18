# Kai Code (Python)

`kai-code` is a small Python library for running a **local coding agent** against a project directory, built on top of LangChain’s `deepagents`.

This is a Python port *in spirit* of `letta-code`’s developer workflow (tools + project context), but implemented using `deepagents` rather than the Letta API.

## Install

```bash
pip install -e .
```

If you want OpenAI models:

```bash
pip install -e '.[openai]'
export OPENAI_API_KEY=...
```

If you want Gemini models:

```bash
pip install -e '.[google_genai]'
export GOOGLE_API_KEY=...
```

## Usage

```python
from kai_code import KaiAgent

agent = KaiAgent(root_dir=".", model="openai:gpt-4o", yolo=True)
result = agent.run("Summarize this repo and propose a cleanup PR.")
print(result.output)
```

## CLI

`letta-code` parity target is headless workflows; this repo ships a `kai` CLI:

```bash
# prompt from args
kai -p "Summarize this repo"

# prompt from stdin
echo "Summarize this repo" | kai -p

# new session
kai --new -p "Start fresh"

# named agent/session
kai --agent myproj -p "Work on myproj"

# JSON output
kai -p "Hello" --output-format json

# Print resolved config without calling a model
kai --new -p "Hello" --dry-run --output-format json

# Print stream-json schema without calling a model
kai --new -p "Hello" --dry-run --output-format stream-json
```

If you omit `model=...`, `deepagents` will use its default model (Anthropic Claude) and you’ll need the corresponding credentials configured.

By default, conversation state is persisted to `./.kai/session.json` under `root_dir`.

### Settings hierarchy

Kai uses a 3-tier settings hierarchy (highest precedence last):

- Global: `~/.kai/settings.json`
- Project: `<root_dir>/.kai/settings.json`
- Local: `<root_dir>/.kai/settings.local.json`

Precedence: CLI flags/env > local > project > global.

The local file also stores per-directory resume state (`last_session`, and `agents` mappings).

## Permissions

```python
from kai_code import KaiAgent, PermissionConfig

perms = PermissionConfig(
    # allow only a limited tool surface
    allowed_tools=["ls", "read_file", "glob", "grep", "execute", "apply_patch"],
    allowed_commands=["git *", "python *", "pytest *"],
)

agent = KaiAgent(root_dir=".", model="openai:gpt-4o", permissions=perms)
```

## HITL (approvals)

Set `yolo=False` to enable LangGraph human-in-the-loop interrupts for sensitive tools.
`KaiAgent` persists a stable `thread_id` in `./.kai/session.json` so you can resume later.

### Permission modes

The CLI supports letta-style permission modes:

- `default`: approvals for execute + write/edit/apply_patch
- `acceptEdits`: approve execute only
- `plan`: read-only (deny write/edit/patch/execute)
- `bypassPermissions`: YOLO (allow all)

`--yolo` is an alias for `--permission-mode bypassPermissions`.

```python
agent = KaiAgent(root_dir=".", model="openai:gpt-4o", yolo=False)

# If an interrupt happens, resume with decisions:
result = agent.resume([{"type": "approve"}])
print(result.output)
```

### Resuming interrupted runs (CLI)

When the agent is interrupted (exits with code 2), use `kai resume` to continue:

```bash
# Run with HITL enabled (will interrupt on sensitive tool calls)
kai run --permission-mode default -p "Refactor the auth module"
# Exit code 2 indicates interrupt; stderr shows pending tool call details

# Approve and continue
kai resume --approve

# Or reject and skip the pending tool call
kai resume --reject

# Or edit the tool call arguments
kai resume --edit '{"args": {"command": "ls -la"}}'

# Resume a specific named agent
kai resume --approve --agent myagent

# Resume with explicit state path
kai resume --approve --state-path .kai/session.json

# Get JSON output
kai resume --approve --output-format json
```

The resume command reads the session state and checkpoint files created by the interrupted run.
Checkpoints are stored in `.kai/checkpoints.pkl` and require `--permission-mode default` or `acceptEdits` (not `bypassPermissions`).

## Smoke test

```bash
python -m kai_code.smoke
```

## Library parity API

This repo also exports a small set of functions/modules inspired by `letta-code`'s internal entrypoints:

```python
from kai_code import (
    create_agent,
    get_client,
    handle_headless_command,
    resolve_model,
    update_agent_llm_config,
)

client = get_client(root_dir=".")
agent = client.open_agent(model=resolve_model("gpt-4o") or "openai:gpt-4o")

# Create-agent style wrapper
created = create_agent(root_dir=".", model="openai:gpt-4o")

# Switch model (returns a new wrapper pointing at same session)
agent2 = update_agent_llm_config(created.agent, "openai:gpt-4o")

# Headless wrapper (forwards to `kai` CLI implementation)
handle_headless_command(["--new", "-p", "Hello", "--dry-run"])
```

## Notes

- `PermissionConfig` currently gates: `ls`, `read_file`, `glob`, `grep`, `write_file`, `edit_file`, `execute`, and `apply_patch`.
- Shell execution is implemented via `subprocess` and is **not a secure sandbox**.
- Filesystem tools are scoped to `root_dir` using deepagents’ virtual filesystem mode.
- HITL resume uses a local disk-backed checkpointer under `.kai/` so it can survive restarts.

## License

Apache-2.0
