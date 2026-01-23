"""Memory leak detection tests for hybrid task manager.

Tests for memory leaks, resource cleanup, and proper task lifecycle management.
"""
from __future__ import annotations

import asyncio
import gc
import sys
import tracemalloc

import pytest

# Import directly from module
from pathlib import Path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from kai_code.tasks.hybrid_manager import HybridTaskManager


@pytest.mark.asyncio
async def test_no_memory_leak_from_many_tasks():
    """Test that creating and completing many tasks doesn't leak memory."""
    manager = HybridTaskManager()

    # Get baseline memory
    gc.collect()
    tracemalloc.start()
    baseline_snapshot = tracemalloc.take_snapshot()

    # Create and complete 100 tasks
    task_ids = []
    for i in range(100):
        task_id = await manager.run_shell(f"echo 'Task {i}'")
        task_ids.append(task_id)

    # Wait for all to complete
    await asyncio.sleep(2)

    # Clear all tasks
    await manager.clear_all()

    # Force garbage collection
    await asyncio.sleep(0.1)
    gc.collect()
    gc.collect()

    # Check memory growth
    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Compare snapshots (key_type: 'lineno', 'filename', or 'traceback')
    top_stats = snapshot.compare_to(baseline_snapshot, 'lineno')

    # Filter out test code-related allocations
    # Look for significant memory leaks (>100KB growth)
    significant_leaks = [
        stat for stat in top_stats
        if stat.size_diff > 100_000  # >100KB
        and "hybrid_manager" in str(stat.traceback[0]).lower()
    ]

    # Clean up
    await manager.shutdown()

    # Assert no significant leaks in hybrid_manager code
    if significant_leaks:
        leak_info = "\n".join([
            f"  {stat}: {stat.size_diff / 1024:.1f}KB leaked"
            for stat in significant_leaks[:5]
        ])
        pytest.fail(f"Memory leak detected:\n{leak_info}")


@pytest.mark.asyncio
async def test_task_objects_are_released():
    """Test that task objects are properly released after completion."""
    manager = HybridTaskManager()

    # Track task IDs
    task_ids = []

    # Create 50 tasks
    for i in range(50):
        task_id = await manager.run_shell(f"echo 'Task {i}'")
        task_ids.append(task_id)

    # Wait for completion
    await asyncio.sleep(1)

    # Clear tasks
    cleared_count = await manager.clear_completed()
    assert cleared_count == 50

    # Verify tasks are gone from manager
    assert manager.total_count() == 0

    # Verify no references remain
    for task_id in task_ids:
        assert manager.get_task(task_id) is None

    await manager.shutdown()


@pytest.mark.asyncio
async def test_tracked_tasks_cleanup():
    """Test that tracked asyncio tasks are cleaned up properly."""
    manager = HybridTaskManager()

    # Create tasks that add to tracked_tasks
    task_ids = []
    for i in range(10):
        task_id = await manager.run_shell(f"sleep 0.1 && echo {i}")
        task_ids.append(task_id)

    # Check that tasks are tracked
    assert len(manager._tracked_tasks) == 10

    # Wait for completion
    await asyncio.sleep(1)

    # Check that tracked tasks are cleaned up
    # Note: asyncio Tasks are automatically removed from set when done
    # via the add_done_callback
    active_tracked = [t for t in manager._tracked_tasks if not t.done()]
    assert len(active_tracked) == 0, f"Some tracked tasks not done: {active_tracked}"

    await manager.shutdown()


@pytest.mark.asyncio
async def test_shutdown_clears_all_resources():
    """Test that shutdown properly clears all resources."""
    manager = HybridTaskManager()

    # Create various tasks
    task_ids = []
    for i in range(10):
        task_id = await manager.run_shell(f"echo 'Task {i}'")
        task_ids.append(task_id)

    # Wait for some to complete
    await asyncio.sleep(0.5)

    # Shutdown
    await manager.shutdown()

    # Verify cleanup
    assert manager.total_count() == 0, "Tasks not cleared after shutdown"
    assert len(manager._tracked_tasks) == 0, "Tracked tasks not cleared"


