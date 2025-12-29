from __future__ import annotations

import pickle
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig


class KaiFileCheckpointer(MemorySaver):
    """Disk-backed checkpointer.

    LangGraph ships an in-memory saver by default. For HITL resume to survive
    process restarts we persist the internal structures to a local pickle file.

    This is a pragmatic local-development choice and is not meant to be a secure
    multi-tenant store.
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = pickle.loads(self._path.read_bytes())
            if not isinstance(data, dict):
                return
            storage = data.get("storage")
            writes = data.get("writes")
            blobs = data.get("blobs")
            if isinstance(storage, dict):
                self.storage = defaultdict(lambda: defaultdict(dict))
                for thread_id, ns_map in storage.items():
                    if not isinstance(thread_id, str) or not isinstance(ns_map, dict):
                        continue
                    self.storage[thread_id] = ns_map
            if isinstance(writes, dict):
                self.writes = defaultdict(dict)
                self.writes.update(writes)
            if isinstance(blobs, dict):
                self.blobs = blobs
        except Exception:
            return

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)

            def _plain(obj: Any) -> Any:
                if isinstance(obj, dict):
                    return {k: _plain(v) for k, v in obj.items()}
                if isinstance(obj, defaultdict):
                    return _plain(dict(obj))
                return obj

            payload: dict[str, Any] = {
                "storage": _plain(self.storage),
                "writes": dict(self.writes),
                "blobs": dict(self.blobs),
            }
            self._path.write_bytes(pickle.dumps(payload))
        except Exception:
            return

    def put(self, config: RunnableConfig, checkpoint, metadata, new_versions):  # type: ignore[override]
        out = super().put(config, checkpoint, metadata, new_versions)
        self._save()
        return out

    def put_writes(self, config: RunnableConfig, writes, task_id: str, task_path: str = ""):  # type: ignore[override]
        out = super().put_writes(config, writes, task_id, task_path)
        self._save()
        return out

    def delete_thread(self, config: RunnableConfig) -> None:  # type: ignore[override]
        super().delete_thread(config)
        self._save()
