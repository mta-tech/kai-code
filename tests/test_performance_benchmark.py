"""Performance benchmark: Old TaskManager vs New HybridTaskManager.

Measures:
- Task spawn time (time to create and start tasks)
- Concurrent task capacity
- Memory usage
- Task completion throughput

Run with: python -m pytest tests/test_performance_benchmark.py -v --benchmark-only
Or standalone: python tests/test_performance_benchmark.py
"""
from __future__ import annotations

import asyncio
import gc
import sys
import time
import tracemalloc
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def benchmark_old_manager():
    """Benchmark old TaskManager (threading-based)."""
    from kai_code.tasks.manager import TaskManager
    from kai_code.tasks.task import TaskPriority

    print("\n=== Old TaskManager Benchmark (Threading) ===")

    manager = TaskManager()

    # Benchmark 1: Task spawn time
    print("\n1. Task spawn time (100 tasks)...")
    start = time.perf_counter()
    for i in range(100):
        manager.run_shell(f"echo 'Task {i}'", priority=TaskPriority.NORMAL)
    spawn_time = time.perf_counter() - start
    print(f"   Spawned 100 tasks in {spawn_time:.3f}s ({100/spawn_time:.1f} tasks/sec)")

    # Benchmark 2: Concurrent task capacity
    print("\n2. Concurrent task capacity...")
    print("   (Old manager uses semaphore with max_concurrent=5)")
    # Spawn slow tasks to test concurrency
    task_ids = []
    for i in range(10):
        task_id = manager.run_shell("sleep 0.5", priority=TaskPriority.NORMAL)
        task_ids.append(task_id)

    time.sleep(1.0)  # Wait for some to start
    active_count = manager.active_count()
    print(f"   Active tasks: {active_count}/10 (max ~5 due to semaphore)")

    # Wait for completion
    time.sleep(2)
    completed = sum(1 for tid in task_ids if manager.get_task(tid).status.value == "completed")
    print(f"   Completed: {completed}/10")

    # Benchmark 3: Memory usage
    print("\n3. Memory usage (100 tasks)...")
    gc.collect()
    tracemalloc.start()
    baseline = tracemalloc.take_snapshot()

    for i in range(100):
        manager.run_shell(f"echo 'Memory test {i}'", priority=TaskPriority.NORMAL)

    time.sleep(2)  # Wait for completion
    gc.collect()

    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()

    top_stats = snapshot.compare_to(baseline, 'lineno')
    total_memory = sum(stat.size_diff for stat in top_stats) / 1024  # KB
    print(f"   Memory growth: ~{total_memory:.1f} KB")

    # Cleanup
    manager.kill_all()

    return {
        "spawn_time": spawn_time,
        "spawn_rate": 100 / spawn_time,
        "active_count": active_count,
        "memory_kb": total_memory,
    }


async def benchmark_new_manager():
    """Benchmark new HybridTaskManager (async/thread hybrid)."""
    from kai_code.tasks.hybrid_manager import HybridTaskManager

    print("\n=== New HybridTaskManager Benchmark (Async/Thread) ===")

    manager = HybridTaskManager()

    # Benchmark 1: Task spawn time
    print("\n1. Task spawn time (100 tasks)...")
    start = time.perf_counter()
    for i in range(100):
        await manager.run_shell(f"echo 'Task {i}'")
    spawn_time = time.perf_counter() - start
    print(f"   Spawned 100 tasks in {spawn_time:.3f}s ({100/spawn_time:.1f} tasks/sec)")

    # Benchmark 2: Concurrent task capacity
    print("\n2. Concurrent task capacity...")
    print("   (New manager uses asyncio with max_concurrent=20)")
    # Spawn slow tasks to test concurrency
    task_ids = []
    for i in range(25):
        task_id = await manager.run_shell("sleep 0.5")
        task_ids.append(task_id)

    await asyncio.sleep(1.0)  # Wait for some to start
    active_count = manager.active_count()
    print(f"   Active tasks: {active_count}/25 (max ~20 due to asyncio limit)")

    # Wait for completion
    await asyncio.sleep(2)
    completed = sum(
        1 for tid in task_ids
        if manager.get_task(tid) and manager.get_task(tid).status.value == "completed"
    )
    print(f"   Completed: {completed}/25")

    # Benchmark 3: Memory usage
    print("\n3. Memory usage (100 tasks)...")
    gc.collect()
    tracemalloc.start()
    baseline = tracemalloc.take_snapshot()

    for i in range(100):
        await manager.run_shell(f"echo 'Memory test {i}'")

    await asyncio.sleep(2)  # Wait for completion
    gc.collect()

    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()

    top_stats = snapshot.compare_to(baseline, 'lineno')
    total_memory = sum(stat.size_diff for stat in top_stats) / 1024  # KB
    print(f"   Memory growth: ~{total_memory:.1f} KB")

    # Cleanup
    await manager.clear_all()

    return {
        "spawn_time": spawn_time,
        "spawn_rate": 100 / spawn_time,
        "active_count": active_count,
        "memory_kb": total_memory,
    }


