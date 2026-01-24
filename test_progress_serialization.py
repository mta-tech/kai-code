#!/usr/bin/env python
"""Test ToolProgress serialization and deserialization."""
import sys
sys.path.insert(0, "src")

from kai_code.progress import ProgressPhase, ToolProgress

# Test 1: Create ToolProgress
print("Test 1: Creating ToolProgress...")
progress = ToolProgress(
    tool_name="web_search",
    status_message="Searching for information...",
    phase=ProgressPhase.PROCESSING,
    percent_complete=50.0,
    details={"query": "python async", "results_count": 10}
)
print(f"  ✓ Created: {progress.tool_name} - {progress.status_message}")

# Test 2: Serialize to dict
print("\nTest 2: Serializing to dict...")
data = progress.to_dict()
print(f"  ✓ Serialized: {data}")

# Test 3: Deserialize from dict
print("\nTest 3: Deserializing from dict...")
restored = ToolProgress.from_dict(data)
print(f"  ✓ Restored: {restored.tool_name} - {restored.status_message}")

# Test 4: Verify round-trip
print("\nTest 4: Verifying round-trip...")
assert restored.tool_name == progress.tool_name
assert restored.status_message == progress.status_message
assert restored.phase == progress.phase
assert restored.percent_complete == progress.percent_complete
assert restored.details == progress.details
print(f"  ✓ All fields match after round-trip")

# Test 5: Test with_phase helper
print("\nTest 5: Testing with_phase helper...")
new_progress = progress.with_phase(ProgressPhase.COMPLETE)
assert new_progress.phase == ProgressPhase.COMPLETE
print(f"  ✓ Phase changed: {progress.phase} -> {new_progress.phase}")

# Test 6: Test with_percent helper
print("\nTest 6: Testing with_percent helper...")
new_progress = progress.with_percent(100.0)
assert new_progress.percent_complete == 100.0
print(f"  ✓ Percent changed: {progress.percent_complete}% -> {new_progress.percent_complete}%")

# Test 7: Test with_message helper
print("\nTest 7: Testing with_message helper...")
new_progress = progress.with_message("Search completed!")
assert new_progress.status_message == "Search completed!"
print(f"  ✓ Message changed: '{progress.status_message}' -> '{new_progress.status_message}'")

print("\n✓ All ToolProgress tests passed!")
print("\nToolProgress features:")
print("  • Thread-safe progress reporting")
print("  • Serialization/deserialization")
print("  • Fluent helpers for updating progress")
print("  • Phase tracking (starting, connecting, processing, etc.)")
