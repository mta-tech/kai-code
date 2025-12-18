from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .settings import load_settings, update_local_resume


@dataclass
class KaiProjectSettings:
    """Project-local CLI settings (parity with letta-code's per-directory resume).

    Stored in `root_dir/.kai/settings.local.json`.
    """

    last_session: str | None = None  # path relative to root_dir
    agents: dict[str, str] | None = None  # agent name -> relative session path

    @classmethod
    def load(cls, root_dir: Path) -> "KaiProjectSettings":
        settings = load_settings(root_dir)
        return cls(last_session=settings.last_session, agents=dict(settings.agents or {}))

    def save(self, root_dir: Path) -> None:
        # Only update resume-related fields; do not clobber other local settings.
        update_local_resume(root_dir, last_session=self.last_session, agents=self.agents or {})
