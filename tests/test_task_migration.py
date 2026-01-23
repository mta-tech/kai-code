"""Tests for task migration from old TaskManager to HybridTaskManager."""
from __future__ import annotations

import pickle
from datetime import datetime, timedelta

import pytest

# Import directly from module
import sys
from pathlib import Path

# Add src to path for direct imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from kai_code.tasks.migration import (
    TaskMigrationError,
    TaskStatusMapper,
    MigratedTask,
    migrate_old_task,
    migrate_task_manager_state,
)
from kai_code.tasks.task import (
    Task as OldTask,
    TaskStatus as OldTaskStatus,
    TaskPriority,
    BackgroundShellTask,
    BackgroundAgentTask,
)


class TestTaskStatusMapper:
    """Tests for TaskStatusMapper."""

    def test_map_status_queued(self):
        """Test mapping queued status."""
        assert TaskStatusMapper.map_status("queued") == "queued"

    def test_map_status_pending_to_queued(self):
        """Test that PENDING maps to QUEUED."""
        assert TaskStatusMapper.map_status("pending") == "queued"

    def test_map_status_running(self):
        """Test mapping running status."""
        assert TaskStatusMapper.map_status("running") == "running"

    def test_map_status_completed(self):
        """Test mapping completed status."""
        assert TaskStatusMapper.map_status("completed") == "completed"

    def test_map_status_failed(self):
        """Test mapping failed status."""
        assert TaskStatusMapper.map_status("failed") == "failed"

    def test_map_status_killed(self):
        """Test mapping killed status."""
        assert TaskStatusMapper.map_status("killed") == "killed"

    def test_map_status_invalid_raises_error(self):
        """Test that invalid status raises error."""
        with pytest.raises(TaskMigrationError):
            TaskStatusMapper.map_status("invalid_status")


class TestMigratedTask:
    """Tests for MigratedTask dataclass."""

    def test_create_migrated_task(self):
        """Test creating a migrated task."""
        migrated = MigratedTask(
            id="test123",
            status="completed",
            type="shell",
            old_description="! echo test",
            old_output="test output\\n",
        )

        assert migrated.id == "test123"
        assert migrated.status == "completed"
        assert migrated.type == "shell"
        assert migrated.old_description == "! echo test"

    def test_get_command_from_shell_description(self):
        """Test extracting command from shell task description."""
        migrated = MigratedTask(
            id="test123",
            status="completed",
            type="shell",
            old_description="! echo hello world",
        )

        command = migrated._get_command()
        assert command == "echo hello world"

    def test_get_command_from_agent_description(self):
        """Test extracting prompt from agent task description."""
        migrated = MigratedTask(
            id="test123",
            status="completed",
            type="agent",
            old_description="Agent: Review the code",
        )

        command = migrated._get_command()
        assert command == "[agent] Review the code"

    def test_get_command_prefers_new_command(self):
        """Test that new_command is preferred over description."""
        migrated = MigratedTask(
            id="test123",
            status="completed",
            type="shell",
            old_description="! old command",
            new_command="new command",
        )

        command = migrated._get_command()
        assert command == "new command"

    def test_to_new_task(self):
        """Test converting MigratedTask to new HybridTask."""
        from kai_code.tasks.hybrid_manager import TaskStatus

        migrated = MigratedTask(
            id="test123",
            status="completed",
            type="shell",
            old_description="! echo test",
            old_output="test output",
            old_created_at=datetime.now() - timedelta(seconds=10),
            old_finished_at=datetime.now(),
        )

        new_task = migrated.to_new_task()

        assert new_task.id == "test123"
        assert new_task.status == TaskStatus.COMPLETED
        assert new_task.command == "echo test"
        assert new_task.output == "test output"


