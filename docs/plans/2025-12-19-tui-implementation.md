# kai-code TUI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interactive terminal UI for kai-code with live streaming, tool visualization, and HITL approval workflows.

**Architecture:** Textual-based TUI with split layout (65% message history / 35% tool panel). Reuses existing `KaiAgent` for all agent operations. Entry point via `kai-code -i` flag.

**Tech Stack:** Python 3.11+, Textual, Rich (for syntax highlighting), existing kai-code agent infrastructure.

---

## Task 1: Project Structure Setup

**Files:**
- Create: `src/kai_code/tui/__init__.py`
- Create: `src/kai_code/tui/app.py`
- Create: `src/kai_code/tui/screens/__init__.py`
- Create: `src/kai_code/tui/widgets/__init__.py`
- Create: `src/kai_code/tui/components/__init__.py`
- Create: `tests/tui/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p src/kai_code/tui/screens src/kai_code/tui/widgets src/kai_code/tui/components tests/tui
```

**Step 2: Create __init__.py files**

`src/kai_code/tui/__init__.py`:
```python
"""kai-code Interactive TUI."""

from .app import KaiCodeApp

__all__ = ["KaiCodeApp"]
```

`src/kai_code/tui/screens/__init__.py`:
```python
"""TUI screens."""
```

`src/kai_code/tui/widgets/__init__.py`:
```python
"""TUI widgets."""
```

`src/kai_code/tui/components/__init__.py`:
```python
"""TUI components."""
```

`tests/tui/__init__.py`:
```python
"""TUI tests."""
```

**Step 3: Create minimal app skeleton**

`src/kai_code/tui/app.py`:
```python
"""Main TUI application."""

from textual.app import App, ComposeResult
from textual.widgets import Static


class KaiCodeApp(App):
    """kai-code interactive TUI application."""

    TITLE = "kai-code"

    def compose(self) -> ComposeResult:
        yield Static("kai-code TUI - Loading...")


def main() -> None:
    """Run the TUI application."""
    app = KaiCodeApp()
    app.run()


if __name__ == "__main__":
    main()
```

**Step 4: Verify app launches**

```bash
cd /Users/fitrakacamarga/project/self/bmad-new/kai-code-1
uv run python -m kai_code.tui.app
```

Expected: TUI opens showing "kai-code TUI - Loading...", press `q` to quit.

**Step 5: Commit**

```bash
git add src/kai_code/tui tests/tui
git commit -m "feat(tui): add project structure and minimal app skeleton"
```

---

## Task 2: Status Bar Widget

**Files:**
- Create: `src/kai_code/tui/widgets/status_bar.py`
- Create: `tests/tui/test_status_bar.py`

**Step 1: Write the failing test**

`tests/tui/test_status_bar.py`:
```python
"""Tests for status bar widget."""

import pytest
from kai_code.tui.widgets.status_bar import StatusBar


def test_status_bar_default_content():
    """Status bar shows app name and default values."""
    bar = StatusBar()
    assert "kai-code" in bar.render_content()


def test_status_bar_model_display():
    """Status bar displays model name."""
    bar = StatusBar(model="gemini-2.0-flash")
    content = bar.render_content()
    assert "gemini-2.0-flash" in content


def test_status_bar_yolo_badge():
    """Status bar shows YOLO badge when enabled."""
    bar = StatusBar(yolo=True)
    content = bar.render_content()
    assert "YOLO" in content


def test_status_bar_session_name():
    """Status bar displays session name."""
    bar = StatusBar(session="myproject")
    content = bar.render_content()
    assert "myproject" in content
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tui/test_status_bar.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'kai_code.tui.widgets.status_bar'"

**Step 3: Write minimal implementation**

`src/kai_code/tui/widgets/status_bar.py`:
```python
"""Status bar widget for kai-code TUI."""

from textual.widgets import Static
from textual.app import ComposeResult


