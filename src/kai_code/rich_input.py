"""Input handling, completers, and prompt session for the Rich CLI.

Adapted from deepagents-cli for kai-code.
"""

import asyncio
import os
import re
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import (
    Completer,
    Completion,
    PathCompleter,
    merge_completers,
)
from prompt_toolkit.document import Document
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings

from .rich_config import COLORS, COMMANDS, SessionState, ShortcutContext, console
from .image_utils import ImageData, get_clipboard_image

# Type for background task callback
BackgroundTaskCallback = Callable[[str, bool], None]  # (text, is_shell) -> None

# Regex patterns for context-aware completion
AT_MENTION_RE = re.compile(r"@(?P<path>(?:[^\s@]|(?<=\\)\s)*)$")
SLASH_COMMAND_RE = re.compile(r"^/(?P<command>[a-z]*)$")

EXIT_CONFIRM_WINDOW = 3.0


@dataclass
class RotatingHint:
    """Represents a single hint that can be displayed in the rotating hint area.

    Attributes:
        key: The key or trigger (e.g., "@", "/").
        description: Short description for toolbar display (e.g., "files", "commands").
        shortcut_id: Optional ID in KEYBOARD_SHORTCUTS registry for consistent formatting.
    """

    key: str
    description: str
    shortcut_id: str | None = None


class RotatingHintHelper:
    """Manages rotating through secondary hints to keep toolbar compact.

    This helper cycles through a set of secondary hints (like "@ files",
    "/help commands") on a timer. Only one hint is shown at a time to
    save space, but all hints are eventually displayed through rotation.

    Attributes:
        hints: List of RotatingHint objects to cycle through.
        rotation_interval: Seconds between hint rotations (default 5.0).
        current_index: Index of the currently displayed hint.
        last_rotation_time: Monotonic time of the last rotation.
    """

    def __init__(
        self,
        hints: list[RotatingHint] | None = None,
        rotation_interval: float = 5.0,
    ) -> None:
        """Initialize the rotating hint helper.

        Args:
            hints: List of hints to rotate through. If None, uses default hints.
            rotation_interval: Seconds between automatic rotations.
        """
        self.hints = hints or self._default_hints()
        self.rotation_interval = rotation_interval
        self.current_index = 0
        self.last_rotation_time = time.monotonic()

    @staticmethod
    def _default_hints() -> list[RotatingHint]:
        """Get the default set of secondary hints to rotate.

        Returns:
            List of RotatingHint objects for common discoverable features.
        """
        return [
            RotatingHint(key="@", description="files", shortcut_id="at_mention"),
            RotatingHint(key="/", description="commands", shortcut_id="slash_command"),
        ]

    def get_current_hint(self) -> RotatingHint:
        """Get the currently active hint.

        Automatically advances to the next hint if the rotation interval
        has elapsed since the last rotation.

        Returns:
            The current RotatingHint to display.
        """
        if not self.hints:
            return RotatingHint(key="", description="")

        # Check if it's time to rotate
        now = time.monotonic()
        elapsed = now - self.last_rotation_time

        if elapsed >= self.rotation_interval:
            # Calculate how many rotations should have happened
            rotations = int(elapsed / self.rotation_interval)
            self.current_index = (self.current_index + rotations) % len(self.hints)
            self.last_rotation_time = now

        return self.hints[self.current_index]

    def advance(self) -> RotatingHint:
        """Manually advance to the next hint.

        This can be called on input events to cycle hints more quickly
        when the user is actively interacting.

        Returns:
            The new current RotatingHint after advancing.
        """
        if not self.hints:
            return RotatingHint(key="", description="")

        self.current_index = (self.current_index + 1) % len(self.hints)
        self.last_rotation_time = time.monotonic()
        return self.hints[self.current_index]

    def format_current_hint(self, include_separator: bool = True) -> list[tuple[str, str]]:
        """Format the current hint for toolbar display.

        Uses format_shortcut_from_registry if the hint has a shortcut_id,
        otherwise falls back to format_shortcut_hint for consistent styling.

        Args:
            include_separator: Whether to include a leading separator " | ".

        Returns:
            List of (style_class, text) tuples for prompt_toolkit formatted text.
        """
        hint = self.get_current_hint()

        if hint.shortcut_id:
            return format_shortcut_from_registry(hint.shortcut_id, include_separator)
        elif hint.key and hint.description:
            return format_shortcut_hint(hint.key, hint.description, include_separator)
        else:
            return []


