from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def letta_global_settings_path() -> Path:
    return Path.home() / ".letta" / "settings.json"


def letta_local_settings_path(root_dir: Path) -> Path:
    return root_dir / ".letta" / "settings.local.json"


@dataclass
class LettaSettings:
    last_agent: str | None = None
    env: dict[str, str] | None = None


@dataclass
class LettaProjectSettings:
    last_agent: str | None = None


def load_letta_settings() -> LettaSettings:
    data = _read_json(letta_global_settings_path())
    last_agent = data.get("lastAgent")
    if not isinstance(last_agent, str) or not last_agent.strip():
        last_agent = None
    env = data.get("env")
    if not isinstance(env, dict):
        env = None
    else:
        env = {str(k): str(v) for k, v in env.items() if isinstance(k, str) and isinstance(v, str)}
    return LettaSettings(last_agent=last_agent, env=env)


def update_letta_settings(*, last_agent: str | None = None, env: dict[str, str] | None = None) -> None:
    path = letta_global_settings_path()
    data = _read_json(path)
    if last_agent is not None:
        data["lastAgent"] = last_agent
    if env is not None:
        data["env"] = env
    _write_json(path, data)


def load_letta_project_settings(root_dir: Path) -> LettaProjectSettings:
    data = _read_json(letta_local_settings_path(root_dir))
    last_agent = data.get("lastAgent")
    if not isinstance(last_agent, str) or not last_agent.strip():
        last_agent = None
    return LettaProjectSettings(last_agent=last_agent)


def update_letta_project_settings(root_dir: Path, *, last_agent: str | None) -> None:
    path = letta_local_settings_path(root_dir)
    data = _read_json(path)
    if last_agent is not None:
        data["lastAgent"] = last_agent
    _write_json(path, data)
