"""Migration utilities for transitioning from old TaskManager to HybridTaskManager.

This module provides utilities to convert old Task objects to the new HybridTask
format, ensuring no data loss during the transition.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .task import Task as OldTask
    from .hybrid_manager import Task as NewTask, TaskStatus as NewTaskStatus


class TaskMigrationError(Exception):
    """Error during task migration."""


class TaskStatusMapper:
    """Maps old TaskStatus values to new TaskStatus values."""

    # Old task status -> New task status
    STATUS_MAP = {
        "pending": "queued",  # PENDING becomes QUEUED
        "queued": "queued",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
        "killed": "killed",
    }

    @classmethod
    def map_status(cls, old_status: str) -> str:
        """Map old status string to new status value.

        Args:
            old_status: Old task status value

        Returns:
            New task status value

        Raises:
            TaskMigrationError: If status cannot be mapped
        """
        new_status = cls.STATUS_MAP.get(old_status)
        if new_status is None:
            raise TaskMigrationError(f"Unknown status: {old_status}")
        return new_status


@dataclass
class MigratedTask:
    """A task that has been migrated from old to new format.

    This acts as an intermediate representation during migration,
    capturing all data from both old and new formats.
    """
    # Core fields (both old and new)
    id: str
    status: str
    type: str  # "shell" or "agent"

    # Old Task fields
    old_description: str = ""
    old_priority: str = "normal"
    old_output: str = ""
    old_error: str | None = None
    old_created_at: datetime | None = None
    old_finished_at: datetime | None = None
    old_exit_code: int | None = None

    # New Task fields
    new_command: str = ""
    new_output: str = ""
    new_error: str | None = None
    new_created_at: datetime = field(default_factory=datetime.now)
    new_started_at: datetime | None = None
    new_finished_at: datetime | None = None
    new_exit_code: int | None = None

    # Migration metadata
    migrated_at: datetime = field(default_factory=datetime.now)
    migration_warnings: list[str] = field(default_factory=list)

    def to_new_task(self) -> "NewTask":
        """Convert to new HybridTask format.

        Returns:
            A new HybridTask instance
        """
        from .hybrid_manager import Task, TaskStatus

        # Map status
        status_value = TaskStatusMapper.map_status(self.status)
        status = TaskStatus(status_value)

        # Create new task
        new_task = Task(
            id=self.id,
            status=status,
            command=self._get_command(),
            output=self._get_output(),
            error=self._get_error(),
            created_at=self._get_created_at(),
            started_at=self.new_started_at,
            finished_at=self._get_finished_at(),
            exit_code=self._get_exit_code(),
            type=self.type,
        )

        return new_task

    def _get_command(self) -> str:
        """Get command string from old description or command."""
        if self.new_command:
            return self.new_command

        # Extract command from old description
        # Old shell tasks have description like "! command..."
        if self.old_description.startswith("! "):
            return self.old_description[2:].strip()

        # Old agent tasks have description like "Agent: prompt..."
        if self.old_description.startswith("Agent: "):
            return f"[agent] {self.old_description[7:]}"

        # Fallback to description
        return self.old_description

    def _get_output(self) -> str:
        """Get output string (prefer new, fallback to old)."""
        return self.new_output or self.old_output

    def _get_error(self) -> str | None:
        """Get error string (prefer new, fallback to old)."""
        if self.new_error:
            return self.new_error
        return self.old_error

    def _get_created_at(self) -> datetime:
        """Get created timestamp (prefer old, fallback to new)."""
        if self.old_created_at:
            return self.old_created_at
        return self.new_created_at

    def _get_finished_at(self) -> datetime | None:
        """Get finished timestamp (prefer new, fallback to old)."""
        if self.new_finished_at:
            return self.new_finished_at
        return self.old_finished_at

    def _get_exit_code(self) -> int | None:
        """Get exit code (prefer new, fallback to old)."""
        if self.new_exit_code is not None:
            return self.new_exit_code
        return self.old_exit_code


def migrate_old_task(old_task: "OldTask") -> MigratedTask:
    """Migrate an old Task to the new format.

    Args:
        old_task: Old Task instance from task.py

    Returns:
        MigratedTask with all data preserved

    Raises:
        TaskMigrationError: If migration fails
    """
    try:
        # Determine task type
        task_type = "shell" if hasattr(old_task, 'command') else "agent"

        # Create migrated task
        migrated = MigratedTask(
            id=old_task.id,
            status=old_task.status.value,
            type=task_type,
            old_description=old_task.description,
            old_priority=str(old_task.priority.value),  # Convert to string
            old_output=old_task.output,
            old_error=old_task.error,
            old_created_at=old_task.created_at,
            old_finished_at=old_task.finished_at,
            old_exit_code=old_task.exit_code,
        )

        # Add warnings for data that might be lost
        if task_type == "shell" and hasattr(old_task, 'command'):
            migrated.new_command = old_task.command

        if hasattr(old_task, '_thread') and old_task._thread:
            migrated.migration_warnings.append(
                "Task was running in background thread - state may be inconsistent"
            )

        if hasattr(old_task, '_process') and old_task._process:
            migrated.migration_warnings.append(
                "Task had active subprocess - process state not preserved"
            )

        return migrated

    except Exception as e:
        raise TaskMigrationError(f"Failed to migrate task {old_task.id}: {e}") from e


def migrate_task_manager_state(old_manager_tasks: list["OldTask"]) -> list["NewTask"]:
    """Migrate all tasks from old TaskManager to new format.

    Args:
        old_manager_tasks: List of old Task instances

    Returns:
        List of new HybridTask instances

    Raises:
        TaskMigrationError: If migration fails
    """
    migrated_tasks = []
    errors = []

    for old_task in old_manager_tasks:
        try:
            migrated = migrate_old_task(old_task)
            new_task = migrated.to_new_task()
            migrated_tasks.append(new_task)

            # Log warnings
            if migrated.migration_warnings:
                for warning in migrated.migration_warnings:
                    print(f"[Migration Warning] Task {old_task.id}: {warning}")

        except TaskMigrationError as e:
            errors.append(str(e))

    if errors:
        print(f"[Migration] Completed with {len(errors)} errors:")
        for error in errors:
            print(f"  - {error}")

    print(f"[Migration] Successfully migrated {len(migrated_tasks)}/{len(old_manager_tasks)} tasks")

    return migrated_tasks


async def migrate_and_load_tasks(old_task_ids: list[str]) -> dict[str, "NewTask"]:
    """Migrate tasks from old TaskManager and load into HybridTaskManager.

    This is the primary migration function to use during the transition.

    Args:
        old_task_ids: List of task IDs to migrate from old TaskManager

    Returns:
        Dictionary mapping task IDs to new HybridTask instances

    Example:
        ```python
        # Get tasks from old manager
        old_manager = get_task_manager()
        old_tasks = old_manager.get_all_tasks()

        # Migrate to new manager
        from kai_code.tasks.migration import migrate_and_load_tasks
        new_tasks = await migrate_and_load_tasks([t.id for t in old_tasks])

        # Load into new manager
        new_manager = get_hybrid_task_manager()
        for task_id, task in new_tasks.items():
            new_manager._tasks[task_id] = task
        ```
    """
    from .manager import get_task_manager
    from .hybrid_manager import get_hybrid_task_manager

    # Get old tasks
    old_manager = get_task_manager()
    old_tasks = [old_manager.get_task(tid) for tid in old_task_ids]
    old_tasks = [t for t in old_tasks if t is not None]

    # Migrate
    new_tasks = migrate_task_manager_state(old_tasks)

    # Create ID mapping
    task_map = {task.id: task for task in new_tasks}

    return task_map


def create_backup_migration_script() -> str:
    """Generate a backup/migration script for safe transition.

    Returns:
        Script content as string
    """
    return '''#!/usr/bin/env python3
"""Backup and migration script for TaskManager transition.

