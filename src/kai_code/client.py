from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agent import KaiAgent
from .permissions import PermissionConfig


@dataclass(frozen=True)
class KaiClient:
    """Thin compatibility wrapper inspired by `letta-code`'s `getClient()`.

    In `letta-code`, `getClient()` returns a Letta API client.
    In this Python port, we operate locally; `KaiClient` is a convenience
    factory for creating/opening `KaiAgent` sessions under a project root.
    """

    root_dir: Path

    def open_agent(
        self,
        *,
        state_path: str | Path | None = None,
        model: str | None = None,
        yolo: bool = True,
        interrupt_on: dict[str, bool] | None = None,
        skills_dir: str = ".skills",
        system_prompt: str | None = None,
        permissions: PermissionConfig | None = None,
        enabled_tools: list[str] | None = None,
    ) -> KaiAgent:
        return KaiAgent(
            root_dir=self.root_dir,
            state_path=state_path,
            model=model,
            yolo=yolo,
            interrupt_on=interrupt_on,
            skills_dir=skills_dir,
            system_prompt=system_prompt,
            permissions=permissions,
            enabled_tools=enabled_tools,
        )


def get_client(*, root_dir: str | Path | None = None) -> KaiClient:
    """Return a local client bound to a project root."""
    root = Path(root_dir).expanduser().resolve() if root_dir else Path.cwd().resolve()
    return KaiClient(root_dir=root)


# TypeScript-compat alias
getClient = get_client
