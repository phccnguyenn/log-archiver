from __future__ import annotations

from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


class StorageConflictError(RuntimeError):
    """The storage object exists but does not represent the same local file size."""


class StorageArchiveStore:
    """Archive closed files through an S3-compatible object-storage API."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        endpoint_url: str | None = None,
        addressing_style: str = "path",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        self.bucket = bucket

        # These values describe how the S3-compatible storage server should
        # be contacted. "s3" below means the S3 API model; it does not force    
        # the request to go to Amazon when endpoint_url points to MinIO.
        client_kwargs = {
            "endpoint_url": endpoint_url,
            "region_name": region,
            "config": Config(s3={"addressing_style": addressing_style}),
        }

        # When both values are supplied, use them as MinIO credentials. If
        # they are omitted, boto3 falls back to its normal credential chain.
        if access_key_id and secret_access_key:
            client_kwargs.update(
                {
                    "aws_access_key_id": access_key_id,
                    "aws_secret_access_key": secret_access_key,
                }
            )

        # boto3 creates a client that understands the S3 API. The actual
        # network request happens later when we call head_object or upload_file.
        self.client = boto3.client("s3", **client_kwargs)

    def archive(self, source: Path, object_key: str) -> bool:
        source_size = source.stat().st_size

        # Check first so repeated polling does not upload the same object
        # again. A same-size object is treated as already archived.
        existing_size = self._existing_size(object_key)
        if existing_size is not None:
            if existing_size != source_size:
                raise StorageConflictError(
                    f"Storage object {self.bucket}/{object_key} already exists "
                    f"with size {existing_size}, local file has size {source_size}"
                )
            return False

        self.client.upload_file(
            str(source),
            self.bucket,
            object_key,
            ExtraArgs={"ContentType": self._content_type(source)},
        )
        uploaded_size = self.client.head_object(
            Bucket=self.bucket,
            Key=object_key,
        )["ContentLength"]
        if uploaded_size != source_size:
            raise IOError(
                f"Storage object size verification failed for {self.bucket}/{object_key}: "
                f"expected {source_size}, got {uploaded_size}"
            )
        return True

    def _existing_size(self, object_key: str) -> int | None:
        try:
            return int(
                self.client.head_object(
                    Bucket=self.bucket,
                    Key=object_key,
                )["ContentLength"]
            )
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise

    @staticmethod
    def _content_type(source: Path) -> str:
        return "application/gzip" if source.name.endswith(".gz") else "application/x-ndjson"
