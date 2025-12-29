from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kai_code.stream_events import detect_tool_events_from_message


def main() -> int:
    # Anthropic tool_use/tool_result blocks
    anthropic_msg = {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": "tu_1", "name": "execute", "input": {"command": "ls"}},
            {"type": "text", "text": "running"},
            {"type": "tool_result", "tool_use_id": "tu_1", "content": "ok"},
        ],
    }
    ev = detect_tool_events_from_message(anthropic_msg)
    kinds = [e.kind for e in ev]
    assert "tool_call" in kinds
    assert "tool_result" in kinds

    # Google function_call part
    google_msg = {
        "role": "assistant",
        "content": [
            {
                "type": "function_call",
                "name": "execute",
                "arguments": '{"command":"pwd"}',
            }
        ],
    }
    ev2 = detect_tool_events_from_message(google_msg)
    assert len(ev2) == 1
    assert ev2[0].kind == "tool_call"
    assert ev2[0].tool_name == "execute"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