# Global instance of the rotating hint helper for toolbar use
_rotating_hint_helper: RotatingHintHelper | None = None


def get_rotating_hint_helper() -> RotatingHintHelper:
    """Get or create the global rotating hint helper instance.

    Returns:
        The global RotatingHintHelper instance.
    """
    global _rotating_hint_helper
    if _rotating_hint_helper is None:
        _rotating_hint_helper = RotatingHintHelper()
    return _rotating_hint_helper


@dataclass
class InputState:
    """Represents the current state of the input buffer for contextual hints.

    This dataclass captures the state of user input to enable contextual
    keyboard shortcut hints in the bottom toolbar. Each field maps to a
    ShortcutContext enum value for filtering which shortcuts to display.

    Attributes:
        has_text: True if the input buffer contains any text (maps to HAS_INPUT).
        is_multi_line: True if the input contains newline characters (maps to MULTI_LINE).
        cursor_in_middle: True if cursor is not at the end of text (maps to EDITING).
        completion_active: True if the completion menu is visible (maps to COMPLETION_ACTIVE).
        text_length: Length of the current input text.
        line_count: Number of lines in the current input.
        has_at_mention: True if the input contains an @ file mention.
    """

    has_text: bool = False
    is_multi_line: bool = False
    cursor_in_middle: bool = False
    completion_active: bool = False
    text_length: int = 0
    line_count: int = 1
    has_at_mention: bool = False

    def matches_context(self, context: ShortcutContext) -> bool:
        """Check if the current input state matches a shortcut context.

        Args:
            context: The ShortcutContext to check against.

        Returns:
            True if the current state satisfies the context requirement.
        """
        if context == ShortcutContext.ALWAYS:
            return True
        elif context == ShortcutContext.HAS_INPUT:
            return self.has_text
        elif context == ShortcutContext.MULTI_LINE:
            return self.is_multi_line
        elif context == ShortcutContext.EDITING:
            return self.cursor_in_middle
        elif context == ShortcutContext.COMPLETION_ACTIVE:
            return self.completion_active
        return False


@dataclass
class ToolbarSegment:
    """Represents a segment of the toolbar with priority for truncation.

    Toolbar segments are used to build the bottom toolbar content with
    prioritization support. When the total width exceeds terminal width,
    lower-priority segments are truncated first.

    Attributes:
        parts: List of (style_class, text) tuples for prompt_toolkit.
        priority: Display priority (1=highest, higher numbers=lower priority).
                  Priority 1: Critical state (BASH MODE, exit hint, tasks, auto-approve)
                  Priority 2: Contextual hints (ESC ESC cancel, Shift+Enter newline)
                  Priority 3: Rotating general hints (Ctrl+B, Ctrl+E, @ files, / commands)
                  Priority 4: Model display (truncated first when space is limited)
        include_separator: Whether this segment includes a leading separator.
    """

    parts: list[tuple[str, str]] = field(default_factory=list)
    priority: int = 5
    include_separator: bool = True

    @property
    def width(self) -> int:
        """Calculate the display width of this segment.

        Returns:
            Total character width of all text parts in this segment.
        """
        return sum(len(text) for _, text in self.parts)

    def get_parts_with_separator(self) -> list[tuple[str, str]]:
        """Get parts with optional leading separator.

        Returns:
            Parts with " | " prepended if include_separator is True.
        """
        if self.include_separator and self.parts:
            return [("", " | ")] + self.parts
        return self.parts

    @property
    def total_width(self) -> int:
        """Calculate total width including separator if applicable.

        Returns:
            Total width including separator (" | " = 3 chars) if needed.
        """
        base_width = self.width
        if self.include_separator and self.parts:
            base_width += 3  # " | " is 3 characters
        return base_width


def calculate_toolbar_width(segments: list[ToolbarSegment]) -> int:
    """Calculate total width of all toolbar segments.

    Args:
        segments: List of ToolbarSegment objects.

    Returns:
        Total character width of all segments combined.
    """
    total = 0
    for i, segment in enumerate(segments):
        if i == 0:
            # First segment doesn't need separator
            total += segment.width
        else:
            total += segment.total_width
    return total


