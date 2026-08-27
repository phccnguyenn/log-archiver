from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class ArchiveStore(Protocol):
    def archive(self, source: Path, object_key: str) -> bool:
        """Persist one closed local file and return whether it was uploaded."""


@dataclass(frozen=True)
class ArchiveConfig:
    source_dir: Path
    object_prefix: str
    poll_interval_seconds: float = 30.0
    min_age_seconds: float = 60.0


class ArchiveWorker:
    """Find closed APISIX logs and hand them to an archive store."""

    def __init__(self, config: ArchiveConfig, store: ArchiveStore) -> None:
        self.config = config
        self.store = store
        self._observed_signatures: dict[Path, tuple[int, int]] = {}

    def discover_closed_files(self, now: float | None = None) -> list[Path]:
        """Return stable rotated files, never the active ``access.log``."""
        current_time = time.time() if now is None else now
        candidates = []
        for path in self.config.source_dir.glob("access.log.*"):
            if path.is_symlink() or not path.is_file():
                continue
            if current_time - path.stat().st_mtime < self.config.min_age_seconds:
                continue
            if path.name.endswith(".tmp"):
                continue
            candidates.append(path)
        return sorted(candidates, key=lambda item: item.name)

    def object_key_for(self, source: Path) -> str:
        prefix = self.config.object_prefix.strip("/")
        return f"{prefix}/{source.name}" if prefix else source.name

    def run_once(self, now: float | None = None) -> int:
        archived = 0
        for source in self.discover_closed_files(now=now):
            if not self._is_stable(source):
                logger.debug("Waiting for %s to remain unchanged across scans", source)
                continue
            object_key = self.object_key_for(source)
            try:
                uploaded = self.store.archive(source, object_key)
            except Exception:
                logger.exception("Failed to archive %s as %s", source, object_key)
                continue
            archived += 1
            if uploaded:
                logger.info("Uploaded %s as %s", source, object_key)
            else:
                logger.info("Already archived %s as %s; skipped upload", source, object_key)
        return archived

    def _is_stable(self, source: Path) -> bool:
        stat = source.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
        previous = self._observed_signatures.get(source)
        self._observed_signatures[source] = signature
        return previous == signature

    def run_forever(self) -> None:
        while True:
            self.run_once()
            time.sleep(self.config.poll_interval_seconds)
