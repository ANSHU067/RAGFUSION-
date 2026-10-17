---
title: RAGFUSION API
emoji: 📚
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# RAGFUSION Backend

## Hugging Face Docker Space

Publish the **contents of `backend/`** as the Space repository root, including
this README, `Dockerfile`, `.dockerignore`, `entrypoint.sh`, `requirements/`,
`alembic.ini`, `alembic/`, `app/`, and `main.py`. Do not publish `.env`, local
uploads, database files, or credentials. This deploys the API; the React frontend
is hosted separately. The Docker build context is `backend/`, not the monorepo
root. The YAML above configures the Docker SDK and port 7860.

In Space Settings, configure these **Secrets** before starting:

- `RAGFUSION_DATABASE_URL`: the external PostgreSQL SQLAlchemy URL with the
  `postgresql+asyncpg://` scheme, percent-encoded credentials, and provider-required
  TLS settings. Do not use the local Compose host `postgres` or `localhost`.
- `RAGFUSION_REDIS_URL`: the external Redis connection URL, using `rediss://` for
  TLS. The existing limiter requires the Redis protocol and Lua scripting; an
  HTTPS REST Redis URL is not interchangeable.
- `RAGFUSION_JWT_SECRET_KEY`: a unique random secret. Generate it locally with
  `openssl rand -hex 32` and paste it into Secrets. Production validation rejects
  default secrets and values shorter than 32 characters.
- `GROQ_API_KEY`: the Groq API credential.

Set `RAGFUSION_CORS_ORIGINS` as a **Variable** containing a JSON array of the
actual frontend HTTPS origins. Do not use a wildcard. Production mode is set in
the image. Keep `RAGFUSION_TRUSTED_PROXIES` unset unless the proxy addresses are
explicitly known; arbitrary forwarded client headers remain untrusted.

