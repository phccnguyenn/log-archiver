from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    return default if raw is None else float(raw)


@dataclass(frozen=True)
class Settings:
    source_dir: Path
    storage_endpoint_url: str | None
    storage_bucket: str
    storage_object_prefix: str
    storage_region: str
    storage_addressing_style: str
    storage_access_key_id: str | None
    storage_secret_access_key: str | None
    poll_interval_seconds: float
    min_age_seconds: float
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            # Folder that contains completed APISIX files such as
            # access.log.2026-08-24. In Docker this is normally /archive-logs;
            # when running locally it can be ./local-storage.
            source_dir=Path(os.getenv("ARCHIVE_SOURCE_DIR", "/archive-logs")),

            # MinIO uses an S3-compatible API. The host uses localhost, while
            # another Docker container must use the Compose service name:
            # http://minio:9000.
            storage_endpoint_url=os.getenv("STORAGE_ENDPOINT_URL") or None,

            # The bucket is the logical container where archived log objects
            # are stored. The bucket must already exist before uploading.
            storage_bucket=os.getenv("STORAGE_BUCKET", "traffic-log-archive"),

            # A prefix groups objects under a readable virtual folder-like
            # name, for example apisix/access-logs/<filename>.
            storage_object_prefix=os.getenv("STORAGE_OBJECT_PREFIX", "apisix/access-logs"),

            # S3-compatible clients expect a region value. MinIO commonly
            # uses us-east-1 for local development.
            storage_region=os.getenv("STORAGE_REGION", "us-east-1"),

            # Path-style addressing sends requests like
            # /traffic-log-archive/object-name. This is convenient for a
            # local MinIO endpoint.
            storage_addressing_style=os.getenv("STORAGE_ADDRESSING_STYLE", "path"),

            # These are MinIO credentials for local development. If both are
            # absent, boto3 can use its standard credential providers instead.
            storage_access_key_id=os.getenv("STORAGE_ACCESS_KEY_ID") or None,
            storage_secret_access_key=os.getenv("STORAGE_SECRET_ACCESS_KEY") or None,

            # The worker checks for new files at this interval and requires a
            # file to be old enough before considering it for upload.
            poll_interval_seconds=_float_env("ARCHIVER_POLL_INTERVAL_SECONDS", 30.0),
            min_age_seconds=_float_env("ARCHIVER_MIN_AGE_SECONDS", 60.0),

            # INFO shows normal archive results. DEBUG also shows our file
            # stability decisions; boto3 internals are filtered in main.py.
            log_level=os.getenv("ARCHIVER_LOG_LEVEL", "INFO"),
        )
