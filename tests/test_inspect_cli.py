from pathlib import Path

from app.inspect_cli import discover_files


def test_discover_files_lists_matching_regular_files(tmp_path: Path) -> None:
    (tmp_path / "access.log.2026-08-24").write_text("one\n")
    (tmp_path / "notes.txt").write_text("two\n")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "access.log.2026-08-25").write_text("three\n")

    assert discover_files(tmp_path, "access.log.*", recursive=False) == [
        tmp_path / "access.log.2026-08-24"
    ]
    assert discover_files(tmp_path, "access.log.*", recursive=True) == [
        tmp_path / "access.log.2026-08-24",
        tmp_path / "nested" / "access.log.2026-08-25",
    ]