**External service connectivity is required:** Spaces documents outbound ports
80, 443, and 8080 only. PostgreSQL on 5432 and Redis on 6379 are therefore not
usable directly. Provision provider-supported, reachable native-protocol
endpoints on permitted ports (with TLS) or a supported secure gateway before
deployment. Changing a URL's port alone does not create such an endpoint.
See [Spaces networking](https://huggingface.co/docs/hub/spaces-overview#networking).
Failed database migrations prevent startup; unreachable Redis keeps the existing
fail-closed rate limiter returning 503.

The image installs FastEmbed/ONNX Runtime (without PyTorch) and preloads
`sentence-transformers/all-MiniLM-L6-v2` into `/app/cache/fastembed` at build
time. The build verifies a local-only reload and 384 embedding dimensions.
Runtime embedding loading uses that same cache with downloads disabled. The
singleton loads on first use by default (`RAGFUSION_EMBEDDING_WARMUP=false`),
with one inference thread, batches of four, and serialized worker execution. Do not
mount an empty volume over `/app/cache`, which would hide the baked model.
The process runs as UID/GID 1000 and owns `/app/data`, `/app/uploads`, and
`/app/cache`. The entrypoint runs `python -m alembic upgrade head`, then replaces
itself with one Uvicorn worker on `${PORT:-7860}` (7860 on Spaces; Render supplies
`PORT`). Migrations use the same database URL
as the API; take a database backup before deploying schema changes.

Chroma lives at `/app/data/vectorstore`; uploaded files live at `/app/uploads`.
These runtime files are **ephemeral** on this deployment. PostgreSQL source
records can outlive the files/vectors, so after disk loss they may still appear
ready even though retrieval is empty. Re-upload documents and re-ingest URL
sources after such a reset. The baked embedding cache returns with the image.
See [Docker Spaces storage](https://huggingface.co/docs/hub/spaces-sdks-docker#data-persistence).

Build from the RAGFUSION repository root:

```bash
docker build -t ragfusion-hf -f backend/Dockerfile backend
docker run --rm -p 7860:7860 --env-file backend/.env ragfusion-hf
curl --fail-with-body http://localhost:7860/api/v1/health
```

The local `.env` must contain the deployment secrets and origins described above;
host `localhost` inside a container refers to that container. Once deployed,
open `/docs` on the Space's direct application URL to inspect the API. Check the
health response body as well as its HTTP status: dependency outages report a
degraded state. No Docker image build or deployment is implied by these commands.

The local Compose file maps host port 8000 to container port 7860. If reusing
volumes created by the earlier UID 10001 image, stop the API and update ownership
once before starting the new image:

```bash
cd backend
docker compose stop api
docker compose build api
docker compose run --rm --no-deps --user 0 --entrypoint sh api -c \
  'chown -R 1000:1000 /app/uploads /app/data/vectorstore'
docker compose up -d
```

## Low-memory Render deployment and verification

Use the Docker runtime with `backend/` as the build context. The same image
supports Render's `PORT` environment variable. Keep one Uvicorn worker: extra
workers duplicate model and application memory. Keep embedding warmup disabled
for small hosts. The image pre-downloads the ONNX model during build. Runtime
loading reuses that cache and can download missing model files on first use.
`RAGFUSION_EMBEDDING_CACHE_DIR` must point at the FastEmbed cache, not an old
SentenceTransformer cache. Set `RAGFUSION_EMBEDDING_LOCAL_FILES_ONLY=false` in
Render's environment, removing any old `true` override. Native Python services
default to `$XDG_CACHE_HOME/ragfusion/fastembed` or
`~/.cache/ragfusion/fastembed`; Docker defaults to `/app/cache/fastembed`. For a
Render persistent disk mounted at `/var/data`, set
`RAGFUSION_EMBEDDING_CACHE_DIR=/var/data/fastembed`. Without a persistent disk,
the cache can disappear on redeploy and the first embedding request will
download the model again. Downloading requires outbound network access; failures
still propagate to ingestion instead of reporting a falsely ready document.
No `torch`, `torchvision`, `sentence-transformers`,
`transformers`, `FlagEmbedding`, or `langchain-huggingface` package is required.

For an existing native Python service, rebuild in a clean environment using
`requirements/base.txt`; installing updated requirements into an old environment
does not uninstall PyTorch. Set Python 3.11 and a writable
`RAGFUSION_EMBEDDING_CACHE_DIR` that is retained from build to runtime. In the
backend build command, after installing requirements, prefetch with:

```bash
python -c 'import os; from fastembed import TextEmbedding; TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2", cache_dir=os.environ["RAGFUSION_EMBEDDING_CACHE_DIR"], threads=1, lazy_load=True)'
```

The Docker entrypoint uses `/app`; native services should instead run from the
backend directory with their existing environment configuration:

```bash
python -m alembic upgrade head && python -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-7860}" --workers 1 --no-proxy-headers
```

Measure the actual target environment from `backend/` (these commands start a
short-lived server on an ephemeral loopback port, then shut it down):

```bash
python scripts/check_memory.py --max-mib 300
python scripts/check_memory.py --embed --max-mib 512
python -m pytest tests/ -q
python -m pip check
```

The existing semantic/recursive document-parser tests also need their language
resources. For the resolved Unstructured 0.27.x dependency, provision the small
English parser model once with `python -m spacy download en_core_web_sm` before
running offline tests. The Docker image includes that parser model with a
SHA-256-verified download. This resource is separate from the MiniLM ONNX cache
and is not loaded during API boot.

A clean Python 3.11/macOS ARM64 validation on 17 October 2026 measured **157.7 MiB
peak at API startup** and **316.34 MiB including the first real MiniLM inference**
(FastEmbed 0.7.4, ONNX Runtime 1.31.0, NumPy 1.26.4). Neither measurement imported
PyTorch or Transformers. These figures describe the local process, not a Render
container; use the commands above to enforce the budget in the target runtime.

The memory check reports process peak RSS and fails above the requested budget
or if a forbidden heavy embedding runtime is imported. Startup and first
embedding measurements are separate: Chroma, parsers, ingestion buffers, and
concurrent traffic consume additional memory. Passing a startup check does not
guarantee every workload fits 512 MiB. Run the same check on Render/Linux before
asserting the deployment's memory budget; macOS results are not Linux measurements.

The adapter retains MiniLM's 384-dimensional space and uses FastEmbed's
normalized vectors consistently for queries and ingestion. Re-ingest existing
sources when switching encoders to avoid mixed numerical implementations and
normalization in the same index. The optional cross-encoder reranker is ONNX
based and remains disabled in the standard chat pipeline; it would need a
separately cached model and more memory if explicitly enabled.

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