class TestMigrateOldTask:
    """Tests for migrate_old_task function."""

    def test_migrate_shell_task(self):
        """Test migrating a shell task."""
        old_task = BackgroundShellTask(
                id="shell123",
                type="shell",
                description="! echo hello",
                command="echo hello",
                status=OldTaskStatus.COMPLETED,
            priority=TaskPriority.NORMAL,
            output="hello\\n",
        )

        migrated = migrate_old_task(old_task)

        assert migrated.id == "shell123"
        assert migrated.status == "completed"
        assert migrated.type == "shell"
        assert migrated.new_command == "echo hello"
        assert migrated.old_output == "hello\\n"

    def test_migrate_agent_task(self):
        """Test migrating an agent task."""
        old_task = BackgroundAgentTask(
                id="agent123",
                type="agent",
                description="Agent: Test prompt",
                prompt="Test prompt",
                status=OldTaskStatus.RUNNING,
            priority=TaskPriority.HIGH,
        )

        migrated = migrate_old_task(old_task)

        assert migrated.id == "agent123"
        assert migrated.status == "running"
        assert migrated.type == "agent"
        assert migrated.old_priority == "1"  # HIGH = 1

    def test_migrate_with_error(self):
        """Test migrating a task with error."""
        old_task = BackgroundShellTask(
                id="error123",
                type="shell",
                description="! false",
                command="false",
                status=OldTaskStatus.FAILED,
            error="Exit code: 1",
        )

        migrated = migrate_old_task(old_task)

        assert migrated.status == "failed"
        assert migrated.old_error == "Exit code: 1"

    def test_migrate_preserves_timestamps(self):
        """Test that timestamps are preserved."""
        created = datetime.now() - timedelta(seconds=100)
        finished = datetime.now() - timedelta(seconds=50)

        old_task = BackgroundShellTask(
                id="time123",
                type="shell",
                description="! sleep 1",
                command="sleep 1",
                status=OldTaskStatus.COMPLETED,
            created_at=created,
            finished_at=finished,
        )

        migrated = migrate_old_task(old_task)
        new_task = migrated.to_new_task()

        assert new_task.created_at == created
        assert new_task.finished_at == finished


class TestMigrateTaskManagerState:
    """Tests for migrate_task_manager_state function."""

    def test_migrate_multiple_tasks(self):
        """Test migrating multiple tasks at once."""
        old_tasks = [
            BackgroundShellTask(
                id=f"task{i}",
                type="shell",
                description=f"! echo {i}",
                command=f"echo {i}",
                status=OldTaskStatus.COMPLETED,
            )
            for i in range(5)
        ]

        new_tasks = migrate_task_manager_state(old_tasks)

        assert len(new_tasks) == 5
        for i, task in enumerate(new_tasks):
            assert task.id == f"task{i}"
            assert task.command == f"echo {i}"

    def test_migrate_with_mixed_statuses(self):
        """Test migrating tasks with various statuses."""
        old_tasks = [
            BackgroundShellTask(
                id="running",
                type="shell",
                description="! sleep 10",
                command="sleep 10",
                status=OldTaskStatus.RUNNING,
            ),
            BackgroundShellTask(
                id="completed",
                type="shell",
                description="! echo done",
                command="echo done",
                status=OldTaskStatus.COMPLETED,
            ),
            BackgroundShellTask(
                id="failed",
                type="shell",
                description="! false",
                command="false",
                status=OldTaskStatus.FAILED,
            ),
        ]

        new_tasks = migrate_task_manager_state(old_tasks)

        assert len(new_tasks) == 3
        statuses = {t.status.value for t in new_tasks}
        assert statuses == {"running", "completed", "failed"}

    def test_migrate_handles_errors_gracefully(self):
        """Test that migration continues even if some tasks fail."""
        # Create valid tasks
        old_tasks = [
            BackgroundShellTask(
                id="valid1",
                type="shell",
                description="! echo 1",
                command="echo 1",
                status=OldTaskStatus.COMPLETED,
            ),
            BackgroundShellTask(
                id="valid2",
                type="shell",
                description="! echo 2",
                command="echo 2",
                status=OldTaskStatus.COMPLETED,
            ),
        ]

        new_tasks = migrate_task_manager_state(old_tasks)

        # Should complete successfully
        assert len(new_tasks) == 2


class TestMigrationRoundtrip:
    """Tests for migration roundtrip (old -> new -> serialize -> deserialize)."""

    def test_serialization_after_migration(self):
        """Test that migrated tasks can be serialized and deserialized."""
        old_task = BackgroundShellTask(
                id="serialize123",
                type="shell",
                description="! echo test",
                command="echo test",
                status=OldTaskStatus.COMPLETED,
            output="test output\\n",
            created_at=datetime.now(),
            finished_at=datetime.now(),
        )

        # Migrate
        migrated = migrate_old_task(old_task)
        new_task = migrated.to_new_task()

        # Serialize (pickle)
        pickled = pickle.dumps(new_task)

        # Deserialize
        unpickled = pickle.loads(pickled)

        # Verify fields preserved
        assert unpickled.id == new_task.id
        assert unpickled.status == new_task.status
        assert unpickled.command == new_task.command
        assert unpickled.output == new_task.output
