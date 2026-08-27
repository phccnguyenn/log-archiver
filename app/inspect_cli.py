from __future__ import annotations

import argparse
from pathlib import Path


def discover_files(source_dir: Path, pattern: str, recursive: bool) -> list[Path]:
    """Return regular files matching the requested folder and pattern."""
    paths = source_dir.rglob(pattern) if recursive else source_dir.glob(pattern)
    return sorted(path for path in paths if path.is_file())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List files in a local folder."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("."),
        help="folder to inspect (default: current directory)",
    )
    parser.add_argument(
        "--pattern",
        default="*",
        help="filename pattern to match (default: *)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="include files in nested folders",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.source_dir.is_dir():
        parser.error(f"source directory does not exist: {args.source_dir}")

    files = discover_files(args.source_dir, args.pattern, args.recursive)
    if not files:
        print(f"No files found in {args.source_dir} matching {args.pattern!r}")
        return

    for path in files:
        print(f"{path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
