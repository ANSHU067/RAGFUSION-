# RAGFUSION Backend

## Local development

Use Python 3.11 and install the dependencies:

```bash
pip install -r requirements/base.txt
python -m pip check
cp .env.example .env
alembic upgrade head
python -m uvicorn main:app --reload
```

Open Swagger UI at `http://localhost:8000/docs`. The health endpoint is
available at `http://localhost:8000/api/v1/health` and reports `degraded`
until PostgreSQL and Redis are reachable.

## Local PostgreSQL bootstrap

The API and Alembic load `backend/.env` regardless of the working directory.
`RAGFUSION_DATABASE_URL` takes precedence over `DATABASE_URL`; without either,
the default is `postgresql+asyncpg://docpro:docpro@localhost:5432/docpro`.
An authentication failure is reported by the selected database; it does not
silently switch databases or credentials.

For a new local installation using the example credentials, run these commands
as a PostgreSQL administrator. Keep the two `-c` statements separate because
`CREATE DATABASE` cannot run in a transaction block:

```bash
psql -X -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE ROLE docpro WITH LOGIN PASSWORD 'docpro' NOSUPERUSER NOCREATEDB NOCREATEROLE;" \
  -c "CREATE DATABASE docpro OWNER docpro;"
export RAGFUSION_DATABASE_URL='postgresql+asyncpg://docpro:docpro@localhost:5432/docpro'
../ragfusion_env/bin/python -m alembic upgrade head
```

The last command assumes the current directory is `backend`. From the repository
root, use `ragfusion_env/bin/python -m alembic -c backend/alembic.ini upgrade head`.
The application role owns its database and can run migrations without being a
superuser. Match the role password to your own `.env`; the sample password above
is for local development. If you use the standard `DATABASE_URL` name, remove
any competing `RAGFUSION_DATABASE_URL` setting.

On the audited workstation, Batch 2 created the previously missing local role
and database using the existing `backend/.env` password, preserved that file,
and applied revision `20261005_0001`. Do not rerun the creation commands there.

## Docker

```bash
docker compose up --build
```

The Compose stack starts the API, PostgreSQL, and Redis. It uses `.env` for
the API configuration and waits for the database and cache health checks.
Inside Compose, the API explicitly connects to `postgres:5432` and `redis:6379`.
PostgreSQL is published only on `127.0.0.1:55432`, avoiding the local server's
port 5432. To run the API on the host against Compose PostgreSQL, set
`RAGFUSION_DATABASE_URL=postgresql+asyncpg://docpro:docpro@localhost:55432/docpro`.
The image's `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` initialize
an empty volume only; changing those variables does not reset an existing volume.

## Verification

From the repository root, use a Python 3.11 virtual environment:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements/base.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest --collect-only -q
.venv/bin/python audits/2026-10-04/verify_findings.py --batch 1
.venv/bin/python -m pytest -q backend/tests/test_app.py backend/tests/test_auth.py
```

`base.txt` includes `embeddings.txt`, so local embeddings, reranking, Argon2,
multipart uploads, and the YouTube v1 client are installed by both local and
Docker setup. Keep the LangChain integrations on the compatible 0.3 release
family. The root `requirements.txt` belongs to the legacy YouTube pipeline;
do not mix that environment with the backend environment.

Browser crawling remains disabled. Its optional engine is declared in
`requirements/crawling.txt` and imported only when a crawl is explicitly run.
Ordinary startup and test collection do not import Crawl4AI, launch a browser,
download embedding models, or connect to external services. Installing the
optional engine does not enable the router or establish SSRF safety.

The remediation probe defaults to positive assertions for completed batches.
Use `--batch 1 --source-only` to inspect source tracking and dependency
declarations without validating the installed environment. This reduced check
does not establish that a fresh dependency installation works.
`--baseline` explicitly runs the historical defect reproductions instead;
it is not a passing-security check. A02 verification requires the restored
source files to be in the Git index or committed.

Batch 2's positive regression probe runs independently of the unresolved Batch 1
dependency installation check:

```bash
ragfusion_env/bin/python audits/2026-10-04/verify_findings.py --batch 2
```

By default this checks SQLite and reports skipped PostgreSQL cases explicitly.
For real locking verification, set `BATCH2_POSTGRES_URL` to a disposable PostgreSQL
server URL whose test administrator can create databases. The tests create and
drop randomly named databases and never use the application's data tables.

The Batch 2 migration keeps the newest SQL embedding row per document/chunk and
preserves other source types. Downgrade removes the constraints and `deleted_at`
column but cannot reconstruct discarded duplicate chunks or deleted timestamps.
If legacy settings have negative overlap or overlap greater than or equal to
chunk size, upgrade stops before schema changes. Inspect and correct those
settings before retrying; the migration does not silently rewrite user settings:

```sql
SELECT user_id, chunk_size, chunk_overlap
FROM user_settings
WHERE chunk_overlap < 0 OR chunk_overlap >= chunk_size;
```

Batch 3 uses Redis for distributed request quotas and fails business requests
closed with HTTP 503 when Redis is unavailable. Auth endpoints allow 7 requests
per minute per trusted client identity; chat, ingestion, and general API routes
have separate budgets. Configure `RAGFUSION_TRUSTED_PROXIES` only with proxy CIDRs
you operate; arbitrary `X-Forwarded-For` headers are ignored. Token logout and
refresh rotate the database-backed `auth_version`, so every prior access and
refresh token is rejected. The Compose API runs as UID 10001 and persists uploads
and vectors in named volumes.

## Database architecture

The application uses async SQLAlchemy sessions and repositories. PostgreSQL is
the production database; SQLite with `aiosqlite` is supported for integration
tests. Apply schema changes with `alembic upgrade head`; generate a reviewed
revision with `alembic revision --autogenerate -m "description"`.

## RAGFUSION profile and branding upgrade

Before starting the updated API, apply migration `20261006_0001`:

```bash
cd backend
../ragfusion_env/bin/alembic upgrade head
```

The migration adds optional bio and workspace label fields plus an avatar color
with a safe default. It preserves account IDs, passwords, token revocation
versions, ownership, and existing sources. Profile changes use authenticated
`PATCH /api/v1/auth/me`; role, email, credentials, and account IDs are not editable.

Use `RAGFUSION_*` for new configuration. Legacy environment names remain accepted
through `app/config/branding_compat.py`; canonical names take precedence within
the same configuration source. Existing PostgreSQL database/role identifiers,
JWT issuer/audience identifiers, and the Redis quota namespace intentionally
remain compatible. Renaming them as display text would break existing accounts,
disconnect stored data, or reset active request quotas.

Compose still uses the same named upload and vector volumes, mounted at
`/var/lib/ragfusion/uploads` and `/var/lib/ragfusion/vectorstore`. Do not delete
or recreate named volumes during the upgrade. Local default upload storage
continues using the legacy directory when it already exists. No private `.env`
or database credentials are rewritten by this change.

The frontend uses `/profile`, `/settings`, and `/chat/:sessionId`; old dashboard
profile/settings URLs redirect to the new routes. It consumes message history
in bounded pages before enabling continuation. Both `chat_session_id` and the
legacy `session_id` request field are accepted, but conflicting IDs are rejected.
Message timestamps are stored/read as UTC and displayed in the browser's local
timezone, with a safe fallback for missing or invalid values.
