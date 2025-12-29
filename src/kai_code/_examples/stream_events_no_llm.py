from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kai_code.stream_events import detect_tool_events_from_message
from kai_code.stream_events import synthesize_tool_call_id


def main() -> int:
    tool_call_msg = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "execute", "arguments": '{"command":"ls"}'},
            }
        ],
    }
    events = detect_tool_events_from_message(tool_call_msg)
    assert len(events) == 1
    assert events[0].kind == "tool_call"
    assert events[0].tool_name == "execute"
    assert events[0].tool_call_id == "call_1"

    # Synthesis keeps existing IDs unchanged.
    assert synthesize_tool_call_id(events[0], turn_id=0, step_id=0) == "call_1"

    tool_result_msg = {
        "role": "tool",
        "tool_call_id": "call_1",
        "name": "execute",
        "content": "ok",
    }
    events2 = detect_tool_events_from_message(tool_result_msg)
    assert len(events2) == 1
    assert events2[0].kind == "tool_result"
    assert events2[0].tool_call_id == "call_1"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