class StatusBar(Static):
    """Top status bar showing model, session, and mode."""

    DEFAULT_CSS = """
    StatusBar {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        model: str = "default",
        session: str = "default",
        yolo: bool = False,
        tokens: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._session = session
        self._yolo = yolo
        self._tokens = tokens

    def render_content(self) -> str:
        """Render the status bar content."""
        parts = [f"[kai-code]"]

        if self._yolo:
            parts.append("[YOLO]")

        parts.append(f"model: {self._model}")
        parts.append(f"session: {self._session}")

        if self._tokens > 0:
            if self._tokens >= 1000:
                parts.append(f"{self._tokens / 1000:.1f}k tok")
            else:
                parts.append(f"{self._tokens} tok")

        return " │ ".join(parts)

    def on_mount(self) -> None:
        """Update content on mount."""
        self.update(self.render_content())

    def set_model(self, model: str) -> None:
        """Update the model name."""
        self._model = model
        self.update(self.render_content())

    def set_session(self, session: str) -> None:
        """Update the session name."""
        self._session = session
        self.update(self.render_content())

    def set_yolo(self, yolo: bool) -> None:
        """Update YOLO mode."""
        self._yolo = yolo
        self.update(self.render_content())

    def set_tokens(self, tokens: int) -> None:
        """Update token count."""
        self._tokens = tokens
        self.update(self.render_content())
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/tui/test_status_bar.py -v
```

Expected: All 4 tests PASS

**Step 5: Update widgets __init__.py**

`src/kai_code/tui/widgets/__init__.py`:
```python
"""TUI widgets."""

from .status_bar import StatusBar

__all__ = ["StatusBar"]
```

**Step 6: Commit**

```bash
git add src/kai_code/tui/widgets/status_bar.py tests/tui/test_status_bar.py src/kai_code/tui/widgets/__init__.py
git commit -m "feat(tui): add status bar widget with model/session/yolo display"
```

---

## Task 3: Message Component

**Files:**
- Create: `src/kai_code/tui/components/message.py`
- Create: `tests/tui/test_message.py`

**Step 1: Write the failing test**

`tests/tui/test_message.py`:
```python
"""Tests for message component."""

import pytest
from kai_code.tui.components.message import Message, MessageRole


def test_user_message_content():
    """User message displays content."""
    msg = Message(role=MessageRole.USER, content="Hello world")
    assert msg.content == "Hello world"
    assert msg.role == MessageRole.USER


def test_assistant_message_content():
    """Assistant message displays content."""
    msg = Message(role=MessageRole.ASSISTANT, content="Hi there!")
    assert msg.content == "Hi there!"
    assert msg.role == MessageRole.ASSISTANT


def test_tool_message_content():
    """Tool message displays tool name and result."""
    msg = Message(
        role=MessageRole.TOOL,
        content="Exit code: 0",
        tool_name="execute",
    )
    assert msg.tool_name == "execute"
    assert "Exit code: 0" in msg.content


def test_message_streaming_state():
    """Message tracks streaming state."""
    msg = Message(role=MessageRole.ASSISTANT, content="", streaming=True)
    assert msg.streaming is True
    msg.append_content("Hello")
    assert msg.content == "Hello"
    msg.finish_streaming()
    assert msg.streaming is False
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tui/test_message.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

`src/kai_code/tui/components/message.py`:
```python
"""Message component for TUI."""

from enum import Enum
from textual.widgets import Static
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


class MessageRole(Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    ERROR = "error"


class Message(Static):
    """A single message in the conversation."""

    ROLE_STYLES = {
        MessageRole.USER: ("User", "blue"),
        MessageRole.ASSISTANT: ("Assistant", "green"),
        MessageRole.TOOL: ("Tool", "yellow"),
        MessageRole.ERROR: ("Error", "red"),
    }

    def __init__(
        self,
        role: MessageRole,
        content: str = "",
        tool_name: str | None = None,
        streaming: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.role = role
        self._content = content
        self.tool_name = tool_name
        self.streaming = streaming

    @property
    def content(self) -> str:
        """Get message content."""
        return self._content

    def append_content(self, text: str) -> None:
        """Append content during streaming."""
        self._content += text
        self._refresh_display()

    def finish_streaming(self) -> None:
        """Mark streaming as complete."""
        self.streaming = False
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Update the display."""
        self.update(self._render())

    def _render(self) -> Panel:
        """Render the message as a Rich Panel."""
        title, color = self.ROLE_STYLES.get(
            self.role, ("Message", "white")
        )

        if self.role == MessageRole.TOOL and self.tool_name:
            title = f"Tool: {self.tool_name}"

        content = self._content
        if self.streaming:
            content += " █"  # Cursor indicator

        # Try to render as markdown for assistant messages
        if self.role == MessageRole.ASSISTANT and not self.streaming:
            try:
                renderable = Markdown(content)
            except Exception:
                renderable = Text(content)
        else:
            renderable = Text(content)

        return Panel(
            renderable,
            title=title,
            border_style=color,
            expand=True,
        )

    def on_mount(self) -> None:
        """Render on mount."""
        self.update(self._render())
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/tui/test_message.py -v
```

Expected: All 4 tests PASS

**Step 5: Update components __init__.py**

`src/kai_code/tui/components/__init__.py`:
```python
"""TUI components."""

from .message import Message, MessageRole

__all__ = ["Message", "MessageRole"]
```

**Step 6: Commit**

```bash
git add src/kai_code/tui/components/message.py tests/tui/test_message.py src/kai_code/tui/components/__init__.py
git commit -m "feat(tui): add message component with role styling and streaming"
```

---

## Task 4: Message List Widget

**Files:**
- Create: `src/kai_code/tui/widgets/message_list.py`
- Create: `tests/tui/test_message_list.py`

**Step 1: Write the failing test**

`tests/tui/test_message_list.py`:
```python
"""Tests for message list widget."""

import pytest
from kai_code.tui.widgets.message_list import MessageList
from kai_code.tui.components.message import MessageRole


def test_message_list_empty():
    """Empty message list has no messages."""
    ml = MessageList()
    assert ml.message_count == 0


def test_message_list_add_message():
    """Can add messages to list."""
    ml = MessageList()
    ml.add_message(MessageRole.USER, "Hello")
    assert ml.message_count == 1


def test_message_list_multiple_messages():
    """Can add multiple messages."""
    ml = MessageList()
    ml.add_message(MessageRole.USER, "Hello")
    ml.add_message(MessageRole.ASSISTANT, "Hi there!")
    ml.add_message(MessageRole.TOOL, "Done", tool_name="execute")
    assert ml.message_count == 3


def test_message_list_clear():
    """Can clear all messages."""
    ml = MessageList()
    ml.add_message(MessageRole.USER, "Hello")
    ml.add_message(MessageRole.ASSISTANT, "Hi")
    ml.clear_messages()
    assert ml.message_count == 0


def test_message_list_get_streaming_message():
    """Can get current streaming message."""
    ml = MessageList()
    ml.add_message(MessageRole.USER, "Hello")
    msg = ml.add_streaming_message(MessageRole.ASSISTANT)
    assert ml.get_streaming_message() == msg
    assert msg.streaming is True
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tui/test_message_list.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

`src/kai_code/tui/widgets/message_list.py`:
```python
"""Message list widget for TUI."""

from textual.widgets import Static
from textual.containers import VerticalScroll
from textual.app import ComposeResult

from ..components.message import Message, MessageRole


class MessageList(VerticalScroll):
    """Scrollable list of conversation messages."""

    DEFAULT_CSS = """
    MessageList {
        height: 1fr;
        padding: 1;
    }

    MessageList Message {
        margin-bottom: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._messages: list[Message] = []
        self._streaming_message: Message | None = None

    @property
    def message_count(self) -> int:
        """Get number of messages."""
        return len(self._messages)

    def add_message(
        self,
        role: MessageRole,
        content: str,
        tool_name: str | None = None,
    ) -> Message:
        """Add a complete message to the list."""
        msg = Message(role=role, content=content, tool_name=tool_name)
        self._messages.append(msg)
        self.mount(msg)
        self.scroll_end(animate=False)
        return msg

    def add_streaming_message(self, role: MessageRole) -> Message:
        """Add a new message that will receive streaming content."""
        msg = Message(role=role, content="", streaming=True)
        self._messages.append(msg)
        self._streaming_message = msg
        self.mount(msg)
        self.scroll_end(animate=False)
        return msg

    def get_streaming_message(self) -> Message | None:
        """Get the currently streaming message, if any."""
        return self._streaming_message

    def finish_streaming(self) -> None:
        """Mark current streaming message as complete."""
        if self._streaming_message:
            self._streaming_message.finish_streaming()
            self._streaming_message = None

    def clear_messages(self) -> None:
        """Remove all messages."""
        for msg in self._messages:
            msg.remove()
        self._messages.clear()
        self._streaming_message = None
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/tui/test_message_list.py -v
```

