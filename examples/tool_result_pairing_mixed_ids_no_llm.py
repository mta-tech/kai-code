from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kai_code.stream_events import ToolEvent, correlate_tool_events


def main() -> int:
    # Simulate mixed-id streams:
    # - Two calls A and B
    # - A completes with explicit id
    # - Next result has no id and should match B (not A)
    events = [
        ToolEvent(kind="tool_call", tool_name="a", tool_call_id="A", args={}, content=None, raw={}),
        ToolEvent(kind="tool_call", tool_name="b", tool_call_id="B", args={}, content=None, raw={}),
        ToolEvent(kind="tool_result", tool_name="a", tool_call_id="A", args=None, content="ok", raw={}),
        ToolEvent(kind="tool_result", tool_name="b", tool_call_id=None, args=None, content="ok", raw={}),
    ]

    correlated = correlate_tool_events(events, turn_id=0, step_id=0)
    results = [e for e in correlated if e.kind == "tool_result"]
    assert results[0].tool_call_id == "A"
    assert results[1].tool_call_id == "B"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

