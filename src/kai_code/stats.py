from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class RunStats:
    started_ms: int
    ended_ms: int
    chunk_count: int = 0
    interrupted: bool = False

    @property
    def duration_ms(self) -> int:
        return max(0, self.ended_ms - self.started_ms)


def now_ms() -> int:
    return int(time.time() * 1000)