def get_terminal_width() -> int:
    """Get the current terminal width.

    Returns:
        Terminal width in columns, defaults to 80 if detection fails.
    """
    try:
        return shutil.get_terminal_size().columns
    except (AttributeError, ValueError):
        return 80  # Fallback to standard width


def truncate_toolbar_segments(
    segments: list[ToolbarSegment], max_width: int
) -> list[tuple[str, str]]:
    """Truncate toolbar segments to fit within max_width.

    Segments are sorted by priority (lower number = higher priority).
    Lower-priority segments are removed first when space is limited.

    Priority order (lower number = higher priority):
    1. Critical state - BASH MODE, exit hint, tasks, auto-approve (priority 1)
    2. Contextual hints - ESC ESC cancel, Shift+Enter newline (priority 2)
    3. Rotating general hints - @ files, / commands, Ctrl+B, Ctrl+E (priority 3)
    4. Model display (priority 4) - shows last, truncated first

    Args:
        segments: List of ToolbarSegment objects to display.
        max_width: Maximum width in characters (terminal width).

    Returns:
        Flattened list of (style_class, text) tuples that fit within max_width.
    """
    if not segments:
        return []

    # Sort segments by priority (lower number = higher priority)
    sorted_segments = sorted(segments, key=lambda s: s.priority)

    # Build result by adding segments until we exceed max_width
    result_segments: list[ToolbarSegment] = []
    current_width = 0

    for segment in sorted_segments:
        # Calculate width this segment would add
        if not result_segments:
            # First segment doesn't need separator
            segment_width = segment.width
        else:
            segment_width = segment.total_width

        # Check if adding this segment would exceed max_width
        # Leave some buffer (5 chars) for safety
        if current_width + segment_width <= max_width - 5:
            result_segments.append(segment)
            current_width += segment_width

    # Re-sort by original order for display (we want model first, then status, etc.)
    # Since we sorted by priority, just flatten in that order
    result: list[tuple[str, str]] = []
    for i, segment in enumerate(result_segments):
        if i == 0:
            result.extend(segment.parts)
        else:
            result.extend(segment.get_parts_with_separator())

    return result


def format_shortcut_hint(
    key: str, display: str, include_separator: bool = True
) -> list[tuple[str, str]]:
    """Format a keyboard shortcut hint with consistent styling.

    Formats shortcut hints for the bottom toolbar with distinct styles for
    the key combination and description text. This ensures visual consistency
    across all shortcut hints displayed in the toolbar.

    Args:
        key: The key combination string (e.g., "Ctrl+E", "ESC ESC").
        display: The short description (e.g., "editor", "cancel").
        include_separator: Whether to include a leading separator " | ".

    Returns:
        List of (style_class, text) tuples for prompt_toolkit formatted text.
        Example: [("", " | "), ("class:toolbar-key", "Ctrl+E"), ("", " "),
                  ("class:toolbar-shortcut", "editor")]
    """
    parts: list[tuple[str, str]] = []

    # Add separator if requested (for chaining multiple hints)
    if include_separator:
        parts.append(("", " | "))

    # Key combination with distinct styling (e.g., "Ctrl+E")
    parts.append(("class:toolbar-key", key))

    # Space between key and description
    parts.append(("", " "))

    # Description with subdued styling (e.g., "editor")
    parts.append(("class:toolbar-shortcut", display))

    return parts


def format_shortcut_from_registry(
    shortcut_id: str, include_separator: bool = True
) -> list[tuple[str, str]]:
    """Format a shortcut hint from the KEYBOARD_SHORTCUTS registry.

    Convenience function to format a shortcut by its registry ID,
    looking up the key and display text automatically.

    Args:
        shortcut_id: The shortcut identifier in KEYBOARD_SHORTCUTS (e.g., "ctrl_e").
        include_separator: Whether to include a leading separator " | ".

    Returns:
        List of (style_class, text) tuples, or empty list if shortcut not found.
    """
    from .rich_config import KEYBOARD_SHORTCUTS

    shortcut = KEYBOARD_SHORTCUTS.get(shortcut_id)
    if not shortcut:
        return []

    return format_shortcut_hint(
        key=shortcut["key"],
        display=shortcut["display"],
        include_separator=include_separator,
    )


