# CLI UX Improvements Design

**Date:** 2025-01-16
**Status:** Design
**Author:** Claude + User Collaboration
**Direction:** Polished Current - Enhance existing style without dramatic changes

## Overview

This document outlines visual and user experience improvements for the kai-code CLI. The focus is on polishing the existing interface with better colors, spacing, structure, and consistency while maintaining familiarity.

## Design Philosophy

**Core Principles:**
- **Consistent semantic coloring** - Specific colors for specific purposes (success, warning, error, info, dim)
- **Visual hierarchy** - Clear distinction between headers, content, and metadata
- **Breathing room** - Proper spacing between sections and elements
- **Scannability** - Users should grasp status at a glance
- **Familiar patterns** - Use conventions users know from other tools

## Color Palette

Enhanced colors with semantic meaning:

```python
Success:  #10b981 (emerald green)  ✓
Warning:  #f59e0b (amber orange)   ⚠️
Error:    #ef4444 (red)             ✗
Info:     #3b82f6 (blue)            ℹ️
Dim:      #6b7280 (gray)            —
Accent:   #8b5cf6 (purple)          ◈
Critical: #ef4444 (red bg)          🔴
```

**Toolbar-specific colors:**
- `toolbar-green`: bg:#10b981 #000000 - auto-accept ON
- `toolbar-orange`: bg:#f59e0b #000000 - manual accept
- `toolbar-critical`: bg:#ef4444 #ffffff - critical token usage
- `toolbar-warning`: bg:#f59e0b #000000 - warning token usage
- `toolbar-model`: bg:#3b82f6 #ffffff - model display

## Typography & Readability

**Font Hierarchy:**
- **Headers**: Bold, primary color, size 14-16px if supported
- **Step numbers**: Bold, accent color, clearly visible
- **User content**: User theme color
- **Agent content**: Agent theme color, markdown rendering
- **Code/paths**: Monospace, subtle background, syntax highlighting
- **Metadata**: Dim by default, brightens on relevant context

**Text Formatting:**
```python
# Success messages
console.print("[green]✓ Operation completed[/green]")

# Error messages
console.print("[red]✗ Failed: {details}[/red]")

# Warnings
console.print("[yellow]⚠️ Warning: {message}[/yellow]")

# Info/dim
console.print("[dim]→ Background info[/dim]")

# File paths
console.print("[dim cyan]path/to/file.py[/dim cyan]")
```

**Spacing Standards:**
- Empty line before each major section
- Empty line after each major section
- 2 spaces indentation for nested content
- Single space between related items
- Extra line before/after code blocks

## Layout Structure

**Section Headers:**
```
═══════════════════════════════════════════════════════════════
Testing Auto-Nudge Feature
═══════════════════════════════════════════════════════════════
```

- Bold title in primary color
- Empty line before and after
- Consistent width based on terminal

**Status Indicators:**
```
✓  Task completed successfully  (green)
⚠️  Warning: context at 80%     (amber)
✗  Command failed               (red)
⏳  Processing...                (blue)
ℹ️  Info message                 (dim gray)
```

**Step-by-Step Output:**
```
1. Creating agent...
   Agent ID: d28e7add

2. Checking registries...
   Agent registered: True

3. Creating background task...
   Task ID: 847b52b2
```

Each step gets:
- Number (bold, colored)
- Description (normal)
- Result (indented, color-coded)

## Status & Feedback System

**Real-time Status Updates:**
```
[⏳] Creating agent...
[⏳] Registering with task manager...
[✓] Agent registered: d28e7add
[⏳] Starting background task...
[✓] Task created: 847b52b2
```

**Completion Summary:**
```
═══════════════════════════════════════════════════════════════
Test Summary
═══════════════════════════════════════════════════════════════
✓ Auto-nudge feature      PASSED
✓ Multiple agents         PASSED
✓ Edge cases              PASSED

Result: 3/3 tests passed ✓✓✓
Duration: 2.3 seconds
```

**Error Messaging:**
```
✗ Connection failed
  └─ Reason: Timeout after 30s
  └─ Suggestion: Check network connection
  └─ Command: kai --test-connection
```

