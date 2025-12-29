"""Model selector UI for the Rich CLI."""
from __future__ import annotations

import os
import sys
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED

from .model import models, models_static, ModelInfo, resolve_model, get_default_model

console = Console(highlight=False)

# Colors matching the main CLI
COLORS = {
    "primary": "#10b981",
    "dim": "#6b7280",
    "selected": "#fbbf24",
    "default": "#8b5cf6",
}


def get_available_models(use_static: bool = False) -> list[ModelInfo]:
    """Get list of available models with API key checks.

    Args:
        use_static: If True, use static models only (no API calls)

    Returns:
        List of ModelInfo objects for models that have configured API keys
    """
    # Get models - dynamic from APIs or static fallback
    all_models = models_static() if use_static else models()
    available = []

    for model in all_models:
        provider = model.provider or (model.handle.split(":")[0] if ":" in model.handle else "")

        # Check if API key is configured for this provider
        has_key = False
        if provider == "anthropic":
            has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        elif provider == "openai":
            has_key = bool(os.environ.get("OPENAI_API_KEY"))
        elif provider in ("google_genai", "google"):
            has_key = bool(os.environ.get("GOOGLE_API_KEY"))
        else:
            # Unknown provider - include it anyway
            has_key = True

        if has_key:
            available.append(model)

    return available


def show_model_selector(
    current_model: str | None = None,
    on_select: Callable[[ModelInfo], None] | None = None,
) -> ModelInfo | None:
    """Display an interactive model selector.

    Args:
        current_model: Currently selected model ID or handle
        on_select: Callback when a model is selected

    Returns:
        Selected ModelInfo or None if cancelled
    """
    available = get_available_models()

    if not available:
        console.print()
        console.print("[red]No models available. Configure API keys:[/red]")
        console.print("  ANTHROPIC_API_KEY for Claude models")
        console.print("  OPENAI_API_KEY for GPT models")
        console.print("  GOOGLE_API_KEY for Gemini models")
        console.print()
        return None

    # Find current selection index
    selected_idx = 0
    if current_model:
        for i, model in enumerate(available):
            if model.id == current_model or model.handle == current_model:
                selected_idx = i
                break

    try:
        import termios
        import tty

        # Save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Set terminal to raw mode for key capture
            tty.setcbreak(sys.stdin.fileno())

            while True:
                _render_model_list(available, selected_idx, current_model)

                # Read key
                key = sys.stdin.read(1)

                if key == '\x1b':  # Escape sequence
                    next1 = sys.stdin.read(1)
                    if next1 == '[':
                        next2 = sys.stdin.read(1)
                        if next2 == 'A':  # Up arrow
                            selected_idx = max(0, selected_idx - 1)
                        elif next2 == 'B':  # Down arrow
                            selected_idx = min(len(available) - 1, selected_idx + 1)
                    else:
                        # Plain Escape - cancel
                        console.clear()
                        return None
                elif key == '\r' or key == '\n':  # Enter
                    console.clear()
                    selected = available[selected_idx]
                    if on_select:
                        on_select(selected)
                    return selected
                elif key == 'q':
                    console.clear()
                    return None
                elif key.isdigit():
                    # Quick select by number
                    num = int(key)
                    if 1 <= num <= len(available):
                        selected_idx = num - 1

        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            console.clear()

    except ImportError:
        # Fall back to simple selection on Windows
        return _simple_model_selector(available, current_model)

    return None


def _render_model_list(
    models_list: list[ModelInfo],
    selected_idx: int,
    current_model: str | None = None,
) -> None:
    """Render the model selection list."""
    console.clear()

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Num", style="dim", width=3)
    table.add_column("Select", width=2)
    table.add_column("Model", min_width=20)
    table.add_column("Provider", min_width=30)
    table.add_column("Status", width=12)

    for i, model in enumerate(models_list):
        is_selected = i == selected_idx
        is_current = current_model and (model.id == current_model or model.handle == current_model)
        is_default = model.is_default

        # Number
        num = str(i + 1)

        # Selection indicator
        prefix = ">" if is_selected else " "

        # Model name
        model_name = model.id

        # Provider (extract from handle)
        provider = model.handle

        # Status badges
        status_parts = []
        if is_current:
            status_parts.append("active")
        if is_default:
            status_parts.append("default")
        status = ", ".join(status_parts) if status_parts else ""

        if is_selected:
            table.add_row(
                Text(num, style="bold cyan"),
                Text(prefix, style="bold cyan"),
                Text(model_name, style="bold"),
                Text(provider, style="bold dim"),
                Text(status, style="bold green" if is_current else "bold " + COLORS["default"]),
            )
        else:
            table.add_row(
                Text(num, style="dim"),
                prefix,
                model_name,
                Text(provider, style="dim"),
                Text(status, style="green" if is_current else COLORS["default"]),
            )

    # Help line
    help_text = Text()
    help_text.append("↑/↓ ", style="dim")
    help_text.append("select", style="dim")
    help_text.append(" · ", style="dim")
    help_text.append("1-9 ", style="dim")
    help_text.append("quick select", style="dim")
    help_text.append(" · ", style="dim")
    help_text.append("Enter ", style="dim")
    help_text.append("confirm", style="dim")
    help_text.append(" · ", style="dim")
    help_text.append("Esc ", style="dim")
    help_text.append("cancel", style="dim")

    from rich.console import Group
    content = Group(table, Text(), help_text)

    panel = Panel(
        content,
        title="Select Model",
        subtitle=f"{len(models_list)} available",
        border_style=COLORS["primary"],
        box=ROUNDED,
    )

    console.print()
    console.print(panel)


def _simple_model_selector(
    models_list: list[ModelInfo],
    current_model: str | None = None,
) -> ModelInfo | None:
    """Simple model selector for terminals without raw input support."""
    console.print()
    console.print("[bold]Available Models:[/bold]")
    console.print()

    for i, model in enumerate(models_list):
        is_current = current_model and (model.id == current_model or model.handle == current_model)
        is_default = model.is_default

        status = ""
        if is_current:
            status = " [green](active)[/green]"
        elif is_default:
            status = f" [dim](default)[/dim]"

        console.print(f"  {i + 1}. {model.id} - {model.handle}{status}")

    console.print()

    try:
        choice = input("Select model (number or 'q' to cancel): ").strip()
        if choice.lower() == 'q':
            return None
        num = int(choice)
        if 1 <= num <= len(models_list):
            return models_list[num - 1]
    except (ValueError, EOFError, KeyboardInterrupt):
        pass

    return None


def format_current_model(model_id: str | None) -> str | None:
    """Format the current model for status bar display.

    Args:
        model_id: Current model ID or handle

    Returns:
        Short display string or None
    """
    if not model_id:
        return None

    # Try to find model info
    all_models = models()
    for m in all_models:
        if m.id == model_id or m.handle == model_id:
            return m.id

    # Fall back to extracting from handle
    if ":" in model_id:
        return model_id.split(":")[-1][:15]

    return model_id[:15] if len(model_id) > 15 else model_id
