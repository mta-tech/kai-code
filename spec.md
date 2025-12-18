# Kai Code (Python) — Spec

## Context

We are building a **Python port** of `letta-code` (a local coding-agent harness), but **implemented on top of** LangChain’s `deepagents`.

`letta-code` (TypeScript) is primarily a CLI harness around a stateful agent system, with:

- A project-resume concept ("last agent for this directory")
- Tooling for local dev workflows (read/search/edit files, run shell, apply patches)
- A `.skills/` directory convention
- Optional tool approval ("yolo" vs approval-required)

This repository (`kai-code-1`) contains the Python library implementation.

## Goals

- Provide a **simple Python API** to run a stateful coding agent against a local project directory.
- Use `deepagents.create_deep_agent()` as the orchestration engine.
- Offer a familiar “coding-agent tool belt”: file browsing, reads, greps, edits, shell execution, and patch application.
- Support a practical default: **YOLO mode** (no human approvals), plus an opt-in “approval required” mode.
- Ship with clear examples + a smoke-test script.

## Parity target (CLI)

This project targets parity with **letta-code headless workflows** (not the Ink TUI).

Minimum parity set to mirror from `letta`:

- `--new` to start fresh
- `--continue` to resume last session
- `--agent <name>` to select a specific session identity
- `-p/--prompt` prompt from args or stdin
- `-m/--model` model selection
- `--toolset {codex,default,gemini}` as a *preset* for default model choice when `--model` is omitted
- `--yolo/--no-yolo` for bypass vs approvals
- `--output-format {text,json,stream-json}`

Phase-2 parity (next):

- **Settings hierarchy** (global/project/local) with precedence and migration.
  - Global: `~/.kai/settings.json`
  - Project: `<root_dir>/.kai/settings.json`
  - Local: `<root_dir>/.kai/settings.local.json`
  - Precedence: CLI/env > local > project > global
  - Local file continues to own per-directory resume state (agent mapping + last session).
- **Permission modes** aligned to letta-code semantics:
  - `default`: approvals (HITL interrupts) for sensitive tools.
  - `acceptEdits`: allow edits/patches without prompts; still approve execution.
  - `plan`: read-only (deny write/edit/patch/execute) for safe planning.
  - `bypassPermissions`: YOLO (allow all, no approvals).
  - `--yolo` is an alias for `--permission-mode bypassPermissions`.
- **Output formatting parity**:
  - `--output-format json`: emit a single JSON object including output, thread_id, state_path, and basic run stats.
  - `--output-format stream-json`: emit JSONL events (`init`, `chunk`, optional `interrupt`, final `result`) plus basic stats.
  - Streaming persistence must be safe: only persist a complete final state when available (avoid saving stream deltas).

Python mapping:

- Letta agent IDs map to **local session files** under `root_dir/.kai/`.
- Per-directory resume is implemented via `root_dir/.kai/settings.local.json`.
- Conversation state lives in `root_dir/.kai/*.json` (messages + thread_id).

## Parity target (Library API)

`letta-code` is primarily a CLI, but it also exposes several modules/functions that are useful as a library.

This Python port mirrors those entrypoints as thin wrappers over the local `KaiAgent` session model:

- `kai_code.headless.handle_headless_command(argv, model=None, skills_directory=None)`
- `kai_code.create.create_agent(...) -> CreateAgentResult`
- `kai_code.modify.update_agent_llm_config(agent, model_handle, update_args=None) -> KaiAgent`
- `kai_code.modify.link_tools_to_agent(agent) -> LinkResult` (no-op locally)
- `kai_code.modify.unlink_tools_from_agent(agent) -> UnlinkResult` (no-op locally)
- `kai_code.client.get_client(root_dir=None) -> KaiClient`
- `kai_code.model.*` helpers (`resolve_model`, `get_default_model`, etc.)

TypeScript-name aliases are provided too (e.g. `resolveModel`, `getClient`, `createAgent`, `handleHeadlessCommand`).

Notes on semantic differences:

- `get_client()` returns a **local** project-bound helper (not a network API client).
- `create_agent()` creates/opens a **local session file** (no server-side memory blocks).
- `update_agent_llm_config()` returns a new wrapper pointing at the same session, but with a different model.

Phase-2 parity (next):

