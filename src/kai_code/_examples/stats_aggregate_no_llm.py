from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kai_code.stream_events import aggregate_usage, count_turns_steps, last_stop_reason


def main() -> int:
    msgs = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": "ok",
            "response_metadata": {"stop_reason": "end_turn"},
            "usage_metadata": {"input_tokens": 3, "output_tokens": 5, "total_tokens": 8},
        },
        {
            "role": "assistant",
            "content": "more",
            "usage_metadata": {"input_tokens": 2, "output_tokens": 4, "total_tokens": 6},
        },
    ]

    u = aggregate_usage(msgs)
    assert u.prompt_tokens == 5
    assert u.completion_tokens == 9
    assert u.total_tokens == 14

    turns, steps = count_turns_steps(msgs)
    assert turns == 1
    assert steps == 2

    assert last_stop_reason(msgs) == "end_turn"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