Run this script to backup existing task state before switching to
the new HybridTaskManager.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

def backup_current_tasks():
    """Backup current task state to file."""
    from kai_code.tasks import get_task_manager

    manager = get_task_manager()
    tasks = manager.get_all_tasks()

    backup_data = {
        "timestamp": datetime.now().isoformat(),
        "task_count": len(tasks),
        "tasks": []
    }

    for task in tasks:
        task_data = {
            "id": task.id,
            "type": task.type,
            "status": task.status.value,
            "priority": task.priority.value,
            "description": task.description,
            "command": getattr(task, 'command', ''),
            "prompt": getattr(task, 'prompt', ''),
            "output": task.output,
            "error": task.error,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            "exit_code": task.exit_code,
        }
        backup_data["tasks"].append(task_data)

    # Write backup
    backup_dir = Path(".kai/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_file = backup_dir / f"tasks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)

    print(f"✓ Backed up {len(tasks)} tasks to {backup_file}")
    return backup_file


def restore_tasks_from_backup(backup_file):
    """Restore tasks from backup file (for rollback)."""
    import json
    from kai_code.tasks import get_task_manager, BackgroundShellTask, BackgroundAgentTask, TaskStatus, TaskPriority

    with open(backup_file) as f:
        backup_data = json.load(f)

    manager = get_task_manager()

    for task_data in backup_data["tasks"]:
        if task_data["type"] == "shell":
            task = BackgroundShellTask(
                command=task_data.get("command", ""),
                priority=TaskPriority(task_data["priority"]),
            )
        else:
            task = BackgroundAgentTask(
                prompt=task_data.get("prompt", ""),
                priority=TaskPriority(task_data["priority"]),
            )

        # Restore state
        task.id = task_data["id"]
        task.status = TaskStatus(task_data["status"])
        task.output = task_data.get("output", "")
        task.error = task_data.get("error")
        task.exit_code = task_data.get("exit_code")

        if task_data.get("created_at"):
            task.created_at = datetime.fromisoformat(task_data["created_at"])
        if task_data.get("finished_at"):
            task.finished_at = datetime.fromisoformat(task_data["finished_at"])

        manager._tasks[task.id] = task

    print(f"✓ Restored {len(backup_data['tasks'])} tasks from {backup_file}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) < 3:
            print("Usage: python migrate.py restore <backup_file>")
            sys.exit(1)
        restore_tasks_from_backup(sys.argv[2])
    else:
        backup_current_tasks()
'''