async def benchmark_throughput():
    """Benchmark task completion throughput."""
    from kai_code.tasks.hybrid_manager import HybridTaskManager

    print("\n=== Throughput Benchmark (Quick Tasks) ===")

    manager = HybridTaskManager()

    # Test with varying concurrency levels
    for concurrency in [5, 10, 20, 50]:
        print(f"\nConcurrency: {concurrency}")

        task_ids = []
        start = time.perf_counter()

        # Spawn tasks
        for i in range(concurrency):
            task_id = await manager.run_shell("echo 'test'")
            task_ids.append(task_id)

        # Wait for all to complete
        while True:
            completed = sum(
                1 for tid in task_ids
                if manager.get_task(tid)
                and manager.get_task(tid).status.value in ("completed", "failed", "killed")
            )
            if completed >= concurrency:
                break
            await asyncio.sleep(0.05)

        elapsed = time.perf_counter() - start
        throughput = concurrency / elapsed
        print(f"  Completed {concurrency} tasks in {elapsed:.3f}s")
        print(f"  Throughput: {throughput:.1f} tasks/sec")

        await manager.clear_all()

    await manager.shutdown()


def print_comparison(old_metrics, new_metrics):
    """Print comparison between old and new managers."""
    print("\n" + "=" * 60)
    print("SUMMARY: Old vs New Performance Comparison")
    print("=" * 60)

    print("\nMetric                  | Old Manager     | New Manager     | Improvement")
    print("-" * 70)

    # Spawn rate
    spawn_improvement = new_metrics["spawn_rate"] / old_metrics["spawn_rate"]
    print(f"Spawn Rate (tasks/sec)  | {old_metrics['spawn_rate']:>8.1f}      | {new_metrics['spawn_rate']:>8.1f}      | {spawn_improvement:>9.1f}x")

    # Concurrent tasks
    concurrent_improvement = new_metrics["active_count"] / old_metrics["active_count"]
    print(f"Concurrent Tasks        | {old_metrics['active_count']:>8}      | {new_metrics['active_count']:>8}      | {concurrent_improvement:>9.1f}x")

    # Memory (lower is better, so we invert the ratio)
    if new_metrics["memory_kb"] > 0:
        memory_improvement = old_metrics["memory_kb"] / new_metrics["memory_kb"]
    else:
        memory_improvement = float('inf')
    print(f"Memory Usage (KB)       | {old_metrics['memory_kb']:>8.1f}      | {new_metrics['memory_kb']:>8.1f}      | {memory_improvement:>9.1f}x")

    print("\nKey Findings:")
    print(f"  • {spawn_improvement:.1f}x faster task spawning")
    print(f"  • {concurrent_improvement:.1f}x more concurrent tasks")
    if memory_improvement != float('inf'):
        if memory_improvement > 1:
            print(f"  • {memory_improvement:.1f}x less memory usage")
        else:
            print(f"  • {1/memory_improvement:.1f}x more memory usage (acceptable tradeoff)")

    print("\nConclusion:")
    if spawn_improvement > 2 and concurrent_improvement > 2:
        print("  ✓ HybridTaskManager is SIGNIFICANTLY faster")
    elif spawn_improvement > 1.5:
        print("  ✓ HybridTaskManager is noticeably faster")
    else:
        print("  ~ Performance is comparable")

    print("=" * 60)


async def main():
    """Run all benchmarks."""
    print("\n" + "=" * 60)
    print("PERFORMANCE BENCHMARK: TaskManager vs HybridTaskManager")
    print("=" * 60)

    # Run old manager benchmark
    old_metrics = benchmark_old_manager()

    # Run new manager benchmark
    new_metrics = await benchmark_new_manager()

    # Run throughput test
    await benchmark_throughput()

    # Print comparison
    print_comparison(old_metrics, new_metrics)

    print("\n✓ Benchmark complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(0)
