from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agent import KaiAgent
from .permissions import PermissionConfig


@dataclass(frozen=True)
class BlockProvenance:
    label: str
    source: str  # "global" | "project" | "new" (kept for parity)


@dataclass(frozen=True)
class AgentProvenance:
    is_new: bool
    fresh_blocks: bool
    blocks: list[BlockProvenance]


@dataclass(frozen=True)
class CreateAgentResult:
    agent: KaiAgent
    provenance: AgentProvenance


def create_agent(
    *,
    root_dir: str | Path = ".",
    model: str | None = None,
    force_new_blocks: bool = False,
    skills_directory: str = ".skills",
    yolo: bool = True,
    permissions: PermissionConfig | None = None,
    state_path: str | Path | None = None,
    system_prompt: str | None = None,
) -> CreateAgentResult:
    """Create a new local KaiAgent session.

    This mirrors `letta-code`'s `createAgent()` shape, but for local sessions:
    - `force_new_blocks` maps to creating a new session file (`state_path`) when provided.
    """
    root = Path(root_dir).expanduser().resolve()

    agent = KaiAgent(
        root_dir=root,
        model=model,
        yolo=yolo,
        skills_dir=skills_directory,
        state_path=state_path,
        permissions=permissions,
        system_prompt=system_prompt,
    )

    provenance = AgentProvenance(is_new=True, fresh_blocks=force_new_blocks, blocks=[])
    return CreateAgentResult(agent=agent, provenance=provenance)


# TypeScript-compat alias
createAgent = create_agent
