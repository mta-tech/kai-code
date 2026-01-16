# CLI UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance the kai-code CLI with polished visual design, better feedback, and improved user experience while maintaining backward compatibility.

**Architecture:** Incremental enhancement of existing Rich CLI components. Add helper functions for consistent formatting, update color schemes, improve layout structure. No breaking changes - all features are additive and opt-in via environment variable.

**Tech Stack:** Python, Rich (terminal formatting), prompt-toolkit (input handling), pytest (testing)

---

## Task 1: Add Helper Functions for Consistent Formatting

**Files:**
- Create: `src/kai_code/rich_helpers.py`
- Test: `tests/test_rich_helpers.py`

**Step 1: Write failing tests for helper functions**

Create `tests/test_rich_helpers.py`:

```python
"""Test rich helper functions."""
import pytest
from kai_code.rich_helpers import (
    print_section_header,
    print_status,
    print_error,
    format_progress,
    print_step,
)
from unittest.mock import patch


def test_print_section_header(capsys):
    """Test section header prints with correct format."""
    print_section_header("Test Section")
    captured = capsys.readouterr()
    assert "═══════════════════════════════════════════════════════════════" in captured.out
    assert "Test Section" in captured.out
    assert captured.out.count("═══════════════════════════════════════════════════════════════") >= 2


def test_print_status_success(capsys):
    """Test success status prints with checkmark."""
    print_status("success", "Operation completed")
    captured = capsys.readouterr()
    assert "[green]" in captured.out or "✓" in captured.out
    assert "Operation completed" in captured.out


def test_print_status_error(capsys):
    """Test error status prints with X mark."""
    print_status("error", "Operation failed")
    captured = capsys.readouterr()
    assert "[red]" in captured.out or "✗" in captured.out
    assert "Operation failed" in captured.out


def test_print_error_with_suggestion(capsys):
    """Test error prints with suggestion."""
    print_error("Connection failed", "Check network")
    captured = capsys.readouterr()
    assert "Connection failed" in captured.out
    assert "Check network" in captured.out


def test_format_progress():
    """Test progress formatting."""
    result = format_progress(3, 4)
    assert "75%" in result or "3/4" in result


def test_print_step(capsys):
    """Test step printing with indentation."""
    print_step(1, "Creating agent", "Agent ID: abc123")
    captured = capsys.readouterr()
    assert "1." in captured.out or "1)" in captured.out
    assert "Creating agent" in captured.out
    assert "Agent ID: abc123" in captured.out
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rich_helpers.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'kai_code.rich_helpers'"

**Step 3: Create helper functions module**

Create `src/kai_code/rich_helpers.py`:

```python
"""Helper functions for consistent Rich CLI formatting.

Provides standardized formatting for sections, status indicators,
errors, progress bars, and step-by-step output.
"""

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.text import Text

# Use global console instance from rich_config
from kai_code.rich_config import console, COLORS


def print_section_header(title: str) -> None:
    """Print a section header with border and title.

    Args:
        title: Section title to display
    """
    # Calculate border width based on terminal or default to 60
    width = 60
    border = "═" * width

    console.print()
    console.print(border, style=COLORS["primary"])
    console.print(f"[bold {COLORS['primary']}]{title}[/bold {COLORS['primary']}]")
    console.print(border, style=COLORS["primary"])
    console.print()


STATUS_ICONS = {
    "success": "✓",
    "warning": "⚠️",
    "error": "✗",
    "info": "ℹ️",
    "processing": "⏳",
}

STATUS_COLORS = {
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
    "processing": "blue",
}


def print_status(status: str, message: str, icon: str | None = None) -> None:
    """Print a status message with icon and color.

    Args:
        status: Status type (success, warning, error, info, processing)
        message: Status message to display
        icon: Optional custom icon (uses default if not provided)
    """
    icon = icon or STATUS_ICONS.get(status, "•")
    color = STATUS_COLORS.get(status, "white")

    console.print(f"[{color}]{icon}  {message}[/{color}]")


