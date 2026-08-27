from __future__ import annotations

import os
import time
from pathlib import Path

from app.archive import ArchiveConfig, ArchiveWorker


class RecordingStore:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def archive(self, source: Path, object_key: str) -> bool:
        self.calls.append((source, object_key))
        return True


def make_worker(tmp_path: Path) -> tuple[ArchiveWorker, RecordingStore]:
    store = RecordingStore()
    worker = ArchiveWorker(
        ArchiveConfig(
            source_dir=tmp_path,
            object_prefix="apisix/access-logs",
            min_age_seconds=60,
        ),
        store,
    )
    return worker, store


def test_discovery_excludes_active_and_unstable_files(tmp_path: Path) -> None:
    active = tmp_path / "access.log"
    rotated = tmp_path / "access.log.2026-08-23"
    temporary = tmp_path / "access.log.2026-08-24.tmp"
    active.write_text("active\n")
    rotated.write_text("closed\n")
    temporary.write_text("still-being-written\n")
    old_time = time.time() - 120
    os.utime(rotated, (old_time, old_time))
    os.utime(temporary, (old_time, old_time))

    worker, _ = make_worker(tmp_path)

    assert worker.discover_closed_files() == [rotated]


def test_run_once_archives_closed_files_with_stable_key(tmp_path: Path) -> None:
    rotated = tmp_path / "access.log.2026-08-23"
    rotated.write_text("closed\n")
    old_time = time.time() - 120
    os.utime(rotated, (old_time, old_time))
    worker, store = make_worker(tmp_path)

    assert worker.run_once() == 0
    assert worker.run_once() == 1
    assert store.calls == [(rotated, "apisix/access-logs/access.log.2026-08-23")]


def test_recent_rotated_file_waits_for_minimum_age(tmp_path: Path) -> None:
    rotated = tmp_path / "access.log.2026-08-23"
    rotated.write_text("closed\n")
    worker, store = make_worker(tmp_path)

    assert worker.run_once() == 0
    assert store.calls == []