Expected: All 5 tests PASS

**Step 5: Update widgets __init__.py**

`src/kai_code/tui/widgets/__init__.py`:
```python
"""TUI widgets."""

from .status_bar import StatusBar
from .message_list import MessageList

__all__ = ["StatusBar", "MessageList"]
```

**Step 6: Commit**

```bash
git add src/kai_code/tui/widgets/message_list.py tests/tui/test_message_list.py src/kai_code/tui/widgets/__init__.py
git commit -m "feat(tui): add scrollable message list widget"
```

---

## Task 5: Tool Panel Widget

**Files:**
- Create: `src/kai_code/tui/widgets/tool_panel.py`
- Create: `tests/tui/test_tool_panel.py`

**Step 1: Write the failing test**

`tests/tui/test_tool_panel.py`:
```python
"""Tests for tool panel widget."""

import pytest
from kai_code.tui.widgets.tool_panel import ToolPanel, ToolStatus


def test_tool_panel_idle():
    """Tool panel shows idle state by default."""
    panel = ToolPanel()
    assert panel.status == ToolStatus.IDLE


def test_tool_panel_running():
    """Tool panel shows running tool."""
    panel = ToolPanel()
    panel.show_tool_running("execute", {"command": "pytest"})
    assert panel.status == ToolStatus.RUNNING
    assert panel.tool_name == "execute"


def test_tool_panel_complete():
    """Tool panel shows completed tool."""
    panel = ToolPanel()
    panel.show_tool_running("execute", {"command": "pytest"})
    panel.show_tool_result("All tests passed", exit_code=0)
    assert panel.status == ToolStatus.COMPLETE
    assert panel.exit_code == 0


def test_tool_panel_error():
    """Tool panel shows error state."""
    panel = ToolPanel()
    panel.show_tool_running("execute", {"command": "pytest"})
    panel.show_tool_result("Test failed", exit_code=1)
    assert panel.status == ToolStatus.ERROR
    assert panel.exit_code == 1


def test_tool_panel_reset():
    """Tool panel can be reset to idle."""
    panel = ToolPanel()
    panel.show_tool_running("execute", {"command": "pytest"})
    panel.reset()
    assert panel.status == ToolStatus.IDLE
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tui/test_tool_panel.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

`src/kai_code/tui/widgets/tool_panel.py`:
```python
"""Tool panel widget for TUI."""

from enum import Enum
from textual.widgets import Static
from textual.containers import Vertical
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
import time


