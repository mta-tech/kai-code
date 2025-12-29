from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kai_code.stream_events import ToolEvent, synthesize_tool_call_id


def main() -> int:
    e1 = ToolEvent(
        kind="tool_call",
        tool_name="execute",
        tool_call_id=None,
        args={"command": "ls"},
        content=None,
        raw={},
        msg_index=3,
        part_index=0,
    )
    e2 = ToolEvent(
        kind="tool_call",
        tool_name="execute",
        tool_call_id=None,
        args={"command": "ls"},
        content=None,
        raw={},
        msg_index=3,
        part_index=1,
    )

    id1 = synthesize_tool_call_id(e1, turn_id=0, step_id=0)
    id1b = synthesize_tool_call_id(e1, turn_id=0, step_id=0)
    id2 = synthesize_tool_call_id(e2, turn_id=0, step_id=0)

    assert id1 == id1b
    assert id1 != id2
    assert id1.startswith("kai_")

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

