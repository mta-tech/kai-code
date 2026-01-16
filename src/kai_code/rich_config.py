"""Configuration and constants for the Rich CLI.

This module bridges kai-code's settings with deepagents-cli patterns.
"""

import os
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import dotenv
from rich.console import Console

dotenv.load_dotenv()

# Color scheme (from deepagents-cli)
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

# ASCII art banner for Kai Code
KAI_CODE_ASCII = """
 ██╗  ██╗  █████╗  ██╗
 ██║ ██╔╝ ██╔══██╗ ██║
 █████╔╝  ███████║ ██║
 ██╔═██╗  ██╔══██║ ██║
 ██║  ██╗ ██║  ██║ ██║
 ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝

  ██████╗  ██████╗  ██████╗  ███████╗
 ██╔════╝ ██╔═══██╗ ██╔══██╗ ██╔════╝
 ██║      ██║   ██║ ██║  ██║ █████╗
 ██║      ██║   ██║ ██║  ██║ ██╔══╝
 ╚██████╗ ╚██████╔╝ ██████╔╝ ███████╗
  ╚═════╝  ╚═════╝  ╚═════╝  ╚══════╝
"""

# Interactive commands
COMMANDS = {
    "clear": "Clear screen and reset conversation",
    "help": "Show help information",
    "model": "Select or switch model",
    "models": "List available models",
    "skills": "List available skills",
    "tasks": "Show background tasks panel",
    "tokens": "Show token usage; toggle real-time indicator (show/hide)",
    "ralph-loop": "Start Ralph autonomous loop",
    "ralph-status": "Show Ralph loop status",
    "cancel-ralph": "Cancel active Ralph loop",
    "quit": "Exit the CLI",
    "exit": "Exit the CLI",
}


class ShortcutContext(Enum):
    """Defines when a keyboard shortcut should be displayed in the toolbar.

    These contexts control the visibility of shortcut hints based on the
    current input state, enabling contextual discovery of relevant shortcuts.

    Attributes:
        ALWAYS: Show this shortcut hint at all times (e.g., Ctrl+E editor).
        HAS_INPUT: Show only when there is text in the input buffer (e.g., ESC ESC cancel).
        MULTI_LINE: Show only when input spans multiple lines (e.g., Ctrl+J newline).
        EDITING: Show when actively editing text (cursor in middle of text).
        COMPLETION_ACTIVE: Show only when the completion menu is visible.
    """

    ALWAYS = "always"
    HAS_INPUT = "has_input"
    MULTI_LINE = "multi_line"
    EDITING = "editing"
    COMPLETION_ACTIVE = "completion_active"


# Keyboard shortcuts registry for toolbar display and discoverability
# Each shortcut has:
#   - key: The key combination (e.g., "Ctrl+E")
#   - description: Full description for help text
#   - display: Short text for toolbar display (e.g., "editor")
#   - context: ShortcutContext enum value controlling when to show in toolbar
#   - priority: Display priority (1=highest, 10=lowest) - higher priority shown first when space is limited
KEYBOARD_SHORTCUTS = {
    "ctrl_e": {
        "key": "Ctrl+E",
        "description": "Open current input in external editor (nano by default)",
        "display": "editor",
        "context": ShortcutContext.ALWAYS,
        "priority": 3,
    },
    "ctrl_t": {
        "key": "Ctrl+T",
        "description": "Toggle auto-approve mode for tool execution",
        "display": "toggle approve",
        "context": ShortcutContext.ALWAYS,
        "priority": 1,
    },
    "ctrl_b": {
        "key": "Ctrl+B",
        "description": "Run current input as a background task",
        "display": "background",
        "context": ShortcutContext.ALWAYS,
        "priority": 2,
    },
    "double_esc": {
        "key": "ESC ESC",
        "description": "Cancel current input and clear the buffer",
        "display": "cancel",
        "context": ShortcutContext.HAS_INPUT,
        "priority": 4,
    },
    "shift_enter": {
        "key": "Shift+Enter",
        "description": "Insert newline for multi-line input",
        "display": "newline",
        "context": ShortcutContext.ALWAYS,
        "priority": 5,
    },
    "enter": {
        "key": "Enter",
        "description": "Submit the current input",
        "display": "submit",
        "context": ShortcutContext.HAS_INPUT,
        "priority": 1,
    },
    "ctrl_c": {
        "key": "Ctrl+C",
        "description": "Cancel input or interrupt the agent (double-press to exit)",
        "display": "interrupt",
        "context": ShortcutContext.ALWAYS,
        "priority": 6,
    },
    "at_mention": {
        "key": "@",
        "description": "Type @ followed by path to auto-complete and inject file content",
        "display": "files",
        "context": ShortcutContext.ALWAYS,
        "priority": 7,
    },
    "slash_command": {
        "key": "/",
        "description": "Type / at start to access commands like /help, /model, /tasks",
        "display": "commands",
        "context": ShortcutContext.ALWAYS,
        "priority": 8,
    },
    "arrow_keys": {
        "key": "↑↓←→",
        "description": "Navigate within the input buffer",
        "display": "navigate",
        "context": ShortcutContext.HAS_INPUT,
        "priority": 10,
    },
    "ctrl_j": {
        "key": "Ctrl+J",
        "description": "Insert newline (alternative to Alt+Enter)",
        "display": "newline",
        "context": ShortcutContext.MULTI_LINE,
        "priority": 9,
    },
}

