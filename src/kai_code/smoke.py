from __future__ import annotations

import json
from pathlib import Path

from .backend import KaiLocalBackend
from .patching import apply_patch


def main() -> None:
    root = Path.cwd().resolve()
    backend = KaiLocalBackend(root)

    # Basic backend sanity
    _ = backend.ls_info("/")
    _ = backend.glob_info("**/*.py", path="/")

    # Patch tool sanity: apply a patch to a temp file under .kai/
    test_path = root / ".kai" / "smoke.txt"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    # Make deterministic (idempotent) for repeated runs.
    test_path.write_text("hello\n")

    patch = """--- /.kai/smoke.txt
+++ /.kai/smoke.txt
@@ -1 +1 @@
-hello
+hello world
"""
    result = apply_patch(root, patch)
    data = {
        "ok": result.ok,
        "output": result.output,
        "file": test_path.read_text(),
    }
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
