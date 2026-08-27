# Current CLI Demo Checklist

Use this checklist to demonstrate the current Python + boto3 + MinIO project.

## 1. Prepare the environment

- [ ] Open a terminal in the log-archiver project:

  ```bash
  cd /Users/phucnguyen/Project/log-archiver
  ```

- [ ] Activate the virtual environment:

  ```bash
  source ../venv/bin/activate
  ```

- [ ] Load `.env` into the shell:

  ```bash
  set -a
  source .env
  set +a
  ```

- [ ] Confirm the source folder:

  ```bash
  echo "$ARCHIVE_SOURCE_DIR"
  ls -la "$ARCHIVE_SOURCE_DIR"
  ```

- [ ] Install the package in editable mode:

  ```bash
  python -m pip install -e .
  ```

## 2. Explain the current commands

The project currently exposes:

```text
log-archiver   archive eligible files to MinIO
log-inspect    list files in a folder
```

Show the command help:

```bash
log-archiver --help
log-inspect --help
```

Explain the entry-point mapping in `pyproject.toml`:

```toml
[project.scripts]
log-archiver = "app.main:main"
log-inspect = "app.inspect_cli:main"
```

## 3. Demonstrate `log-inspect`

List all regular files in the configured folder:

```bash
log-inspect --source-dir "$ARCHIVE_SOURCE_DIR"
```

List only date-shaped rotated APISIX logs:

```bash
log-inspect \
  --source-dir "$ARCHIVE_SOURCE_DIR" \
  --pattern 'access.log.????-??-??'
```

Search nested folders:

```bash
log-inspect \
  --source-dir "$ARCHIVE_SOURCE_DIR" \
  --recursive
```

Explain:

> `log-inspect` is read-only. It lists files; it does not upload or delete them.

## 4. Demonstrate the default source directory

The environment variable remains the default:

```bash
log-archiver
```

The application scans:

```text
ARCHIVE_SOURCE_DIR
    ↓
access.log.*
    ↓
stable files
    ↓
MinIO
```

Run continuously because stability requires two observations:

```bash
log-archiver
```

Expected messages:

```text
DEBUG app.archive Waiting for ... to remain unchanged across scans
INFO app.archive Uploaded ... as apisix/access-logs/...
```

If the object already exists:

```text
INFO app.archive Already archived ...; skipped upload
```

Stop continuous mode with `Ctrl+C`.

## 5. Demonstrate a one-command source override

Keep the `.env` default unchanged but scan another folder for this process:

```bash
log-archiver \
  --source-dir ./other-log-folder
```

One scan only:

```bash
log-archiver \
  --once \
  --source-dir ./other-log-folder
```

Explain:

> `--source-dir` overrides `ARCHIVE_SOURCE_DIR` only for this invocation. It does not modify `.env`.

Important: `--once` performs one scan. A newly discovered file may only show `Waiting for ...` because the stability check needs a second scan in the same process. Continuous mode is the correct current demonstration for a new file.

## 6. Explain the boto3 part

Show the storage adapter:

```text
app/storage_store.py
```

Point out these operations:

```python
self.client = boto3.client("s3", ...)
self.client.head_object(...)
self.client.upload_file(...)
```

Explain:

```text
Python:
  chooses the eligible file and object key

boto3:
  builds, signs, sends, and parses the S3 API request

MinIO:
  receives and stores the object
```

## 7. Verify MinIO

Check that MinIO is reachable:

```bash
curl http://localhost:9000/minio/health/live
```

Expected response:

```text
OK
```

Open the MinIO console:

```text
http://localhost:9001
```

Check bucket and object path:

```text
Bucket: traffic-log-archive
Prefix: apisix/access-logs
```

## 8. Run tests

```bash
pytest -q
```

Expected current result:

```text
4 passed
```

## 9. Questions to prepare for

- Why use boto3 with MinIO? — MinIO implements the S3-compatible API.
- What does Python do? — File discovery, stability, policy, polling, and CLI behavior.
- What does boto3 do? — Credentials, S3 request construction, signing, upload, and response handling.
- How are duplicate uploads avoided? — `head_object` checks for an existing same-size object.
- What happens if MinIO is down? — The file remains local and the worker can retry.
- Why is the active `access.log` ignored? — It is still being written.
- What is not complete? — APISIX rotation and local/long-term retention are separate follow-up work.

## 10. Final demo sentence

> I built a Python CLI that discovers stable rotated APISIX logs and uses boto3’s S3-compatible client to archive them into MinIO. Python owns the workflow; boto3 owns the storage protocol; MinIO owns the stored object.
