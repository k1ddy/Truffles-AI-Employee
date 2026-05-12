"""JSONL artifact sink for shadow-run.

Spec: SPECS/SHADOW_RUN_V3.md (B.2.a extension; production-grade sink).

One ComparisonRecord per line, append-only, atomic per record. File writes
run on a thread so the async hot path never blocks. A lock serializes
concurrent writers within one process.
"""
from __future__ import annotations

import asyncio
import json
import pathlib

from .comparison_artifact import ComparisonRecord


class JsonlArtifactSink:
    """Append-only JSONL sink suitable for production shadow-run capture.

    Hard rules (consistent with shadow-run rule §1):
    - Sink errors must never propagate into the customer hot path. The
      runner already swallows sink exceptions, but this implementation
      also tries hard not to raise on common transient issues
      (missing parent dir is auto-created on first write).
    - Each call to `emit` writes exactly one line: a single JSON object
      followed by `\\n`. No partial writes — the line is built in memory
      and flushed in one syscall via `to_thread`.
    """

    def __init__(self, path: pathlib.Path | str) -> None:
        self._path = pathlib.Path(path)
        self._lock = asyncio.Lock()
        self._parent_ready = False

    @property
    def path(self) -> pathlib.Path:
        return self._path

    async def emit(self, record: ComparisonRecord) -> None:
        line = json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
        )
        async with self._lock:
            await asyncio.to_thread(self._append_line, line)

    def _append_line(self, line: str) -> None:
        if not self._parent_ready:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._parent_ready = True
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.write("\n")
