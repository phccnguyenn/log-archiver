# Local archive fixtures

This folder contains small rotated APISIX access-log fixtures for local testing.

The log archiver scans for files matching:

```text
access.log.*
```

It should discover the two dated files, ignore the active `access.log` if one is
added, and ignore the temporary `.tmp` file. The fixtures use newline-delimited
JSON (NDJSON): one valid JSON access event per line.

The files are not automatically mounted into Docker Compose. The current local
Compose configuration uses the shared named volume `apisix_logs` at
`/archive-logs`. Use this folder for direct local tests, or bind-mount it into a
temporary test container when you want the containerized archiver to read these
fixtures.

The archiver also checks file age and stability. A newly checked-out fixture may
need to be at least `ARCHIVER_MIN_AGE_SECONDS` old and observed unchanged across
two scans before it is uploaded.
