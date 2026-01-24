#!/usr/bin/env python
"""Demo script to showcase new CLI UX improvements.

This script demonstrates all the new visual enhancements including:
- Section headers with decorative borders
- Status indicators with icons and colors
- Error messages with suggestions
- Progress bars for multi-step operations
- Enhanced color scheme
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, "src")

from kai_code.progress import ProgressBar, ProgressPhase, ToolProgress
from kai_code.rich_config import COLORS, console
from kai_code.rich_helpers import (
    format_progress,
    print_error,
    print_section_header,
    print_status,
    print_step,
    print_summary,
)


def demo_section_headers():
    """Demonstrate section headers."""
    print("\n" + "=" * 60)
    print("DEMO: Section Headers")
    print("=" * 60)

    print_section_header("Getting Started")
    console.print("[dim]This is a section header with decorative borders.[/dim]")
    console.print()


def demo_status_indicators():
    """Demonstrate all status types."""
    print("\n" + "=" * 60)
    print("DEMO: Status Indicators")
    print("=" * 60)

    print_section_header("Operation Status")

    print_status("info", "Loading configuration...")
    time.sleep(0.3)

    print_status("processing", "Analyzing data...")
    time.sleep(0.3)

    print_status("success", "Operation completed successfully!")
    time.sleep(0.3)

    print_status("warning", "Found 2 non-critical warnings")
    time.sleep(0.3)

    print_status("error", "Connection timeout")
    console.print()


def demo_error_messages():
    """Demonstrate error formatting with suggestions."""
    print("\n" + "=" * 60)
    print("DEMO: Error Messages")
    print("=" * 60)

    print_section_header("Error Handling Examples")

    # Error without suggestion
    print_error("File not found: config.yaml")

    # Error with suggestion
    print_error(
        "Authentication failed",
        "Check your API credentials and try again"
    )

    # Multiple errors
    print_section_header("Validation Errors")
    print_error("Invalid email format", "Use format: user@example.com")
    print_error("Password too weak", "Use at least 12 characters with mixed case")
    console.print()


def demo_progress_formatting():
    """Demonstrate progress formatting."""
    print("\n" + "=" * 60)
    print("DEMO: Progress Formatting")
    print("=" * 60)

    print_section_header("Progress Display")

    # Show various progress states
    states = [
        (0, 10, "Starting"),
        (3, 10, "In progress"),
        (5, 10, "Halfway there"),
        (8, 10, "Almost done"),
        (10, 10, "Complete"),
    ]

    for current, total, label in states:
        formatted = format_progress(current, total)
        print_status("processing", f"{label}: {formatted}")
        time.sleep(0.3)

    console.print()


def demo_step_by_step():
    """Demonstrate step-by-step output."""
    print("\n" + "=" * 60)
    print("DEMO: Step-by-Step Output")
    print("=" * 60)

    print_section_header("Multi-Step Operation")

    print_step(1, "Initialize system", "Configuration loaded")
    time.sleep(0.2)

    print_step(2, "Connect to services", "Connected to 3/3 services")
    time.sleep(0.2)

    print_step(3, "Process data", "Processed 150 records")
    time.sleep(0.2)

    print_step(4, "Generate report", "Report saved to output/reports/")
    time.sleep(0.2)

    print_step(5, "Cleanup", "Temporary files removed")
    console.print()


def demo_progress_bar():
    """Demonstrate progress bar component."""
    print("\n" + "=" * 60)
    print("DEMO: Progress Bar Component")
    print("=" * 60)

    print_section_header("Long-Running Operation")

    # Create progress bar with steps
    progress = ProgressBar(total=5)
    progress.add_step("Initialize", "pending")
    progress.add_step("Download", "pending")
    progress.add_step("Process", "pending")
    progress.add_step("Validate", "pending")
    progress.add_step("Complete", "pending")

    console.print(progress.render())
    console.print()

    # Simulate progress
    steps = [
        (1, "Initialize", "complete"),
        (1, "Download", "in_progress"),
        (1, "Download", "complete"),
        (1, "Process", "in_progress"),
        (1, "Process", "complete"),
        (1, "Validate", "in_progress"),
        (1, "Validate", "complete"),
        (1, "Complete", "complete"),
    ]

    for count, step_name, status in steps:
        progress.update(count)
        console.print(f"  {format_progress(progress.current, progress.total)} - {step_name}")
        time.sleep(0.3)

    console.print()
    console.print(progress.render())
    console.print()


def demo_tool_progress():
    """Demonstrate ToolProgress for tool operations."""
    print("\n" + "=" * 60)
    print("DEMO: Tool Progress Reporting")
    print("=" * 60)

    print_section_header("Tool Execution Status")

    # Simulate tool execution with progress phases
    phases = [
        (ProgressPhase.STARTING, "Initializing web search tool", 0),
        (ProgressPhase.CONNECTING, "Connecting to search API", 10),
        (ProgressPhase.PROCESSING, "Processing search results", 50),
        (ProgressPhase.FINALIZING, "Formatting output", 90),
        (ProgressPhase.COMPLETE, "Search completed", 100),
    ]

    for phase, message, percent in phases:
        progress = ToolProgress(
            tool_name="web_search",
            status_message=message,
            phase=phase,
            percent_complete=percent,
        )
        icon = {
            ProgressPhase.STARTING: "🚀",
            ProgressPhase.CONNECTING: "🔗",
            ProgressPhase.PROCESSING: "⚙️",
            ProgressPhase.FINALIZING: "📝",
            ProgressPhase.COMPLETE: "✅",
        }.get(phase, "•")

        console.print(f"{icon} [{phase.value:12s}] {message:30s} {percent}%")
        time.sleep(0.4)

    console.print()


def demo_test_summary():
    """Demonstrate test result summary."""
    print("\n" + "=" * 60)
    print("DEMO: Test Summary")
    print("=" * 60)

    # Simulate test results
    results = {
        "test_section_headers": True,
        "test_status_indicators": True,
        "test_error_messages": True,
        "test_progress_formatting": True,
        "test_step_output": True,
        "test_progress_bar": True,
        "test_tool_progress": True,
        "test_integration": False,  # One failed test
    }

    print_summary(results)


def demo_color_scheme():
    """Demonstrate new semantic color scheme."""
    print("\n" + "=" * 60)
    print("DEMO: Semantic Color Scheme")
    print("=" * 60)

    print_section_header("Color Palette")

    colors = [
        ("primary", "Primary color (headings, accents)"),
        ("accent", "Accent color (highlights)"),
        ("success", "Success color (checkmarks, success)"),
        ("warning", "Warning color (warnings, cautions)"),
        ("error", "Error color (errors, failures)"),
        ("info", "Info color (informational messages)"),
        ("dim", "Dim color (secondary text)"),
        ("user", "User message color"),
        ("agent", "Agent message color"),
    ]

    console.print()
    for color_name, description in colors:
        hex_code = COLORS.get(color_name, "#ffffff")
        console.print(
            f"[{color_name}]■ {color_name:12s}[/] [dim]{hex_code:10s}[/] [dim]- {description}[/]"
        )

    console.print()
    console.print("[dim]Token Status Colors:[/]")
    console.print(f"  [{COLORS['token_warning']}]■ token_warning[/] [dim]{COLORS['token_warning']:10s}[/] [dim]- Token usage warning[/]")
    console.print(f"  [{COLORS['token_critical']}]■ token_critical[/] [dim]{COLORS['token_critical']:10s}[/] [dim]- Token usage critical[/]")
    console.print()


def demo_enhanced_ui_toggle():
    """Demonstrate enhanced UI environment variable."""
    print("\n" + "=" * 60)
    print("DEMO: Enhanced UI Toggle")
    print("=" * 60)

    print_section_header("Environment Variable Control")

    # Check current setting
    enhanced = os.environ.get("KAI_ENHANCED_UI", "1")
    is_enabled = enhanced in ("1", "true", "yes", "on")

    console.print()
    print_status(
        "info",
        f"KAI_ENHANCED_UI = {enhanced} ({'enabled' if is_enabled else 'disabled'})"
    )

    console.print()
    console.print("[dim]To disable enhanced UI features:[/]")
    console.print("  [dim]export KAI_ENHANCED_UI=0[/]")
    console.print()
    console.print("[dim]To re-enable enhanced UI features:[/]")
    console.print("  [dim]export KAI_ENHANCED_UI=1[/]")
    console.print("[dim]  (or simply unset the variable - defaults to enabled)[/]")
    console.print()


def main():
    """Run all demos."""
    console.print()
    console.print("[bold cyan]" + "═" * 58 + "[/bold cyan]")
    console.print("[bold cyan]  CLI UX Improvements Demonstration[/bold cyan]")
    console.print("[bold cyan]" + "═" * 58 + "[/bold cyan]")
    console.print()
    console.print("[dim]This demo showcases the new CLI UX features:[/dim]")
    console.print("[dim]• Consistent formatting with helper functions[/dim]")
    console.print("[dim]• Enhanced status indicators with icons[/dim]")
    console.print("[dim]• Error messages with helpful suggestions[/dim]")
    console.print("[dim]• Progress tracking components[/dim]")
    console.print("[dim]• Semantic color scheme[/dim]")
    console.print()

    try:
        demo_section_headers()
        demo_status_indicators()
        demo_error_messages()
        demo_progress_formatting()
        demo_step_by_step()
        demo_progress_bar()
        demo_tool_progress()
        demo_color_scheme()
        demo_enhanced_ui_toggle()
        demo_test_summary()

        print_section_header("Demo Complete")
        console.print("[green]✓ All CLI UX features demonstrated successfully![/green]")
        console.print()
        console.print("[dim]For more information, see:[/dim]")
        console.print("  [dim]• docs/cli-ux-guide.md - User guide[/dim]")
        console.print("  [dim]• examples/cli_output_demo.py - Code examples[/dim]")
        console.print()

    except KeyboardInterrupt:
        console.print()
        print_error("Demo interrupted by user", "Run again to see the full demo")
        sys.exit(1)
    except Exception as e:
        console.print()
        print_error(f"Demo error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
