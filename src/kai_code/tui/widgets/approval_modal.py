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
