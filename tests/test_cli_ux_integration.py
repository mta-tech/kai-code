"""Integration tests for CLI UX improvements.

Tests complete workflows using multiple helper functions together,
verifying that the enhanced UI components work correctly in practice.
"""

import os

from kai_code.progress import ProgressBar, ProgressPhase, ToolProgress
from kai_code.rich_config import _parse_bool_env
from kai_code.rich_helpers import (
    format_progress,
    print_error,
    print_section_header,
    print_status,
    print_step,
    print_summary,
)


def test_full_workflow_with_all_helpers(capsys):
    """Test complete workflow using all helper functions together."""
    # Simulate a multi-step operation
    print_section_header("Test Operation")

    print_step(1, "Initialize operation", "Config loaded")
    print_status("success", "Initialization complete")

    print_step(2, "Process data", "5 records processed")
    print_status("processing", "Processing in progress")

    print_step(3, "Finalize operation", "Operation complete")
    print_status("success", "Operation finished successfully")

    results = {
        "test_init": True,
        "test_process": True,
        "test_finalize": False,
    }
    print_summary(results)

    captured = capsys.readouterr()

    # Verify all components present
    assert "Test Operation" in captured.out
    assert "Initialize operation" in captured.out
    assert "Process data" in captured.out
    assert "Finalize operation" in captured.out
    assert "✓" in captured.out or "success" in captured.out
    assert "Summary" in captured.out
    assert "2/3" in captured.out


def test_error_message_workflow(capsys):
    """Test error message workflow with suggestions."""
    # Simulate error handling flow
    print_status("error", "Connection failed")

    print_error(
        "Unable to connect to server",
        "Check your network connection and server status"
    )

    print_status("info", "Retrying in 5 seconds...")

    captured = capsys.readouterr()

    # Verify error formatting
    assert "Connection failed" in captured.out
    assert "Unable to connect to server" in captured.out
    assert "Suggestion:" in captured.out
    assert "Check your network connection" in captured.out
    assert "Retrying" in captured.out


def test_progress_bar_workflow(capsys):
    """Test progress bar through complete lifecycle."""
    progress = ProgressBar(total=4)

    # Add steps
    progress.add_step("Initialize", "pending")
    progress.add_step("Configure", "pending")
    progress.add_step("Execute", "pending")
    progress.add_step("Finalize", "pending")

    # Update progress
    progress.update(1)
    assert progress.format() == "25% (1/4)"

    progress.update(1)
    assert progress.format() == "50% (2/4)"

    progress.update(1)
    assert progress.format() == "75% (3/4)"

    progress.update(1)
    assert progress.format() == "100% (4/4)"
    assert progress.is_complete()

    # Render final state
    output = progress.render()
    assert "Progress: 100% (4/4)" in output
    assert "Step 1:" in output
    assert "Step 4:" in output


def test_tool_progress_workflow(capsys):
    """Test ToolProgress through complete lifecycle."""
    # Create initial progress
    progress = ToolProgress(
        tool_name="test_tool",
        status_message="Starting operation",
        phase=ProgressPhase.STARTING,
        percent_complete=0.0,
    )

    # Update through phases
    progress = progress.with_phase(ProgressPhase.PROCESSING)
    progress = progress.with_message("Processing data")
    progress = progress.with_percent(50.0)

    assert progress.phase == ProgressPhase.PROCESSING
    assert progress.percent_complete == 50.0
    assert progress.status_message == "Processing data"

    # Complete
    progress = progress.with_phase(ProgressPhase.COMPLETE)
    progress = progress.with_percent(100.0)
    progress = progress.with_message("Operation complete")

    assert progress.phase == ProgressPhase.COMPLETE
    assert progress.percent_complete == 100.0

    # Test serialization
    data = progress.to_dict()
    assert data["tool_name"] == "test_tool"
    assert data["phase"] == "complete"

    # Test deserialization
    restored = ToolProgress.from_dict(data)
    assert restored.tool_name == progress.tool_name
    assert restored.phase == progress.phase
    assert restored.percent_complete == progress.percent_complete


def test_format_progress_edge_cases():
    """Test format_progress with edge cases."""
    # Zero total
    assert format_progress(5, 0) == "0% (0/0)"

    # Negative current (normalized to 0)
    assert format_progress(-1, 10) == "0% (0/10)"

    # Current > total (capped at 100%)
    assert format_progress(15, 10) == "100% (15/10)"

    # Normal case
    assert format_progress(3, 4) == "75% (3/4)"


def test_enhanced_ui_environment_variable():
    """Test KAI_ENHANCED_UI environment variable."""
    # Test default (enabled)
    result = _parse_bool_env("KAI_ENHANCED_UI", default=True)
    assert result is True

    # Test explicit disable
    os.environ["KAI_ENHANCED_UI"] = "0"
    result = _parse_bool_env("KAI_ENHANCED_UI", default=True)
    assert result is False

    # Test explicit enable
    os.environ["KAI_ENHANCED_UI"] = "1"
    result = _parse_bool_env("KAI_ENHANCED_UI", default=False)
    assert result is True

    # Cleanup
    os.environ.pop("KAI_ENHANCED_UI", None)


def test_multi_step_operation_with_status_updates(capsys):
    """Test multi-step operation with various status types."""
    print_section_header("Multi-Step Operation")

    # Step 1: Starting
    print_step(1, "Initialize system", None)
    print_status("info", "Loading configuration...")

    # Step 2: Processing
    print_step(2, "Process data", None)
    print_status("processing", "Working on task 1/3...")
    print_status("processing", "Working on task 2/3...")
    print_status("processing", "Working on task 3/3...")
    print_status("success", "All tasks completed")

    # Step 3: Warning
    print_step(3, "Validate results", "Minor issues detected")
    print_status("warning", "Found 2 non-critical warnings")

    # Step 4: Complete
    print_step(4, "Generate report", "Report saved to output.txt")
    print_status("success", "Operation completed successfully")

    captured = capsys.readouterr()

    # Verify all status types present
    assert "Multi-Step Operation" in captured.out
    assert "Initialize system" in captured.out
    assert "Process data" in captured.out
    assert "Validate results" in captured.out
    assert "Generate report" in captured.out
    assert "Loading configuration" in captured.out
    assert "All tasks completed" in captured.out
    assert "non-critical warnings" in captured.out
    assert "Operation completed" in captured.out
