from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from app.archive import ArchiveConfig, ArchiveWorker
from app.config import Settings
from app.storage_store import StorageArchiveStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upload closed APISIX access-log files to configurable object storage."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="scan and archive once, then exit",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="override ARCHIVE_SOURCE_DIR for this invocation",
    )
    return parser


def build_worker(settings: Settings) -> ArchiveWorker:
    store = StorageArchiveStore(
        bucket=settings.storage_bucket,
        region=settings.storage_region,
        endpoint_url=settings.storage_endpoint_url,
        addressing_style=settings.storage_addressing_style,
        access_key_id=settings.storage_access_key_id,
        secret_access_key=settings.storage_secret_access_key,
    )
    return ArchiveWorker(
        ArchiveConfig(
            source_dir=settings.source_dir,
            object_prefix=settings.storage_object_prefix,
            poll_interval_seconds=settings.poll_interval_seconds,
            min_age_seconds=settings.min_age_seconds,
        ),
        store,
    )


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Keep ARCHIVER_LOG_LEVEL=DEBUG useful for our own workflow without
    # flooding the console with boto3/botocore implementation details.
    for logger_name in ("boto3", "botocore", "s3transfer", "urllib3"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    args = build_parser().parse_args()
    if args.source_dir is not None:
        settings = replace(settings, source_dir=args.source_dir)
    worker = build_worker(settings)
    if args.once:
        worker.run_once()
    else:
        worker.run_forever()


if __name__ == "__main__":
    main()