def detect_input_state(session: PromptSession | None) -> InputState:
    """Detect the current input state from a PromptSession.

    Examines the session's buffer to determine the current input state,
    enabling contextual display of keyboard shortcut hints.

    Args:
        session: The active PromptSession, or None if unavailable.

    Returns:
        InputState with detected values, or default empty state if session is None.
    """
    if session is None:
        return InputState()

    try:
        buffer = session.default_buffer
        text = buffer.text
        cursor_position = buffer.cursor_position

        # Calculate state values
        has_text = len(text.strip()) > 0
        is_multi_line = "\n" in text
        text_length = len(text)
        line_count = text.count("\n") + 1

        # Cursor is in middle if not at the end of the text
        cursor_in_middle = cursor_position < text_length

        # Check if completion menu is active
        completion_active = buffer.complete_state is not None

        # Check for @ file mentions (e.g., @path/to/file)
        has_at_mention = AT_MENTION_RE.search(text) is not None or "@" in text

        return InputState(
            has_text=has_text,
            is_multi_line=is_multi_line,
            cursor_in_middle=cursor_in_middle,
            completion_active=completion_active,
            text_length=text_length,
            line_count=line_count,
            has_at_mention=has_at_mention,
        )
    except (AttributeError, TypeError):
        # Silently return default state if session is not fully initialized
        return InputState()


class ImageTracker:
    """Track pasted images in the current conversation."""

    def __init__(self) -> None:
        self.images: list[ImageData] = []
        self.next_id = 1

    def add_image(self, image_data: ImageData) -> str:
        """Add an image and return its placeholder text.

        Args:
            image_data: The image data to track

        Returns:
            Placeholder string like "[image 1]"
        """
        placeholder = f"[image {self.next_id}]"
        image_data.placeholder = placeholder
        self.images.append(image_data)
        self.next_id += 1
        return placeholder

    def get_images(self) -> list[ImageData]:
        """Get all tracked images."""
        return self.images.copy()

    def clear(self) -> None:
        """Clear all tracked images and reset counter."""
        self.images.clear()
        self.next_id = 1


class FilePathCompleter(Completer):
    """Activate filesystem completion only when cursor is after '@'."""

    def __init__(self) -> None:
        self.path_completer = PathCompleter(
            expanduser=True,
            min_input_len=0,
            only_directories=False,
        )

    def get_completions(self, document, complete_event):
        """Get file path completions when @ is detected."""
        text = document.text_before_cursor

        # Use regex to detect @path pattern at end of line
        m = AT_MENTION_RE.search(text)
        if not m:
            return  # Not in an @path context

        path_fragment = m.group("path")

        # Unescape the path for PathCompleter (it doesn't understand escape sequences)
        unescaped_fragment = path_fragment.replace("\\ ", " ")

        # Strip trailing backslash if present (user is in the process of typing an escape)
        unescaped_fragment = unescaped_fragment.removesuffix("\\")

        # Create temporary document for the unescaped path fragment
        temp_doc = Document(
            text=unescaped_fragment, cursor_position=len(unescaped_fragment)
        )

        # Get completions from PathCompleter and use its start_position
        # PathCompleter returns suffix text with start_position=0 (insert at cursor)
        for comp in self.path_completer.get_completions(temp_doc, complete_event):
            # Add trailing / for directories so users can continue navigating
            completed_path = Path(unescaped_fragment + comp.text).expanduser()
            # Re-escape spaces in the completion text for the command line
            completion_text = comp.text.replace(" ", "\\ ")
            if completed_path.is_dir() and not completion_text.endswith("/"):
                completion_text += "/"

            yield Completion(
                text=completion_text,
                start_position=comp.start_position,  # Use PathCompleter's position (usually 0)
                display=comp.display,
                display_meta=comp.display_meta,
            )


