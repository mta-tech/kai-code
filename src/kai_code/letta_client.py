from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class LettaNotInstalledError(RuntimeError):
    pass


@dataclass(frozen=True)
class LettaClientConfig:
    api_key: str | None = None
    base_url: str | None = None
    project: str | None = None


def get_letta_client(config: LettaClientConfig) -> Any:
    """Create a Letta client instance.

    Kept behind an optional dependency boundary: install with `pip install kai-code[letta]`.
    """

    try:
        from letta_client import Letta  # type: ignore
    except Exception as e:  # pragma: no cover
        raise LettaNotInstalledError(
            "Letta server mode requires the optional dependency 'letta-client'. "
            "Install with: pip install kai-code[letta]"
        ) from e

    kwargs: dict[str, Any] = {}
    if config.api_key:
        kwargs["api_key"] = config.api_key
    if config.base_url:
        kwargs["base_url"] = config.base_url
    if config.project:
        kwargs["project"] = config.project

    return Letta(**kwargs)
