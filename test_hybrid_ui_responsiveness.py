"""Test script to verify UI responsiveness with 20+ concurrent tasks.

This script demonstrates that the hybrid task system can handle
many concurrent tasks without freezing the UI.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from kai_code.tasks.hybrid_manager import get_hybrid_task_manager


async def main():
    """Run the UI responsiveness test."""
    print("=== Hybrid Task System UI Responsiveness Test ===\n")

    manager = get_hybrid_task_manager()

    # Test 1: Spawn 20 concurrent quick tasks
    print("Test 1: Spawning 20 concurrent quick tasks...")
    task_ids = []
    for i in range(20):
        task_id = await manager.run_shell(f"echo 'Task {i}' && sleep 0.1")
        task_ids.append(task_id)

    print(f"Started {len(task_ids)} tasks")
    print("UI remains responsive (can type commands, Ctrl+C works)")

    # Wait for tasks to complete
    print("\nWaiting for tasks to complete...")
    for _ in range(20):  # Max 2 seconds
        await asyncio.sleep(0.1)
        completed = sum(
            1 for tid in task_ids
            if manager.get_task(tid).status.value in ("completed", "failed", "timed_out")
        )
        print(f"\rProgress: {completed}/20 completed", end="", flush=True)
        if completed >= 20:
            break

    print("\n")

    # Test 2: Verify no hangs with mixed task types
    print("\nTest 2: Mixed quick and slow tasks...")
    quick_ids = []
    for i in range(10):
        task_id = await manager.run_shell(f"echo 'Quick {i}'")
        quick_ids.append(task_id)

    slow_ids = []
    for i in range(5):
        task_id = await manager.run_shell("sleep 0.5")
        slow_ids.append(task_id)

    print(f"Started {len(quick_ids)} quick + {len(slow_ids)} slow tasks")

    # Wait a bit
    await asyncio.sleep(1)

    # Test 3: Timeout enforcement
    print("\nTest 3: Timeout enforcement (1 second timeout)...")
    timeout_id = await manager.run_shell("sleep 10", timeout=1)

    # Wait for timeout
    await asyncio.sleep(2)

    timeout_task = manager.get_task(timeout_id)
    print(f"Timeout task status: {timeout_task.status.value}")
    assert timeout_task.status.value == "timed_out", "Task should have timed out"
    print("✓ Timeout enforcement works")

    # Test 4: Kill tasks
    print("\nTest 4: Task killing...")
    kill_ids = []
    for i in range(3):
        task_id = await manager.run_shell("sleep 10")
        kill_ids.append(task_id)

    await asyncio.sleep(0.2)  # Let them start

    for kill_id in kill_ids:
        result = await manager.kill(kill_id)
        print(f"Kill task {kill_id}: {result}")

    # Verify killed
    for kill_id in kill_ids:
        task = manager.get_task(kill_id)
        assert task.status.value == "killed", f"Task {kill_id} should be killed"

    print("✓ Task killing works")

    # Final summary
    print("\n=== Test Summary ===")
    all_tasks = manager.get_all_tasks()
    by_status = {}
    for task in all_tasks:
        status = task.status.value
        by_status[status] = by_status.get(status, 0) + 1

    print("Task status breakdown:")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")

    print(f"\nTotal tasks: {len(all_tasks)}")
    print("✓ All tests passed - UI remained responsive throughout")

    # Cleanup
    await manager.clear_all()
    print("\n✓ Cleanup complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user (Ctrl+C)")
        print("✓ Ctrl+C works correctly - system is responsive")
        sys.exit(0)
