from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kai_code.stream_events import correlate_tool_events, detect_tool_events_from_messages


def main() -> int:
    # Simulate a snapshot with a tool call (no id) followed by a tool result (no id).
    messages = [
        {"role": "user", "content": "do thing"},
        {
            "role": "assistant",
            "content": [
                {"type": "function_call", "name": "execute", "arguments": '{"command":"pwd"}'},
                {"type": "function_response", "name": "execute", "response": {"stdout": "/tmp\n"}},
            ],
        },
    ]

    # Turn/step ids for this snapshot: 1 user message, 0 assistant messages in our heuristic? Actually assistant role counts.
    # In the CLI we pass turn_id/step_id derived from counts; we can hardcode representative values.
    events = detect_tool_events_from_messages(messages)
    correlated = correlate_tool_events(events, turn_id=0, step_id=0)

    calls = [e for e in correlated if e.kind == "tool_call"]
    results = [e for e in correlated if e.kind == "tool_result"]
    assert len(calls) == 1
    assert len(results) == 1
    assert calls[0].tool_call_id is not None
    # The pairing should assign the same id to the result.
    assert results[0].tool_call_id == calls[0].tool_call_id

    # msg_index/part_index should be present for block-based parts.
    assert calls[0].msg_index is not None
    assert calls[0].part_index is not None

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