class CommandCompleter(Completer):
    """Activate command completion only when line starts with '/'."""

    def get_completions(self, document, complete_event):
        """Get command completions when / is at the start."""
        text = document.text_before_cursor

        # Use regex to detect /command pattern at start of line
        m = SLASH_COMMAND_RE.match(text)
        if not m:
            return  # Not in a /command context

        command_fragment = m.group("command")

        # Match commands that start with the fragment (case-insensitive)
        for cmd_name, cmd_desc in COMMANDS.items():
            if cmd_name.startswith(command_fragment.lower()):
                yield Completion(
                    text=cmd_name,
                    start_position=-len(
                        command_fragment
                    ),  # Fixed position for original document
                    display=cmd_name,
                    display_meta=cmd_desc,
                )


def parse_file_mentions(text: str) -> tuple[str, list[Path]]:
    """Extract @file mentions and return cleaned text with resolved file paths."""
    pattern = r"@((?:[^\s@]|(?<=\\)\s)+)"  # Match @filename, allowing escaped spaces
    matches = re.findall(pattern, text)

    files = []
    for match in matches:
        # Remove escape characters
        clean_path = match.replace("\\ ", " ")
        path = Path(clean_path).expanduser()

        # Try to resolve relative to cwd
        if not path.is_absolute():
            path = Path.cwd() / path

        try:
            path = path.resolve()
            if path.exists() and path.is_file():
                files.append(path)
            else:
                console.print(f"[yellow]Warning: File not found: {match}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Warning: Invalid path {match}: {e}[/yellow]")

    return text, files


def parse_image_placeholders(text: str) -> tuple[str, int]:
    """Count image placeholders in text.

    Args:
        text: Input text potentially containing [image] or [image N] placeholders

    Returns:
        Tuple of (text, count) where count is the number of image placeholders found
    """
    # Match [image] or [image N] patterns
    pattern = r"\[image(?:\s+\d+)?\]"
    matches = re.findall(pattern, text, re.IGNORECASE)
    return text, len(matches)


