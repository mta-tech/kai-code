from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PatchResult:
    ok: bool
    output: str


_DIFF_HEADER_RE = re.compile(r"^(---|\+\+\+)\s+(?P<path>\S+)")


def _sanitize_patch_paths(patch_text: str) -> str:
    """Make patch paths safe and compatible with a root-scoped workspace.

    - Strips leading a/ and b/
    - Converts virtual paths like /foo/bar to foo/bar
    - Rejects path traversal
    """
    out_lines: list[str] = []
    for line in patch_text.splitlines():
        m = _DIFF_HEADER_RE.match(line)
        if not m:
            out_lines.append(line)
            continue

        raw_path = m.group("path")
        if raw_path in ("/dev/null", "dev/null"):
            out_lines.append(line)
            continue

        # remove quotes if any
        path = raw_path.strip('"')

        if path.startswith("a/") or path.startswith("b/"):
            path = path[2:]
        if path.startswith("/"):
            path = path.lstrip("/")
        if ".." in path or path.startswith("~"):
            raise ValueError(f"Path traversal not allowed in patch: {raw_path}")

        out_lines.append(f"{m.group(1)} {path}")

    return "\n".join(out_lines) + ("\n" if patch_text.endswith("\n") else "")


def apply_patch(root_dir: Path, patch_text: str) -> PatchResult:
    sanitized = _sanitize_patch_paths(patch_text)
    try:
        proc = subprocess.run(  # noqa: S603
            ["patch", "-p0", "-u", "--batch"],
            input=sanitized,
            text=True,
            capture_output=True,
            cwd=str(root_dir),
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return PatchResult(ok=proc.returncode == 0, output=output)
    except FileNotFoundError:
        return PatchResult(ok=False, output="Error: 'patch' binary not found")