Structure: What failed → Why → What to do

**Progress Bars:**
```
Processing: [━━━━━━━━━━━━━━━━━━━━━━━━] 75% (3/4)
  ✓ Step 1: Initialize
  ✓ Step 2: Configure
  ✓ Step 3: Execute
  ⏳ Step 4: Finalize
```

## Interactive Elements & Shortcuts

**Multi-line Input (Standard Pattern):**

Like Slack, Discord, and code editors:
- **Enter**: Send/submit the message
- **Shift+Enter**: Add a new line (multi-line input)

**Visual indication:**
```
> Type your message (Enter to send, Shift+Enter for new line)
```

When in multi-line mode:
```
multi> This is the first line
multi> This is the second line
multi> [Enter to send, Shift+Enter for more lines]
```

**Keyboard Shortcuts Display:**
```
Keyboard Shortcuts:
  ESC        Interrupt current operation
  Shift+Enter New line in multi-line mode
  Enter       Send/submit message
  Ctrl+C      Double-press to exit
  Ctrl+T      Toggle auto-approve mode
  Ctrl+B      Run as background task

Type /help for more commands
```

**Confirmation Prompts:**
```
⚠️ This will clear 15 messages from context.
Continue? (y/N):
```

- Clear warning symbol + question
- Default to safe option (N)
- Show what will be affected

**Status Line Priority:**

The bottom toolbar shows (in priority order):
1. **Critical state**: Exit hint, bash mode, error state
2. **Session info**: Auto-approve, token count, model
3. **Contextual hints**: Relevant shortcuts for current action
4. **Help hint**: Type /help for commands

Example:
```
[auto-accept ON] [12K/128K tokens] [gpt-4o] [ESC interrupt] [/help]
```

## Implementation Strategy

### Phase 1: Quick Wins (1-2 hours)
- Add CSS styles for new semantic colors (critical, warning)
- Implement section header formatting function
- Add status indicator icons (✓, ✗, ⚠️, ⏳, ℹ️)
- Update error message format
- **Files**: `rich_config.py`, `rich_execution.py`

### Phase 2: Layout Updates (2-3 hours)
- Update test output formatting
- Add progress bar component for long operations
- Implement completion summary format
- Update spacing/indentation standards
- **Files**: `rich_execution.py`, test files

### Phase 3: Interactive Enhancements (2-3 hours)
- **Change multi-line to Shift+Enter** (from Alt+Enter)
- Improve multi-line input indication
- Add confirmation prompt formatting
- Enhance auto-complete hints
- **Files**: `rich_input.py`, `rich_config.py`, `rich_commands.py`

### Phase 4: Polish & Consistency (1-2 hours)
- Audit all output for consistency
- Add typography helper functions
- Ensure accessibility (contrast, color-independent)
- Document standards
- **Files**: All files

### Helper Functions to Create

```python
# rich_helpers.py (new file)
def print_section_header(title: str)
def print_status(status: str, message: str, icon: str = None)
def print_error(error: str, suggestion: str = None)
def print_summary(results: dict)
def format_progress(current: int, total: int)
def print_step(number: int, description: str, result: str = None)
```

## Migration Path

- **No breaking changes**: All enhancements are additive
- **Opt-in via settings**: Add `KAI_ENHANCED_UI=1` env var to toggle
- **Gradual rollout**: Implement per-file, test incrementally
- **Backward compatible**: Old output still works, new features layered on

## Accessibility Considerations

- Minimum contrast ratio: 4.5:1 for text
- Color-independent meaning: Use icons (✓, ✗, ⚠️) with colors
- Avoid color-only distinctions (add symbols/bold)
- Line length: Aim for 80-100 chars max
- Clear typography hierarchy for screen readers

## Related Documentation

- `CLAUDE.md` - Project context
- `src/kai_code/rich_config.py` - Color definitions
- `src/kai_code/rich_input.py` - Keyboard shortcuts
- `src/kai_code/rich_execution.py` - Output formatting
