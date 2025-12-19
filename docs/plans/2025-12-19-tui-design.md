# kai-code Interactive TUI Design

## Overview

Interactive terminal UI for kai-code, providing a letta-code-like experience with live streaming, tool visualization, and HITL approval workflows.

## Framework

**Textual** - Modern Python TUI framework with reactive components, already in dependencies.

## Architecture

```
kai_code/tui/
├── __init__.py
├── app.py              # Main TUI application class
├── screens/
│   ├── main.py         # Primary chat screen (split layout)
│   └── welcome.py      # Initial welcome/setup screen
├── widgets/
│   ├── message_list.py # Scrollable message history
│   ├── input_area.py   # Multi-line input with slash commands
│   ├── tool_panel.py   # Right-side tool status/preview
│   ├── status_bar.py   # Top bar (model, session, tokens)
│   └── approval_modal.py # HITL approval overlay
├── components/
│   ├── message.py      # Individual message rendering
│   ├── code_block.py   # Syntax-highlighted code
│   ├── diff_view.py    # File diff rendering
│   └── tool_result.py  # Tool output formatting
└── commands.py         # Slash command registry & handlers
```

**Entry Point**: `kai-code --interactive` or `kai-code -i`

## Layout

Split view (65% / 35%):

```
┌──────────────────────────────────────────────────────────────────┐
│ [kai-code] model: gemini-2.0-flash │ session: default │ 1.2k tok │
├─────────────────────────────────────┬────────────────────────────┤
│                                     │ Tool Status                │
│  Message History                    ├────────────────────────────┤
│                                     │ ● execute                  │
│  ┌─ User ──────────────────────┐   │   command: pytest tests/   │
│  │ Run the tests and fix any   │   │   elapsed: 2.3s            │
│  │ failures                    │   │   status: running...       │
│  └─────────────────────────────┘   │                            │
│                                     ├────────────────────────────┤
│  ┌─ Assistant ─────────────────┐   │ Output Preview             │
│  │ I'll run pytest now...      │   │ ──────────────────────     │
│  │ █ (streaming)               │   │ PASSED test_cli.py::test1  │
│  └─────────────────────────────┘   │ PASSED test_cli.py::test2  │
│                                     │ FAILED test_api.py::test3  │
│  (scrollable)                       │ ...                        │
├─────────────────────────────────────┴────────────────────────────┤
│ > Type a message... (/help for commands)                     [vi]│
└──────────────────────────────────────────────────────────────────┘
```

### Status Bar
- App branding: `[kai-code]`
- YOLO badge when active
- Current model
- Session name
- Token usage

### Message History
- Scrollable with j/k or arrow keys
- User messages, assistant responses, tool calls/results
- Syntax-highlighted code blocks
- Colored diff rendering

### Tool Panel
- When idle: Quick stats (session info, token count, last tool)
- When tool running: Live tool name, arguments, elapsed time
- When tool complete: Result preview, exit code for `execute`
- File diffs shown inline with syntax highlighting

### Input Area
- Multi-line support with Shift+Enter
- Vim mode indicator
- Slash command autocomplete on `/`

## Data Flow

```
User Input → KaiAgent.stream() → Stream Events → TUI Updates
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              Message Delta      Tool Call          Tool Result
                    │                  │                  │
                    ▼                  ▼                  ▼
              Update Message     Update Tool        Update Tool
              List (append)      Panel (live)       Panel (result)
                                       │
                              [if HITL & sensitive]
                                       ▼
                              Show Approval Modal
```

### Streaming
- Chunk-buffered display (natural LLM token chunks)
- Subtle cursor/spinner indicates "still typing"
- YOLO mode: uninterrupted streaming
- HITL mode: pauses for approval on sensitive tools

## Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/model <name>` | Switch model |
| `/clear` | Clear conversation history |
| `/exit` | Exit TUI (aliases: `/quit`, `/q`) |
| `/agent <name>` | Switch named agent |
| `/swap <name>` | Alias for `/agent` |
| `/toolset <name>` | Change toolset (codex/default/gemini) |
| `/yolo` | Toggle YOLO mode on/off |
| `/session` | Show current session info |
| `/save` | Force save current session |

## Approval Modal

```
┌─────────────────────────────────────────────────────────────┐
│                  ⚠️  Approval Required                       │
├─────────────────────────────────────────────────────────────┤
│  Tool:  execute                                             │
│                                                             │
│  ┌─ Arguments ────────────────────────────────────────────┐ │
│  │  command: rm -rf ./dist && npm run build               │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Context ──────────────────────────────────────────────┐ │
│  │  This will delete the dist folder and rebuild.         │ │
│  │  Working directory: /Users/you/project                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│         [A]pprove    [R]eject    [E]dit    [Esc] Cancel    │
└─────────────────────────────────────────────────────────────┘
```

### Keyboard Shortcuts
- `a` or `Enter` → Approve and continue
- `r` → Reject (agent receives rejection message)
- `e` → Open edit dialog to modify arguments
- `Esc` → Cancel (same as reject)

### Tool-Specific Display
- `execute`: Command, working directory
- `write_file`: File path, content preview
- `edit_file`: File path, old/new string diff
- `apply_patch`: Diff with syntax highlighting

## Keyboard Navigation

Vim-inspired bindings:
- `j/k` or arrows: Scroll message history
- `Ctrl+C`: Interrupt/cancel current operation
- `Enter`: Send message (in input area)
- `Shift+Enter`: Multi-line input
- `/`: Start slash command
- `Esc`: Cancel/close dialogs
- `q`: Quit (with confirmation)

## Error Handling

| Error Type | Display Location | Behavior |
|------------|------------------|----------|
| Network/API error | Message area (red box) | Show retry option |
| Model error | Message area | Show error, allow new input |
| Tool execution failure | Tool panel (red) | Show exit code, stderr |
| Invalid slash command | Input area hint | Show suggestion |
| Session load failure | Welcome screen | Offer to start fresh |

### Graceful Degradation
- Streaming failure: Show partial content + error
- Tool panel failure: Log to debug, don't crash
- Session save failure: Warning in status bar, auto-retry

### Interrupt Handling
- `Ctrl+C` during streaming: Cancel gracefully
- `Ctrl+C` at idle: Prompt "Exit kai-code? (y/n)"
- `Ctrl+C` in modal: Close modal

## Testing Strategy

### Unit Tests (`tests/tui/`)
- `test_message_list.py` - Message rendering, scrolling
- `test_tool_panel.py` - Tool status updates
- `test_input_area.py` - Input handling, slash commands
- `test_approval_modal.py` - Modal behavior, shortcuts
- `test_commands.py` - Slash command execution

### Integration Tests
- `test_tui_streaming.py` - Full message flow with mock
- `test_tui_hitl.py` - Approval workflow end-to-end
- `test_tui_yolo.py` - YOLO mode without interrupts
- `test_tui_commands.py` - Slash commands affecting state

### Textual Testing
```python
async def test_send_message():
    async with KaiCodeApp().run_test() as pilot:
        await pilot.type("Hello world")
        await pilot.press("enter")
        assert "Hello world" in pilot.app.message_list.content
```

## Integration Points

- Reuses `KaiAgent` for all agent operations
- Reuses `KaiLocalBackend` for tool execution
- TUI wraps `agent.stream()` for live updates
- Session state uses same `.kai/session.json`
