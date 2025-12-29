from __future__ import annotations

import os
from pathlib import Path


def _parse_env_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export ") :].lstrip()
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if (len(value) >= 2) and ((value[0] == value[-1]) and value[0] in {'"', "'"}):
        value = value[1:-1]
    return key, value


def load_env_file(path: Path, *, override: bool = False) -> bool:
    """Load a .env-style file into os.environ.

    - Does not override existing env vars unless override=True.
    - Returns True if file existed and was read.
    """

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False

    for raw in text.splitlines():
        parsed = _parse_env_line(raw)
        if not parsed:
            continue
        k, v = parsed
        if not override and os.environ.get(k) is not None:
            continue
        os.environ[k] = v
    return True


def load_dotenv(*, root_dir: Path | None = None, override: bool = False) -> None:
    """Best-effort .env loading.

    Loads from:
      1) cwd/.env
      2) root_dir/.env (if provided and different)
    """

    cwd = Path.cwd().resolve()
    load_env_file(cwd / ".env", override=override)
    if root_dir is not None:
        root = root_dir.resolve()
        if root != cwd:
            load_env_file(root / ".env", override=override)
