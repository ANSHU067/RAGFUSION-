# RAGFUSION

**Enterprise multi-modal Retrieval-Augmented Generation workspace**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST%20%2B%20SSE-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB?logo=react&logoColor=111827)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-frontend-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-vector%20store-F97316)](https://www.trychroma.com/)
[![Redis](https://img.shields.io/badge/Redis-rate%20limiting-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

RAGFUSION is a production-oriented, multi-tenant knowledge workspace. It indexes documents, YouTube transcripts, and public web pages, then answers questions with source-grounded retrieval, resumable conversations, and citation metadata that identifies the originating source.

This repository contains the FastAPI service, React workspace, relational migrations, vector ingestion code, the standalone YouTube pipeline, regression tests, and historical recovery material. The active application is under `backend/` and `frontend/`; `youtube_pipeline/` is a reusable pipeline module and `archive/` contains historical, non-runtime material.

## What RAGFUSION provides

- **One knowledge workspace:** authenticated users can upload files, ingest YouTube videos, and crawl public web pages from one interface.
- **Grounded chat:** questions are embedded, retrieved from ChromaDB, reranked, placed into a bounded prompt, and answered through a streaming or non-streaming API.
- **Balanced all-source retrieval:** an “all indexed sources” query is filtered to the authenticated tenant before retrieval and samples document, website, and YouTube candidates so a large source cannot consume the complete top-k window.
- **Precise citations:** responses preserve `source_type`, source title/name, filename or URL, source ID, content snippet, and relevance score.
- **Resumable conversations:** chat sessions and messages are persisted, can be loaded at `/chat/:sessionId`, and support continuation turns without creating detached sessions.
- **Production session lifecycle:** short-lived access tokens, rotating refresh tokens, database-backed `auth_version` revocation, and a concurrency-locked Axios refresh interceptor prevent replay and 401 retry storms.
- **Tenant isolation:** database queries, source selection, vector filters, and post-retrieval checks are scoped to the authenticated user. Soft-deleted sessions are excluded from normal history and chat lookups.
- **Operational guardrails:** Redis-backed sliding-window rate limiting, bounded crawler payloads and timeouts, CPU-heavy work offloaded from the event loop, sanitized public errors, structured logs, and browser security headers.
- **Workspace controls:** profile editing, per-user model/temperature/token settings, source management, light/dark themes, and a ChatGPT-style borderless chat UI.

## Feature modules

### Document ingestion

`POST /api/v1/documents/upload` accepts PDF, DOCX, TXT, CSV, and Markdown uploads. The service validates content type, file size, and chunking parameters before writing bytes. Storage keys are generated from server-side UUIDs (`uploads/<user>/<document>/content`); the client filename is display metadata only. Extraction, text cleaning, chunking, embedding, and Chroma insertion run through bounded worker capacity. A failed vector write marks the document as `failed` instead of reporting a false `ready` state. `POST /documents/{id}/reprocess` runs the same pipeline with new chunk settings.

### YouTube transcript ingestion

`POST /api/v1/youtube/ingest` parses a video URL, obtains an automatic or requested-language transcript through `youtube-transcript-api`, creates timestamp-aware chunks, stores video metadata, and indexes the chunks. Transcript and provider failures are returned as sanitized API errors and never trigger an unbounded retry loop. The source list and transcript endpoints allow the workspace to display and manage indexed videos.

### Website crawling and ingestion

`POST /api/v1/website/ingest` validates and stores a public HTTP(S) URL, while `POST /api/v1/website/{source_id}/process` performs the crawl. The crawler uses an `aiohttp` `PublicResolver` and checks every resolved destination with `ipaddress.ip_address(...).is_global`. Loopback, RFC 1918, link-local, multicast, reserved, and cloud metadata destinations are rejected. Redirects are disabled or validated before the next connection, response bodies are capped at 2 MiB, and connection/read timeouts are bounded. HTML is reduced to readable content, chunked, embedded, and indexed with the same tenant-aware metadata contract as other sources.

### Balanced multi-source RAG

The active embedding space is Hugging Face `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions), loaded once and shared by the application. A chat request may provide `source_ids` grouped as `document`, `website`, and `youtube`. When omitted or empty, retrieval spans all ready sources owned by the user. When supplied, Chroma receives an `$or` predicate for the selected IDs before top-k truncation; multi-modality requests retrieve per type and interleave candidates. A defense-in-depth authorization pass rejects legacy or stale vector records that cannot be tied to a live owned source.

### Conversational workspace

The React workspace keeps the active session in context across route changes, synchronizes `/chat/:sessionId`, and aborts stale history requests when the route or account changes. User messages are optimistic and receive a local timestamp immediately. Persisted UTC timestamps are formatted in the browser’s local timezone: today shows a time such as `11:25 AM`, older messages show a date and time such as `Oct 5, 2:30 PM`, and malformed timestamps fall back safely to `Just now`.

The chat feed is intentionally borderless: assistant responses use readable markdown and quiet actions, user messages are compact right-aligned pills, and the prompt bar shares the same centered max-width as the conversation stream. The streaming endpoint emits SSE chunks of type `content`, `citation`, `metadata`, `done`, or sanitized `error`.

### Security and reliability

- **Authentication and authorization:** Bearer JWT access/refresh tokens are validated against the user’s current `auth_version`. Logout increments that version atomically. Refresh validates and rotates it, invalidating replayed refresh tokens. Every object lookup includes the current user ID.
- **Rate limiting:** `RateLimitMiddleware` uses Redis atomic Lua operations (`INCR` plus `PEXPIRE`) for distributed sliding-window limits. Auth routes are limited to approximately 7 requests/minute, chat routes to a higher bounded interactive limit, ingestion routes to approximately 10 requests/minute, and other API traffic to a general limit. Untrusted `X-Forwarded-For` values are ignored; proxy addresses must be explicitly configured. If Redis cannot be reached, protected traffic fails closed with a service-unavailable response rather than silently disabling protection.
- **SSRF and resource limits:** URL ingestion resolves only globally routable addresses, validates redirect destinations, caps bodies at 2 MiB, and uses bounded timeouts. File uploads are size-limited and path traversal is prevented with resolved-root checks.
- **Async safety:** Argon2 hashing, parsing, chunking, embeddings, and vector writes are moved to worker threads with capacity limiters. Streaming checks client disconnects and is enclosed by a timeout so abandoned clients do not retain upstream work.
- **API hygiene:** Pydantic request/response schemas enforce bounds such as `chunk_overlap < chunk_size`; validation and application errors use a uniform sanitized envelope. SQL details, stack traces, and provider exceptions are logged internally but are not returned to clients.
- **Browser defenses:** configured CORS origins are enforced and responses include CSP, `X-Content-Type-Options`, `X-Frame-Options`, Referrer-Policy, Permissions-Policy, and HSTS in production.

## Architecture

```mermaid
flowchart LR
    subgraph Sources[Knowledge sources]
        PDF[PDF / DOCX / TXT / CSV / Markdown]
        YT[YouTube URL and transcript]
        WEB[Public website URL]
    end

    PDF --> EX[Extract and normalize]
    YT --> EX
    WEB --> SSRF[PublicResolver, limits, HTML extraction]
    SSRF --> EX
    EX --> CHUNK[Validated chunker]
    CHUNK --> EMB[Shared MiniLM embedder<br/>384 dimensions]
    EMB --> CHROMA[(ChromaDB<br/>source metadata + tenant filters)]
    EX --> PG[(PostgreSQL<br/>users, sources, chunks, sessions)]

    Browser[React workspace] -->|Bearer REST / SSE| API[FastAPI API]
    API --> AUTH[JWT + auth_version]
    API --> PG
    API --> REDIS[(Redis<br/>rate limiter / short-lived state)]
    API --> RAG[RAG pipeline]
    RAG --> EMB
    RAG --> RETRIEVE[Authorized multi-source retrieval]
    RETRIEVE --> RERANK[Top-k reranking and balance]
    RERANK --> PROMPT[History + citations prompt]
    PROMPT --> LLM[Configured LLM provider]
    LLM -->|content, citations, metadata| API
    API --> Browser
```

The request path is:

1. The browser sends a Bearer-authenticated request and optional source selection.
2. FastAPI authenticates the token, applies the Redis limiter, and loads user settings.
3. The shared RAG pipeline embeds the question and queries Chroma with tenant/source predicates.
4. Candidates are balanced across active modalities, reranked, and bounded by the context budget.
5. Conversation history is formatted chronologically with the current question.
6. The configured LLM produces a response; the API persists the turn and returns citations or emits them as SSE events.

## Repository layout

```text
RAGFUSION/
├── README.md                         # This platform guide
├── QUICK_START_GUIDE.md              # Short local setup reference
├── STABILIZATION_REPORT.md            # Repository stabilization notes
├── .env.example                       # Legacy standalone-pipeline example
├── .gitignore                         # Secrets, caches, builds, local data
├── requirements.txt                   # Legacy YouTube/pipeline requirements
├── pytest.ini                         # Pytest configuration
├── alembic.ini                        # Root Alembic entry point
├── backend/
│   ├── .env.example                   # Active API configuration template
│   ├── Dockerfile                      # Python 3.11 non-root API image
│   ├── docker-compose.yml              # API + PostgreSQL + Redis stack
│   ├── .dockerignore
│   ├── requirements/
│   │   ├── base.txt                    # FastAPI, DB, auth, ingestion, RAG
│   │   ├── embeddings.txt              # Sentence Transformers / reranking
│   │   └── crawling.txt                # Optional crawler integrations
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/                   # Ordered schema migrations and merge
│   │       ├── 20260801_0001_initial_schema.py
│   │       ├── 20260802_0002_rename_chat_session_metadata.py
│   │       ├── 20260802_0003_user_settings.py
│   │       ├── 20260803_0001_fix_processing_status.py
│   │       ├── 20261005_0001_storage_integrity.py
│   │       ├── 20261005_0002_auth_version.py
│   │       ├── 20261006_0001_user_profile.py
│   │       └── 7efa7e63b3ce_merge_migration_heads.py
│   ├── main.py                         # FastAPI factory, middleware, lifespan
│   ├── app/
│   │   ├── api/                        # Auth, chat, documents, YouTube, web
│   │   ├── config/                     # Environment and compatibility config
│   │   ├── core/                       # JWT, RAG config, rate limiter, runtime
│   │   ├── db/                         # Async SQLAlchemy and vector store
│   │   ├── dependencies/               # FastAPI dependency providers
│   │   ├── llm/providers/              # Provider interface and integrations
│   │   ├── middleware/                 # Rate limit, context, security headers
│   │   ├── models/                     # SQLAlchemy entities and settings
│   │   ├── rag/
│   │   │   ├── embeddings/              # Embedding manager/runtime
│   │   │   ├── pipelines/               # LangGraph RAG orchestration
│   │   │   ├── prompts/                 # Prompt construction and citations
│   │   │   ├── rerankers/               # Candidate reranking
│   │   │   └── retrievers/              # Chroma retrieval adapters
│   │   ├── repositories/               # Database access patterns
│   │   ├── schemas/                    # Pydantic request/response contracts
│   │   ├── services/                   # Ingestion, chat, auth, history logic
│   │   ├── utils/                      # Retry and timeout helpers
│   │   └── workers/                    # Background worker package
│   └── tests/                          # Backend unit, API, security, RAG tests
├── frontend/
│   ├── .env.example                    # VITE_API_BASE_URL template
│   ├── package.json                    # Vite, React, Tailwind, Vitest scripts
│   ├── vite.config.js / eslint.config.js
│   ├── public/                         # Static browser assets
│   ├── src/
│   │   ├── components/                 # Chat, layout, dashboard, forms, UI
│   │   │   ├── chat/                    # Feed, bubbles, prompt input, citations
│   │   │   ├── landing/                 # Hero, pricing, source cards
│   │   │   ├── layout/                  # Navbar, sidebar, authenticated shell
│   │   │   └── upload/                  # Upload cards and progress UI
│   │   ├── context/                    # Auth, user, chat, upload, theme state
│   │   ├── hooks/                      # Abortable async scope helpers
│   │   ├── layouts/                    # Authenticated/global layouts
│   │   ├── lib/                        # Dates, profiles, validation, utilities
│   │   ├── pages/                      # Auth, dashboard, readers, profile, settings
│   │   ├── routes/                     # React Router route definitions
│   │   ├── services/                   # Axios API clients and endpoint wrappers
│   │   ├── styles/                     # Tailwind/global styles
│   │   └── main.jsx                    # React entry point
│   └── tests/                          # Vitest and Testing Library regressions
├── youtube_pipeline/                   # Standalone transcript/chunk/embed module
│   ├── transcript_extractor.py
│   ├── metadata_extractor.py
│   ├── chunker.py
│   ├── embedding_generator.py
│   └── pipeline.py
├── audits/2026-10-04/                  # Audit probes and finding verification
│   ├── verify_findings.py
│   ├── AUDIT_REPORT.md and BATCH_*.md
│   └── findings.json and verification artifacts
├── examples/                           # Small integration examples
└── archive/                            # Historical recovery reports and scripts
    ├── phase8-9-recovery/              # Recovery-era prototypes
    ├── phase8-9-stabilization/         # Stabilization-era prototypes/tests
    ├── reports/                        # Historical audit and architecture reports
    └── scripts/                        # Historical verification utilities
```

The archive is intentionally outside the runtime import path. Do not copy archived configuration or pipeline files into production deployments.

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer and npm
- PostgreSQL 14 or newer (PostgreSQL 16 is used by Compose)
- Redis 7 or newer
- A local Hugging Face cache containing `sentence-transformers/all-MiniLM-L6-v2` when `RAGFUSION_EMBEDDING_LOCAL_FILES_ONLY=true`
- A Groq API key for the active `ChatGroq` RAG path
- Docker Desktop or Docker Engine with Compose, if using the containerized path

## Configuration

The active API reads `backend/.env`. Copy `backend/.env.example` and replace secrets and hostnames for the target environment:

```dotenv
RAGFUSION_APP_NAME=RAGFUSION API
RAGFUSION_ENVIRONMENT=development
RAGFUSION_DEBUG=false
RAGFUSION_API_V1_PREFIX=/api/v1
RAGFUSION_DATABASE_URL=postgresql+asyncpg://docpro:change-me@localhost:5432/docpro
RAGFUSION_REDIS_URL=redis://localhost:6379/0
RAGFUSION_UPLOAD_DIR=/var/lib/ragfusion/uploads
RAG_VECTOR_STORE_PATH=/var/lib/ragfusion/vectorstore
RAGFUSION_CORS_ORIGINS=["http://localhost:5173"]
RAGFUSION_LOG_LEVEL=INFO
RAGFUSION_JWT_SECRET_KEY=replace-with-a-long-random-secret
RAGFUSION_JWT_ALGORITHM=HS256
RAGFUSION_ACCESS_TOKEN_EXPIRE_MINUTES=15
RAGFUSION_REFRESH_TOKEN_EXPIRE_DAYS=30
RAGFUSION_TRUSTED_PROXIES=[]
RAGFUSION_RATE_LIMIT_REDIS_TIMEOUT_SECONDS=1.0
GROQ_API_KEY=replace-with-your-groq-key
RAGFUSION_EMBEDDING_LOCAL_FILES_ONLY=true
RAGFUSION_EMBEDDING_WARMUP=true
ANONYMIZE_TELEMETRY=False
CHROMA_TELEMETRY=False
ANONYMIZED_TELEMETRY=False
```

`DATABASE_URL` is also accepted for local compatibility, but `RAGFUSION_DATABASE_URL` takes precedence. The default local database identity is `docpro`; it is a compatibility name and should be given a strong password outside development.

The frontend reads `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Only public browser configuration belongs in `VITE_*` variables. Never put database credentials, JWT secrets, provider keys, or refresh tokens in frontend environment files.

## Local installation

### 1. Create PostgreSQL and Redis

Start PostgreSQL and Redis with your operating system, or create the local PostgreSQL role/database once:

```bash
psql -X -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE ROLE docpro WITH LOGIN PASSWORD 'docpro' NOSUPERUSER NOCREATEDB NOCREATEROLE;" \
  -c "CREATE DATABASE docpro OWNER docpro;"
```

If the role or database already exists, run the corresponding `ALTER ROLE` or skip the completed statement. Confirm the API can use:

```bash
export RAGFUSION_DATABASE_URL='postgresql+asyncpg://docpro:docpro@localhost:5432/docpro'
redis-cli ping
```

### 2. Install the backend

From the repository root:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
cd backend
cp .env.example .env
python -m pip install -r requirements/base.txt
python -m pip check
python -m alembic -c alembic.ini upgrade head
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://127.0.0.1:8000`; OpenAPI is at `/docs`, and the dependency readiness probe is `GET /api/v1/health`. A degraded health result means PostgreSQL or Redis is not ready yet; it is not a substitute for running migrations.

### 3. Install the frontend

In a second terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Vite serves the workspace at the URL it prints, normally `http://localhost:5173`.

### 4. Docker Compose

Compose runs the API, PostgreSQL, and Redis together, persists database/uploads/vector data in named volumes, and runs the API as UID 10001:

```bash
cd backend
cp .env.example .env
docker compose up --build
```

The API is published on port `8000`. PostgreSQL is bound to `127.0.0.1:55432` for host-side inspection; Redis is internal to the Compose network. When a host-run API must connect to the Compose database, use:

```dotenv
RAGFUSION_DATABASE_URL=postgresql+asyncpg://docpro:docpro@localhost:55432/docpro
RAGFUSION_REDIS_URL=redis://localhost:6379/0
```

The API container uses `postgresql+asyncpg://docpro:docpro@postgres:5432/docpro` and `redis://redis:6379/0`. Named volumes are `postgres_data`, `redis_data`, `uploads_data`, and `vectors_data`.

## API reference

All application endpoints are prefixed with `/api/v1` and require `Authorization: Bearer <access-token>` unless marked public. FastAPI’s generated OpenAPI document at `/docs` is the authoritative schema for all fields and validation constraints.

### Authentication and profile

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/signup` | Create an account and return access/refresh tokens. |
| `POST` | `/auth/login` | Authenticate with credentials and return tokens. |
| `POST` | `/auth/refresh` | Validate and atomically rotate a refresh token. |
| `POST` | `/auth/logout` | Increment `auth_version` and revoke active tokens. |
| `GET` | `/auth/me` | Return the authenticated user profile. |
| `PATCH` | `/auth/me` | Validate and update editable profile fields. |

### Chat and history

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/chat/sources` | List the caller’s ready document, website, and YouTube sources. |
| `POST` | `/chat` | Run a bounded non-streaming RAG turn. Use `session_id` or `chat_session_id` to continue a session. |
| `POST` | `/chat/stream` | Run the same turn as Server-Sent Events. Check `is_disconnected()` and handle `error` chunks. |
| `GET` | `/chat/sessions` | List non-deleted sessions with message counts. |
| `GET` | `/chat/sessions/{session_id}` | Load a session and paginated message history. |
| `POST` | `/chat/sessions` | Create an empty named session. |
| `PATCH` | `/chat/sessions/{session_id}` | Rename a session and update metadata. |
| `DELETE` | `/chat/sessions/{session_id}` | Soft-delete a session. |
| `DELETE` | `/chat/sessions/{session_id}/messages` | Clear messages while retaining the session. |
| `GET` | `/history`, `/history/search` | Paginated history and title search. |
| `POST` | `/history/{session_id}/restore` | Restore a soft-deleted session. |

`ChatRequest` accepts `message`, optional session ID, `source_ids`, `top_k`, `temperature`, `max_tokens`, `include_sources`, and `stream`. `source_ids` has `document`, `website`, and `youtube` UUID arrays. Omit it or send empty arrays for all of the caller’s ready sources; never use a client-only source ID as an authorization mechanism.

### Knowledge ingestion

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/documents/upload` | Multipart upload with validated format and chunk settings. The route reports the final persisted state with its declared `202` response. |
| `GET` | `/documents` | Paginated owned documents, optionally filtered by status. |
| `GET` | `/documents/{document_id}` | Read owned document state and metadata. |
| `POST` | `/documents/{document_id}/reprocess` | Re-run extraction/indexing with new chunk parameters. |
| `DELETE` | `/documents/{document_id}` | Remove the document and its vectors. |
| `POST` | `/youtube/ingest` | Ingest a YouTube transcript. Returns `202` with source status. |
| `GET` | `/youtube` | List owned YouTube sources. |
| `GET` | `/youtube/{youtube_source_id}` | Read one YouTube source. |
| `GET` | `/youtube/{youtube_source_id}/transcript` | Read transcript metadata/content. |
| `DELETE` | `/youtube/{youtube_source_id}` | Remove a YouTube source and vectors. |
| `POST` | `/website/ingest` | Validate and register a public website URL. |
| `GET` | `/website` | List owned websites and processing states. |
| `GET` | `/website/{source_id}` | Read one website source. |
| `POST` | `/website/{source_id}/process` | Crawl, extract, chunk, embed, and index a website. |
| `DELETE` | `/website/{source_id}` | Remove a website and its vectors. |

Document chunk parameters are bounded (`chunk_size` 100–10,000 and `chunk_overlap` 0–1,000) and must satisfy `chunk_overlap < chunk_size`. Website submissions use the `WebsiteSubmission` schema and are subject to the crawler’s SSRF policy.

### Settings, dashboard, and system

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/settings` | Read per-user LLM, embedding, retrieval, and chunk settings. |
| `PUT` | `/settings` | Validate and update settings; `temperature=0.0` is preserved. |
| `POST` | `/settings/reset` | Restore defaults. |
| `GET` | `/dashboard` | Return live source counts and recent non-deleted sessions. |
| `GET` | `/health` | Report PostgreSQL/Redis/application readiness. |
| `GET` | `/info` | Return non-sensitive application name and environment. |

## Testing and quality checks

Run backend tests from the repository root with the environment that has `backend/requirements/base.txt` installed:

```bash
.venv/bin/python -m pytest -q backend/tests
.venv/bin/python -m pytest -q backend/tests/test_security.py backend/tests/test_rate_limiter.py backend/tests/test_rag.py
```

Run frontend tests and production checks:

```bash
cd frontend
npm test -- --run
npm run lint
npm run build
npm run typecheck
```

The Vitest suite uses JSDOM and Testing Library for API-session, auth-expiry, chat-session, profile, and workspace regression coverage. The backend suite includes database/migration, authentication, rate limiting, SSRF/crawler, documents, YouTube, RAG, history, performance, and regression tests.

Useful audit probes are kept under `audits/2026-10-04/`:

```bash
.venv/bin/python audits/2026-10-04/verify_findings.py --batch 1
.venv/bin/python audits/2026-10-04/verify_findings.py --batch 2
.venv/bin/python audits/2026-10-04/verify_findings.py --batch 3
.venv/bin/python audits/2026-10-04/verify_findings.py --batch 4
.venv/bin/python audits/2026-10-04/verify_findings.py --batch 5
.venv/bin/python audits/2026-10-04/verify_findings.py --batch 6
```

## Deployment and operations notes

- Run Alembic migrations before starting application workers and back up PostgreSQL before upgrades.
- Mount durable storage for uploads and Chroma’s vector directory. Losing either breaks source availability or requires re-ingestion.
- Keep the embedding model cache warm on each worker or provision the image with the model before enabling `RAGFUSION_EMBEDDING_LOCAL_FILES_ONLY=true`.
- Set a unique high-entropy `RAGFUSION_JWT_SECRET_KEY` and real provider credentials in the secret manager. Do not commit `.env` files, keys, vector data, databases, or build output.
- Configure `RAGFUSION_TRUSTED_PROXIES` only with addresses owned by the deployment. Rate-limit identity falls back to `request.client.host` when no trusted proxy is configured.
- Monitor `/api/v1/health`, rate-limit 503/429 responses, ingestion failures, Chroma disk usage, PostgreSQL pool saturation, and LLM provider latency.
- Treat provider settings as deployment configuration. The settings contract accepts provider identifiers and the provider package contains the integration boundary; the active RAG graph currently constructs `ChatGroq` and therefore requires `GROQ_API_KEY` unless the graph is extended with another configured adapter.

## License

RAGFUSION is distributed under the MIT License. Add the repository’s `LICENSE` file before publishing a release if one is not already present.
