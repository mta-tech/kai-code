"""Example showing improved CLI output formatting."""
from kai_code.rich_helpers import (
    print_section_header,
    print_status,
    print_step,
    print_summary,
)


def demo_improved_output():
    """Demonstrate improved CLI output."""
    # Section header
    print_section_header("Testing Auto-Nudge Feature")

    # Step-by-step output
    print_step(1, "Creating agent...")
    print_status("processing", "Agent initialization in progress")
    
    print_step(2, "Checking registries...")
    print_step(2, "", "Agent ID: d28e7add")
    print_step(2, "", "Agent registered: True")

    print_step(3, "Creating background task...")
    print_step(3, "", "Task ID: 847b52b2")

    # Status updates
    print_status("processing", "Waiting for task to complete...")
    print_status("success", "Task completed successfully")

    # Summary
    results = {
        "Auto-nudge feature": True,
        "Multiple agents": True,
        "Edge cases": True,
    }
    print_summary(results)


if __name__ == "__main__":
    demo_improved_output()