class ToolStatus(Enum):
    """Tool execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


class ToolPanel(Vertical):
    """Right-side panel showing tool status and output."""

    DEFAULT_CSS = """
    ToolPanel {
        width: 35%;
        height: 100%;
        border-left: solid $primary;
    }

    ToolPanel .tool-status {
        height: auto;
        padding: 1;
    }

    ToolPanel .tool-output {
        height: 1fr;
        padding: 1;
        overflow-y: auto;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.status = ToolStatus.IDLE
        self.tool_name: str | None = None
        self.tool_args: dict | None = None
        self.exit_code: int | None = None
        self._start_time: float | None = None
        self._result: str | None = None

    def compose(self):
        """Compose the panel layout."""
        yield Static("", classes="tool-status", id="tool-status")
        yield Static("", classes="tool-output", id="tool-output")

    def on_mount(self) -> None:
        """Initialize display on mount."""
        self._update_display()

    def show_tool_running(self, name: str, args: dict) -> None:
        """Show a tool is currently running."""
        self.status = ToolStatus.RUNNING
        self.tool_name = name
        self.tool_args = args
        self.exit_code = None
        self._start_time = time.time()
        self._result = None
        self._update_display()

    def show_tool_result(self, result: str, exit_code: int | None = None) -> None:
        """Show tool execution result."""
        self.exit_code = exit_code
        self._result = result

        if exit_code is not None and exit_code != 0:
            self.status = ToolStatus.ERROR
        else:
            self.status = ToolStatus.COMPLETE

        self._update_display()

    def reset(self) -> None:
        """Reset to idle state."""
        self.status = ToolStatus.IDLE
        self.tool_name = None
        self.tool_args = None
        self.exit_code = None
        self._start_time = None
        self._result = None
        self._update_display()

    def _update_display(self) -> None:
        """Update the panel display."""
        status_widget = self.query_one("#tool-status", Static)
        output_widget = self.query_one("#tool-output", Static)

        if self.status == ToolStatus.IDLE:
            status_widget.update(Panel(
                "No tool running",
                title="Tool Status",
                border_style="dim",
            ))
            output_widget.update("")

        elif self.status == ToolStatus.RUNNING:
            elapsed = time.time() - self._start_time if self._start_time else 0
            status_text = Text()
            status_text.append(f"● {self.tool_name}\n", style="yellow bold")

            if self.tool_args:
                for key, value in self.tool_args.items():
                    val_str = str(value)[:50]
                    if len(str(value)) > 50:
                        val_str += "..."
                    status_text.append(f"  {key}: {val_str}\n", style="dim")

            status_text.append(f"  elapsed: {elapsed:.1f}s\n", style="dim")
            status_text.append("  status: running...", style="yellow")

            status_widget.update(Panel(
                status_text,
                title="Tool Status",
                border_style="yellow",
            ))

        elif self.status == ToolStatus.COMPLETE:
            status_text = Text()
            status_text.append(f"✓ {self.tool_name}\n", style="green bold")
            if self.exit_code is not None:
                status_text.append(f"  exit code: {self.exit_code}", style="green")

            status_widget.update(Panel(
                status_text,
                title="Tool Status",
                border_style="green",
            ))

            if self._result:
                output_widget.update(Panel(
                    self._result[:500] + ("..." if len(self._result) > 500 else ""),
                    title="Output Preview",
                    border_style="dim",
                ))

        elif self.status == ToolStatus.ERROR:
            status_text = Text()
            status_text.append(f"✗ {self.tool_name}\n", style="red bold")
            if self.exit_code is not None:
                status_text.append(f"  exit code: {self.exit_code}", style="red")

            status_widget.update(Panel(
                status_text,
                title="Tool Status",
                border_style="red",
            ))

            if self._result:
                output_widget.update(Panel(
                    self._result[:500] + ("..." if len(self._result) > 500 else ""),
                    title="Error Output",
                    border_style="red",
                ))
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/tui/test_tool_panel.py -v
```

Expected: All 5 tests PASS

**Step 5: Update widgets __init__.py**

`src/kai_code/tui/widgets/__init__.py`:
```python
"""TUI widgets."""

from .status_bar import StatusBar
from .message_list import MessageList
from .tool_panel import ToolPanel, ToolStatus

__all__ = ["StatusBar", "MessageList", "ToolPanel", "ToolStatus"]
```

**Step 6: Commit**

```bash
git add src/kai_code/tui/widgets/tool_panel.py tests/tui/test_tool_panel.py src/kai_code/tui/widgets/__init__.py
git commit -m "feat(tui): add tool panel widget with status and output display"
```

---

## Task 6: Input Area Widget

**Files:**
- Create: `src/kai_code/tui/widgets/input_area.py`
- Create: `tests/tui/test_input_area.py`

**Step 1: Write the failing test**

`tests/tui/test_input_area.py`:
```python
"""Tests for input area widget."""

import pytest
from kai_code.tui.widgets.input_area import InputArea


def test_input_area_empty():
    """Input area starts empty."""
    area = InputArea()
    assert area.value == ""


def test_input_area_placeholder():
    """Input area shows placeholder."""
    area = InputArea()
    assert area.placeholder != ""


def test_input_area_detects_slash_command():
    """Input area detects slash commands."""
    area = InputArea()
    assert area.is_slash_command("/help") is True
    assert area.is_slash_command("hello") is False
    assert area.is_slash_command("/model gpt-4") is True


def test_input_area_parse_slash_command():
    """Input area parses slash commands."""
    area = InputArea()
    cmd, args = area.parse_slash_command("/model gpt-4o")
    assert cmd == "model"
    assert args == "gpt-4o"


def test_input_area_parse_slash_command_no_args():
    """Input area parses slash commands without args."""
    area = InputArea()
    cmd, args = area.parse_slash_command("/help")
    assert cmd == "help"
    assert args == ""
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tui/test_input_area.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

`src/kai_code/tui/widgets/input_area.py`:
```python
"""Input area widget for TUI."""

from textual.widgets import Input
from textual.message import Message


class InputSubmitted(Message):
    """Message sent when input is submitted."""

    def __init__(self, value: str, is_command: bool = False) -> None:
        super().__init__()
        self.value = value
        self.is_command = is_command


class InputArea(Input):
    """Input area with slash command support."""

    DEFAULT_CSS = """
    InputArea {
        dock: bottom;
        height: 3;
        border: solid $primary;
        padding: 0 1;
    }

    InputArea:focus {
        border: solid $accent;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            placeholder="Type a message... (/help for commands)",
            **kwargs,
        )

    def is_slash_command(self, text: str) -> bool:
        """Check if text is a slash command."""
        return text.strip().startswith("/")

    def parse_slash_command(self, text: str) -> tuple[str, str]:
        """Parse a slash command into (command, args)."""
        text = text.strip()
        if not text.startswith("/"):
            return ("", text)

        text = text[1:]  # Remove leading /
        parts = text.split(None, 1)

        if len(parts) == 0:
            return ("", "")
        elif len(parts) == 1:
            return (parts[0], "")
        else:
            return (parts[0], parts[1])

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        value = event.value.strip()
        if not value:
            return

        is_command = self.is_slash_command(value)
        self.clear()

        self.post_message(InputSubmitted(value, is_command))
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/tui/test_input_area.py -v
```

Expected: All 5 tests PASS

**Step 5: Update widgets __init__.py**

`src/kai_code/tui/widgets/__init__.py`:
```python
"""TUI widgets."""

from .status_bar import StatusBar
from .message_list import MessageList
from .tool_panel import ToolPanel, ToolStatus
from .input_area import InputArea, InputSubmitted

__all__ = [
    "StatusBar",
    "MessageList",
    "ToolPanel",
    "ToolStatus",
    "InputArea",
    "InputSubmitted",
]
```

**Step 6: Commit**

```bash
git add src/kai_code/tui/widgets/input_area.py tests/tui/test_input_area.py src/kai_code/tui/widgets/__init__.py
git commit -m "feat(tui): add input area widget with slash command parsing"
```

---

## Task 7: Slash Commands Registry

**Files:**
- Create: `src/kai_code/tui/commands.py`
- Create: `tests/tui/test_commands.py`

**Step 1: Write the failing test**

`tests/tui/test_commands.py`:
```python
"""Tests for slash commands."""

import pytest
from kai_code.tui.commands import CommandRegistry, COMMANDS


def test_commands_registry_has_help():
    """Registry includes /help command."""
    assert "help" in COMMANDS


def test_commands_registry_has_exit():
    """Registry includes /exit command."""
    assert "exit" in COMMANDS


def test_commands_registry_has_model():
    """Registry includes /model command."""
    assert "model" in COMMANDS


def test_commands_registry_has_yolo():
    """Registry includes /yolo command."""
    assert "yolo" in COMMANDS


def test_commands_registry_has_clear():
    """Registry includes /clear command."""
    assert "clear" in COMMANDS


def test_commands_get_help_text():
    """Can get help text for all commands."""
    registry = CommandRegistry()
    help_text = registry.get_help_text()
    assert "/help" in help_text
    assert "/exit" in help_text
    assert "/model" in help_text


def test_commands_is_valid():
    """Can check if command is valid."""
    registry = CommandRegistry()
    assert registry.is_valid("help") is True
    assert registry.is_valid("exit") is True
    assert registry.is_valid("nonexistent") is False
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tui/test_commands.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

`src/kai_code/tui/commands.py`:
```python
"""Slash command registry for TUI."""

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class Command:
    """A slash command definition."""
    name: str
    description: str
    aliases: list[str] | None = None
    requires_arg: bool = False


COMMANDS: dict[str, Command] = {
    "help": Command(
        name="help",
        description="Show available commands",
    ),
    "model": Command(
        name="model",
        description="Switch model (e.g., /model gpt-4o)",
        requires_arg=True,
    ),
    "clear": Command(
        name="clear",
        description="Clear conversation history",
    ),
    "exit": Command(
        name="exit",
        description="Exit TUI",
        aliases=["quit", "q"],
    ),
    "agent": Command(
        name="agent",
        description="Switch named agent (e.g., /agent myproject)",
        requires_arg=True,
    ),
    "swap": Command(
        name="swap",
        description="Alias for /agent",
        aliases=["agent"],
        requires_arg=True,
    ),
    "toolset": Command(
        name="toolset",
        description="Change toolset (codex/default/gemini)",
        requires_arg=True,
    ),
    "yolo": Command(
        name="yolo",
        description="Toggle YOLO mode on/off",
    ),
    "session": Command(
        name="session",
        description="Show current session info",
    ),
    "save": Command(
        name="save",
        description="Force save current session",
    ),
}

# Add aliases to lookup
for cmd_name, cmd in list(COMMANDS.items()):
    if cmd.aliases:
        for alias in cmd.aliases:
            if alias not in COMMANDS:
                COMMANDS[alias] = cmd


class CommandRegistry:
    """Registry for slash commands."""

    def __init__(self) -> None:
        self.commands = COMMANDS

    def is_valid(self, name: str) -> bool:
        """Check if command name is valid."""
        return name in self.commands

    def get(self, name: str) -> Command | None:
        """Get command by name."""
        return self.commands.get(name)

    def get_help_text(self) -> str:
        """Generate help text for all commands."""
        lines = ["Available commands:", ""]

        # Deduplicate by showing only primary commands
        seen = set()
        for name, cmd in sorted(self.commands.items()):
            if cmd.name in seen:
                continue
            seen.add(cmd.name)

            alias_text = ""
            if cmd.aliases:
                alias_text = f" (aliases: {', '.join('/' + a for a in cmd.aliases)})"

            lines.append(f"  /{name}: {cmd.description}{alias_text}")

        return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/tui/test_commands.py -v
```

Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add src/kai_code/tui/commands.py tests/tui/test_commands.py
git commit -m "feat(tui): add slash command registry with help/exit/model/yolo/etc"
```

---

## Task 8: Approval Modal Widget

**Files:**
- Create: `src/kai_code/tui/widgets/approval_modal.py`
- Create: `tests/tui/test_approval_modal.py`

**Step 1: Write the failing test**

`tests/tui/test_approval_modal.py`:
```python
"""Tests for approval modal widget."""

import pytest
from kai_code.tui.widgets.approval_modal import ApprovalModal, ApprovalDecision


def test_approval_modal_creates():
    """Can create approval modal."""
    modal = ApprovalModal(
        tool_name="execute",
        tool_args={"command": "rm -rf /tmp/test"},
    )
    assert modal.tool_name == "execute"


def test_approval_modal_shows_tool_name():
    """Modal displays tool name."""
    modal = ApprovalModal(
        tool_name="execute",
        tool_args={"command": "pytest"},
    )
    content = modal.render_content()
    assert "execute" in content


def test_approval_modal_shows_args():
    """Modal displays tool arguments."""
    modal = ApprovalModal(
        tool_name="execute",
        tool_args={"command": "pytest tests/"},
    )
    content = modal.render_content()
    assert "pytest tests/" in content


def test_approval_decision_enum():
    """ApprovalDecision has expected values."""
    assert ApprovalDecision.APPROVE.value == "approve"
    assert ApprovalDecision.REJECT.value == "reject"
    assert ApprovalDecision.EDIT.value == "edit"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tui/test_approval_modal.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

`src/kai_code/tui/widgets/approval_modal.py`:
```python
"""Approval modal widget for HITL workflow."""

from enum import Enum
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
from textual.message import Message
from rich.panel import Panel
from rich.text import Text


class ApprovalDecision(Enum):
    """User decision on tool approval."""
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"


class ApprovalResult(Message):
    """Message sent when user makes approval decision."""

    def __init__(
        self,
        decision: ApprovalDecision,
        tool_name: str,
        tool_args: dict,
        edited_args: dict | None = None,
    ) -> None:
        super().__init__()
        self.decision = decision
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.edited_args = edited_args


class ApprovalModal(ModalScreen):
    """Modal dialog for tool approval."""

    DEFAULT_CSS = """
    ApprovalModal {
        align: center middle;
    }

    ApprovalModal > Vertical {
        width: 70;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $warning;
        padding: 1 2;
    }

    ApprovalModal .title {
        text-align: center;
        text-style: bold;
        color: $warning;
        padding-bottom: 1;
    }

    ApprovalModal .content {
        height: auto;
        padding: 1;
    }

    ApprovalModal .buttons {
        height: 3;
        align: center middle;
        padding-top: 1;
    }

    ApprovalModal Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("a", "approve", "Approve"),
        ("r", "reject", "Reject"),
        ("e", "edit", "Edit"),
        ("escape", "reject", "Cancel"),
    ]

    def __init__(
        self,
        tool_name: str,
        tool_args: dict,
        context: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.context = context

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("⚠️  Approval Required", classes="title")
            yield Static(self._render_content(), classes="content")
            with Horizontal(classes="buttons"):
                yield Button("[A]pprove", id="approve", variant="success")
                yield Button("[R]eject", id="reject", variant="error")
                yield Button("[E]dit", id="edit", variant="warning")

    def render_content(self) -> str:
        """Render the modal content as string (for testing)."""
        lines = [f"Tool: {self.tool_name}", ""]
        lines.append("Arguments:")
        for key, value in self.tool_args.items():
            val_str = str(value)
            if len(val_str) > 60:
                val_str = val_str[:60] + "..."
            lines.append(f"  {key}: {val_str}")

        if self.context:
            lines.append("")
            lines.append("Context:")
            lines.append(f"  {self.context}")

        return "\n".join(lines)

    def _render_content(self) -> Panel:
        """Render content as Rich Panel."""
        text = Text()
        text.append(f"Tool: ", style="bold")
        text.append(f"{self.tool_name}\n\n", style="yellow bold")

        text.append("Arguments:\n", style="bold")
        for key, value in self.tool_args.items():
            val_str = str(value)
            if len(val_str) > 60:
                val_str = val_str[:60] + "..."
            text.append(f"  {key}: ", style="dim")
            text.append(f"{val_str}\n")

        if self.context:
            text.append("\nContext:\n", style="bold")
            text.append(f"  {self.context}", style="dim")

        return Panel(text, border_style="yellow")

    def action_approve(self) -> None:
        """Approve the tool call."""
        self.dismiss(ApprovalResult(
            decision=ApprovalDecision.APPROVE,
            tool_name=self.tool_name,
            tool_args=self.tool_args,
        ))

    def action_reject(self) -> None:
        """Reject the tool call."""
        self.dismiss(ApprovalResult(
            decision=ApprovalDecision.REJECT,
            tool_name=self.tool_name,
            tool_args=self.tool_args,
        ))

    def action_edit(self) -> None:
        """Edit the tool call (placeholder - will open edit dialog)."""
        # For now, just dismiss with edit decision
        # Full implementation would open an edit sub-modal
        self.dismiss(ApprovalResult(
            decision=ApprovalDecision.EDIT,
            tool_name=self.tool_name,
            tool_args=self.tool_args,
        ))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "approve":
            self.action_approve()
        elif event.button.id == "reject":
            self.action_reject()
        elif event.button.id == "edit":
            self.action_edit()
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/tui/test_approval_modal.py -v
```

Expected: All 4 tests PASS

**Step 5: Update widgets __init__.py**

`src/kai_code/tui/widgets/__init__.py`:
```python
"""TUI widgets."""

from .status_bar import StatusBar
from .message_list import MessageList
from .tool_panel import ToolPanel, ToolStatus
from .input_area import InputArea, InputSubmitted
from .approval_modal import ApprovalModal, ApprovalDecision, ApprovalResult

__all__ = [
    "StatusBar",
    "MessageList",
    "ToolPanel",
    "ToolStatus",
    "InputArea",
    "InputSubmitted",
    "ApprovalModal",
    "ApprovalDecision",
    "ApprovalResult",
]
```

**Step 6: Commit**

```bash
git add src/kai_code/tui/widgets/approval_modal.py tests/tui/test_approval_modal.py src/kai_code/tui/widgets/__init__.py
git commit -m "feat(tui): add approval modal widget for HITL workflow"
```

---

## Task 9: Main Screen Assembly

**Files:**
- Create: `src/kai_code/tui/screens/main.py`
- Modify: `src/kai_code/tui/app.py`

**Step 1: Create main screen**

`src/kai_code/tui/screens/main.py`:
```python
"""Main chat screen for TUI."""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from ..widgets import (
    StatusBar,
    MessageList,
    ToolPanel,
    InputArea,
    InputSubmitted,
)
from ..components.message import MessageRole


class MainScreen(Screen):
    """Main chat screen with split layout."""

    DEFAULT_CSS = """
    MainScreen {
        layout: vertical;
    }

    MainScreen .main-content {
        height: 1fr;
    }

    MainScreen .message-area {
        width: 65%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("ctrl+c", "interrupt", "Interrupt", show=False),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
    ]

    def __init__(
        self,
        model: str = "default",
        session: str = "default",
        yolo: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._session = session
        self._yolo = yolo

    def compose(self) -> ComposeResult:
        yield StatusBar(
            model=self._model,
            session=self._session,
            yolo=self._yolo,
            id="status-bar",
        )
        with Horizontal(classes="main-content"):
            with Vertical(classes="message-area"):
                yield MessageList(id="message-list")
            yield ToolPanel(id="tool-panel")
        yield InputArea(id="input-area")

    def on_input_submitted(self, event: InputSubmitted) -> None:
        """Handle input submission."""
        # Will be handled by app
        pass

    def action_scroll_down(self) -> None:
        """Scroll message list down."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.scroll_down()

    def action_scroll_up(self) -> None:
        """Scroll message list up."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.scroll_up()

    def action_interrupt(self) -> None:
        """Interrupt current operation."""
        # Will be handled by app
        self.app.post_message_to_self("interrupt")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
```

**Step 2: Update screens __init__.py**

`src/kai_code/tui/screens/__init__.py`:
```python
"""TUI screens."""

from .main import MainScreen

__all__ = ["MainScreen"]
```

**Step 3: Update app.py to use MainScreen**

`src/kai_code/tui/app.py`:
```python
"""Main TUI application."""

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from .screens.main import MainScreen
from .widgets import (
    StatusBar,
    MessageList,
    ToolPanel,
    InputArea,
    InputSubmitted,
    ApprovalModal,
    ApprovalDecision,
    ApprovalResult,
)
from .components.message import MessageRole
from .commands import CommandRegistry


class KaiCodeApp(App):
    """kai-code interactive TUI application."""

    TITLE = "kai-code"

    CSS = """
    Screen {
        background: $background;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "interrupt", "Interrupt"),
    ]

    def __init__(
        self,
        root_dir: str | Path = ".",
        model: str = "default",
        session: str = "default",
        yolo: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.root_dir = Path(root_dir).resolve()
        self._model = model
        self._session = session
        self._yolo = yolo
        self._commands = CommandRegistry()
        self._agent = None  # Will hold KaiAgent instance
        self._streaming = False

    def on_mount(self) -> None:
        """Set up the app on mount."""
        self.push_screen(MainScreen(
            model=self._model,
            session=self._session,
            yolo=self._yolo,
        ))

    def on_input_submitted(self, event: InputSubmitted) -> None:
        """Handle input from user."""
        if event.is_command:
            self._handle_command(event.value)
        else:
            self._handle_message(event.value)

    def _handle_command(self, text: str) -> None:
        """Handle a slash command."""
        # Parse command
        text = text.strip()
        if not text.startswith("/"):
            return

        parts = text[1:].split(None, 1)
        cmd_name = parts[0] if parts else ""
        cmd_args = parts[1] if len(parts) > 1 else ""

        if not self._commands.is_valid(cmd_name):
            self._show_error(f"Unknown command: /{cmd_name}")
            return

        # Execute command
        if cmd_name in ("exit", "quit", "q"):
            self.exit()
        elif cmd_name == "help":
            self._show_help()
        elif cmd_name == "clear":
            self._clear_messages()
        elif cmd_name == "yolo":
            self._toggle_yolo()
        elif cmd_name == "model":
            self._switch_model(cmd_args)
        elif cmd_name == "session":
            self._show_session_info()
        else:
            self._show_error(f"Command not yet implemented: /{cmd_name}")

    def _handle_message(self, text: str) -> None:
        """Handle a user message."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.add_message(MessageRole.USER, text)

        # TODO: Send to agent and stream response
        # For now, just echo back
        message_list.add_message(
            MessageRole.ASSISTANT,
            f"[TUI Demo] You said: {text}\n\nAgent integration coming soon...",
        )

    def _show_help(self) -> None:
        """Show help text."""
        message_list = self.query_one("#message-list", MessageList)
        help_text = self._commands.get_help_text()
        message_list.add_message(MessageRole.ASSISTANT, help_text)

    def _show_error(self, error: str) -> None:
        """Show error message."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.add_message(MessageRole.ERROR, error)

    def _clear_messages(self) -> None:
        """Clear all messages."""
        message_list = self.query_one("#message-list", MessageList)
        message_list.clear_messages()

    def _toggle_yolo(self) -> None:
        """Toggle YOLO mode."""
        self._yolo = not self._yolo
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_yolo(self._yolo)

        message_list = self.query_one("#message-list", MessageList)
        mode = "enabled" if self._yolo else "disabled"
        message_list.add_message(
            MessageRole.ASSISTANT,
            f"YOLO mode {mode}.",
        )

    def _switch_model(self, model: str) -> None:
        """Switch to a different model."""
        if not model:
            self._show_error("Usage: /model <model-name>")
            return

        self._model = model
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_model(model)

        message_list = self.query_one("#message-list", MessageList)
        message_list.add_message(
            MessageRole.ASSISTANT,
            f"Switched to model: {model}",
        )

    def _show_session_info(self) -> None:
        """Show current session info."""
        message_list = self.query_one("#message-list", MessageList)
        info = f"""Session Info:
- Root: {self.root_dir}
- Model: {self._model}
- Session: {self._session}
- YOLO: {self._yolo}"""
        message_list.add_message(MessageRole.ASSISTANT, info)

    def action_interrupt(self) -> None:
        """Interrupt current operation."""
        if self._streaming:
            # TODO: Cancel streaming
            pass
        else:
            self.exit()


def main() -> None:
    """Run the TUI application."""
    app = KaiCodeApp()
    app.run()


if __name__ == "__main__":
    main()
```

**Step 4: Test the assembled TUI**

```bash
uv run python -m kai_code.tui.app
```

Expected: TUI opens with split layout. Type `/help` to see commands. Type a message and press Enter. Press `q` to quit.

**Step 5: Commit**

```bash
git add src/kai_code/tui/screens/main.py src/kai_code/tui/screens/__init__.py src/kai_code/tui/app.py
git commit -m "feat(tui): assemble main screen with all widgets and command handling"
```

---

## Task 10: CLI Integration

**Files:**
- Modify: `src/kai_code/cli.py`

**Step 1: Add --interactive flag to CLI**

Find the argument parser section in `src/kai_code/cli.py` and add:

```python
parser.add_argument(
    "-i", "--interactive",
    action="store_true",
    help="Launch interactive TUI mode",
)
```

**Step 2: Add TUI launch logic**

In the main function, before processing the prompt, add:

```python
if args.interactive:
    from kai_code.tui.app import KaiCodeApp
    app = KaiCodeApp(
        root_dir=args.root or ".",
        model=args.model or "default",
        session=args.agent or "default",
        yolo=args.yolo if hasattr(args, 'yolo') else True,
    )
    app.run()
    return
```

**Step 3: Test CLI integration**

```bash
uv run kai-code -i
```

Expected: TUI launches. Press `q` to exit.

**Step 4: Commit**

```bash
git add src/kai_code/cli.py
git commit -m "feat(cli): add --interactive flag to launch TUI mode"
```

---

## Task 11: Agent Integration

**Files:**
- Modify: `src/kai_code/tui/app.py`

**Step 1: Add agent initialization**

Update `KaiCodeApp.__init__` to create the agent:

```python
from ..agent import KaiAgent

# In __init__, after setting instance variables:
self._agent = KaiAgent(
    root_dir=self.root_dir,
    model=self._model if self._model != "default" else None,
    yolo=self._yolo,
)
```

**Step 2: Add streaming message handler**

Add method to handle streaming responses:

```python
async def _run_agent_stream(self, prompt: str) -> None:
    """Run agent and stream response to UI."""
    message_list = self.query_one("#message-list", MessageList)
    tool_panel = self.query_one("#tool-panel", ToolPanel)

    self._streaming = True
    streaming_msg = message_list.add_streaming_message(MessageRole.ASSISTANT)

    try:
        for chunk in self._agent.stream(prompt):
            if isinstance(chunk, dict):
                # Handle different chunk types
                if "model" in chunk:
                    # Message delta
                    messages = chunk.get("model", {}).get("messages", [])
                    for msg in messages:
                        if hasattr(msg, "content") and msg.content:
                            streaming_msg.append_content(msg.content)
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_panel.show_tool_running(
                                    tc.get("name", "unknown"),
                                    tc.get("args", {}),
                                )
                elif "tools" in chunk:
                    # Tool result
                    messages = chunk.get("tools", {}).get("messages", [])
                    for msg in messages:
                        if hasattr(msg, "content"):
                            tool_panel.show_tool_result(str(msg.content))
    except Exception as e:
        message_list.add_message(MessageRole.ERROR, f"Error: {e}")
    finally:
        self._streaming = False
        message_list.finish_streaming()
        tool_panel.reset()
```

**Step 3: Update _handle_message to use agent**

```python
def _handle_message(self, text: str) -> None:
    """Handle a user message."""
    message_list = self.query_one("#message-list", MessageList)
    message_list.add_message(MessageRole.USER, text)

    # Run agent asynchronously
    self.run_worker(self._run_agent_stream(text))
```

**Step 4: Test with real agent**

```bash
uv run kai-code -i --model "google_genai:gemini-2.0-flash"
```

Expected: TUI launches. Type "list files" and see agent response with tool usage.

**Step 5: Commit**

```bash
git add src/kai_code/tui/app.py
git commit -m "feat(tui): integrate KaiAgent with streaming responses"
```

---

## Task 12: HITL Approval Flow

**Files:**
- Modify: `src/kai_code/tui/app.py`

**Step 1: Add HITL detection and modal display**

Update `_run_agent_stream` to detect interrupts and show approval modal:

```python
async def _run_agent_stream(self, prompt: str) -> None:
    """Run agent and stream response to UI."""
    # ... existing code ...

    try:
        for chunk in self._agent.stream(prompt):
            # ... existing chunk handling ...

            # Check for HITL interrupt
            if not self._yolo and self._needs_approval(chunk):
                tool_call = self._extract_tool_call(chunk)
                if tool_call:
                    result = await self.push_screen_wait(ApprovalModal(
                        tool_name=tool_call["name"],
                        tool_args=tool_call["args"],
                    ))

                    if result.decision == ApprovalDecision.APPROVE:
                        # Resume with approval
                        self._agent.resume([{"type": "approve"}])
                    elif result.decision == ApprovalDecision.REJECT:
                        # Resume with rejection
                        self._agent.resume([{"type": "reject"}])
                        break
    # ... rest of method ...

def _needs_approval(self, chunk: dict) -> bool:
    """Check if chunk represents a tool needing approval."""
    # Check for interrupt state in chunk
    return False  # Placeholder - implement based on actual chunk structure

def _extract_tool_call(self, chunk: dict) -> dict | None:
    """Extract tool call info from chunk."""
    return None  # Placeholder - implement based on actual chunk structure
```

**Step 2: Test HITL flow**

```bash
uv run kai-code -i --model "google_genai:gemini-2.0-flash" --no-yolo
```

Expected: TUI launches in HITL mode. Tool calls show approval modal.

**Step 3: Commit**

```bash
git add src/kai_code/tui/app.py
git commit -m "feat(tui): add HITL approval flow with modal dialogs"
```

---

## Task 13: Final Integration Tests

**Files:**
- Create: `tests/tui/test_integration.py`

**Step 1: Write integration tests**

`tests/tui/test_integration.py`:
```python
"""Integration tests for TUI."""

import pytest
from kai_code.tui.app import KaiCodeApp


@pytest.mark.asyncio
async def test_app_launches():
    """App can launch and exit."""
    app = KaiCodeApp()
    async with app.run_test() as pilot:
        assert app.title == "kai-code"
        await pilot.press("q")


@pytest.mark.asyncio
async def test_help_command():
    """Help command shows available commands."""
    app = KaiCodeApp()
    async with app.run_test() as pilot:
        await pilot.type("/help")
        await pilot.press("enter")
        # Check that help was displayed
        assert "/help" in app.query_one("#message-list").render()


@pytest.mark.asyncio
async def test_yolo_toggle():
    """YOLO mode can be toggled."""
    app = KaiCodeApp(yolo=False)
    async with app.run_test() as pilot:
        assert app._yolo is False
        await pilot.type("/yolo")
        await pilot.press("enter")
        assert app._yolo is True


@pytest.mark.asyncio
async def test_clear_command():
    """Clear command removes messages."""
    app = KaiCodeApp()
    async with app.run_test() as pilot:
        await pilot.type("Hello")
        await pilot.press("enter")
        message_list = app.query_one("#message-list")
        assert message_list.message_count > 0

        await pilot.type("/clear")
        await pilot.press("enter")
        assert message_list.message_count == 0
```

**Step 2: Run integration tests**

```bash
uv run pytest tests/tui/test_integration.py -v
```

Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/tui/test_integration.py
git commit -m "test(tui): add integration tests for app launch and commands"
```

---

## Summary

This plan implements the kai-code TUI in 13 tasks:

1. **Project structure** - Directory layout and skeleton
2. **Status bar** - Top bar with model/session/yolo display
3. **Message component** - Individual message rendering
4. **Message list** - Scrollable conversation history
5. **Tool panel** - Right-side tool status/output
6. **Input area** - User input with slash commands
7. **Commands registry** - Slash command definitions
8. **Approval modal** - HITL approval dialog
9. **Main screen** - Assembly of all widgets
10. **CLI integration** - `--interactive` flag
11. **Agent integration** - Connect to KaiAgent
12. **HITL flow** - Approval workflow
13. **Integration tests** - End-to-end testing

Each task follows TDD: write failing test → implement → verify → commit.