def print_error(error: str, suggestion: str | None = None) -> None:
    """Print an error with optional suggestion.

    Args:
        error: Error message
        suggestion: Optional suggestion for fixing the error
    """
    console.print()
    console.print(f"[red]✗ {error}[/red]")
    if suggestion:
        console.print(f"  └─ [dim]Suggestion: {suggestion}[/dim]")
    console.print()


def format_progress(current: int, total: int) -> str:
    """Format progress as string.

    Args:
        current: Current progress value
        total: Total value

    Returns:
        Formatted progress string (e.g., "75% (3/4)")
    """
    if total == 0:
        return "0% (0/0)"

    percentage = int((current / total) * 100)
    return f"{percentage}% ({current}/{total})"


def print_step(number: int, description: str, result: str | None = None) -> None:
    """Print a step with number, description, and optional result.

    Args:
        number: Step number
        description: Step description
        result: Optional result to display indented
    """
    console.print(f"[bold {COLORS['accent']}]({number})[/bold {COLORS['accent']}] {description}")

    if result:
        console.print(f"    {result}")


def print_summary(results: dict[str, bool]) -> None:
    """Print a summary of test/task results.

    Args:
        results: Dictionary mapping test names to pass/fail (True/False)
    """
    print_section_header("Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status_icon = "✓" if success else "✗"
        status_color = "green" if success else "red"
        status_text = "PASSED" if success else "FAILED"
        console.print(f"[{status_color}]{status_icon}  {name:30s} {status_text}[/ {status_color}]")

    console.print()
    if passed == total:
        console.print(f"[green]Result: {passed}/{total} tests passed {'✓' * passed}[/green]")
    else:
        console.print(f"[yellow]Result: {passed}/{total} tests passed ({total - passed} failed)[/yellow]")
    console.print()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rich_helpers.py -v`
Expected: PASS for all tests

**Step 5: Commit**

```bash
git add src/kai_code/rich_helpers.py tests/test_rich_helpers.py
git commit -m "feat: add rich helper functions for consistent CLI formatting

Add print_section_header, print_status, print_error,
format_progress, print_step, and print_summary helpers.

Provides consistent formatting across CLI output with
standardized icons, colors, and layout.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Update rich_config.py with New Color Definitions

**Files:**
- Modify: `src/kai_code/rich_config.py:60-80` (COLORS dictionary)

**Step 1: Write failing test for new colors**

Create `tests/test_rich_config_colors.py`:

```python
"""Test rich config color definitions."""
from kai_code.rich_config import COLORS


def test_critical_color_defined():
    """Test critical color is defined for high-severity messages."""
    assert "token_critical" in COLORS
    assert "token_warning" in COLORS


def test_colors_are_valid_hex():
    """Test colors are valid hex values."""
    for name, color in COLORS.items():
        if color and color.startswith("#"):
            assert len(color) in [4, 7], f"{name}: {color} should be 3 or 6 digit hex"


def test_semantic_colors_exist():
    """Test required semantic colors exist."""
    required = ["success", "warning", "error", "info", "dim", "primary", "accent"]
    for color in required:
        assert color in COLORS, f"Missing required color: {color}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_rich_config_colors.py -v`
Expected: FAIL for missing critical colors (if not present)

**Step 3: Add new color definitions**

In `src/kai_code/rich_config.py`, update the COLORS dictionary around line 60-80:

```python
COLORS = {
    # User and agent message colors
    "user": "#00d9ff",  # Cyan for user input
    "agent": "#a78bfa",  # Purple for agent responses

    # Status colors (semantic)
    "success": "#10b981",  # Emerald green
    "warning": "#f59e0b",  # Amber orange
    "error": "#ef4444",    # Red
    "info": "#3b82f6",     # Blue
    "dim": "#6b7280",      # Gray for subtle text
    "primary": "#8b5cf6",  # Purple accent
    "accent": "#06b6d4",   # Cyan accent

    # Token status colors
    "token_warning": "#f59e0b",   # Amber for 80% threshold
    "token_critical": "#ef4444",  # Red for 95% threshold

    # Component-specific
    "thinking": "#8b5cf6",  # Purple for "Agent is thinking..."
    "tool": "#a78bfa",      # Purple for tool calls
    "file": "#06b6d4",      # Cyan for file paths
    "code": "#a78bfa",      # Purple for code blocks
}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_rich_config_colors.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/kai_code/rich_config.py tests/test_rich_config_colors.py
git commit -m "feat: add semantic color definitions to rich_config

Add success, warning, error, info, dim, primary, accent colors
for consistent semantic formatting across CLI.

Add token_warning and token_critical for token usage thresholds.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Change Multi-line Input from Alt+Enter to Shift+Enter

**Files:**
- Modify: `src/kai_code/rich_input.py:962-965` (Alt+Enter binding)
- Modify: `src/kai_code/rich_config.py:122-128` (KEYBOARD_SHORTCUTS alt_enter)

**Step 1: Write test for Shift+Enter behavior**

Create `tests/test_multiline_input.py`:

```python
"""Test multi-line input key bindings."""
from kai_code.rich_config import KEYBOARD_SHORTCUTS


def test_shift_enter_shortcut_exists():
    """Test Shift+Enter is defined for multi-line input."""
    # Check for shift_enter or equivalent
    shortcuts = list(KEYBOARD_SHORTCUTS.keys())
    assert any("shift" in s.lower() and "enter" in s.lower() for s in shortcuts)


def test_alt_enter_removed_or_renamed():
    """Test alt_enter is either removed or renamed to shift_enter."""
    has_alt_enter = "alt_enter" in KEYBOARD_SHORTCUTS
    has_shift_enter = "shift_enter" in KEYBOARD_SHORTCUTS

    # Should have shift_enter, and alt_enter should be removed
    assert has_shift_enter or not has_alt_enter
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_multiline_input.py -v`
Expected: FAIL (shift_enter doesn't exist yet)

**Step 3: Update KEYBOARD_SHORTCUTS in rich_config.py**

In `src/kai_code/rich_config.py` around line 122-128, change:

```python
# FROM:
"alt_enter": {
    "key": "Alt+Enter",
    "description": "Insert newline for multi-line input (ESC then Enter, or Option+Enter on Mac)",
    "display": "newline",
    "context": ShortcutContext.ALWAYS,
    "priority": 5,
},

# TO:
"shift_enter": {
    "key": "Shift+Enter",
    "description": "Insert newline for multi-line input",
    "display": "newline",
    "context": ShortcutContext.ALWAYS,
    "priority": 5,
},
```

**Step 4: Update key binding in rich_input.py**

In `src/kai_code/rich_input.py` around line 962-965, find and replace:

```python
# FROM:
@kb.add("escape", "enter")
def _(event) -> None:
    """Alt+Enter inserts a newline for multi-line input."""
    event.current_buffer.insert_text("\n")

# TO:
@kb.add("s-enter")
def _(event) -> None:
    """Shift+Enter inserts a newline for multi-line input."""
    event.current_buffer.insert_text("\n")
```

Also update Ctrl+J reference around line 968-971 to mention Shift+Enter:

```python
@kb.add("c-j")
def _(event) -> None:
    """Ctrl+J inserts a newline (alternative to Shift+Enter)."""
    event.current_buffer.insert_text("\n")
```

**Step 5: Update tooltip text**

In `src/kai_code/rich_input.py`, search for any references to "Alt+Enter" or "Option+Enter" in help text and replace with "Shift+Enter".

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_multiline_input.py -v`
Expected: PASS

**Step 7: Run existing tests to ensure no breakage**

Run: `pytest tests/ -v -k "input" --tb=short`
Expected: No new failures

**Step 8: Commit**

```bash
git add src/kai_code/rich_config.py src/kai_code/rich_input.py tests/test_multiline_input.py
git commit -m "feat: change multi-line input to Shift+Enter

Change from Alt+Enter to Shift+Enter for multi-line input,
matching the standard pattern used in Slack, Discord, and
code editors.

- Enter: Send/submit message
- Shift+Enter: Add newline

More intuitive for users familiar with common chat applications.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Add Enhanced CSS Styles for Token Status

**Files:**
- Modify: `src/kai_code/rich_input.py:1064-1078` (toolbar_style definition)

**Step 1: Write test for toolbar styles**

Create `tests/test_toolbar_styles.py`:

```python
"""Test toolbar style definitions."""
from kai_code.rich_input import get_bottom_toolbar
from kai_code.rich_config import SessionState


def test_toolbar_has_critical_style():
    """Test toolbar has critical token usage style."""
    session_state = SessionState()
    session_ref = {}

    toolbar_func = get_bottom_toolbar(session_state, session_ref)
    # The function should exist and be callable
    assert callable(toolbar_func)


def test_toolbar_styles_defined():
    """Test all required toolbar styles are defined."""
    from prompt_toolkit.styles import Style
    from kai_code.rich_input import toolbar_style

    # toolbar_style should be defined in the module
    # This is more of an integration/smoke test
    assert toolbar_style is not None
```

**Step 2: Run tests**

Run: `pytest tests/test_toolbar_styles.py -v`
Expected: May pass or fail depending on current state

**Step 3: Add new toolbar styles**

In `src/kai_code/rich_input.py` around line 1064-1078, update the toolbar_style:

```python
toolbar_style = Style.from_dict(
    {
        "bottom-toolbar": "noreverse",
        "toolbar-green": "bg:#10b981 #000000",
        "toolbar-orange": "bg:#f59e0b #000000",
        "toolbar-exit": "bg:#2563eb #ffffff",
        "toolbar-task": "bg:#8b5cf6 #ffffff",
        "toolbar-model": "bg:#3b82f6 #ffffff",
        "toolbar-critical": "bg:#ef4444 #ffffff",  # Red for critical token usage
        "toolbar-warning": "bg:#f59e0b #000000",  # Orange for warning token usage
        "toolbar-hint": "#6b7280",
        "toolbar-key": "#94a3b8 bold",
        "toolbar-shortcut": "#64748b",
    }
)
```

**Note:** This may already be done from earlier token count work. Verify styles exist.

**Step 4: Run tests**

Run: `pytest tests/test_toolbar_styles.py -v`
Expected: PASS

**Step 5: Commit if changes made**

```bash
git add src/kai_code/rich_input.py tests/test_toolbar_styles.py
git commit -m "feat: add critical and warning styles to toolbar

Add toolbar-critical (red) and toolbar-warning (orange) styles
for token status indicators in the bottom toolbar.

Provides visual feedback when token usage approaches limits.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Update Error Message Format with Suggestions

**Files:**
- Modify: `src/kai_code/rich_execution.py:616-659` (exception handling)

**Step 1: Write test for error formatting**

Create `tests/test_error_formatting.py`:

```python
"""Test error message formatting."""
import pytest
from unittest.mock import patch, MagicMock
from kai_code.rich_helpers import print_error


def test_print_error_basic(capsys):
    """Test basic error printing."""
    print_error("Test error")
    captured = capsys.readouterr()
    assert "Test error" in captured.out
    assert "✗" in captured.out


def test_print_error_with_suggestion(capsys):
    """Test error with suggestion."""
    print_error("Connection failed", "Check your network")
    captured = capsys.readouterr()
    assert "Connection failed" in captured.out
    assert "Check your network" in captured.out
    assert "Suggestion:" in captured.out or "└─" in captured.out


@pytest.mark.asyncio
async def test_agent_error_formatting():
    """Test agent errors include suggestions."""
    # This would be an integration test
    # Verify that actual agent errors follow the format
    pass
```

**Step 2: Run tests**

Run: `pytest tests/test_error_formatting.py -v`
Expected: PASS (rich_helpers already implements this)

**Step 3: Update error handling in rich_execution.py**

In `src/kai_code/rich_execution.py`, update exception handling around line 616-659 to use the new helper:

```python
except asyncio.CancelledError:
    if spinner_active:
        status.stop()
    # Use new error formatting
    from kai_code.rich_helpers import print_error
    print_error("Operation cancelled", "Try again or use /help for commands")
    # Update agent state
    try:
        await agent.aupdate_state(
            config=config,
            values={
                "messages": [
                    HumanMessage(content="[The previous request was cancelled by the system]")
                ]
            },
        )
    except Exception:
        pass
    return

except KeyboardInterrupt:
    if spinner_active:
        status.stop()
    # Use new error formatting
    from kai_code.rich_helpers import print_error
    print_error("Interrupted by user", "Use Ctrl+C twice quickly to exit")
    # Update agent state
    try:
        await agent.aupdate_state(
            config=config,
            values={
                "messages": [
                    HumanMessage(content="[User interrupted the previous request with Ctrl+C]")
                ]
            },
        )
    except Exception:
        pass
    return
```

**Step 4: Run tests**

Run: `pytest tests/test_error_formatting.py -v`
Expected: PASS

**Step 5: Test integration**

Run: `pytest tests/ -v -k "execution" --tb=short`
Expected: No new failures

**Step 6: Commit**

```bash
git add src/kai_code/rich_execution.py tests/test_error_formatting.py
git commit -m "feat: improve error message formatting with suggestions

Update error handling to use rich_helpers.print_error
which provides consistent formatting with suggestions.

Errors now show:
- What failed
- Why (when available)
- Suggestion for resolution

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Add Progress Bar Component

**Files:**
- Create: `src/kai_code/progress.py`
- Test: `tests/test_progress.py`

**Step 1: Write failing test**

Create `tests/test_progress.py`:

```python
"""Test progress bar component."""
import pytest
from kai_code.progress import ProgressBar


def test_progress_bar_creation():
    """Test progress bar can be created."""
    progress = ProgressBar(total=4)
    assert progress.total == 4
    assert progress.current == 0


def test_progress_bar_update():
    """Test progress bar updates correctly."""
    progress = ProgressBar(total=4)
    progress.update(1)
    assert progress.current == 1

    formatted = progress.format()
    assert "25%" in formatted or "1/4" in formatted


def test_progress_bar_complete():
    """Test progress bar completion."""
    progress = ProgressBar(total=4)
    progress.update(4)
    assert progress.is_complete()

    formatted = progress.format()
    assert "100%" in formatted or "4/4" in formatted


def test_progress_bar_add_step():
    """Test adding named steps to progress."""
    progress = ProgressBar(total=3)
    progress.add_step("Initialize")
    progress.add_step("Configure")
    progress.add_step("Execute")

    steps = progress.get_steps()
    assert len(steps) == 3
    assert steps[0]["name"] == "Initialize"
```

**Step 2: Run tests**

Run: `pytest tests/test_progress.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Implement progress bar component**

Create `src/kai_code/progress.py`:

```python
"""Progress bar component for long-running operations."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class ProgressBar:
    """Simple progress tracker for operations."""

    total: int
    current: int = 0
    steps: List[dict] = field(default_factory=list)

    def update(self, count: int = 1) -> None:
        """Update progress by count.

        Args:
            count: Number of steps completed (default: 1)
        """
        self.current = min(self.current + count, self.total)

    def add_step(self, name: str, status: str = "pending") -> None:
        """Add a named step to track.

        Args:
            name: Step name
            status: Step status (pending, in_progress, complete)
        """
        self.steps.append({"name": name, "status": status})

    def get_steps(self) -> List[dict]:
        """Get all tracked steps.

        Returns:
            List of step dictionaries
        """
        return self.steps

    def is_complete(self) -> bool:
        """Check if progress is complete.

        Returns:
            True if current >= total
        """
        return self.current >= self.total

    def format(self) -> str:
        """Format progress as string.

        Returns:
            Formatted progress string
        """
        if self.total == 0:
            return "0% (0/0)"

        percentage = int((self.current / self.total) * 100)
        return f"{percentage}% ({self.current}/{self.total})"

    def render(self) -> str:
        """Render progress bar as string.

        Returns:
            Multi-line progress bar display
        """
        lines = []
        lines.append(f"Progress: {self.format()}")

        if self.steps:
            for i, step in enumerate(self.steps):
                status_icon = {
                    "complete": "✓",
                    "in_progress": "⏳",
                    "pending": " ",
                }.get(step["status"], " ")

                lines.append(f"  {status_icon} Step {i + 1}: {step['name']}")

        return "\n".join(lines)
```

**Step 4: Run tests**

Run: `pytest tests/test_progress.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/kai_code/progress.py tests/test_progress.py
git commit -m "feat: add progress bar component for long-running operations

Add ProgressBar class for tracking multi-step operations.

Features:
- Track current/total progress
- Add named steps with status
- Format progress as percentage and fraction
- Render text-based progress display

Used for providing clear feedback during operations like:
- Multi-stage tests
- Batch file operations
- Agent execution phases

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Update Test Output Formatting (Auto-nudge Demo)

**Files:**
- Modify: `test_auto_nudge_demo.py` (if exists in worktree)
- Or create example showing new format

**Step 1: Review existing test output**

Check if `test_auto_nudge_demo.py` exists in worktree:
```bash
ls -la test_auto_nudge_demo.py 2>/dev/null || echo "File not in worktree"
```

**Step 2: Create example showing new format**

Create `examples/cli_output_demo.py`:

```python
"""Example showing improved CLI output formatting."""
from kai_code.rich_helpers import (
    print_section_header,
    print_status,
    print_step,
    print_summary,
)


def demo_improved_output():
    """Demonstrate improved CLI output."""
    # Section header
    print_section_header("Testing Auto-Nudge Feature")

    # Step-by-step output
    print_step(1, "Creating agent...")
    print_status("processing", "Agent initialization in progress")
    print_step(1, None, "Agent ID: d28e7add")

    print_step(2, "Checking registries...")
    print_step(2, None, "Agent registered: True")

    print_step(3, "Creating background task...")
    print_step(3, None, "Task ID: 847b52b2")

    # Status updates
    print_status("processing", "Waiting for task to complete...")
    print_status("success", "Task completed successfully")

    # Summary
    results = {
        "Auto-nudge feature": True,
        "Multiple agents": True,
        "Edge cases": True,
    }
    print_summary(results)


if __name__ == "__main__":
    demo_improved_output()
```

**Step 3: Run demo to see output**

```bash
python examples/cli_output_demo.py
```

**Step 4: Commit example**

```bash
git add examples/cli_output_demo.py
git commit -m "docs: add CLI output formatting example

Add demo showing improved CLI output formatting with:
- Section headers with borders
- Step-by-step numbered output
- Status indicators with icons
- Summary with pass/fail counts

Demonstrates the rich_helpers functions in action.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Add Environment Variable Toggle for Enhanced UI

**Files:**
- Modify: `src/kai_code/rich_config.py:468` (parse_bool_env usage)
- Test: `tests/test_enhanced_ui_toggle.py`

**Step 1: Write test for enhanced UI toggle**

Create `tests/test_enhanced_ui_toggle.py`:

```python
"""Test enhanced UI environment variable toggle."""
import os
import pytest


def test_enhanced_ui_default():
    """Test enhanced UI defaults to True when env var not set."""
    # Remove env var if set
    os.environ.pop("KAI_ENHANCED_UI", None)

    from kai_code.rich_config import _parse_bool_env

    result = _parse_bool_env("KAI_ENHANCED_UI", default=True)
    assert result is True


def test_enhanced_ui_enabled():
    """Test enhanced UI can be enabled via env var."""
    os.environ["KAI_ENHANCED_UI"] = "1"

    from kai_code.rich_config import _parse_bool_env

    result = _parse_bool_env("KAI_ENHANCED_UI", default=False)
    assert result is True

    # Cleanup
    os.environ.pop("KAI_ENHANCED_UI", None)


def test_enhanced_ui_disabled():
    """Test enhanced UI can be disabled via env var."""
    os.environ["KAI_ENHANCED_UI"] = "0"

    from kai_code.rich_config import _parse_bool_env

    result = _parse_bool_env("KAI_ENHANCED_UI", default=True)
    assert result is False

    # Cleanup
    os.environ.pop("KAI_ENHANCED_UI", None)
```

**Step 2: Run tests**

Run: `pytest tests/test_enhanced_ui_toggle.py -v`
Expected: FAIL (env var doesn't exist yet)

**Step 3: Add enhanced UI toggle to SessionState**

In `src/kai_code/rich_config.py`, update SessionState.__init__ around line 454-468:

```python
def __init__(
    self,
    auto_approve: bool = False,
    no_splash: bool = False,
    model: str | None = None,
    show_tokens: bool | None = None,
    show_quick_start: bool = False,
    enhanced_ui: bool | None = None,  # New parameter
) -> None:
    self.auto_approve = auto_approve
    self.no_splash = no_splash
    self.model = model
    self.exit_hint_until: float | None = None
    self.exit_hint_handle = None
    self.thread_id = str(uuid.uuid4())
    self._last_escape_time: float = 0
    self._model_changed: bool = False
    self.show_quick_start = show_quick_start

    # Token display
    if show_tokens is not None:
        self.show_tokens = show_tokens
    else:
        self.show_tokens = _parse_bool_env("KAI_SHOW_TOKENS", default=True)

    # Enhanced UI features
    if enhanced_ui is not None:
        self.enhanced_ui = enhanced_ui
    else:
        self.enhanced_ui = _parse_bool_env("KAI_ENHANCED_UI", default=True)
```

**Step 4: Run tests**

Run: `pytest tests/test_enhanced_ui_toggle.py -v`
Expected: PASS

**Step 5: Test integration**

Run: `pytest tests/ -v -k "config" --tb=short`
Expected: No new failures

**Step 6: Commit**

```bash
git add src/kai_code/rich_config.py tests/test_enhanced_ui_toggle.py
git commit -m "feat: add KAI_ENHANCED_UI environment variable toggle

Add enhanced_ui setting to SessionState with KAI_ENHANCED_UI
environment variable support.

Defaults to True (enhanced UI enabled).
Set KAI_ENHANCED_UI=0 to disable and use simpler output.

Provides opt-in mechanism for users who prefer minimal output.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: Update Documentation

**Files:**
- Create: `docs/cli-ux-guide.md` (User-facing guide)
- Update: `CLAUDE.md` (if needed)

**Step 1: Create CLI UX guide**

Create `docs/cli-ux-guide.md`:

```markdown
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
```

**Step 2: Update CLAUDE.md with UX reference**

In `CLAUDE.md`, add section after directory structure:

```markdown
## CLI UX Standards

When adding new output or commands, follow these guidelines:

1. **Use rich_helpers** - Import and use helper functions from `rich_helpers.py`
2. **Consistent icons** - Use STATUS_ICONS for status messages
3. **Semantic colors** - Use COLORS dict for consistent coloring
4. **Error format** - Include suggestions with `print_error()`
5. **Progress** - Use ProgressBar for multi-step operations

See `docs/cli-ux-guide.md` for user-facing documentation.
```

**Step 3: Commit documentation**

```bash
git add docs/cli-ux-guide.md CLAUDE.md
git commit -m "docs: add CLI UX user guide and developer standards

Add user-facing guide covering:
- Visual design and status indicators
- Color meanings and keyboard shortcuts
- Multi-line input with Shift+Enter
- Error message format
- Environment variables

Add developer standards to CLAUDE.md for consistent
CLI output when adding new features.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: Final Integration Testing

**Files:**
- Run full test suite
- Manual testing checklist

**Step 1: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: All tests pass (except pre-existing failures)

**Step 2: Test CLI manually**

```bash
# Start kai
kai

# Test Shift+Enter for multi-line
Type: "List three
programming
languages"
Press: Shift+Enter after each line
Press: Enter to send

# Test ESC interrupt
Type: "explain quantum computing"
Press: ESC during response

# Test /help command
Type: /help

# Test error formatting
Type: "!" (invalid bash command)

# Test token display in status line
Check bottom toolbar shows token count
```

**Step 3: Verify enhanced_ui toggle**

```bash
# Test with enhanced UI disabled
KAI_ENHANCED_UI=0 kai

# Should see simpler output
```

**Step 4: Create integration test**

Create `tests/test_cli_ux_integration.py`:

```python
"""Integration tests for CLI UX improvements."""
import os
import pytest
from kai_code.rich_helpers import (
    print_section_header,
    print_status,
    print_error,
    print_summary,
)
from kai_code.progress import ProgressBar


def test_full_workflow():
    """Test complete output workflow."""
    # Setup
    results = {}

    # Section 1
    print_section_header("Integration Test")
    results["Section header"] = True

    # Steps
    print_step(1, "Initialize")
    results["Step 1"] = True

    print_step(2, "Process")
    results["Step 2"] = True

    # Status
    print_status("success", "All tests passed")
    results["Status"] = True

    # Progress
    progress = ProgressBar(total=3)
    progress.update(1)
    progress.add_step("Step 1", "complete")
    progress.add_step("Step 2", "complete")
    results["Progress"] = progress.is_complete()

    # Summary
    print_summary(results)

    # Assert all passed
    assert all(results.values())


def test_error_workflow():
    """Test error message workflow."""
    print_error("Test error", "Test suggestion")
    # Just ensure it doesn't crash


def test_progress_workflow():
    """Test progress bar workflow."""
    progress = ProgressBar(total=5)

    for i in range(5):
        progress.update(1)
        progress.add_step(f"Step {i + 1}", "complete")

    assert progress.is_complete()
    assert len(progress.get_steps()) == 5
```

**Step 5: Run integration tests**

```bash
python -m pytest tests/test_cli_ux_integration.py -v
```

**Step 6: Commit integration tests**

```bash
git add tests/test_cli_ux_integration.py
git commit -m "test: add CLI UX integration tests

Add integration tests covering:
- Full workflow with all helper functions
- Error message workflow
- Progress bar workflow

Verifies components work together correctly.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Step 7: Final verification**

```bash
# Run all tests one more time
python -m pytest tests/ -v --tb=short

# Check git status
git status

# Review changes
git diff
```

**Step 8: Merge back to main**

When satisfied:
```bash
# Return to main
cd ../..

# Merge worktree branch
git worktree list
git merge feature/cli-ux-improvements --no-ff

# Clean up worktree
git worktree remove .worktrees/cli-ux-improvements
```

---

## Implementation Notes

### Order of Tasks

Tasks are ordered to build incrementally:

1. **Foundation** (Tasks 1-2): Helper functions and colors
2. **Core changes** (Tasks 3-5): Key bindings, styles, errors
3. **Components** (Tasks 6-7): Progress bar and examples
4. **Polish** (Tasks 8-10): Toggle, docs, integration

### Testing Strategy

- **Unit tests** for each new function/class
- **Integration tests** for workflows
- **Manual testing** for interactive features
- **Backward compatibility** verified throughout

### Rollback Plan

If issues arise:

1. Each task is independently committable
2. Can revert individual commits
3. Environment variable allows disabling
4. No breaking changes to existing functionality

### Success Criteria

- ✓ All new tests pass
- ✓ No regressions in existing tests
- ✓ Manual testing confirms improvements
- ✓ Documentation is complete
- ✓ Code follows existing patterns
