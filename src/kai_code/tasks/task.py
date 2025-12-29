"""Task models for background execution."""
from __future__ import annotations

import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..agent import KaiAgent


class TaskStatus(Enum):
    """Status of a background task."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class TaskPriority(Enum):
    """Priority level for task scheduling.

    Lower numeric values indicate higher priority for heap ordering.
    HIGH priority tasks are executed before NORMAL, which execute before LOW.
    """

    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Task:
    """Base class for background tasks."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    type: Literal["shell", "agent"] = "shell"
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    output: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    exit_code: int | None = None
    error: str | None = None

    # Internal
    _thread: threading.Thread | None = field(default=None, repr=False)
    _process: subprocess.Popen | None = field(default=None, repr=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def run(self) -> None:
        """Execute the task. Override in subclasses."""
        raise NotImplementedError

    def kill(self) -> bool:
        """Kill the running task."""
        if self.status != TaskStatus.RUNNING:
            return False

        self._stop_event.set()

        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except Exception:
                pass

        self.status = TaskStatus.KILLED
        self.finished_at = datetime.now()
        return True

    @property
    def duration(self) -> float | None:
        """Get task duration in seconds."""
        if self.finished_at:
            return (self.finished_at - self.created_at).total_seconds()
        if self.status == TaskStatus.RUNNING:
            return (datetime.now() - self.created_at).total_seconds()
        return None

    @property
    def priority_indicator(self) -> str:
        """Get priority indicator string.

        Returns empty string for NORMAL priority (the default),
        or [H]/[L] prefix for HIGH/LOW priority respectively.
        """
        if self.priority == TaskPriority.HIGH:
            return "[H] "
        elif self.priority == TaskPriority.LOW:
            return "[L] "
        return ""

    def get_display_status(self, show_priority: bool = False) -> str:
        """Get display string for status.

        Args:
            show_priority: If True, prepend priority indicator for non-NORMAL priorities.

        Returns:
            Formatted status string with optional priority prefix.
        """
        priority_prefix = self.priority_indicator if show_priority else ""

        if self.status == TaskStatus.RUNNING:
            duration = self.duration or 0
            return f"{priority_prefix}⟳ {duration:.1f}s"
        elif self.status == TaskStatus.COMPLETED:
            duration = self.duration or 0
            return f"{priority_prefix}✓ done ({duration:.1f}s)"
        elif self.status == TaskStatus.FAILED:
            return f"{priority_prefix}✗ failed"
        elif self.status == TaskStatus.KILLED:
            return f"{priority_prefix}killed"
        elif self.status == TaskStatus.PENDING:
            return f"{priority_prefix}pending"
        elif self.status == TaskStatus.QUEUED:
            return f"{priority_prefix}⏳ queued"
        return f"{priority_prefix}{self.status.value}"

    @property
    def display_status(self) -> str:
        """Get display string for status (without priority indicator).

        For backward compatibility, this property does not show priority.
        Use get_display_status(show_priority=True) to include priority indicator.
        """
        return self.get_display_status(show_priority=False)


@dataclass
class BackgroundShellTask(Task):
    """Background shell command execution."""

    command: str = ""
    working_dir: Path = field(default_factory=Path.cwd)
    type: Literal["shell", "agent"] = "shell"

    def __post_init__(self):
        if not self.description:
            # Truncate command for display
            self.description = f"! {self.command[:50]}..." if len(self.command) > 50 else f"! {self.command}"

    def run(self) -> None:
        """Execute the shell command."""
        try:
            self.status = TaskStatus.RUNNING
            self._process = subprocess.Popen(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self.working_dir,
                text=True,
            )

            # Read output
            output_lines = []
            while True:
                if self._stop_event.is_set():
                    break
                line = self._process.stdout.readline()
                if not line and self._process.poll() is not None:
                    break
                if line:
                    output_lines.append(line)

            self.output = "".join(output_lines)
            self.exit_code = self._process.returncode

            if self._stop_event.is_set():
                self.status = TaskStatus.KILLED
            elif self.exit_code == 0:
                self.status = TaskStatus.COMPLETED
            else:
                self.status = TaskStatus.FAILED
                self.error = f"Exit code: {self.exit_code}"

        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = str(e)
            self.output = f"Error: {e}"

        finally:
            self.finished_at = datetime.now()
            self._process = None


@dataclass
class BackgroundAgentTask(Task):
    """Background agent execution."""

    prompt: str = ""
    root_dir: Path = field(default_factory=Path.cwd)
    model: str = "default"
    type: Literal["shell", "agent"] = "agent"

    def __post_init__(self):
        if not self.description:
            # Truncate prompt for display
            truncated = self.prompt[:40] + "..." if len(self.prompt) > 40 else self.prompt
            self.description = f"Agent: {truncated}"

    def run(self) -> None:
        """Execute the agent task."""
        try:
            self.status = TaskStatus.RUNNING

            # Import here to avoid circular imports
            from ..agent import KaiAgent
            from ..model import get_default_model, resolve_model

            # Resolve model
            if self.model == "default":
                model_name = get_default_model()
            else:
                model_name = self.model
            model_string = resolve_model(model_name)

            # Create fresh agent (no history)
            agent = KaiAgent(
                root_dir=self.root_dir,
                model=model_string,
                yolo=True,  # Background agents auto-approve
            )

            # Check for stop before running
            if self._stop_event.is_set():
                self.status = TaskStatus.KILLED
                return

            # Run the prompt
            result = agent.run(self.prompt)
            self.output = result.output

            if self._stop_event.is_set():
                self.status = TaskStatus.KILLED
            else:
                self.status = TaskStatus.COMPLETED

        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = str(e)
            self.output = f"Error: {e}"

        finally:
            self.finished_at = datetime.now()
