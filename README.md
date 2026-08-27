# Log Archiver

The log archiver uploads closed APISIX access-log files to configurable object storage. The current adapter uses boto3 and an S3-compatible API, which supports MinIO locally and AWS S3 later.

It is intentionally separate from:

- the APISIX log rotator, which renames the active file and signals APISIX/Nginx to reopen it;
- Fluent Bit, which ships individual access events to Kafka;
- TMI, which consumes Kafka and performs endpoint-probe aggregation.

## Behavior

The worker scans `ARCHIVE_SOURCE_DIR` for files matching:

```text
access.log.*
```

It ignores the active `access.log`, symbolic links, temporary files ending in `.tmp`, and files newer than `ARCHIVER_MIN_AGE_SECONDS`. It also requires the file size and modification time to remain unchanged across two scans before uploading.

For each eligible file, it:

1. derives a stable object key from the configured prefix and filename;
2. checks whether the object already exists;
3. skips an existing object with the same size;
4. raises a conflict for an existing object with a different size;
5. uploads a new object with boto3;
6. verifies the uploaded object size with `HeadObject`.

The worker does not delete local files. Local deletion remains a separate retention decision after Fluent Bit handoff and successful archive verification.

## Standalone Docker Compose

This project can run independently with its own MinIO container and the local
fixtures under `local-storage`:

```bash
cp .env.example .env
docker compose up -d
docker compose logs -f log-archiver
```

MinIO is available from the host at `http://localhost:9000`, and its console is
available at `http://localhost:9001`. Inside the Compose network, the archiver
uses `http://minio:9000`.

The standalone Compose file is intended for archiver development and demos. In
the full platform stack, the archiver should mount the shared APISIX log volume
instead of the local fixture folder.

## Configuration

```text
ARCHIVE_SOURCE_DIR=/archive-logs
STORAGE_ENDPOINT_URL=http://minio:9000
STORAGE_BUCKET=traffic-log-archive
STORAGE_OBJECT_PREFIX=apisix/access-logs
STORAGE_ADDRESSING_STYLE=path
STORAGE_REGION=us-east-1
STORAGE_ACCESS_KEY_ID=minioadmin
STORAGE_SECRET_ACCESS_KEY=minioadminpassword
ARCHIVER_POLL_INTERVAL_SECONDS=30
ARCHIVER_MIN_AGE_SECONDS=60
ARCHIVER_LOG_LEVEL=INFO
```

For AWS S3, omit `STORAGE_ENDPOINT_URL` and omit the explicit storage credentials when the runtime has an IAM role or another standard boto3 credential source. For MinIO, provide the endpoint and storage credentials through the environment.

## Commands

The project currently provides two CLI commands:

```text
log-archiver   scan and archive eligible files to MinIO/S3-compatible storage
log-inspect    list files in a local folder
```

`log-ingest` is not currently defined by this project. The existing inspection
command is named `log-inspect`.

### Local CLI setup

From the project directory:

```bash
cd /Users/phucnguyen/Project/log-archiver
source /Users/phucnguyen/Project/real-time-click-tracking-platform/venv/bin/activate
set -a
source .env
set +a
python -m pip install -e .
```

The `source .env` step exports configuration into the shell. The editable
install registers both CLI commands in the active virtual environment.

### Show help

```bash
log-archiver --help
log-inspect --help
```

### `log-inspect` — list files

List every regular file in the default local fixture folder:

```bash
log-inspect --source-dir ./local-storage
```

List only date-shaped rotated APISIX logs:

```bash
log-inspect \
  --source-dir ./local-storage \
  --pattern 'access.log.????-??-??'
```

List matching files recursively:

```bash
log-inspect \
  --source-dir ./local-storage \
  --pattern 'access.log.*' \
  --recursive
```

The wildcard pattern must be quoted so `zsh` passes it to Python unchanged.
`log-inspect` is read-only: it does not upload, delete, or modify files.

### `log-archiver` — continuous mode

Use the configured `ARCHIVE_SOURCE_DIR` and scan continuously:

```bash
log-archiver
```

The worker scans every `ARCHIVER_POLL_INTERVAL_SECONDS` seconds. It uploads
stable rotated files matching `access.log.*` and keeps local files after
successful upload.

Stop the worker with:

```text
Ctrl+C
```

### `log-archiver` — one-scan mode

Run one scan and exit:

```bash
log-archiver --once
```

The current stability check requires two observations in the same process. A
newly discovered file may therefore print `Waiting for ...` and exit in
`--once` mode. Use continuous mode when testing a newly created file.

### Override the source folder

Override `ARCHIVE_SOURCE_DIR` for one invocation without changing `.env`:

```bash
log-archiver --source-dir ./other-log-folder
```

Combine the override with one-scan mode:

```bash
log-archiver \
  --once \
  --source-dir ./other-log-folder
```

Use an absolute path when running from another directory:

```bash
log-archiver \
  --source-dir "/Users/phucnguyen/logs/archive-2026-08-24"
```

The CLI option takes precedence over `ARCHIVE_SOURCE_DIR` only for that
process. It does not modify `.env`.

### Standalone Docker Compose commands

Start MinIO and the archiver:

```bash
docker compose up -d
```

View archiver logs:

```bash
docker compose logs -f log-archiver
```

Run one scan inside a new archiver container:

```bash
docker compose run --rm log-archiver log-archiver --once
```

Run one scan against a different folder mounted at `/archive-logs`:

```bash
docker compose run --rm log-archiver \
  log-archiver --once --source-dir /archive-logs
```

Check container status:

```bash
docker compose ps
```

Stop the standalone stack:

```bash
docker compose down
```

The standalone Compose stack exposes MinIO at:

```text
S3-compatible API: http://localhost:9000
MinIO console:     http://localhost:9001
Bucket:            traffic-log-archive
```

Inside Docker, the archiver connects to MinIO using:

```text
http://minio:9000
```