- Provide a Python-visible `PermissionMode` type and make it usable from both CLI and library.
- Provide a settings loader/merger so library entrypoints can respect the same global/project/local defaults as the CLI.

## Non-goals (initial MVP)

- A full TUI like `letta-code`.
- A cloud-hosted stateful agent backend (Letta API parity).
- A perfectly secure sandbox for arbitrary shell commands.

## User-facing API (proposed)

### 1) Create an agent

```py
from kai_code import KaiAgent

agent = KaiAgent(
    root_dir="/path/to/project",
    model="openai:gpt-4o",   # Any LangChain chat model handle supported by init_chat_model
    yolo=True,                # default True
)
```

Key constructor args:

- `root_dir: str | Path` — project root. All filesystem tools are scoped to this directory.
- `model: str | BaseChatModel | None` — model handle or object (defaults to deepagents default).
- `yolo: bool` — if `False`, configure HITL interrupts for sensitive tools.
- `system_prompt: str | None` — appended to deepagents base prompt.
- `skills_dir: str` — default `.skills`.
- `state_path: str | Path | None` — where to persist conversation state (`.kai/session.json` by default).
- `permissions: PermissionConfig | None` — optional allow/deny rules for `execute`, `write_file`, `edit_file`, `apply_patch`.

### 2) Run prompts (headless)

```py
result = agent.run("Add a CLI entrypoint and write usage docs")
print(result.output)
```

`KaiResult`:

- `output: str` — final assistant text.
- `messages: list[dict]` — persisted message history in `{role, content}` form.
- `raw: dict` — raw LangGraph state from deepagents.

### 3) Streaming

```py
for event in agent.stream("Refactor the module layout"):
    ...
```

Streaming yields LangGraph chunks (implementation will expose a minimal wrapper).

### 4) Reset or fork

```py
agent.reset()                 # clear in-memory + persisted conversation
fork = agent.fork(state_path="/tmp/new.json")
```

### 5) HITL resume

When `yolo=False`, the agent may interrupt on sensitive tools. The library persists a stable `thread_id` inside `state_path` so the host can resume.

```py
result = agent.resume([{"type": "approve"}])
```

## Tooling

DeepAgents already provides:

- `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `execute` (if backend supports)

We will add:

- `apply_patch(patch: str) -> str` — apply unified diffs under `root_dir`.

### Tool approvals

If `yolo=False`, configure HITL interrupts for:

- `execute`
- `write_file`
- `edit_file`
- `apply_patch`

In MVP we will wire interrupts, but we’ll keep the public surface small: the library user can run in `yolo=True` by default.

## Project structure

```
.
├─ pyproject.toml
├─ spec.md
├─ README.md
├─ src/kai_code/
│  ├─ __init__.py
│  ├─ agent.py
│  ├─ backend.py
│  ├─ permissions.py
│  ├─ skills.py
│  └─ patching.py
│  └─ smoke.py
└─ examples/
   └─ basic_run.py
```

## Implementation plan

1. **API + UX**
   - Implement `KaiAgent` + `KaiResult`.
   - Default project-local persistence at `root_dir/.kai/session.json`.

2. **DeepAgents integration**
   - Build `KaiLocalBackend` extending `deepagents.backends.FilesystemBackend` and `SandboxBackendProtocol`.
   - Enable `execute` tool by implementing `execute()` with `subprocess.run(..., cwd=root_dir)`.

3. **Patch tool**
   - Implement `apply_patch` with path sanitization and the system `patch` command.

4. **Skills**
   - Discover `.skills/**/SKILL.MD` and inject a concise summary into the system prompt.
   - Keep reading via filesystem tools (no separate registry needed).

5. **Examples + smoke test**
   - Provide `examples/basic_run.py`.
   - Add a small `python -m kai_code.smoke` module that runs a deterministic tool-only check (no LLM call) and validates backend operations.

## Open questions (defer unless required)

- Add a CLI wrapper (`kai`) akin to `letta`? (Likely yes, but not required for the MVP library.)
- Add a richer event model for streaming (tool call events, stdout/stderr separation).
- Add interactive slash commands parity (`/model`, `/clear`, etc.) in a future phase.

---

This spec intentionally targets a **minimal but useful** Python library that can evolve toward `letta-code` parity over time.