def get_bottom_toolbar(
    session_state: SessionState, session_ref: dict
) -> Callable[[], list[tuple[str, str]]]:
    """Return toolbar function that shows auto-approve status, BASH MODE, model, and background tasks.

    The toolbar detects the current input state to enable contextual keyboard
    shortcut hints based on whether there is text, multi-line input, cursor
    position, and completion menu state.

    Smart truncation is applied when content exceeds terminal width.
    Priority order (lower number = higher priority):
    1. Critical state - BASH MODE, exit hint, tasks, auto-approve (priority 1)
    2. Contextual hints - ESC ESC cancel, Shift+Enter newline (priority 2)
    3. Rotating general hints - @ files, / commands, Ctrl+B, Ctrl+E (priority 3)
    4. Model display (priority 4) - shows last, truncated first
    """

    def toolbar() -> list[tuple[str, str]]:
        segments: list[ToolbarSegment] = []

        # Detect current input state for contextual hints
        session = session_ref.get("session")
        input_state = detect_input_state(session)

        # Get terminal width for truncation
        terminal_width = get_terminal_width()

        # === Priority 4: Model display (lowest priority - truncated first) ===
        if hasattr(session_state, 'model') and session_state.model:
            try:
                from .model_selector import format_current_model
                model_display = format_current_model(session_state.model)
                if model_display:
                    segments.append(ToolbarSegment(
                        parts=[("class:toolbar-model", f" {model_display} ")],
                        priority=4,
                        include_separator=False,  # First segment, no separator
                    ))
            except ImportError:
                pass

        # === Priority 1: Critical state indicators (highest priority) ===

        # BASH mode indicator (critical - tells user they're in shell mode)
        try:
            if session:
                current_text = session.default_buffer.text
                if current_text.startswith("!"):
                    segments.append(ToolbarSegment(
                        parts=[("bg:#ff1493 fg:#ffffff bold", " BASH MODE ")],
                        priority=1,
                        include_separator=True,
                    ))
        except (AttributeError, TypeError):
            pass

        # Exit confirmation hint (critical when active)
        hint_until = session_state.exit_hint_until
        if hint_until is not None:
            now = time.monotonic()
            if now < hint_until:
                segments.append(ToolbarSegment(
                    parts=[("class:toolbar-exit", " Ctrl+C again to exit ")],
                    priority=1,  # Highest priority when active
                    include_separator=True,
                ))
            else:
                session_state.exit_hint_until = None

        # Background task count
        try:
            from .tasks import format_task_status_line
            task_status = format_task_status_line()
            if task_status:
                segments.append(ToolbarSegment(
                    parts=[("class:toolbar-task", f" {task_status} ")],
                    priority=1,
                    include_separator=True,
                ))
        except ImportError:
            pass

        # Auto-approve status (critical user feedback)
        if session_state.auto_approve:
            base_msg = "auto-accept ON (CTRL+T to toggle)"
            base_class = "class:toolbar-green"
        else:
            base_msg = "manual accept (CTRL+T to toggle)"
            base_class = "class:toolbar-orange"

        segments.append(ToolbarSegment(
            parts=[(base_class, base_msg)],
            priority=1,
            include_separator=True,
        ))

        # === Priority 2: Contextual hints (based on input state) ===

        # When input has text: show ESC ESC cancel
        if input_state.has_text:
            shortcut_parts = format_shortcut_from_registry("double_esc", include_separator=False)
            if shortcut_parts:
                segments.append(ToolbarSegment(
                    parts=shortcut_parts,
                    priority=2,
                    include_separator=True,
                ))

        # Show Shift+Enter newline hint contextually when user might want multi-line input:
        # - When already multi-line (user is writing multiple lines)
        # - When @ file is mentioned (likely writing a longer prompt about the file)
        # - When user has typed text (might want to add additional context on new lines)
        wants_multiline_hint = (
            input_state.is_multi_line
            or input_state.has_at_mention
            or input_state.has_text
        )
        if wants_multiline_hint:
            shortcut_parts = format_shortcut_from_registry("shift_enter", include_separator=False)
            if shortcut_parts:
                segments.append(ToolbarSegment(
                    parts=shortcut_parts,
                    priority=2,
                    include_separator=True,
                ))

        # === Priority 3: Rotating general hints (discoverable features) ===
        # These hints are lower priority than critical state and contextual hints.
        # They provide feature discoverability but can be truncated when space is limited.

        # Ctrl+B background hint
        shortcut_parts = format_shortcut_from_registry("ctrl_b", include_separator=False)
        if shortcut_parts:
            segments.append(ToolbarSegment(
                parts=shortcut_parts,
                priority=3,
                include_separator=True,
            ))

        # Ctrl+E editor hint (powerful hidden feature)
        shortcut_parts = format_shortcut_from_registry("ctrl_e", include_separator=False)
        if shortcut_parts:
            segments.append(ToolbarSegment(
                parts=shortcut_parts,
                priority=3,
                include_separator=True,
            ))

        # Rotating hints - show one at a time to keep toolbar compact
        # Hints cycle through on a timer (e.g., "@ files", "/ commands")
        rotating_helper = get_rotating_hint_helper()
        rotating_parts = rotating_helper.format_current_hint(include_separator=False)
        if rotating_parts:
            segments.append(ToolbarSegment(
                parts=rotating_parts,
                priority=3,
                include_separator=True,
            ))

        # Apply smart truncation based on terminal width
        return truncate_toolbar_segments(segments, terminal_width)

    return toolbar


