# Rich + asyncio Integration Patterns and Best Practices

**Research Date:** 2026-01-23
**Purpose:** Provide specific patterns and code examples for effective Rich + asyncio integration to support the Async Task System implementation.

---

## Executive Summary

This document synthesizes research from official Rich documentation, prompt_toolkit documentation, GitHub repositories, and community best practices to provide concrete implementation patterns for integrating Rich's live displays with asyncio-based applications.

**Key Findings:**
- Rich Progress class is thread-safe (uses `threading.RLock` since v13.8.1+)
- Rich Live displays had historical thread-safety issues (GitHub #1530), use with care in async contexts
- prompt_toolkit 3.0+ has native asyncio support with `patch_stdout()` for output coordination
- `asyncio.Queue` is NOT thread-safe; use `janus` library for thread-async boundaries
- Multiple concurrent Live displays supported via nesting (Rich v14.0.0+)

---

## Table of Contents

1. [Rich Live Display with asyncio](#pattern-1-rich-live-display-with-asyncio)
2. [Refresh Rate Optimization](#pattern-2-refresh-rate-optimization)
3. [Thread-Safe Updates](#pattern-3-thread-safe-updates)
4. [Integrating Rich with prompt_toolkit](#pattern-4-integrating-rich-with-prompt_toolkit)
5. [Multiple Concurrent Live Displays](#pattern-5-multiple-concurrent-live-displays)
6. [Progress Bars with Async Task Updates](#pattern-6-progress-bars-with-async-task-updates)
7. [Terminal Resize Event Handling](#pattern-7-terminal-resize-event-handling)
8. [Performance Considerations](#pattern-8-performance-considerations)

---

## Pattern 1: Rich Live Display with asyncio

### Basic Pattern

The recommended pattern for using Rich's `Live` display with asyncio:

```python
from rich.live import Live
from rich.table import Table
import asyncio

class AsyncLiveDisplay:
    """Live display that updates from async tasks."""

    def __init__(self, refresh_per_second: int = 4):
        self.live = Live(refresh_per_second=refresh_per_second)
        self._update_queue = asyncio.Queue()
        self._running = False

    async def update(self, renderable):
        """Thread-safe update from async context."""
        await self._update_queue.put(renderable)

    async def _display_loop(self):
        """Async loop that updates the Live display."""
        self._running = True
        self.live.start()

        try:
            while self._running:
                # Wait for update with timeout
                try:
                    renderable = await asyncio.wait_for(
                        self._update_queue.get(),
                        timeout=0.25
                    )
                    self.live.update(renderable)
                except asyncio.TimeoutError:
                    # Continue loop, maintains refresh rate
                    pass
        finally:
            self.live.stop()

    async def stop(self):
        """Stop the display loop."""
        self._running = False
```

### Usage Example

```python
async def main():
    display = AsyncLiveDisplay()

    # Start display in background
    display_task = asyncio.create_task(display._display_loop())

    # Simulate async task generating updates
    for i in range(10):
        table = Table()
        table.add_column("Count")
        table.add_row(str(i))
        await display.update(table)
        await asyncio.sleep(0.5)

    await display.stop()
    await display_task

asyncio.run(main())
```

### Best Practices

1. **Always use a queue for updates** - Never call `live.update()` directly from concurrent tasks
2. **Set appropriate `refresh_per_second`** - Default is 4, adjust based on needs
3. **Use context manager when possible** - Ensures cleanup on exceptions
4. **Stop gracefully** - Set flag before cancelling display task

### Official Documentation Reference

- [Rich Live Display Documentation](https://rich.readthedocs.io/en/latest/live.html)
- Basic usage with `refresh_per_second` parameter
- Auto-refresh configuration
- Transient displays for temporary output

---

## Pattern 2: Refresh Rate Optimization

### Pattern: Adaptive Refresh Based on Activity

```python
from rich.live import Live
import asyncio

class AdaptiveLiveDisplay:
    """Live display that adjusts refresh rate based on update frequency."""

    def __init__(self, base_refresh_rate: int = 4):
        self.base_refresh_rate = base_refresh_rate
        self.live = None  # Created on start
        self._last_update_time = None
        self._update_interval = 1.0 / base_refresh_rate

    async def start(self):
        """Start live display with initial refresh rate."""
        self.live = Live(refresh_per_second=self.base_refresh_rate)
        self.live.start()

    async def update(self, renderable):
        """Update with intelligent refresh timing."""
        import time
        current_time = time.time()

        if self._last_update_time:
            elapsed = current_time - self._last_update_time
            # Slow down refresh if updates are infrequent
            if elapsed > 2.0:
                self._update_interval = min(elapsed * 0.5, 1.0)
            else:
                # Speed up for rapid updates
                self._update_interval = max(elapsed * 0.8, 0.1)

        self.live.update(renderable)
        self._last_update_time = current_time
```

### Refresh Rate Guidelines

| Use Case | Recommended Rate | Rationale |
|----------|-----------------|-----------|
| Fast task status (10+ tasks) | 10-15/sec | Responsive feedback |
| Slow progress (long-running) | 1-4/sec | Reduce CPU usage |
| Status indicators | 4/sec | Balance responsiveness |
| Text output streaming | 15-30/sec | Smooth scrolling |

### Performance Optimization

```python
from rich.live import Live

# Configure for different scenarios
configs = {
    "high_frequency": {
        "refresh_per_second": 15,
        "transient": True,  # Don't persist after exit
    },
    "low_frequency": {
        "refresh_per_second": 2,
        "auto_refresh": False,  # Manual updates only
    },
    "balanced": {
        "refresh_per_second": 4,
        "auto_refresh": True,
    }
}

# Apply configuration
live = Live(**configs["balanced"])
```

### Official Documentation Reference

- [Rich Live Display - Refresh Control](https://rich.readthedocs.io/en/latest/live.html#refresh-control)
- `auto_refresh` parameter for manual update control
- `refresh_per_second` limits update frequency

---

## Pattern 3: Thread-Safe Updates

### Problem: Rich + Threading + asyncio

When mixing Rich displays with both threads and async tasks, you need thread-safe communication.

### Pattern: Using `janus` for Thread-Async Queues

```python
import asyncio
import threading
from rich.live import Live
from rich.table import Table
import janus  # pip install janus

class ThreadSafeAsyncDisplay:
    """Live display that accepts updates from both threads and async tasks."""

    def __init__(self):
        # janus provides thread-async synchronization
        self._queue = janus.Queue()
        self.live = Live(refresh_per_second=4)
        self._running = False

    def update_from_thread(self, renderable):
        """Thread-safe update from synchronous code."""
        self._queue.sync_q.put(renderable)

    async def update_from_async(self, renderable):
        """Async-safe update from async code."""
        await self._queue.async_q.put(renderable)

    async def _display_loop(self):
        """Async display loop consuming updates."""
        self._running = True
        self.live.start()

        try:
            while self._running:
                renderable = await self._queue.async_q.get()
                self.live.update(renderable)
        finally:
            self.live.stop()
            self._queue.close()

    def stop(self):
        """Stop the display."""
        self._running = False
```

### Usage Example

```python
import time
import threading

def worker_thread(display: ThreadSafeAsyncDisplay):
    """Simulate thread producing updates."""
    for i in range(5):
        table = Table()
        table.add_column("Thread Update")
        table.add_row(f"Count {i}")
        display.update_from_thread(table)
        time.sleep(0.5)

async def main():
    display = ThreadSafeAsyncDisplay()

    # Start display loop
    display_task = asyncio.create_task(display._display_loop())

    # Start thread producing updates
    thread = threading.Thread(
        target=worker_thread,
        args=(display,)
    )
    thread.start()

    # Also produce updates from async
    for i in range(5):
        table = Table()
        table.add_column("Async Update")
        table.add_row(f"Count {i}")
        await display.update_from_async(table)
        await asyncio.sleep(0.3)

    thread.join()
    display.stop()
    await display_task

asyncio.run(main())
```

### Thread Safety Insights

**Rich Progress Thread Safety:**
- ✅ **Thread-safe** - Uses `threading.RLock` internally (v13.8.1+)
- Safe to update from multiple threads

**Rich Live Thread Safety:**
- ⚠️ **Historically NOT thread-safe** - GitHub Issue #1530 (Sept 2021)
- Use queue-based pattern to avoid race conditions

**Key Source:** [GitHub Issue #1530](https://github.com/Textualize/rich/issues/1530)

### Alternatives to janus

If you prefer not to add the `janus` dependency:

```python
import asyncio
import queue
import threading

class ThreadSafeQueue:
    """Simple thread-async bridge without janus."""

    def __init__(self):
        self._queue = queue.Queue()
        self._async_queue = asyncio.Queue()
        self._running = True
        self._forward_task = None

    def put_sync(self, item):
        """Put from thread."""
        self._queue.put(item)

    async def get_async(self):
        """Get from async."""
        return await self._async_queue.get()

    async def _forwarder(self):
        """Forward from thread queue to async queue."""
        while self._running:
            try:
                # Non-blocking check
                item = await asyncio.to_thread(self._queue.get, timeout=0.1)
                await self._async_queue.put(item)
            except:
                continue

    def start(self):
        """Start forwarding."""
        self._forward_task = asyncio.create_task(self._forwarder())

    def stop(self):
        """Stop forwarding."""
        self._running = False
```

---

## Pattern 4: Integrating Rich with prompt_toolkit

### Pattern: Using `patch_stdout()` for Output Coordination

prompt_toolkit's `patch_stdout()` context manager coordinates Rich output with prompt rendering:

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.live import Live
from rich.console import Console
import asyncio

class RichPromptToolkitIntegration:
    """Integration pattern for Rich + prompt_toolkit in async context."""

    def __init__(self):
        self.console = Console()
        self.live = None
        self.session = PromptSession()

    async def display_with_prompt(self):
        """Show Rich display while accepting user input."""
        self.live = Live(refresh_per_second=4, console=self.console)
        self.live.start()

        try:
            # patch_stdout ensures Rich display and prompt don't conflict
            with patch_stdout():
                while True:
                    # Prompt is rendered below Live display
                    user_input = await self.session.prompt_async(
                        ">>> ",
                        async_=True
                    )

                    # Process input
                    if user_input == "/exit":
                        break
                    elif user_input == "/status":
                        table = self._render_status()
                        self.live.update(table)

        finally:
            self.live.stop()

    def _render_status(self):
        """Render status table."""
        from rich.table import Table
        table = Table(title="Status")
        table.add_column("Item")
        table.add_column("Value")
        table.add_row("Tasks Running", "5")
        table.add_row("Tasks Queued", "3")
        return table

async def main():
    integration = RichPromptToolkitIntegration()
    await integration.display_with_prompt()

asyncio.run(main())
```

### Best Practices for prompt_toolkit Integration

1. **Always use `patch_stdout()`** - Prevents output conflicts between Rich and prompt
2. **Use `prompt_async()` method** - Native async support in prompt_toolkit 3.0+
3. **Share the same Console** - Pass Console instance to both Live and prompt_toolkit
4. **Transient displays for prompts** - Use `transient=True` for temporary output

### Official Documentation References

- [prompt_toolkit Asyncio Documentation](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/advanced_topics/asyncio.html)
- [Rich Console Integration](https://rich.readthedocs.io/en/latest/console.html)
- `patch_stdout()` for output coordination

### Alternative: Using prompt_toolkit's `Application.run()`

For more control over the event loop:

```python
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.reactive import Variable

async def run_with_application():
    """Use prompt_toolkit Application with Rich display."""

    # Reactive variable for Rich content
    rich_content = Variable("")

    # Create layout
    layout = Layout(
        Window(
            content=lambda: rich_content.get()
        )
    )

    # Run application
    app = Application(layout=layout)

    # In async task, update Rich content
    rich_content.set("[bold]Task Status[/bold]")

    await app.run_async()
```

---

## Pattern 5: Multiple Concurrent Live Displays

### Pattern: Nested Live Displays (Rich v14.0.0+)

Rich v14.0.0+ supports nested Live displays:

```python
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import asyncio

class MultiLiveDisplay:
    """Manage multiple concurrent Live displays."""

    def __init__(self):
        self.main_live = Live(refresh_per_second=4)
        self.progress_live = None

    async def show_multiple_displays(self):
        """Show nested Live displays."""
        self.main_live.start()

        try:
            # Create table for main display
            main_table = Table()
            main_table.add_column("Component")
            main_table.add_column("Status")
            main_table.add_row("Tasks", "[green]Running[/green]")
            main_table.add_row("Progress", "[yellow]Updating[/yellow]")

            self.main_live.update(main_table)

            # Create nested Live for progress
            self.progress_live = Live(refresh_per_second=10)
            self.progress_live.start()

            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            )

            # Run progress tracker
            with progress:
                task1 = progress.add_task("Download", total=100)
                for i in range(100):
                    progress.update(task1, advance=1)
                    await asyncio.sleep(0.05)

        finally:
            if self.progress_live:
                self.progress_live.stop()
            self.main_live.stop()
```

### Alternative: Multiple Independent Live Displays

For Rich versions < 14.0.0, use separate displays:

```python
async def run_multiple_independent_displays():
    """Run multiple Live displays independently."""

    # Display 1: Task status
    status_live = Live(refresh_per_second=4)
    status_display_task = asyncio.create_task(
        run_status_display(status_live)
    )

    # Display 2: Progress bars
    progress_live = Live(refresh_per_second=10)
    progress_display_task = asyncio.create_task(
        run_progress_display(progress_live)
    )

    # Run both concurrently
    await asyncio.gather(
        status_display_task,
        progress_display_task
    )

async def run_status_display(live: Live):
    """Run status display loop."""
    live.start()
    try:
        for i in range(10):
            table = Table()
            table.add_column("Status")
            table.add_row(f"Update {i}")
            live.update(table)
            await asyncio.sleep(0.5)
    finally:
        live.stop()

async def run_progress_display(live: Live):
    """Run progress display loop."""
    live.start()
    try:
        progress = Progress()
        live.update(progress)
        task = progress.add_task("Working", total=100)
        for i in range(100):
            progress.update(task, advance=1)
            await asyncio.sleep(0.05)
    finally:
        live.stop()
```

### Best Practices

1. **Limit refresh rates** - Multiple displays multiply CPU usage
2. **Use transient displays** - Clear after completion
3. **Consider using a single Live** - Update multiple regions within one display
4. **Test for performance** - Multiple Live displays can be resource-intensive

---

## Pattern 6: Progress Bars with Async Task Updates

### Pattern: Using Rich Progress with asyncio

Rich's `Progress` class is thread-safe and works well with asyncio:

```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import asyncio

class AsyncProgressTracker:
    """Track multiple async tasks with Rich progress bars."""

    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            transient=True,
        )
        self.progress.start()
        self._tasks = {}

    def add_task(self, description: str, total: int = 100) -> str:
        """Add a new task to track."""
        task_id = self.progress.add_task(description, total=total)
        self._tasks[task_id] = {"description": description, "total": total}
        return task_id

    async def update_task(self, task_id: str, advance: float = 1):
        """Update task progress from async context."""
        self.progress.update(task_id, advance=advance)

    async def complete_task(self, task_id: str):
        """Mark task as complete."""
        self.progress.update(task_id, completed=self._tasks[task_id]["total"])

    def stop(self):
        """Stop progress display."""
        self.progress.stop()
```

### Usage Example

```python
async def long_running_task(progress: AsyncProgressTracker, task_id: str):
    """Simulate async task with progress updates."""
    for i in range(100):
        await progress.update_task(task_id, advance=1)
        await asyncio.sleep(0.05)
    await progress.complete_task(task_id)

async def main():
    tracker = AsyncProgressTracker()

    # Create multiple tasks
    tasks = []
    for i in range(5):
        task_id = tracker.add_task(f"Task {i}")
        task = asyncio.create_task(long_running_task(tracker, task_id))
        tasks.append(task)

    # Wait for all to complete
    await asyncio.gather(*tasks)
    tracker.stop()

asyncio.run(main())
```

### Advanced: Dynamic Task Addition

```python
async def dynamic_task_tracker():
    """Add and track tasks dynamically."""
    progress = Progress()
    progress.start()

    active_tasks = []

    async def worker(worker_id: int):
        task_id = progress.add_task(f"Worker {worker_id}", total=100)
        for i in range(100):
            progress.update(task_id, advance=1)
            await asyncio.sleep(0.1)

    # Add workers dynamically
    for i in range(10):
        task = asyncio.create_task(worker(i))
        active_tasks.append(task)
        await asyncio.sleep(0.5)  # Stagger task creation

    await asyncio.gather(*active_tasks)
    progress.stop()
```

### Thread-Safe Progress Updates

Since Rich Progress is thread-safe, you can update from threads:

```python
import threading
import time

def threaded_worker(progress: Progress, task_id: int):
    """Worker thread that updates progress."""
    for i in range(100):
        progress.update(task_id, advance=1)
        time.sleep(0.05)

async def mixed_thread_async_progress():
    """Mix thread and async progress updates."""
    progress = Progress()
    progress.start()

    # Create tasks
    thread_tasks = []
    async_tasks = []

    # Thread workers
    for i in range(3):
        task_id = progress.add_task(f"Thread {i}", total=100)
        thread = threading.Thread(
            target=threaded_worker,
            args=(progress, task_id)
        )
        thread.start()
        thread_tasks.append(thread)

    # Async workers
    for i in range(3):
        task_id = progress.add_task(f"Async {i}", total=100)
        task = asyncio.create_task(async_worker(progress, task_id))
        async_tasks.append(task)

    # Wait for all
    for thread in thread_tasks:
        thread.join()
    await asyncio.gather(*async_tasks)
    progress.stop()

async def async_worker(progress: Progress, task_id: int):
    """Async worker that updates progress."""
    for i in range(100):
        progress.update(task_id, advance=1)
        await asyncio.sleep(0.05)
```

### Official Documentation Reference

- [Rich Progress Display](https://rich.readthedocs.io/en/latest/progress.html)
- Thread-safe implementation details
- Multiple concurrent task tracking

---

## Pattern 7: Terminal Resize Event Handling

### Pattern: Handling Terminal Resize in asyncio

Rich handles terminal resize automatically, but you may need to react to resize events:

```python
import asyncio
import signal
from rich.live import Live
from rich.table import Table

class ResizeAwareDisplay:
    """Live display that adapts to terminal size changes."""

    def __init__(self):
        self.live = Live(refresh_per_second=4)
        self._terminal_size = self._get_terminal_size()
        self._resize_event = asyncio.Event()

    def _get_terminal_size(self):
        """Get current terminal size."""
        import shutil
        return shutil.get_terminal_size()

    async def _watch_resize(self):
        """Watch for terminal resize events."""
        import os

        def handle_resize(signum, frame):
            self._resize_event.set()

        # Register signal handler
        signal.signal(signal.SIGWINCH, handle_resize)

        while True:
            await self._resize_event.wait()

            # Update terminal size
            new_size = self._get_terminal_size()
            if new_size != self._terminal_size:
                self._terminal_size = new_size
                # Trigger re-render
                self.live.update(self._render_for_size(new_size))

            self._resize_event.clear()

    def _render_for_size(self, size):
        """Render content adapted to terminal size."""
        table = Table()
        table.add_column("Info")
        table.add_row(f"Width: {size.columns}")
        table.add_row(f"Height: {size.lines}")
        return table

    async def run(self):
        """Run resize-aware display."""
        self.live.start()

        # Start resize watcher
        resize_task = asyncio.create_task(self._watch_resize())

        try:
            # Main display loop
            while True:
                self.live.update(self._render_for_size(self._terminal_size))
                await asyncio.sleep(0.5)
        finally:
            resize_task.cancel()
            self.live.stop()
```

### Usage Example

```python
async def main():
    display = ResizeAwareDisplay()
    await display.run()

asyncio.run(main())
```

### Best Practices

1. **Debounce resize events** - Multiple resize signals fire during window drag
2. **Re-render on resize** - Update content to fit new dimensions
3. **Test edge cases** - Very small windows, zero-size terminals
4. **Graceful degradation** - Handle extreme size constraints

---

## Pattern 8: Performance Considerations

### Pattern: Optimizing Frequent Updates

High-frequency updates can impact performance. Use these patterns to optimize:

#### 1. Batch Updates

```python
class BatchedLiveDisplay:
    """Batch multiple rapid updates into single render."""

    def __init__(self, batch_interval: float = 0.1):
        self.live = Live(refresh_per_second=10)
        self._pending_updates = []
        self._batch_interval = batch_interval
        self._last_render_time = 0
        self._render_lock = asyncio.Lock()

    async def update(self, renderable):
        """Queue update for batched rendering."""
        self._pending_updates.append(renderable)

    async def _render_loop(self):
        """Render at most once per batch interval."""
        self.live.start()

        try:
            while True:
                await asyncio.sleep(self._batch_interval)

                if self._pending_updates:
                    # Take latest update
                    latest = self._pending_updates[-1]
                    self._pending_updates.clear()

                    async with self._render_lock:
                        self.live.update(latest)
        finally:
            self.live.stop()
```

#### 2. Throttle Updates

```python
class ThrottledLiveDisplay:
    """Throttle updates to maximum rate."""

    def __init__(self, max_updates_per_second: int = 10):
        self.live = Live(refresh_per_second=max_updates_per_second)
        self._min_interval = 1.0 / max_updates_per_second
        self._last_update_time = 0

    async def update(self, renderable):
        """Update only if enough time has elapsed."""
        import time
        current_time = time.time()

        if current_time - self._last_update_time >= self._min_interval:
            self.live.update(renderable)
            self._last_update_time = current_time
```

#### 3. Use Internal Console for Logging

```python
from rich.live import Live
from rich.console import Console

class LiveWithLogging:
    """Live display with internal console for logging."""

    def __init__(self):
        self.live = Live(console=Console())
        self.live.console = Console()  # Internal console

    def log(self, message: str):
        """Print message above live display."""
        self.live.console.print(message)

    def update(self, renderable):
        """Update live display."""
        self.live.update(renderable)
```

### Performance Guidelines

| Scenario | Recommended Pattern | Refresh Rate |
|----------|-------------------|--------------|
| 10+ concurrent tasks | Batch updates | 4-10/sec |
| Real-time streaming | Throttle updates | 15-30/sec |
| Status indicators | Direct updates | 1-4/sec |
| Progress bars | Built-in Progress | 10-15/sec |

### Memory Considerations

```python
# Avoid memory leaks with unbounded queues
class MemorySafeDisplay:
    """Live display with bounded update queue."""

    def __init__(self, max_queue_size: int = 100):
        self._update_queue = asyncio.Queue(maxsize=max_queue_size)
        self.live = Live(refresh_per_second=4)

    async def update(self, renderable):
        """Non-blocking update, drops oldest if queue full."""
        try:
            self._update_queue.put_nowait(renderable)
        except asyncio.QueueFull:
            # Drop oldest update
            self._update_queue.get_nowait()
            self._update_queue.put_nowait(renderable)
```

### Monitoring Performance

```python
import time
from rich.panel import Panel

class PerformanceMonitoringDisplay:
    """Monitor display update performance."""

    def __init__(self):
        self.live = Live(refresh_per_second=4)
        self._update_times = []
        self._last_update_time = None

    def update(self, renderable):
        """Update with performance tracking."""
        update_time = time.time()

        if self._last_update_time:
            interval = update_time - self._last_update_time
            self._update_times.append(interval)

            # Keep last 100 intervals
            if len(self._update_times) > 100:
                self._update_times.pop(0)

        self._last_update_time = update_time
        self.live.update(renderable)

    def get_performance_stats(self):
        """Get update performance statistics."""
        if not self._update_times:
            return "No data"

        avg_interval = sum(self._update_times) / len(self._update_times)
        min_interval = min(self._update_times)
        max_interval = max(self._update_times)

        return Panel(
            f"Average: {avg_interval:.3f}s\n"
            f"Min: {min_interval:.3f}s\n"
            f"Max: {max_interval:.3f}s\n"
            f"Updates/sec: {1/avg_interval:.1f}",
            title="Performance Stats"
        )
```

---

## Summary of Key Patterns

| Pattern | Use Case | Key Components |
|---------|----------|----------------|
| **Async Live Display** | General async live updates | `asyncio.Queue`, background task |
| **Adaptive Refresh** | Variable update frequency | Dynamic rate adjustment |
| **Thread-Safe Updates** | Mixed thread/async contexts | `janus.Queue` or custom bridge |
| **prompt_toolkit Integration** | Interactive CLI with Rich | `patch_stdout()`, `prompt_async()` |
| **Multiple Live Displays** | Complex multi-region UI | Nested Lives (v14.0.0+) or independent |
| **Progress Bars** | Task completion tracking | `Progress` class, thread-safe updates |
| **Resize Handling** | Responsive terminal UI | `SIGWINCH` signal handling |
| **Performance Optimization** | High-frequency updates | Batching, throttling, bounded queues |

---

## Implementation Recommendations for Async Task System

Based on the research, here are specific recommendations for the `AsyncTaskDisplay` class in the plan:

### 1. Use Queue-Based Updates

```python
class AsyncTaskDisplay:
    def __init__(self, manager: AsyncTaskManager):
        self.manager = manager
        self.live = Live(refresh_per_second=4)
        self._update_queue = asyncio.Queue(maxsize=100)
        self._running = False

    async def update(self, task_id: str):
        """Queue update for task status change."""
        await self._update_queue.put(task_id)

    async def _display_loop(self):
        """Process updates and re-render."""
        self.live.start()
        try:
            while self._running:
                try:
                    task_id = await asyncio.wait_for(
                        self._update_queue.get(),
                        timeout=0.25
                    )
                    table = self._render_task_list()
                    self.live.update(table)
                except asyncio.TimeoutError:
                    # Periodic refresh for durations/emojis
                    table = self._render_task_list()
                    self.live.update(table)
        finally:
            self.live.stop()
```

### 2. Integrate with prompt_toolkit

```python
async def simple_cli_with_tasks():
    """CLI with Rich task display."""
    task_manager = AsyncTaskManager()
    task_display = AsyncTaskDisplay(task_manager)

    # Start task display
    display_task = asyncio.create_task(task_display._display_loop())

    session = PromptSession()

    try:
        with patch_stdout():
            while True:
                user_input = await session.prompt_async(">>> ")

                if user_input.startswith("/run "):
                    command = user_input[5:]
                    task_id = await task_manager.run_shell(command)
                    await task_display.update(task_id)

    finally:
        await task_manager.shutdown()
        display_task.cancel()
```

### 3. Use Progress for Long-Running Tasks

```python
class AsyncProgressTracker:
    """Track async task progress with Rich Progress."""

    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            transient=True,
        )
        self.progress.start()
        self._task_ids = {}

    def add_task(self, task: AsyncTask) -> str:
        """Add Rich progress task for async task."""
        task_id = self.progress.add_task(
            task.description,
            total=100,
        )
        self._task_ids[task.id] = task_id
        return task_id

    def update_progress(self, task_id: str, advance: float = 1):
        """Update progress from async context."""
        rich_task_id = self._task_ids.get(task_id)
        if rich_task_id:
            self.progress.update(rich_task_id, advance=advance)
```

### 4. Handle Resize Events

```python
class ResizeAwareTaskDisplay(AsyncTaskDisplay):
    """Task display that adapts to terminal size."""

    async def _watch_resize(self):
        """Watch for terminal resize events."""
        self._terminal_size = shutil.get_terminal_size()

        def handle_resize(signum, frame):
            self._terminal_size = shutil.get_terminal_size()
            # Trigger re-render
            asyncio.create_task(self.update(""))

        signal.signal(signal.SIGWINCH, handle_resize)

    def _render_task_list(self) -> Table:
        """Render table adapted to terminal size."""
        width = self._terminal_size.columns

        if width < 80:
            # Compact mode for small terminals
            return self._render_compact()
        else:
            # Full table for larger terminals
            return self._render_full()
```

---

## References

### Official Documentation

- [Rich Live Display](https://rich.readthedocs.io/en/latest/live.html)
- [Rich Progress Display](https://rich.readthedocs.io/en/latest/progress.html)
- [prompt_toolkit Asyncio Integration](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/advanced_topics/asyncio.html)

### Community Resources

- [Rich GitHub Issue #1530 - Thread Safety](https://github.com/Textualize/rich/issues/1530)
- [janus Library - Thread-Async Queues](https://github.com/aio-libs/janus)
- [Real-world Async + Rich Examples](https://github.com/pydantic/pydantic-ai)
- [AsyncIO Best Practices](https://docs.python.org/3/library/asyncio-task.html)

### Example Repositories

- [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) - Rich Live with async chat
- [FoundationAgents/ReCode](https://github.com/FoundationAgents/ReCode) - Rich progress with asyncio
- [9600dev/mmr](https://github.com/9600dev/mmr) - Rich Live with asyncio and click

---

**End of Patterns Document**