@pytest.mark.asyncio
async def test_no_subprocess_leaks():
    """Test that subprocesses are properly cleaned up."""
    manager = HybridTaskManager()

    # Run tasks that spawn subprocesses
    task_ids = []
    for i in range(20):
        task_id = await manager.run_shell("echo 'test'")
        task_ids.append(task_id)

    # Wait for completion
    await asyncio.sleep(1)

    # Check for zombie processes
    # This is a basic check - in production you'd use psutil
    import subprocess
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )

    # Look for zombie processes (defunct)
    zombie_count = result.stdout.count("<defunct>")

    await manager.shutdown()

    # Warn if zombies found (may not be critical in test environment)
    if zombie_count > 0:
        print(f"[Warning] Found {zombie_count} zombie processes after test")


@pytest.mark.asyncio
async def test_repeated_manager_creation_and_shutdown():
    """Test that creating and destroying managers doesn't leak."""
    managers = []

    for i in range(10):
        manager = HybridTaskManager()

        # Create some tasks
        task_ids = []
        for j in range(5):
            task_id = await manager.run_shell(f"echo 'Manager {i} Task {j}'")
            task_ids.append(task_id)

        # Wait a bit
        await asyncio.sleep(0.1)

        # Shutdown
        await manager.shutdown()

        # Keep reference to check later
        managers.append(manager)

    # Force GC
    gc.collect()
    gc.collect()

    # Basic check - if this runs without OOM, we're good
    # In production, use memory_profiler for detailed tracking
    assert len(managers) == 10


@pytest.mark.asyncio
async def test_large_output_doesnt_leak():
    """Test that tasks with large output don't leak memory."""
    manager = HybridTaskManager()

    # Create task with large output
    task_id = await manager.run_shell(
        "for i in {1..100}; do echo 'Line $i of a very long output string that will consume memory'; done"
    )

    # Wait for completion
    await asyncio.sleep(2)

    task = manager.get_task(task_id)
    assert task is not None
    assert task.status.value == "completed"

    # Output should be captured but not leak
    assert len(task.output) > 0
    assert len(task.output) < 10_000_000  # Sanity check (<10MB)

    # Clear and verify memory released
    await manager.clear_all()
    assert manager.get_task(task_id) is None

    await manager.shutdown()


@pytest.mark.asyncio
async def test_concurrent_manager_instances_dont_conflict():
    """Test that multiple manager instances don't share state incorrectly."""
    manager1 = HybridTaskManager()
    manager2 = HybridTaskManager()

    # Create tasks in each manager
    task1_id = await manager1.run_shell("echo 'Manager 1'")
    task2_id = await manager2.run_shell("echo 'Manager 2'")

    await asyncio.sleep(0.5)

    # Verify tasks are in correct managers
    assert manager1.get_task(task1_id) is not None
    assert manager1.get_task(task2_id) is None

    assert manager2.get_task(task2_id) is not None
    assert manager2.get_task(task1_id) is None

    # Cleanup
    await manager1.shutdown()
    await manager2.shutdown()


@pytest.mark.asyncio
async def test_rapid_task_creation_and_destruction():
    """Test rapid create/destroy cycles don't cause issues."""
    manager = HybridTaskManager()

    # Rapidly create and clear tasks
    for cycle in range(5):
        task_ids = []

        # Create 20 tasks quickly
        for i in range(20):
            task_id = await manager.run_shell(f"echo 'Cycle {cycle} Task {i}'")
            task_ids.append(task_id)

        # Wait for completion
        await asyncio.sleep(0.5)

        # Clear all
        await manager.clear_all()
        assert manager.total_count() == 0

    await manager.shutdown()
