"""Configuration and constants for the Rich CLI.

This module bridges kai-code's settings with deepagents-cli patterns.
"""

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

import dotenv
from rich.console import Console

dotenv.load_dotenv()

# Color scheme (from deepagents-cli)
COLORS = {
    "primary": "#10b981",
    "dim": "#6b7280",
    "user": "#ffffff",
    "agent": "#10b981",
    "thinking": "#34d399",
    "tool": "#fbbf24",
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
    "tokens": "Show token usage for current session",
    "ralph-loop": "Start Ralph autonomous loop",
    "ralph-status": "Show Ralph loop status",
    "cancel-ralph": "Cancel active Ralph loop",
    "quit": "Exit the CLI",
    "exit": "Exit the CLI",
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

    Attributes:
        project_root: Current project root directory (if in a git project)
        openai_api_key: OpenAI API key if available
        anthropic_api_key: Anthropic API key if available
        google_api_key: Google API key if available
        tavily_api_key: Tavily API key if available
    """

    # API keys
    openai_api_key: str | None
    anthropic_api_key: str | None
    google_api_key: str | None
    tavily_api_key: str | None

    # Project information
    project_root: Path | None

    @classmethod
    def from_environment(cls, *, start_path: Path | None = None) -> "RichSettings":
        """Create settings by detecting the current environment.

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

        return cls(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            google_api_key=google_key,
            tavily_api_key=tavily_key,
            project_root=project_root,
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


class SessionState:
    """Holds mutable session state (auto-approve mode, etc)."""

    def __init__(
        self,
        auto_approve: bool = False,
        no_splash: bool = False,
        model: str | None = None,
    ) -> None:
        self.auto_approve = auto_approve
        self.no_splash = no_splash
        self.model = model  # Current model ID or handle
        self.exit_hint_until: float | None = None
        self.exit_hint_handle = None
        self.thread_id = str(uuid.uuid4())
        self._last_escape_time: float = 0
        self._model_changed: bool = False  # Flag to signal agent recreation needed

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