# Maximum argument length for display
MAX_ARG_LENGTH = 150

# Agent configuration
config = {"recursion_limit": 1000}

# Rich console instance
console = Console(highlight=False)


def _find_project_root(start_path: Path | None = None) -> Path | None:
    """Find the project root by looking for .git directory.

    Walks up the directory tree from start_path (or cwd) looking for a .git
    directory, which indicates the project root.

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.

    Returns:
        Path to the project root if found, None otherwise.
    """
    current = Path(start_path or Path.cwd()).resolve()

    # Walk up the directory tree
    for parent in [current, *list(current.parents)]:
        git_dir = parent / ".git"
        if git_dir.exists():
            return parent

    return None


def _find_project_agent_md(project_root: Path) -> list[Path]:
    """Find project-specific agent.md file(s).

    Checks two locations and returns ALL that exist:
    1. project_root/.kai/agent.md
    2. project_root/agent.md

    Both files will be loaded and combined if both exist.

    Args:
        project_root: Path to the project root directory.

    Returns:
        List of paths to project agent.md files (may contain 0, 1, or 2 paths).
    """
    paths = []

    # Check .kai/agent.md (preferred)
    kai_md = project_root / ".kai" / "agent.md"
    if kai_md.exists():
        paths.append(kai_md)

    # Check root agent.md (fallback, but also include if both exist)
    root_md = project_root / "agent.md"
    if root_md.exists():
        paths.append(root_md)

    return paths