def create_prompt_session(
    _assistant_id: str,
    session_state: SessionState,
    image_tracker: ImageTracker | None = None,
    background_task_callback: BackgroundTaskCallback | None = None,
) -> PromptSession:
    """Create a configured PromptSession with all features.

    Args:
        _assistant_id: Assistant identifier (used for path resolution)
        session_state: Session state for auto-approve, etc.
        image_tracker: Optional tracker for pasted images
        background_task_callback: Optional callback for Ctrl+B to run background tasks.
            Called with (text, is_shell) where is_shell is True if text starts with !
    """
    # Set default editor if not already set
    if "EDITOR" not in os.environ:
        os.environ["EDITOR"] = "nano"

    # Create key bindings
    kb = KeyBindings()

    @kb.add("c-c")
    def _(event) -> None:
        """Require double Ctrl+C within a short window to exit."""
        app = event.app
        now = time.monotonic()

        if (
            session_state.exit_hint_until is not None
            and now < session_state.exit_hint_until
        ):
            handle = session_state.exit_hint_handle
            if handle:
                handle.cancel()
                session_state.exit_hint_handle = None
            session_state.exit_hint_until = None
            app.invalidate()
            app.exit(exception=KeyboardInterrupt())
            return

        session_state.exit_hint_until = now + EXIT_CONFIRM_WINDOW

        handle = session_state.exit_hint_handle
        if handle:
            handle.cancel()

        loop = asyncio.get_running_loop()
        app_ref = app

        def clear_hint() -> None:
            if (
                session_state.exit_hint_until is not None
                and time.monotonic() >= session_state.exit_hint_until
            ):
                session_state.exit_hint_until = None
                session_state.exit_hint_handle = None
                app_ref.invalidate()

        session_state.exit_hint_handle = loop.call_later(
            EXIT_CONFIRM_WINDOW, clear_hint
        )

        app.invalidate()

    # Bind Ctrl+T to toggle auto-approve
    @kb.add("c-t")
    def _(event) -> None:
        """Toggle auto-approve mode."""
        session_state.toggle_auto_approve()
        # Force UI refresh to update toolbar
        event.app.invalidate()

    # Bind Ctrl+B to run current input as background task
    @kb.add("c-b")
    def _(event) -> None:
        """Run current input as a background task."""
        buffer = event.current_buffer
        text = buffer.text.strip()

        if not text:
            return

        if background_task_callback:
            # Determine if this is a shell command
            is_shell = text.startswith("!")
            if is_shell:
                text = text[1:].strip()  # Remove the ! prefix

            # Clear the buffer
            buffer.reset()

            # Call the callback
            background_task_callback(text, is_shell)

            # Force UI refresh
            event.app.invalidate()
        else:
            # No callback configured - show message
            console.print("[yellow]Background tasks not available.[/yellow]")

    # Custom paste handler to detect images
    if image_tracker:
        from prompt_toolkit.keys import Keys

        def _handle_paste_with_image_check(event, pasted_text: str = "") -> None:
            """Check clipboard for image, otherwise insert pasted text."""
            # Try to get an image from clipboard
            clipboard_image = get_clipboard_image()

            if clipboard_image:
                # Found an image! Add it to tracker and insert placeholder
                placeholder = image_tracker.add_image(clipboard_image)
                # Insert placeholder (no confirmation message)
                event.current_buffer.insert_text(placeholder)
            elif pasted_text:
                # No image, insert the pasted text
                event.current_buffer.insert_text(pasted_text)
            else:
                # Fallback: try to get text from prompt_toolkit clipboard
                clipboard_data = event.app.clipboard.get_data()
                if clipboard_data and clipboard_data.text:
                    event.current_buffer.insert_text(clipboard_data.text)

        @kb.add(Keys.BracketedPaste)
        def _(event) -> None:
            """Handle bracketed paste (Cmd+V on macOS) - check for images first."""
            # Bracketed paste provides the pasted text in event.data
            pasted_text = event.data if hasattr(event, "data") else ""
            _handle_paste_with_image_check(event, pasted_text)

        @kb.add("c-v")
        def _(event) -> None:
            """Handle Ctrl+V paste - check for images first."""
            _handle_paste_with_image_check(event)

    # Bind regular Enter to submit (intuitive behavior)
    @kb.add("enter")
    def _(event) -> None:
        """Enter submits the input, unless completion menu is active."""
        buffer = event.current_buffer

        # If completion menu is showing, apply the current completion
        if buffer.complete_state:
            # Get the current completion (the highlighted one)
            current_completion = buffer.complete_state.current_completion

            # If no completion is selected (user hasn't navigated), select and apply the first one
            if not current_completion and buffer.complete_state.completions:
                # Move to the first completion
                buffer.complete_next()
                # Now apply it
                buffer.apply_completion(buffer.complete_state.current_completion)
            elif current_completion:
                # Apply the already-selected completion
                buffer.apply_completion(current_completion)
            else:
                # No completions available, close menu
                buffer.complete_state = None
        # Don't submit if buffer is empty or only whitespace
        elif buffer.text.strip():
            session_state._last_escape_time = 0
            # Normal submit
            buffer.validate_and_handle()
            # If empty, do nothing (don't submit)

    # Shift+Enter for newlines
    @kb.add("s-enter")
    def _(event) -> None:
        """Shift+Enter inserts a newline for multi-line input."""
        event.current_buffer.insert_text("\n")

    # Ctrl+J for newlines (alternative to Shift+Enter, standard terminal control code)
    @kb.add("c-j")
    def _(event) -> None:
        """Ctrl+J inserts a newline (alternative to Shift+Enter)."""
        event.current_buffer.insert_text("\n")

    @kb.add("escape")
    def _(event) -> None:
        import time

        now = time.time()

        if now - session_state._last_escape_time < 0.5:
            session_state._last_escape_time = 0
            event.current_buffer.reset()
            console.print("\n[yellow]Input cancelled.[/yellow]")
        else:
            session_state._last_escape_time = now

    # Ctrl+E to open in external editor
    @kb.add("c-e")
    def _(event) -> None:
        """Open the current input in an external editor (nano by default)."""
        event.current_buffer.open_in_editor()

    # Backspace handler to retrigger completions and delete image tags as units
    @kb.add("backspace")
    def _(event) -> None:
        """Handle backspace: delete image tags as single unit, retrigger completion."""
        buffer = event.current_buffer
        text_before = buffer.document.text_before_cursor

        # Check if cursor is right after an image tag like [image 1] or [image 12]
        image_tag_pattern = r"\[image \d+\]$"
        match = re.search(image_tag_pattern, text_before)

        if match and image_tracker:
            # Delete the entire tag
            tag_length = len(match.group(0))
            buffer.delete_before_cursor(count=tag_length)

            # Remove the image from tracker and reset counter
            tag_text = match.group(0)
            image_num_match = re.search(r"\d+", tag_text)
            if image_num_match:
                image_num = int(image_num_match.group(0))
                # Remove image at index (1-based to 0-based)
                if 0 < image_num <= len(image_tracker.images):
                    image_tracker.images.pop(image_num - 1)
                    # Reset counter to next available number
                    image_tracker.next_id = len(image_tracker.images) + 1
        else:
            # Normal backspace
            buffer.delete_before_cursor(count=1)

        # Check if we're in a completion context (@ or /)
        text = buffer.document.text_before_cursor
        if AT_MENTION_RE.search(text) or SLASH_COMMAND_RE.match(text):
            # Retrigger completion
            buffer.start_completion(select_first=False)

    from prompt_toolkit.styles import Style

    # Define styles for the toolbar with full-width background colors
    toolbar_style = Style.from_dict(
        {
            "bottom-toolbar": "noreverse",  # Disable default reverse video
            "toolbar-green": "bg:#10b981 #000000",  # Green for auto-accept ON
            "toolbar-orange": "bg:#f59e0b #000000",  # Orange for manual accept
            "toolbar-exit": "bg:#2563eb #ffffff",  # Blue for exit hint
            "toolbar-task": "bg:#8b5cf6 #ffffff",  # Purple for background tasks
            "toolbar-model": "bg:#3b82f6 #ffffff",  # Blue for current model
            "toolbar-hint": "#6b7280",  # Dim gray for hints
            "toolbar-key": "#94a3b8 bold",  # Brighter gray bold for shortcut keys
            "toolbar-shortcut": "#64748b",  # Slate gray for shortcut descriptions
        }
    )

    # Create session reference dict for toolbar to access session
    session_ref = {}

    # Create the session
    session = PromptSession(
        message=HTML(f'<style fg="{COLORS["user"]}">></style> '),
        multiline=True,  # Keep multiline support but Enter submits
        key_bindings=kb,
        completer=merge_completers([CommandCompleter(), FilePathCompleter()]),
        editing_mode=EditingMode.EMACS,
        complete_while_typing=True,  # Show completions as you type
        complete_in_thread=True,  # Async completion prevents menu freezing
        mouse_support=False,
        enable_open_in_editor=True,  # Allow Ctrl+X Ctrl+E to open external editor
        bottom_toolbar=get_bottom_toolbar(
            session_state, session_ref
        ),  # Persistent status bar at bottom
        style=toolbar_style,  # Apply toolbar styling
        reserve_space_for_menu=7,  # Reserve space for completion menu to show 5-6 results
    )

    # Store session reference for toolbar to access
    session_ref["session"] = session

    return session
