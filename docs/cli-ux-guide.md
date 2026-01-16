# CLI User Experience Guide

## Visual Design

The kai-code CLI uses consistent visual cues to help you understand what's happening at a glance.

### Status Indicators

- **✓** (green) - Success, operation completed
- **⚠️** (amber) - Warning, something needs attention
- **✗** (red) - Error, operation failed
- **⏳** (blue) - Processing, operation in progress
- **ℹ️** (blue) - Information, contextual details

### Color Meanings

- **Green** - Success, completion, auto-approve ON
- **Amber/Orange** - Warning, manual accept mode, token usage at 80%
- **Red** - Error, critical issues, token usage at 95%
- **Blue** - Info, processing, model display
- **Gray** - Dimmed metadata, secondary information
- **Purple** - Agent responses, accents
- **Cyan** - User input, file paths

## Keyboard Shortcuts

### Input Editing

- **Enter** - Send/submit your message
- **Shift+Enter** - Add a new line (multi-line input)
- **Ctrl+E** - Open external editor (nano)
- **Ctrl+J** - Alternative for Shift+Enter (new line)

### Session Control

- **Ctrl+C** (twice) - Exit the CLI
- **ESC** - Interrupt current operation
- **Ctrl+T** - Toggle auto-approve mode
- **Ctrl+B** - Run as background task

### Navigation

- **↑↓** - Navigate input history
- **@** - Auto-complete file paths (injects content)
- **/** - Access commands (/help, /model, /tasks, etc.)

## Status Line

The bottom toolbar shows (left to right):

1. **Auto-approve status** - "auto-accept ON" or "manual accept"
2. **Token usage** - "12K/128K" with color coding
   - Blue: Normal usage
   - Orange: >80% used (warning)
   - Red: >95% used (critical, use /clear)
3. **Model name** - Current AI model
4. **Contextual hints** - Relevant shortcuts
5. **Help** - Type /help for commands

## Multi-line Input

For longer messages, use **Shift+Enter** to add new lines:

```
> Explain the following:
• First concept
• Second concept
• Third concept
[Enter to send, Shift+Enter for more lines]
```

Press **Enter** (without Shift) to send.

## Error Messages

Errors provide actionable guidance:

```
✗ Connection failed
  └─ Suggestion: Check network connection
  └─ Command: kai --test-connection
```

## Environment Variables

- **KAI_ENHANCED_UI=1** - Enable enhanced UI (default)
- **KAI_ENHANCED_UI=0** - Use simpler output
- **KAI_SHOW_TOKENS=1** - Show token usage (default)
- **KAI_SHOW_TOKENS=0** - Hide token display

## Tips

- Use **/clear** to reset context when tokens are high
- Use **/tasks** to check background task progress
- Use **/model** to switch AI models
- Use **@file.py** to inject file content into your message
- Use **!command** for bash mode in single command