@dataclass
class RichSettings:
    """Settings for the Rich CLI mode.

    This class provides access to:
    - Available models and API keys
    - Current project information
    - Tool availability (e.g., Tavily)
    - File system paths
    - Progress indicator configuration

    Attributes:
        project_root: Current project root directory (if in a git project)
        openai_api_key: OpenAI API key if available
        anthropic_api_key: Anthropic API key if available
        google_api_key: Google API key if available
        tavily_api_key: Tavily API key if available
        progress_enabled: Whether progress indicators are enabled (default True)
        progress_file_size_threshold: File size threshold in bytes for showing
            progress during file reads (default 50KB). Files larger than this
            threshold will display progress indicators during reading.
        progress_update_interval_ms: Minimum interval in milliseconds between
            progress updates (default 100ms). Used to throttle progress
            reporting to avoid excessive updates.
    """

    # API keys
    openai_api_key: str | None
    anthropic_api_key: str | None
    google_api_key: str | None
    tavily_api_key: str | None

    # Project information
    project_root: Path | None

    # Progress indicator settings
    # These control how progress indicators behave during long-running operations
    progress_enabled: bool = True
    progress_file_size_threshold: int = 50 * 1024  # 50KB
    progress_update_interval_ms: int = 100

    @classmethod
    def from_environment(cls, *, start_path: Path | None = None) -> "RichSettings":
        """Create settings by detecting the current environment.

        Reads the following environment variables:
        - OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, TAVILY_API_KEY: API keys
        - KAI_PROGRESS_ENABLED: Set to "false" or "0" to disable progress indicators
        - KAI_PROGRESS_FILE_SIZE_THRESHOLD: File size in bytes for progress threshold
        - KAI_PROGRESS_UPDATE_INTERVAL_MS: Update interval in milliseconds

        Args:
            start_path: Directory to start project detection from (defaults to cwd)

        Returns:
            RichSettings instance with detected configuration
        """
        # Detect API keys
        openai_key = os.environ.get("OPENAI_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        google_key = os.environ.get("GOOGLE_API_KEY")
        tavily_key = os.environ.get("TAVILY_API_KEY")

        # Detect project
        project_root = _find_project_root(start_path)

        # Parse progress settings from environment
        progress_enabled = True
        progress_enabled_env = os.environ.get("KAI_PROGRESS_ENABLED", "").lower()
        if progress_enabled_env in ("false", "0", "no", "off"):
            progress_enabled = False

        progress_file_size_threshold = 50 * 1024  # Default 50KB
        threshold_env = os.environ.get("KAI_PROGRESS_FILE_SIZE_THRESHOLD")
        if threshold_env:
            try:
                progress_file_size_threshold = int(threshold_env)
            except ValueError:
                pass  # Keep default if invalid

        progress_update_interval_ms = 100  # Default 100ms
        interval_env = os.environ.get("KAI_PROGRESS_UPDATE_INTERVAL_MS")
        if interval_env:
            try:
                progress_update_interval_ms = int(interval_env)
            except ValueError:
                pass  # Keep default if invalid

        return cls(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            google_api_key=google_key,
            tavily_api_key=tavily_key,
            project_root=project_root,
            progress_enabled=progress_enabled,
            progress_file_size_threshold=progress_file_size_threshold,
            progress_update_interval_ms=progress_update_interval_ms,
        )

    @property
    def has_openai(self) -> bool:
        """Check if OpenAI API key is configured."""
        return self.openai_api_key is not None

    @property
    def has_anthropic(self) -> bool:
        """Check if Anthropic API key is configured."""
        return self.anthropic_api_key is not None

    @property
    def has_google(self) -> bool:
        """Check if Google API key is configured."""
        return self.google_api_key is not None

    @property
    def has_tavily(self) -> bool:
        """Check if Tavily API key is configured."""
        return self.tavily_api_key is not None

    @property
    def has_project(self) -> bool:
        """Check if currently in a git project."""
        return self.project_root is not None

    @property
    def user_kai_dir(self) -> Path:
        """Get the base user-level .kai directory.

        Returns:
            Path to ~/.kai
        """
        return Path.home() / ".kai"

    def get_agent_dir(self, agent_name: str) -> Path:
        """Get the global agent directory path.

        Args:
            agent_name: Name of the agent

        Returns:
            Path to ~/.kai/{agent_name}
        """
        return Path.home() / ".kai" / agent_name

    def ensure_agent_dir(self, agent_name: str) -> Path:
        """Ensure the global agent directory exists and return its path.

        Args:
            agent_name: Name of the agent

        Returns:
            Path to ~/.kai/{agent_name}
        """
        agent_dir = self.get_agent_dir(agent_name)
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir

    def get_user_skills_dir(self, agent_name: str) -> Path:
        """Get user-level skills directory path for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Path to ~/.kai/{agent_name}/skills/
        """
        return self.get_agent_dir(agent_name) / "skills"

    def get_project_skills_dir(self) -> Path | None:
        """Get project-level skills directory path.

        Returns:
            Path to {project_root}/.kai/skills/, or None if not in a project
        """
        if not self.project_root:
            return None
        return self.project_root / ".kai" / "skills"


# Global settings instance (initialized once)
rich_settings = RichSettings.from_environment()


def _parse_bool_env(env_var: str, default: bool = True) -> bool:
    """Parse a boolean environment variable.

    Args:
        env_var: Name of the environment variable
        default: Default value if not set

    Returns:
        Boolean value based on environment variable
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    # Treat "0", "false", "no", "off" as False (case insensitive)
    return value.lower() not in ("0", "false", "no", "off", "")


class SessionState:
    """Holds mutable session state (auto-approve mode, etc)."""

    def __init__(
        self,
        auto_approve: bool = False,
        no_splash: bool = False,
        model: str | None = None,
        show_tokens: bool | None = None,
        show_quick_start: bool = False,
    ) -> None:
        self.auto_approve = auto_approve
        self.no_splash = no_splash
        self.model = model  # Current model ID or handle
        self.exit_hint_until: float | None = None
        self.exit_hint_handle = None
        self.thread_id = str(uuid.uuid4())
        self._last_escape_time: float = 0
        self._model_changed: bool = False  # Flag to signal agent recreation needed
        self.show_quick_start = show_quick_start  # Force show Quick Start panel

        # Token display: CLI arg takes precedence, then env var, then default True
        if show_tokens is not None:
            self.show_tokens = show_tokens
        else:
            self.show_tokens = _parse_bool_env("KAI_SHOW_TOKENS", default=True)

    def toggle_auto_approve(self) -> bool:
        """Toggle auto-approve and return new state."""
        self.auto_approve = not self.auto_approve
        return self.auto_approve

    def set_model(self, model: str) -> None:
        """Set the current model and flag for recreation."""
        if self.model != model:
            self.model = model
            self._model_changed = True

    def clear_model_changed(self) -> bool:
        """Check if model changed and clear the flag."""
        changed = self._model_changed
        self._model_changed = False
        return changed
