# RAGFUSION technical and security audit

Audit date: **4 October 2026**. Repository HEAD: `d5daa5dadc8af8ee29ad13e11cf5ef05a8ba95f9` plus locally present ignored source. Application source was not modified.

**Release recommendation: resolve the confirmed High findings before production deployment.** There are **28 findings: 11 High, 16 Medium, 1 Low**. One High finding (A12, crawler SSRF) is dormant because its router is disabled. No Critical issue was confirmed. Severity reflects potential impact and observed code reachability; it is not a CVSS assessment.

The actual stack is React 19/Vite/Tailwind with Context, Axios, React Hook Form and Zod; FastAPI/Pydantic/async SQLAlchemy; PostgreSQL plus a local Chroma index; Redis in Compose; LangGraph/Groq and local HuggingFace embeddings. There is no React Query/Redux layer in the reviewed application. The auth flow uses bearer JWTs rather than cookie sessions.

## What was checked

Inspected active routing, authentication, middleware, schemas, ORM entities, Alembic revisions, ingestion/storage, RAG retrieval/prompt construction, history/settings, frontend providers/API clients/readers/forms, dependency manifests, Docker configuration and test setup. Existing historical audit reports were not treated as proof. Archived implementations are outside the active application assessment.

- Frontend: `npm run build`, `npm run lint`, and the configured `npm run typecheck` all exited 0. The build warned about an ineffective dynamic import of HeroScene. These commands do not establish browser behavior or accessibility correctness.
- Backend: application import and OpenAPI generation succeeded with synthetic configuration. The selected existing suite **did not run**: collection stopped at the Crawl4AI import in conftest (A25).
- [Offline probe script](/Users/anshusonkar067/Desktop/RAGFUSION/audits/2026-10-04/verify_findings.py) ran successfully. [Machine-readable results](/Users/anshusonkar067/Desktop/RAGFUSION/audits/2026-10-04/verification-results.json) record path traversal, password corruption, refresh replay, index-failure success, duplicate chunks/metadata loss, migration drift, wrong exception dispatch, embedding error masking, invalid chunking, discarded history, post-filtered retrieval and dormant URL-validator bypasses.
- The probes used disposable SQLite/files, synthetic credentials, and mocked external services. They did not touch the application's data, fetch private network URLs, call an LLM, or load an embedding model.
- No live PostgreSQL/Redis/Chroma integration, production reverse proxy/TLS, real browser E2E, dependency CVE scanner, penetration/load test, or full WCAG audit was performed. Concurrent PostgreSQL and browser findings are explicitly marked as code analysis. No claim of exhaustive vulnerability absence is made.

## Remediation order

1. Contain file traversal (A01), preserve required source in Git (A02), repair connection handling/migrations (A03–A04), and restore reproducible dependencies/tests (A25).
2. Enforce throttling and persistent session revocation (A05–A06), bound heavy work (A08), persist storage (A11), and make ingestion failure/retry behavior truthful (A09–A10).
3. Fix client isolation and async races (A07/A20), wire settings/history/retrieval (A13–A15), repair API error/validation contracts (A16–A19), then remaining product/database/accessibility findings. Keep the crawler disabled until A12's network protections are complete.

## Reading the fixes

Each entry includes the requested severity, component, location, problem, before/after code and verification. **After snippets are proposed changes, not applied or production-validated patches.** They show the concrete change at the named integration points; import additions, migrations, fixture changes and cross-file contracts called out in the entry must be implemented together. Authentication storage and durable ingestion require coordinated designs, so isolated copy-paste is insufficient. Release gating is provided where an advertised feature has no implementation.

## A01 — Upload filenames escape storage and allow file overwrite

- **[Severity]:** High
- **[Component]:** Security
- **[File/Location]:** [backend/app/services/document.py:643](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/document.py:643), [backend/app/api/documents.py:312](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/documents.py:312)
- **Evidence:** Reproduced offline against actual upload function.

**[The Problem]:** The multipart filename is concatenated into the storage key and opened with wb before validation. Authenticated users can traverse outside upload_dir and overwrite files writable by the API process. The stored key is later trusted by DELETE, so the same path can be unlinked. RCE depends on writable executable/configuration paths and was not attempted.

**[Code Fix] — flawed code:**

```text
storage_key = f"uploads/{user_id}/{document_id}/{filename}"
file_path = Path(settings.upload_dir) / storage_key
async with aiofiles.open(file_path, "wb") as f:
    await f.write(file_content)
```

**Corrected implementation at the indicated integration points:**

```text
# Client filenames are display metadata only. The storage tree must be
# private to this service account; migrate/reject legacy unsafe keys.
root = Path(settings.upload_dir).resolve()
storage_key = f"uploads/{user_id}/{document_id}/content"
file_path = root / storage_key
file_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
created = False
try:
    async with aiofiles.open(file_path, "xb") as f:
        created = True
        await f.write(file_content)
    validate_file(file_path, content_type, len(file_content))
except Exception:
    if created:
        file_path.unlink(missing_ok=True)
    raise

# Apply before opening OR deleting a pre-existing storage key:
def resolve_storage_key(root: Path, key: str) -> Path:
    root = root.resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or path == root:
        raise DocumentValidationError("Invalid storage key")
    return path
```

**[Verification]:** Run verify_findings.py: the actual upload service writes a harmless marker outside its configured root, entirely within a temporary directory. After remediation, a filename ../../../../outside.txt must never create a file outside the root; check delete handling of legacy traversal keys too.

Use generated storage names and independent content/size checks; see [OWASP File Upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).

## A02 — Required application source is absent from Git

- **[Severity]:** High
- **[Component]:** Backend
- **[File/Location]:** [.gitignore:17](/Users/anshusonkar067/Desktop/RAGFUSION/.gitignore:17), [.gitignore:72](/Users/anshusonkar067/Desktop/RAGFUSION/.gitignore:72), [backend/app/models/entities.py:1](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/models/entities.py:1), [backend/app/rag/embeddings/embedding_manager.py:1](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/rag/embeddings/embedding_manager.py:1), [frontend/src/lib/utils.js:1](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/lib/utils.js:1)
- **Evidence:** Confirmed with Git tracked-file and ignore inventories.

**[The Problem]:** Broad lib/, models/, and embeddings/ ignore patterns hide real application source. These files exist locally but are not in git ls-files. A clean checkout loses the ORM models, embedding implementation, frontend utilities and validation schemas, causing import/build failures. A successful local build does not validate the deliverable repository.

**[Code Fix] — flawed code:**

```text
lib/
models/
embeddings/
```

**Corrected implementation at the indicated integration points:**

```text
# Keep existing artifact ignores, but explicitly preserve source directories.
!frontend/src/lib/
!frontend/src/lib/**
!backend/app/models/
!backend/app/models/**
!backend/app/rag/embeddings/
!backend/app/rag/embeddings/**

# Then stage the source files (after reviewing their content):
# git add .gitignore frontend/src/lib backend/app/models backend/app/rag/embeddings
```

**[Verification]:** git ls-files backend/app/models backend/app/rag/embeddings frontend/src/lib currently returns no files. git check-ignore -v identifies the three rules. Verify a fresh checkout can import main and build the frontend.

## A03 — Database URL conversion replaces the real password with ***

- **[Severity]:** High
- **[Component]:** Database
- **[File/Location]:** [backend/app/db/session.py:32](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/db/session.py:32)
- **Evidence:** Reproduced with installed SQLAlchemy 2.0.51.

**[The Problem]:** SQLAlchemy URL.__str__ masks passwords. Re-parsing that result gives the async engine the literal password ***. PostgreSQL password authentication consequently fails even with correct configuration. SQLite tests cannot catch this.

**[Code Fix] — flawed code:**

```text
return str(url.set(drivername=replacements.get(driver, driver)))
```

**Corrected implementation at the indicated integration points:**

```text
return url.set(
    drivername=replacements.get(driver, driver)
).render_as_string(hide_password=False)
```

**[Verification]:** Run verify_findings.py. Using synthetic credentials, assert make_url(to_async_database_url('postgresql://u:synthetic@localhost/db')).password == 'synthetic'. Then test PostgreSQL login in a disposable database. Never log the unmasked URL.

SQLAlchemy documents password masking and the explicit override in [URL.render_as_string](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.engine.URL.render_as_string).

## A04 — Alembic head lacks chat_sessions.deleted_at

- **[Severity]:** High
- **[Component]:** Database
- **[File/Location]:** [backend/app/models/entities.py:183](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/models/entities.py:183), [backend/alembic/versions/20260801_0001_initial_schema.py:1](/Users/anshusonkar067/Desktop/RAGFUSION/backend/alembic/versions/20260801_0001_initial_schema.py:1), [backend/alembic/versions/7efa7e63b3ce_merge_migration_heads.py:1](/Users/anshusonkar067/Desktop/RAGFUSION/backend/alembic/versions/7efa7e63b3ce_merge_migration_heads.py:1)
- **Evidence:** Reproduced through complete Alembic upgrade on disposable SQLite.

**[The Problem]:** The ORM reads deleted_at, but no revision creates it. Upgrading an empty database to head succeeds and still leaves the column missing. Selecting ChatSession, including normal chat/history operations, fails. Tests build tables from ORM metadata and therefore conceal this schema drift.

**[Code Fix] — flawed code:**

```text
# ORM:
deleted_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True, index=True
)
# No corresponding Alembic operation exists.
```

**Corrected implementation at the indicated integration points:**

```text
# New revision; do not edit already-applied migrations.
from alembic import op
import sqlalchemy as sa

revision = "20261004_0001"
down_revision = "7efa7e63b3ce"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("chat_sessions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_chat_sessions_deleted_at",
                    "chat_sessions", ["deleted_at"])

def downgrade():
    op.drop_index("ix_chat_sessions_deleted_at", table_name="chat_sessions")
    op.drop_column("chat_sessions", "deleted_at")
```

**[Verification]:** Run the audit probe: a fresh disposable Alembic database lacks deleted_at. After the migration, assert the column/index exist and run ORM chat CRUD against the migrated PostgreSQL schema, rather than Base.metadata.create_all().

## A05 — Rate limiting is implemented but never installed

- **[Severity]:** High
- **[Component]:** API
- **[File/Location]:** [backend/main.py:17](/Users/anshusonkar067/Desktop/RAGFUSION/backend/main.py:17), [backend/app/middleware/rate_limit_middleware.py:14](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/middleware/rate_limit_middleware.py:14)
- **Evidence:** Confirmed active middleware inventory; no load attack performed.

**[The Problem]:** create_app installs no RateLimitMiddleware or route limit dependency. Login hashing, signup, ingestion and billable chat can be repeated without application throttling. Simply installing the existing middleware is insufficient for multiple workers; it uses process-local state and trusts arbitrary X-Forwarded-For values. Reverse-proxy protections were not available for inspection.

**[Code Fix] — flawed code:**

```text
app.add_middleware(PerformanceMiddleware)
# No RateLimitMiddleware registration.
forwarded = request.headers.get("X-Forwarded-For")
```

**Corrected implementation at the indicated integration points:**

```text
# A shared Redis implementation matching the existing check() interface.
import math
from redis.asyncio import Redis
from app.core.rate_limiter import RateLimitResult

class RedisRateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check(self, key, policy):
        window_ms = math.ceil(policy.window_seconds * 1000)
        count, ttl = await self.redis.eval("""
            local n = redis.call('INCR', KEYS[1])
            if n == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end
            return {n, redis.call('PTTL', KEYS[1])}
        """, 1, "rate:" + key, window_ms)
        capacity = policy.limit + policy.burst
        return RateLimitResult(count <= capacity, max(0, capacity-count),
                               max(1, math.ceil(ttl/1000)))

# During app construction; also aclose this client at shutdown.
app.state.rate_redis = Redis.from_url(settings.redis_url)
app.add_middleware(RateLimitMiddleware,
    limiter=RedisRateLimiter(app.state.rate_redis))

# Replace _identity: trust only ASGI's client address.
# Configure Uvicorn trusted proxy addresses explicitly at deployment.
@staticmethod
def _identity(request):
    return f"ip:{request.client.host if request.client else 'unknown'}"
```

**[Verification]:** On a disposable instance, exceed seven login attempts per minute and expect 429 with Retry-After. Repeat across two workers and vary X-Forwarded-For: neither should reset the bucket. Add separate authenticated-user limits for ingestion/chat to bound shared-IP and distributed abuse. Fail closed with a controlled 503 if Redis is unavailable.

## A06 — Logout does not revoke tokens; refresh tokens can be replayed

- **[Severity]:** High
- **[Component]:** Security
- **[File/Location]:** [backend/app/api/auth.py:86](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/auth.py:86), [backend/app/services/auth.py:157](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/auth.py:157)
- **Evidence:** Reproduced against active auth service with disposable user.

**[The Problem]:** Logout only decodes a bearer token. Refresh issues new JWTs without invalidating the old refresh token; no persistent revocation state is consulted. A copied refresh token remains usable after logout for its original 30-day lifetime. The separate JWTManager is not used by these routes; its in-memory revocation would not solve multi-process persistence either.

**[Code Fix] — flawed code:**

```text
# logout_endpoint:
decode_token(token)
return LogoutResponse()

# refresh:
payload = decode_token(data.refresh_token)
return create_token_response(user)
```

**Corrected implementation at the indicated integration points:**

```text
# Minimal persistent revocation strategy: account-wide token epoch.
# Add User.auth_version (integer, NOT NULL, default 0) via Alembic.
auth_version: Mapped[int] = mapped_column(Integer, default=0,
                                        server_default="0", nullable=False)

# Include the current epoch in BOTH access and refresh JWTs when issuing:
to_encode["ver"] = user.auth_version

# After loading the user in BOTH get_current_user and refresh:
if not user or not user.is_active or payload.get("ver") != user.auth_version:
    raise UnauthorizedError("Invalid or expired session")

# In refresh, atomically consume the refresh epoch before issuing replacements.
# Changes create_token_response to include user.auth_version in both JWTs.
old_version = payload.get("ver")
if not isinstance(old_version, int):
    raise UnauthorizedError("Invalid session")
new_version = await db.scalar(
    update(User)
    .where(User.id == user.id, User.auth_version == old_version)
    .values(auth_version=User.auth_version + 1)
    .returning(User.auth_version)
)
if new_version is None:
    raise UnauthorizedError("Refresh token already used")
await db.commit()
user.auth_version = new_version
return create_token_response(user)

# Logout authenticates an access token, then revokes all account tokens:
await db.execute(update(User).where(User.id == current_user.id)
                 .values(auth_version=User.auth_version + 1))
await db.commit()
return LogoutResponse()
```

**[Verification]:** The offline probe successfully refreshes the same JWT before and after logout. After the fix, both must fail after revocation, and two concurrent refresh requests must yield exactly one success. This minimal strategy intentionally revokes other devices on refresh/logout; for independent device sessions, move the epoch/rotation state into an auth_sessions table keyed by JWT sid. Update all token-creation callers and test concurrency.

Persistent revocation and browser token handling should follow [OWASP Session Management guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

## A07 — Authentication and private browser state survive across user boundaries

- **[Severity]:** Medium
- **[Component]:** Frontend
- **[File/Location]:** [frontend/src/services/auth.js:3](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/services/auth.js:3), [frontend/src/services/api.js:18](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/services/api.js:18), [frontend/src/context/ChatContext.jsx:6](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/context/ChatContext.jsx:6), [frontend/src/context/UploadContext.jsx:6](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/context/UploadContext.jsx:6), [frontend/src/main.jsx:17](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/main.jsx:17)
- **Evidence:** Static trace; browser exploit and cross-tab race not executed.

**[The Problem]:** Access and 30-day refresh tokens are JavaScript-readable in localStorage, increasing the consequence of any same-origin script compromise; no XSS exploit was confirmed. Logout clears token/profile keys but leaves docpro-current-chat, docpro-chat-session, and docpro-uploads. Providers live above the router and do not reset when identity changes. A second user on the same browser can encounter the previous user's cached content/state even though backend ownership checks remain present.

**[Code Fix] — flawed code:**

```text
localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)
const CURRENT_CHAT_STORAGE_KEY = 'docpro-current-chat'
const UPLOADS_STORAGE_KEY = 'docpro-uploads'
// UserProvider/ChatProvider/UploadProvider remain mounted on logout.
```

**Corrected implementation at the indicated integration points:**

```text
// Immediate privacy fix: clear private caches on every auth transition.
const PRIVATE_KEYS = [
  'access_token', 'refresh_token', 'user', 'docpro-user', 'docpro-profile',
  'docpro-current-chat', 'docpro-chat-session', 'docpro-uploads'
]
export function clearSession() {
  authSessionVersion += 1
  PRIVATE_KEYS.forEach(key => localStorage.removeItem(key))
}

// Place this component INSIDE AuthProvider; remount all private state
// on login/logout/account change.
function PrivateState({ children }) {
  const { user } = useAuth()
  return (
    <UserProvider key={user?.id || 'anonymous'}>
      <ChatProvider><UploadProvider>{children}</UploadProvider></ChatProvider>
    </UserProvider>
  )
}

// Also gate ChatProvider.refreshHistory on useAuth().user and ignore stale
// responses using an identity/epoch guard; remounting alone must not trigger
// anonymous requests that redirect a visitor away from signup.

// Export from api.js, and guard every async cache writer:
export const getAuthSessionVersion = () => authSessionVersion

// Inside each private provider:
const ownSessionVersion = useRef(getAuthSessionVersion()).current
// At the start of persist/saveToStorage (and after awaited reads):
if (ownSessionVersion !== getAuthSessionVersion()) return

// Durable token-storage redesign, in the auth endpoint response:
response.set_cookie(
    "__Host-refresh", refresh_token, secure=True, httponly=True,
    samesite="lax", path="/", max_age=30 * 24 * 3600
)
// Keep access tokens only in memory; read refresh cookies server-side.
// Enforce an exact allowed Origin on cookie-authenticated refresh/logout,
// remove the refresh token from JSON, and clear the cookie on logout.
```

**[Verification]:** Log in as A, populate chat/upload caches, log out, then log in as B without reloading. B must see none of A's state, including after delayed A responses arrive. After the cookie redesign document.cookie must not expose the refresh token; untrusted Origin requests must be rejected. Test cross-tab logout through a storage/BroadcastChannel event.

## A08 — Heavy synchronous work runs in async request paths; streaming has no total deadline

- **[Severity]:** High
- **[Component]:** Backend
- **[File/Location]:** [backend/app/services/document.py:553](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/document.py:553), [backend/app/services/document.py:491](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/document.py:491), [backend/app/services/auth.py:126](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/auth.py:126), [backend/app/services/chat_service.py:62](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/chat_service.py:62), [backend/app/services/chat_service.py:202](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/chat_service.py:202), [backend/app/api/documents.py:147](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/documents.py:147)
- **Evidence:** Static call-path analysis; no stress test against running services.

**[The Problem]:** Extraction, cleaning, chunking, Chroma construction/insertion and password hashing run directly in async functions. RAGPipeline initialization synchronously constructs a HuggingFace model for each request-scoped ChatService. The route advertises background ingestion but awaits it. /chat/stream has no enclosing timeout and buffers the whole LLM result before slicing it. A slow model/file/provider can stall other requests or retain workers beyond the apparent timeout; cancelling to_thread does not terminate its underlying work.

**[Code Fix] — flawed code:**

```text
password_hash = hash_password(data.password)
text, metadata = extract_text(file_path, format_)
retriever = RetrieverManager()
self.rag_pipeline = RAGPipeline()
async for chunk in self._run_rag_pipeline_stream(...):
```

**Corrected implementation at the indicated integration points:**

```text
# Short-term: bounded offloading for local synchronous calls.
# Create these limiters once per process; choose limits using resource budgets.
import anyio
PASSWORD_LIMITER = anyio.CapacityLimiter(2)
INGEST_LIMITER = anyio.CapacityLimiter(2)

password_hash = await anyio.to_thread.run_sync(
    hash_password, data.password, limiter=PASSWORD_LIMITER)
text, metadata = await anyio.to_thread.run_sync(
    extract_text, file_path, format_, limiter=INGEST_LIMITER)

# Initialize/share immutable embedding/retrieval resources at app lifespan,
# outside the event loop. Keep user-specific config separate per invocation.
app.state.rag_pipeline = await anyio.to_thread.run_sync(RAGPipeline)

# Both chat entry points need an enclosing deadline.
async with asyncio.timeout(self.timeout_seconds):
    async for chunk in self._run_rag_pipeline_stream(
        message=message, history=history, session_id=session_id,
        top_k=top_k, max_tokens=max_tokens, temperature=temperature):
        yield chunk
```

**[Verification]:** Inject a slow parser/hash/model constructor while measuring a lightweight /info request. It should remain responsive. Inject a never-completing provider and assert stream termination. Use provider-native network timeouts and a bounded durable worker queue with process-level time/memory limits for untrusted document parsing; threads alone do not contain decompression bombs or stop timed-out CPU work. Return 202 only after durably enqueueing a job.

Offloading keeps blocking work off the event loop; see [Python asyncio.to_thread](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread). Provider deadlines and resource containment remain separate concerns.

## A09 — Ingestion reports success when vector indexing fails; storage has no recovery contract

- **[Severity]:** High
- **[Component]:** Backend
- **[File/Location]:** [backend/app/services/document.py:521](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/document.py:521), [backend/app/api/documents.py:147](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/documents.py:147), [frontend/src/components/upload/UploadCard.jsx:158](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/components/upload/UploadCard.jsx:158), [backend/app/api/documents.py:334](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/documents.py:334), [backend/app/api/youtube.py:274](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/youtube.py:274)
- **Evidence:** Reproduced index-failure success; cross-store failure scenarios statically traced.

**[The Problem]:** store_document catches Chroma errors and commits ready anyway. Upload swallows processing failures and returns an old detached Document status; the UI marks every successful HTTP upload Ready without inspecting status. File/SQL/vector mutations have separate commit points, so failures also leave orphaned vectors/files or a surviving row pointing at deleted storage. A PostgreSQL rollback cannot roll back Chroma or filesystem changes.

**[Code Fix] — flawed code:**

```text
except Exception as exc:
    print(f"ChromaDB insertion failed: {exc}")
db_document.status = SourceStatus.ready
await session.commit()

# upload route:
except Exception:
    pass
```

**Corrected implementation at the indicated integration points:**

```text
# Never suppress indexing failure or mark an unindexed document ready.
texts = [chunk.content for chunk in chunks]
metadatas = [{
    "source_id": str(document.id), "source_type": "document",
    "document_id": str(document.id), "user_id": str(document.user_id),
    "filename": document.filename, "chunk_index": i,
} for i, chunk in enumerate(chunks)]
stable_ids = [f"{document.id}_chunk_{i}" for i in range(len(chunks))]
try:
    await asyncio.to_thread(
        retriever.add_documents, texts, metadatas, stable_ids)
except Exception as exc:
    raise DocumentProcessingError(
        "Document indexing failed", code="INDEX_FAILED") from exc
db_document.status = SourceStatus.ready
await session.commit()

# Synchronous upload contract: return the fresh persisted state.
# Use 201 on completed ingestion, or enqueue durably and return 202/pending.
await process_document(document.id, file_path, format_, config)
document = await db.get(Document, document.id, populate_existing=True)
return DocumentUploadResponse(
    document_id=document.id, filename=document.filename,
    status=safe_document_status(document.status),
    message="Document processing completed")

// Frontend: distinguish accepted/pending, failed, and actually ready.
const ready = data.status === 'ready'
const failed = data.status === 'failed'
setFiles(prev => prev.map(f => f.id === fileObj.id ? {
  ...f, uploading: false, uploaded: ready,
  processing: !ready && !failed,
  error: failed ? 'Document processing failed' : null,
  documentId: data.document_id
} : f))
```

**[Verification]:** The probe forces RetrieverManager failure and observes ready in SQL. After the fix this must become failed/pending and never Ready in the UI. Inject failure after each SQL/file/vector operation and retry; require convergence with stable operation IDs. For durable production recovery, commit an outbox/job record with SQL state, have an idempotent worker perform external writes/deletes, and only then advance status.

## A10 — Reprocessing duplicates chunks and loses metadata

- **[Severity]:** Medium
- **[Component]:** Database
- **[File/Location]:** [backend/app/services/document.py:507](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/document.py:507), [backend/app/models/entities.py:232](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/models/entities.py:232), [backend/app/api/documents.py:361](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/documents.py:361)
- **Evidence:** Reproduced duplicate rows and metadata loss.

**[The Problem]:** Each reprocess appends Embedding rows without replacing existing rows. Composite indexes are non-unique, so repeated/concurrent runs create duplicate chunk positions. metadata=chunk.metadata writes an unmapped attribute instead of metadata_, silently losing page/strategy metadata. Chroma upserts stable IDs but shortened reprocessing can leave old trailing IDs. Embeddings also permit zero or multiple source foreign keys.

**[Code Fix] — flawed code:**

```text
for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
    emb = Embedding(document_id=document.id, chunk_index=i,
        content=chunk.content, vector=embedding,
        model_name=config.model_name, metadata=chunk.metadata)
    session.add(emb)
```

**Corrected implementation at the indicated integration points:**

```text
# In one SQL transaction; serialize jobs for this document.
from sqlalchemy import delete, select
db_document = await session.scalar(select(Document)
    .where(Document.id == document.id).with_for_update())
if len(chunks) != len(embeddings):
    raise DocumentProcessingError("Embedding count mismatch")
await session.execute(delete(Embedding)
    .where(Embedding.document_id == document.id))
session.add_all([
    Embedding(document_id=document.id, chunk_index=i,
        content=chunk.content, vector=vector,
        model_name=config.model_name, token_count=chunk.token_count,
        metadata_=chunk.metadata)
    for i, (chunk, vector) in enumerate(zip(chunks, embeddings))
])
# Add after deduplicating existing data, in an Alembic revision:
op.create_unique_constraint("uq_embedding_document_chunk",
    "embeddings", ["document_id", "chunk_index"])
op.create_unique_constraint("uq_embedding_website_chunk",
    "embeddings", ["website_id", "chunk_index"])
op.create_unique_constraint("uq_embedding_youtube_chunk",
    "embeddings", ["youtube_source_id", "chunk_index"])
op.create_check_constraint("ck_embedding_one_source", "embeddings",
    "(CASE WHEN document_id IS NULL THEN 0 ELSE 1 END + "
    "CASE WHEN website_id IS NULL THEN 0 ELSE 1 END + "
    "CASE WHEN youtube_source_id IS NULL THEN 0 ELSE 1 END) = 1")
```

**[Verification]:** The probe stores one chunk twice and gets two rows with empty metadata instead of {'page':7}. After remediation the same job must retain one row and metadata. Reprocess a long file into fewer chunks and confirm obsolete Chroma IDs disappear. Couple vector replacement to A09's versioned/idempotent job; do not hold a database lock during expensive model inference.

## A11 — Container recreation loses uploads and the vector index

- **[Severity]:** High
- **[Component]:** Backend
- **[File/Location]:** [backend/docker-compose.yml:2](/Users/anshusonkar067/Desktop/RAGFUSION/backend/docker-compose.yml:2), [backend/app/config/settings.py:39](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/config/settings.py:39), [backend/app/core/rag_config.py:43](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/core/rag_config.py:43), [backend/Dockerfile:1](/Users/anshusonkar067/Desktop/RAGFUSION/backend/Dockerfile:1)
- **Evidence:** Static deployment inspection; no container recreation performed.

**[The Problem]:** Only PostgreSQL and Redis have volumes. Uploaded files default to /tmp/docpro_uploads and Chroma to ./data/vectorstore in the API container's writable layer. Recreating that container loses source files/index while SQL retains ready sources. The API image also runs as root and COPY . . has no backend .dockerignore, potentially copying local .env/data into the image when present.

**[Code Fix] — flawed code:**

```text
api:
  build: .
  env_file: .env
  ports:
    - "8000:8000"
# No API volumes; Dockerfile ends with root-owned COPY . .
```

**Corrected implementation at the indicated integration points:**

```text
# docker-compose.yml additions
services:
  api:
    environment:
      DOCPRO_UPLOAD_DIR: /var/lib/docpro/uploads
      RAG_VECTOR_STORE_PATH: /var/lib/docpro/vectorstore
    volumes:
      - uploads_data:/var/lib/docpro/uploads
      - vectors_data:/var/lib/docpro/vectorstore
volumes:
  uploads_data:
  vectors_data:

# Dockerfile, before switching user:
RUN useradd --system --uid 10001 --create-home appuser \
    && mkdir -p /var/lib/docpro/uploads /var/lib/docpro/vectorstore \
    && chown -R appuser:appuser /var/lib/docpro /app
USER 10001

# backend/.dockerignore
.env
.env.*
!.env.example
data/
*.db
__pycache__/
.pytest_cache/
```

**[Verification]:** In disposable deployment infrastructure, ingest a canary then recreate only the API container; verify file existence and retrieval after recreation. Inspect image contents without printing secrets and assert no .env is packaged. Use a managed vector service/object store for multi-host scaling; local named volumes alone are single-host persistence.

## A12 — Dormant crawler has SSRF bypasses and unchecked redirects

- **[Severity]:** High (dormant; router disabled)
- **[Component]:** Security
- **[File/Location]:** [backend/app/services/crawler_service.py:53](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/crawler_service.py:53), [backend/app/services/crawler_service.py:112](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/crawler_service.py:112), [backend/app/api/routes.py:13](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/routes.py:13)
- **Evidence:** Offline validator bypasses reproduced; route disabled.

**[The Problem]:** URL validation blocks a few hostname strings, not resolved destinations. IPv4-mapped IPv6, ULA IPv6, abbreviated loopback, DNS-to-private hosts and redirects bypass it. The browser crawler has an additional subresource network path. This is a High-severity latent risk: the website router is commented out, so it is not remotely reachable through the current main app.

**[Code Fix] — flawed code:**

```text
for pattern in blocked_patterns:
    if re.match(pattern, hostname):
        raise CrawlerValidationError(...)
async with session.get(url, allow_redirects=follow_redirects) as response:
    html = await response.text()
```

**Corrected implementation at the indicated integration points:**

```text
# aiohttp-only fetch path: constrain DNS at connection time, disable
# environment proxies, disable redirects, and bound the response body.
import ipaddress
from aiohttp.resolver import DefaultResolver

class PublicResolver(DefaultResolver):
    async def resolve(self, host, port=0, family=0):
        records = await super().resolve(host, port, family)
        for record in records:
            address = ipaddress.ip_address(record["host"])
            if not address.is_global:
                raise CrawlerValidationError("Destination is not public")
        return records

def validate_target(url):
    parsed = urlparse(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
        or parsed.username or parsed.password
        or parsed.port not in {None, 80, 443}):
        raise CrawlerValidationError("Invalid destination")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return  # DNS results are checked by PublicResolver.
    if not address.is_global:
        raise CrawlerValidationError("Destination is not public")

validate_target(url)
connector = aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False)
async with aiohttp.ClientSession(connector=connector, trust_env=False,
        timeout=aiohttp.ClientTimeout(total=30)) as session:
    async with session.get(url, allow_redirects=False) as response:
        if 300 <= response.status < 400:
            raise CrawlerValidationError("Redirects are disabled")
        response.raise_for_status()
        body = bytearray()
        async for block in response.content.iter_chunked(65536):
            body.extend(block)
            if len(body) > 2 * 1024 * 1024:
                raise CrawlerValidationError("Response too large")
        html = body.decode(response.charset or "utf-8", errors="replace")
```

**[Verification]:** The extracted validator accepts http://[::ffff:127.0.0.1]/, http://[fd00::1]/, http://127.1/, and http://localhost./ in offline probes; no internal URLs were fetched. Before enabling website routes test redirect, DNS rebinding and browser subresource cases in an isolated network. The snippet protects the aiohttp path only: disable Crawl4AI until its entire browser runs behind an egress policy blocking non-public destinations.

The layered DNS, redirect and network restrictions are supported by [OWASP SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).

## A13 — Saved AI settings and request generation options are ignored

- **[Severity]:** Medium
- **[Component]:** Backend
- **[File/Location]:** [backend/app/services/chat_service.py:66](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/chat_service.py:66), [backend/app/rag/pipelines/rag_pipeline.py:76](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/rag/pipelines/rag_pipeline.py:76), [backend/app/rag/pipelines/rag_pipeline.py:418](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/rag/pipelines/rag_pipeline.py:418), [backend/app/services/embedding_helper.py:36](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/embedding_helper.py:36), [backend/app/services/settings_service.py:43](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/settings_service.py:43)
- **Evidence:** Static trace across settings, chat and embedding layers.

**[The Problem]:** The UI persists provider/model/temperature/retrieval settings, but ChatService constructs a default Groq pipeline without loading them. max_tokens and temperature are written into metadata and never used at generation. Embedding generation hardcodes MiniLM despite recording/logging the caller's model_name, so stored provenance is false. top_k is also ignored during retrieval (A15). This can send work to an unintended provider and defeats cost/behavior controls.

**[Code Fix] — flawed code:**

```text
self.rag_pipeline = RAGPipeline()
response = self.llm.invoke(lc_messages)
model_key = "all-minilm-l6-v2"
logger.info(f"Generating {len(texts)} embeddings with model '{model_name}'")
```

**Corrected implementation at the indicated integration points:**

```text
# Load persisted settings in the chat dependency.
saved = await SettingsService(db).get_settings(current_user.id)
# Until other providers are actually wired, fail explicitly.
if saved.provider != "groq":
    raise HTTPException(422, "Only Groq is currently supported for chat")
pipeline = RAGPipeline(llm_model=saved.model_name,
    temperature=saved.temperature, max_tokens=saved.max_tokens)
return ChatService(db=db, user_id=current_user.id, rag_pipeline=pipeline)

# In generation, honor validated per-request overrides without mutating
# shared provider objects.
options = state.get("metadata", {})
kwargs = {key: options[key] for key in ("temperature", "max_tokens")
          if options.get(key) is not None}
response = self.llm.invoke(lc_messages, **kwargs)

# Constructor must preserve 0.0:
temperature = rag_config.temperature if temperature is None else temperature

# For the currently single-model embedding implementation:
ACTUAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
if model_name != ACTUAL_MODEL:
    raise ValueError("Unsupported embedding model")
if dimensions not in {None, 384}:
    raise ValueError("Unsupported embedding dimensions")
# Update API/schema/UI defaults and persisted model_name to ACTUAL_MODEL.
```

**[Verification]:** Mock the provider and inspect the model, temperature=0, max_tokens, and configured provider for a request. Unsupported choices must produce 422 before billable work. Inspect vector dimension and persisted model_name. For full provider support implement an allowlisted provider factory and reindex when changing embedding space; do not silently mix dimensions/models.

## A14 — Conversation history is stored and fetched but discarded before the LLM

- **[Severity]:** Medium
- **[Component]:** Backend
- **[File/Location]:** [backend/app/services/chat_service.py:118](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/chat_service.py:118), [backend/app/services/chat_service.py:378](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/chat_service.py:378), [backend/app/rag/pipelines/rag_pipeline.py:337](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/rag/pipelines/rag_pipeline.py:337), [backend/app/rag/pipelines/rag_pipeline.py:403](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/rag/pipelines/rag_pipeline.py:403)
- **Evidence:** Reproduced with a stub graph; no LLM call.

**[The Problem]:** _run_rag_pipeline accepts history but never places it in graph state. Prompt creation uses only the current question and retrieved documents, and conversion supports only system/user roles. Follow-up questions cannot use previous conversation turns despite the database/context work.

**[Code Fix] — flawed code:**

```text
state = {"question": message, "metadata": {...}}
messages = self.prompt_builder.build_rag_messages(
    question=question, context_documents=context_docs,
    include_metadata=True, include_scores=False)
```

**Corrected implementation at the indicated integration points:**

```text
# Add history: List[Dict[str, str]] to RAGState, then include:
# Preserve the existing question and authorization metadata unchanged.
state["history"] = history

# After constructing the existing current-question RAG messages:
history = [
    {"role": msg["role"], "content": msg["content"]}
    for msg in state.get("history", [])
    if msg["role"] in {"user", "assistant"}
]
messages = [messages[0], *history, messages[-1]]

# Preserve assistant turns when converting to LangChain messages:
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
constructors = {"system": SystemMessage, "user": HumanMessage,
                "assistant": AIMessage}
lc_messages = [constructors[msg["role"]](content=msg["content"])
               for msg in messages if msg["role"] in constructors]
```

**[Verification]:** The probe passes a canary history message and confirms it never reaches graph input. Add an assertion that the final provider call includes the canary and assistant role in order. Enforce a tokenizer-based budget before adding history; current missing token counts must not be counted as zero. A conversation containing 'My project is Atlas' should answer 'What is my project?' from history.

## A15 — Global top-k retrieval can starve a tenant's own documents

- **[Severity]:** Medium
- **[Component]:** Backend
- **[File/Location]:** [backend/app/rag/pipelines/rag_pipeline.py:141](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/rag/pipelines/rag_pipeline.py:141), [backend/app/rag/pipelines/rag_pipeline.py:206](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/rag/pipelines/rag_pipeline.py:206)
- **Evidence:** Reproduced algorithm with stub retriever.

**[The Problem]:** The pipeline retrieves ten nearest chunks across all users and only then filters to authorized source IDs. Ten other-user results can crowd out a user's valid eleventh result. The post-filter prevents those returned chunks from entering current chat context, so this is a relevance/availability bug, not a demonstrated cross-user data leak. Requested top_k does not control retrieval.

**[Code Fix] — flawed code:**

```text
retrieved_docs = self.retriever.retrieve(question, top_k=10)
retrieved_docs = [doc for doc in retrieved_docs
                  if self._is_authorized_source(doc[2], authorized_source_ids)]
```

**Corrected implementation at the indicated integration points:**

```text
authorized = state["metadata"]["authorized_source_ids"]
top_k = state["metadata"].get("top_k") or 5
clauses = [
    {field: {"$in": ids}}
    for kind, field in (
        ("document", "document_id"), ("website", "website_id"),
        ("youtube", "youtube_source_id"))
    if (ids := authorized.get(kind))
]
if not clauses:
    retrieved_docs = []
else:
    source_filter = clauses[0] if len(clauses) == 1 else {"$or": clauses}
    retrieved_docs = self.retriever.retrieve(
        question, top_k=top_k, filter_dict=source_filter)
    # Retain the independent database-derived authorization check.
    retrieved_docs = [
        doc for doc in retrieved_docs
        if self._is_authorized_source(doc[2], authorized)
    ]
```

**[Verification]:** Seed ten very relevant foreign chunks and one slightly less relevant owned chunk; the owner's query must return the owned chunk and no foreign chunks. The probe confirms current retrieval has no filter and drops all ten foreign hits. Normalize/backfill legacy source identity metadata before this change; all new ingestion paths already have specific source IDs.

## A16 — Exception handler is registered for the wrong ValidationError class

- **[Severity]:** Medium
- **[Component]:** API
- **[File/Location]:** [backend/app/core/exceptions.py:184](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/core/exceptions.py:184), [frontend/src/services/api.js:85](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/services/api.js:85)
- **Evidence:** Handler failure reproduced with TestClient.

**[The Problem]:** The Pydantic handler is decorated for the application's own ValidationError rather than PydanticValidationError. It calls .errors() on an AppException that lacks the method, changing intended 422 responses into 500s. Actual Pydantic errors raised inside a route miss the intended handler. Separately, getApiError ignores the backend's error.message/error.details.errors envelope, losing useful errors in forms.

**[Code Fix] — flawed code:**

```text
@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request, exc):
    for error in exc.errors():
        ...

return detail || error.response?.data?.message || error.message
```

**Corrected implementation at the indicated integration points:**

```text
# Keep AppException handling for application validation errors.
@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(request, exc):
    errors = [{"field": ".".join(map(str, item["loc"])),
               "message": item["msg"], "type": item["type"]}
              for item in exc.errors()]
    return JSONResponse(status_code=422, content={
        "error": {"type": "ValidationError",
                  "message": "Data validation failed",
                  "details": {"errors": errors}}})

// Frontend contract:
export function getApiError(error, fallback = 'Request failed') {
  const body = error.response?.data
  if (Array.isArray(body?.error?.details?.errors))
    return body.error.details.errors.map(item => item.message).join(', ')
  if (typeof body?.error?.message === 'string') return body.error.message
  if (Array.isArray(body?.detail))
    return body.detail.map(item => item.msg).join(', ')
  if (typeof body?.detail === 'string') return body.detail
  return error.code === 'ECONNABORTED'
    ? 'The request timed out. Please try again.'
    : fallback
}
```

**[Verification]:** The isolated FastAPI probe raises the application's ValidationError and receives 500. Expect 422 afterward. Test duplicate signup, invalid email, invalid chunk config and database errors through the browser; each should render a useful string without exposing internals.

## A17 — Raw internal errors reach API responses and saved chat messages

- **[Severity]:** Medium
- **[Component]:** Security
- **[File/Location]:** [backend/app/services/chat_service.py:181](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/chat_service.py:181), [backend/app/services/chat_service.py:311](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/chat_service.py:311), [backend/app/api/documents.py:177](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/documents.py:177), [backend/app/api/youtube.py:86](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/youtube.py:86), [backend/app/core/exceptions.py:236](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/core/exceptions.py:236)
- **Evidence:** Static trace; no real secret was read or disclosed.

**[The Problem]:** Chat embeds str(e) in persisted assistant messages and stream error events; ingestion exposes raw exception text; integrity errors expose exc.orig regardless of debug. Provider URLs, filesystem paths, schema/constraint names and submitted values can leak. Chat additionally returns HTTP 200 for unexpected failures, making clients record failures as successful answers.

**[Code Fix] — flawed code:**

```text
error_content = f"An error occurred while processing your request: {str(e)}"
yield StreamChunk(type="error", error=str(e))
"details": {"constraint": str(exc.orig) if exc.orig else "unknown"}
```

**Corrected implementation at the indicated integration points:**

```text
# Non-streaming service failure: let centralized handler return a failure.
except Exception as exc:
    logger.exception("Chat generation failed")
    raise AppException("Chat generation failed", status_code=502) from exc

# Stream already began: use a public error, not exception text.
except Exception:
    logger.exception("Chat stream failed")
    yield StreamChunk(type="error", error="Chat generation failed")

# Constraint response:
return JSONResponse(status_code=409, content={
    "error": {"type": "ConflictError",
              "message": "The requested change conflicts with existing data",
              "details": {}, "path": request.url.path}
})
# Apply the same public-message policy to document/YouTube failures.
# Persist internal diagnostics separately with restricted access and redaction.
```

**[Verification]:** Mock a provider/database failure whose message contains AUDIT_SECRET_CANARY. Assert the canary appears in neither HTTP/SSE bodies nor persisted assistant messages. Expect 502/503 for non-streaming dependency failures and a structured error event for streams. Verify debug cannot be enabled in production configuration.

## A18 — Chunk configuration permits zero/negative progress and arbitrary strategies

- **[Severity]:** Medium
- **[Component]:** API
- **[File/Location]:** [backend/app/schemas/document.py:214](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/schemas/document.py:214), [backend/app/services/document.py:478](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/document.py:478), [backend/app/api/documents.py:93](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/documents.py:93)
- **Evidence:** Reproduced schema acceptance and chunker failure.

**[The Problem]:** chunk_overlap is not constrained relative to chunk_size. The accepted values size=100, overlap=100, strategy=fixed cause range(..., step=0) to fail; greater overlap can produce zero chunks and potentially a ready empty document. Arbitrary strategy strings silently select the fixed branch. A frontend bypass is sufficient because these are server-accepted query parameters.

**[Code Fix] — flawed code:**

```text
strategy: str = Field(default="recursive")
for i in range(0, len(words), chunk_size_words - overlap_words):
```

**Corrected implementation at the indicated integration points:**

```text
from typing import Literal
from pydantic import model_validator, ValidationError as PydanticValidationError

class ChunkingConfig(BaseModel):
    chunk_size: int = Field(default=1000, ge=100, le=10000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    strategy: Literal["recursive", "semantic", "fixed"] = "recursive"

    @model_validator(mode="after")
    def valid_overlap(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return self

# In both upload and reprocess, construct config BEFORE writing/processing,
# and convert construction errors into request validation errors:
try:
    config = ProcessingConfig(chunking={
        "chunk_size": chunk_size, "chunk_overlap": chunk_overlap,
        "strategy": chunking_strategy})
except PydanticValidationError as exc:
    raise HTTPException(422, "Invalid chunking configuration") from exc
```

**[Verification]:** Offline probe currently raises 'range() arg 3 must not be zero'. In disposable API tests submit ?chunk_size=100&chunk_overlap=100&chunking_strategy=fixed and an unknown strategy; both must return 422 before writing a file. Test boundary 100/99 and empty extracted text.

## A19 — Embedding failure handler raises UnboundLocalError and masks the cause

- **[Severity]:** Medium
- **[Component]:** Backend
- **[File/Location]:** [backend/app/services/embedding_helper.py:66](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/embedding_helper.py:66)
- **Evidence:** Reproduced with mocked embedding service.

**[The Problem]:** The raise statement is outside the except block. Python clears the exception variable e when leaving that block, so a provider failure becomes UnboundLocalError instead of the intended RuntimeError. This hides actionable diagnostics and contaminates the public error path.

**[Code Fix] — flawed code:**

```text
except Exception as e:
    logger.error(f"CRITICAL: Failed to generate embeddings: {e}", exc_info=True)
raise RuntimeError(f"Embedding generation failed: {e}") from e
```

**Corrected implementation at the indicated integration points:**

```text
except Exception as exc:
    logger.exception("Embedding generation failed")
    raise RuntimeError("Embedding generation failed") from exc
```

**[Verification]:** The probe injects RuntimeError into service.embed_texts and receives UnboundLocalError. After fixing indentation assert the raised exception is RuntimeError, its message is public-safe, and __cause__ is the original provider error.

## A20 — Chat navigation and overlapping responses restore the wrong conversation

- **[Severity]:** Medium
- **[Component]:** Frontend
- **[File/Location]:** [frontend/src/pages/readers/ChatPage.jsx:27](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/pages/readers/ChatPage.jsx:27), [frontend/src/pages/readers/ChatPage.jsx:59](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/pages/readers/ChatPage.jsx:59), [frontend/src/pages/readers/ChatPage.jsx:123](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/pages/readers/ChatPage.jsx:123)
- **Evidence:** Static asynchronous flow analysis; browser race not executed.

**[The Problem]:** sessionId is initialized from the URL once and not synchronized when the search parameter changes. The history fetch has no cancellation/version guard. Sending in a new session sets sessionId and immediately triggers a history reload that can replace locally appended messages. New Chat clears UI but does not invalidate an in-flight send, whose completion can reopen the previous conversation. Empty fetched histories also leave previous messages because setMessages only runs for nonempty results.

**[Code Fix] — flawed code:**

```text
const [sessionId, setSessionId] = useState(() => searchParams.get('session'))
const session = await chatApi.getSession(sessionId)
if (session?.messages?.length > 0) setMessages(restoredMessages)
setSessionId(response.session_id)
```

**Corrected implementation at the indicated integration points:**

```text
// Distinguish URL-selected history from a session created by sending.
const routeSession = searchParams.get('session')
const sessionRef = useRef(routeSession)
const requestEpoch = useRef(0)
const sending = useRef(false)

useEffect(() => {
  const epoch = ++requestEpoch.current
  const controller = new AbortController()
  sessionRef.current = routeSession
  setMessages([])
  if (routeSession) {
    chatApi.getSession(routeSession, { signal: controller.signal })
      .then(data => {
        if (epoch === requestEpoch.current)
          setMessages(data.messages || [])
      })
      .catch(error => {
        if (!controller.signal.aborted)
          toast.error(getApiError(error))
      })
  }
  return () => { requestEpoch.current++; controller.abort() }
}, [routeSession])

// Service method accepts cancellation:
async function getSession(id, { signal } = {}) {
  const { data } = await api.get(`/chat/sessions/${id}`, { signal })
  return data
}

// At send start (keep the existing rendering/state updates):
if (sending.current) return
sending.current = true
const epoch = requestEpoch.current
try {
  const response = await chatApi.sendMessage({
    message: text, session_id: sessionRef.current, include_sources: true
  })
  if (epoch !== requestEpoch.current) return
  sessionRef.current = response.session_id
  setMessages(prev => [...prev, response.message])
} finally {
  if (epoch === requestEpoch.current) {
    sending.current = false
    setIsStreaming(false)
  }
}
// New Chat increments requestEpoch and clears sessionRef/messages.
// Invalidate or abort its pending send and reset visible loading state too.
```

**[Verification]:** Throttle GET/POST requests, open A then B, navigate to an empty session, click New Chat while a response is pending, and start a fresh chat. Late A results must never replace B/new chat. Server mutations require idempotency keys if an aborted POST can be retried; cancelling the browser request alone does not undo a persisted message.

## A21 — Password recovery always claims success but has no backend

- **[Severity]:** Medium
- **[Component]:** Frontend
- **[File/Location]:** [frontend/src/pages/auth/ForgotPasswordPage.jsx:27](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/pages/auth/ForgotPasswordPage.jsx:27), [frontend/src/pages/auth/ResetPasswordPage.jsx:44](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/pages/auth/ResetPasswordPage.jsx:44), [backend/app/api/auth.py:1](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/auth.py:1)
- **Evidence:** Missing routes confirmed from app.openapi().

**[The Problem]:** The UI posts to password-reset routes that do not exist. ForgotPassword catches every failure—including 404 and network failure—and announces that email was sent. ResetPassword tries to validate a token by posting it to the nonexistent confirmation endpoint without a new password. Users cannot recover their accounts. This is broken recovery, not a demonstrated reset-token takeover.

**[Code Fix] — flawed code:**

```text
await api.post('/auth/password-reset/', { email: data.email })
catch {
  setSuccess(true)
  toast.success('Reset link sent!')
}
```

**Corrected implementation at the indicated integration points:**

```text
// Safe release fix until a real recovery workflow exists:
// replace both recovery pages with an explicit unavailable state and
// remove the 'Forgot password?' action from LoginPage.
export default function RecoveryUnavailable() {
  return (
    <section aria-labelledby="recovery-title">
      <h1 id="recovery-title">Password recovery is unavailable</h1>
      <p>No reset email has been sent.</p>
      <Link to="/login">Return to sign in</Link>
    </section>
  )
}

// Once the backend exists, only a successful request sets success:
try {
  await api.post('/auth/password-reset', { email: data.email })
  setSuccess(true)
} catch (error) {
  setSuccess(false)
  setError(getApiError(error, 'Unable to request password recovery'))
}
```

**[Verification]:** OpenAPI has no reset route; verify both frontend calls return 404 on a local instance. The release fix must stop claiming email delivery. Full recovery implementation needs random single-use token hashes, short expiry, atomic consumption with password update and session revocation, queued email, uniform responses for unknown accounts, rate limits, and separate non-consuming token validation. No email workflow was tested.

## A22 — Unavailable website and mock search/dashboard features are exposed

- **[Severity]:** Medium
- **[Component]:** Frontend
- **[File/Location]:** [backend/app/api/routes.py:13](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/routes.py:13), [frontend/src/routes/index.jsx:49](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/routes/index.jsx:49), [frontend/src/services/website.js:1](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/services/website.js:1), [frontend/src/pages/dashboard/SearchPage.jsx:8](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/pages/dashboard/SearchPage.jsx:8), [frontend/src/pages/dashboard/ChatsPage.jsx:10](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/pages/dashboard/ChatsPage.jsx:10)
- **Evidence:** Website contract confirmed at runtime; demo/profile flows inspected statically.

**[The Problem]:** The website UI remains enabled while its router is commented out, guaranteeing 404s. Global Search filters hardcoded sample records, has a submit form without preventDefault, and result clicks do nothing. Chats, team and workspace pages also contain demonstration records rather than real account data. These are product capability gaps, not evidence of cross-user data leakage. The profile page explicitly labels itself a mock; it is excluded from this finding.

**[Code Fix] — flawed code:**

```text
# router.include_router(website_router)
const [results] = useState(mockResults)
<form className="flex gap-4">
<Card onClick={() => {}}> ... </Card>
```

**Corrected implementation at the indicated integration points:**

```text
// Define capabilities from the implemented server contract, not UI presence.
export const capabilities = Object.freeze({
  websiteIngestion: false,
  globalSearch: false,
})

// Use in route/menu construction; hide actions as well as routes.
const websiteRoutes = capabilities.websiteIngestion ? [{
  path: '/website', element: <DashboardLayout />,
  children: [{ path: 'reader',
    lazy: lazyPage(() => import('../pages/readers/WebsiteReaderPage')) }]
}] : []

// For any retained demo search form, label it Demo and prevent reload:
<form onSubmit={event => event.preventDefault()} className="flex gap-4">
```

**[Verification]:** OpenAPI lacks /api/v1/website. Open Global Search with an empty real database: it still returns Q2 Financial Report.pdf. After gating, unavailable actions and sample metrics must not appear as real account data. Enable website only after A12 is resolved.

## A23 — History has N+1 counts, incorrect message-count sorting, and unbounded message loading

- **[Severity]:** Medium
- **[Component]:** Database
- **[File/Location]:** [backend/app/services/history_service.py:96](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/history_service.py:96), [backend/app/services/history_service.py:332](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/history_service.py:332), [backend/app/services/memory_service.py:76](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/memory_service.py:76), [backend/app/api/chat.py:189](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/api/chat.py:189)
- **Evidence:** Static SQL trace; no production query plan or load test.

**[The Problem]:** History performs one COUNT per returned session; message_count sorting actually sorts updated_at, yielding incorrect results. MemoryService.get_session eagerly loads every message even for ownership checks, and get_session_history queries all messages again. Long conversations therefore amplify latency/memory on ordinary chat/rename operations. Existing FK indexes are present, so this is not a blanket missing-index finding.

**[Code Fix] — flawed code:**

```text
for session in sessions:
    message_count = await self._get_message_count(session.id)
HistorySortField.message_count: ChatSession.updated_at
.options(selectinload(ChatSession.messages))
```

**Corrected implementation at the indicated integration points:**

```text
# Preaggregate counts once; use this in history list/search.
counts = (select(Message.chat_session_id,
                 func.count(Message.id).label("message_count"))
          .group_by(Message.chat_session_id).subquery())
count_column = func.coalesce(counts.c.message_count, 0)
stmt = (select(ChatSession, count_column.label("message_count"))
        .outerjoin(counts, counts.c.chat_session_id == ChatSession.id)
        .where(ChatSession.user_id == user_id))
# Apply existing status/search/date filters to stmt.
sort_column = (count_column if sort.sort_by == HistorySortField.message_count
               else self._get_sort_column(sort.sort_by))
stmt = stmt.order_by(
    sort_column.desc() if sort.sort_order == HistorySortOrder.desc
    else sort_column.asc(), ChatSession.id
).limit(pagination.page_size).offset(
    (pagination.page - 1) * pagination.page_size)
rows = (await self.db.execute(stmt)).all()
# Build responses from (session, message_count), without per-row COUNT.

# Ownership lookup: remove selectinload.
stmt = select(ChatSession).where(
    ChatSession.id == session_id, ChatSession.user_id == user_id)

# History endpoint: paginate messages, with a stable cursor in production.
messages = await memory_service.get_messages(session_id, limit=100)
```

**[Verification]:** Record SQL query count for 1 vs 100 history sessions; it should remain constant. Create a recently updated one-message session and an older twenty-message session; descending message_count must show the latter first. Seed a large conversation and assert ownership/rename queries do not fetch message bodies. Adapt clear_session_messages to a bulk DELETE after removing eager loading; expose pagination in the API/UI rather than silently truncating history.

## A24 — Soft-deleted chats remain active through the chat API

- **[Severity]:** Medium
- **[Component]:** Backend
- **[File/Location]:** [backend/app/services/memory_service.py:66](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/memory_service.py:66), [backend/app/services/memory_service.py:94](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/memory_service.py:94), [backend/app/services/history_service.py:222](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/history_service.py:222)
- **Evidence:** Static consistency check between both APIs.

**[The Problem]:** History DELETE sets deleted_at, but normal chat get/list/update paths do not filter it. A session moved to trash remains listed by /chat/sessions and accepts new messages by ID. The frontend uses both APIs, so trash behavior is inconsistent and users can unintentionally continue deleted conversations. Ownership checks still apply.

**[Code Fix] — flawed code:**

```text
select(ChatSession).where(
    ChatSession.id == session_id, ChatSession.user_id == user_id)
# list_sessions only filters user_id.
```

**Corrected implementation at the indicated integration points:**

```text
# Add this predicate to normal chat lookup/list/count/update paths.
stmt = select(ChatSession).where(
    ChatSession.id == session_id,
    ChatSession.user_id == user_id,
    ChatSession.deleted_at.is_(None),
)
# Keep explicit history trash/restore operations able to access deleted rows.
# For concurrent append/delete, lock the session row in a short transaction
# and recheck deleted_at before persisting each turn.
```

**[Verification]:** Soft-delete a session with DELETE /api/v1/history/{id}; GET /api/v1/chat/sessions must exclude it and POST /api/v1/chat with that session_id must return 404. Restore explicitly and verify it becomes accessible again. Test deletion racing with generation.

## A25 — Dependency declarations cannot reproduce the working environment; tests cannot collect

- **[Severity]:** High
- **[Component]:** Backend
- **[File/Location]:** [backend/requirements/base.txt:1](/Users/anshusonkar067/Desktop/RAGFUSION/backend/requirements/base.txt:1), [backend/requirements/embeddings.txt:1](/Users/anshusonkar067/Desktop/RAGFUSION/backend/requirements/embeddings.txt:1), [backend/Dockerfile:9](/Users/anshusonkar067/Desktop/RAGFUSION/backend/Dockerfile:9), [backend/tests/conftest.py:27](/Users/anshusonkar067/Desktop/RAGFUSION/backend/tests/conftest.py:27), [backend/app/services/youtube_service.py:322](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/youtube_service.py:322)
- **Evidence:** Observed collection failure and installed package metadata; upstream v1 API confirmed.

**[The Problem]:** The Dockerfile installs only base.txt, but imported langchain_groq/langchain_huggingface/langchain_community and the configured Argon2 backend are not explicitly declared there; embedding requirements are separate. YouTube code uses the >=1.0 fetch/list interface while base.txt requires <1.0. Installed Crawl4AI 0.3.74, which satisfies the broad declared range, lacks BrowserConfig/CrawlerRunConfig and blocks every test via conftest. The local environment contains newer packages outside declared ranges and no youtube-transcript-api distribution. Current test results cannot establish backend correctness.

**[Code Fix] — flawed code:**

```text
youtube-transcript-api>=0.6,<1.0
passlib[bcrypt]>=1.7,<2.0
# Dockerfile:
RUN pip install --no-cache-dir -r /tmp/requirements.txt
# conftest eagerly imports the disabled website service.
```

**Corrected implementation at the indicated integration points:**

```text
# Correct direct API requirements; resolve all remaining packages together
# and commit a tested lock. These are requirements inputs, not a verified lock.
youtube-transcript-api>=1.0,<2.0
passlib[argon2]>=1.7,<2.0
python-multipart
langchain-groq
langchain-huggingface
langchain-community
sentence-transformers
# Select a tested Crawl4AI version exposing BrowserConfig/CrawlerRunConfig.
# Align langchain/langgraph/chromadb/numpy constraints with that resolution.

# Test-only service setup should not import disabled integrations globally.
# Move ingestion_service import/patching into website-specific fixtures.

# Add a dependency-contract test in the clean, locked environment:
def test_runtime_dependency_contract():
    from crawl4ai import BrowserConfig, CrawlerRunConfig
    from youtube_transcript_api import YouTubeTranscriptApi
    from passlib.context import CryptContext
    assert callable(YouTubeTranscriptApi().fetch)
    assert callable(YouTubeTranscriptApi().list)
    context = CryptContext(schemes=["argon2"])
    assert context.verify("audit-password", context.hash("audit-password"))
    import main
    assert main.app.openapi()["paths"]
```

**[Verification]:** The selected backend suite stopped at conftest import with 'cannot import name BrowserConfig from crawl4ai'; no selected tests ran. In a fresh container install the committed lock, run pip check, import main, collect all tests, run migrations and service tests. Do not infer compatibility from the existing virtualenv. A resolved lock was not generated or installed during this audit.

The upstream [YouTube Transcript API v1.0 release notes](https://github.com/jdepoix/youtube-transcript-api/releases/tag/v1.0.0) document the switch to instance fetch/list methods.

## A26 — Chat attachments are never uploaded or sent to the backend

- **[Severity]:** Medium
- **[Component]:** Frontend
- **[File/Location]:** [frontend/src/pages/readers/ChatPage.jsx:101](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/pages/readers/ChatPage.jsx:101), [frontend/src/pages/readers/ChatPage.jsx:118](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/pages/readers/ChatPage.jsx:118), [frontend/src/components/chat/PromptInput.jsx:47](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/components/chat/PromptInput.jsx:47)
- **Evidence:** Static UI/request trace.

**[The Problem]:** The chat UI accepts/labels attachments but sends only message, session_id and include_sources. Files stay in browser state and never enter document ingestion or source selection. PromptInput also holds its own attachment list, so clearing/removing parent attachments does not reliably clear the local list. Users can believe a response used a file that the server never received.

**[Code Fix] — flawed code:**

```text
attachments: attachments.length > 0 ? [...attachments] : undefined
await chatApi.sendMessage({
  message: text, session_id: sessionId, include_sources: true
})
```

**Corrected implementation at the indicated integration points:**

```text
// Safe release fix until upload + ready-state + source-binding is complete:
// remove attachment props from ChatPage's PromptInput and remove its
// FilePreviewGrid/attachment state.
<PromptInput
  value={inputValue}
  onChange={setInputValue}
  onSubmit={handleSendMessage}
  disabled={isStreaming}
  isStreaming={isStreaming}
  placeholder="Ask about documents uploaded in Document Reader"
/>

// Full support needs one controlled attachment state, document upload,
// awaited ready status, and server-validated source IDs on ChatRequest.
// Do not imply that merely adding a local file provides LLM context.
```

**[Verification]:** Attach a canary text file and inspect outgoing network requests: no upload or file/source ID is sent. After gating, attachment controls should be absent. For full support, verify upload, failure handling, source ownership, status waiting and that removing an attachment removes it from the request's selected sources.

## A27 — Icon-only upload controls lack accessible names

- **[Severity]:** Low
- **[Component]:** Frontend
- **[File/Location]:** [frontend/src/components/upload/UploadCard.jsx:273](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/components/upload/UploadCard.jsx:273), [frontend/src/components/upload/UploadCard.jsx:309](/Users/anshusonkar067/Desktop/RAGFUSION/frontend/src/components/upload/UploadCard.jsx:309)
- **Evidence:** Static JSX inspection.

**[The Problem]:** Remove buttons in the upload list/grid contain only an X SVG and have no aria-label or text. A screen reader cannot distinguish their purpose or target file. This is a concrete accessibility blocker; contrast, keyboard focus and the rest of WCAG were not assessed by a full browser audit.

**[Code Fix] — flawed code:**

```text
<Button size="icon" variant="ghost"
        onClick={() => removeFile(fileObj.id)}>
  <X className="h-4 w-4" />
</Button>
```

**Corrected implementation at the indicated integration points:**

```text
<Button
  type="button"
  size="icon"
  variant="ghost"
  aria-label={`Remove ${fileObj.name}`}
  onClick={() => removeFile(fileObj.id)}
>
  <X aria-hidden="true" className="h-4 w-4" />
</Button>
// Apply the equivalent label to FilePreviewGrid's onRemove control.
```

**[Verification]:** Run an accessible-name audit (axe button-name rule) with an uploaded file, and navigate with keyboard/screen reader. Each remove button must announce both action and file. No automated browser accessibility test was executed.

## A28 — Concurrent settings requests can violate cross-field invariants

- **[Severity]:** Medium
- **[Component]:** Database
- **[File/Location]:** [backend/app/repositories/settings_repository.py:61](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/repositories/settings_repository.py:61), [backend/app/services/settings_service.py:82](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/services/settings_service.py:82), [backend/app/models/settings.py:94](/Users/anshusonkar067/Desktop/RAGFUSION/backend/app/models/settings.py:94)
- **Evidence:** Static TOCTOU analysis; concurrent PostgreSQL reproduction pending.

**[The Problem]:** get_or_create uses SELECT then INSERT: concurrent first reads can hit the unique user_id constraint instead of both returning settings. Updates validate size/overlap against independently read state without locking. From size=1000/overlap=200, concurrent size=300 and overlap=900 each validate locally but can commit size=300/overlap=900. No database CHECK prevents it.

**[Code Fix] — flawed code:**

```text
settings = await self.get_by_user_id(user_id)
if settings is None:
    settings = await self.create_default(user_id)

validation_data = {
    "chunk_size": settings.chunk_size,
    "chunk_overlap": settings.chunk_overlap,
}
validation_data.update(update_dict)
self._validate_updates(validation_data)
```

**Corrected implementation at the indicated integration points:**

```text
# PostgreSQL get-or-create, then row lock in the same transaction:
from sqlalchemy.dialects.postgresql import insert
await self.session.execute(
    insert(UserSettings).values(user_id=user_id)
    .on_conflict_do_nothing(index_elements=[UserSettings.user_id]))
settings = await self.session.scalar(
    select(UserSettings).where(UserSettings.user_id == user_id)
    .with_for_update().execution_options(populate_existing=True))
# Now merge, validate, update and commit while holding that short row lock.

# New migration (validate/repair any existing bad rows first):
op.create_check_constraint("ck_settings_chunk_overlap", "user_settings",
    "chunk_size >= 128 AND chunk_size <= 4096 "
    "AND chunk_overlap >= 0 AND chunk_overlap < chunk_size")
```

**[Verification]:** Use two independent PostgreSQL sessions synchronized after reading the original settings; submit size=300 and overlap=900 concurrently. Exactly one incompatible change should fail, and the persisted invariant must always hold. Concurrent first GET requests should both succeed. This requires real PostgreSQL isolation testing; it was not simulated with SQLite.

## Controls observed and areas not established

- The reviewed document, YouTube, chat, history and settings endpoints generally use authenticated-user ownership predicates. Current chat also checks database-authorized source IDs after retrieval. No active cross-user BOLA exploit was demonstrated; preserve these checks while fixing A15.
- SQLAlchemy expressions bind values in the reviewed request paths. No direct SQL injection or shell-command execution sink was found there. This does not cover unreviewed third-party parser vulnerabilities.
- The markdown renderer does not enable raw HTML, and no application dangerouslySetInnerHTML sink appeared in the targeted search. Token theft risk in A07 is conditional on script compromise; it is not a claim that XSS was exploited.
- Explicit CORS origins, API security headers and a production check against the default JWT secret exist. HSTS is conditional on production mode. Frontend-host CSP/HSTS cannot be established from API middleware; inspect the actual HTML host/proxy before release. No wildcard-with-credentials finding is asserted.
- Source/user foreign keys, cascade declarations, uniqueness constraints and several lookup indexes are present. The specific gaps are migration parity, embedding constraints and settings concurrency—not a general absence of database integrity.
- Async DB dependencies include commit/rollback and engine disposal. Unbounded/eager reads, synchronous work and separate external storage commits remain the concrete issues documented above.
- There is no payment/webhook implementation in the inspected active routes, so payment/webhook idempotency was not assessed. Search's current mock data means an un-debounced network search is not presently the relevant defect.

## Repeat verification

From the repository root:

```sh
ragfusion_env/bin/python audits/2026-10-04/verify_findings.py
```

The audit probe intentionally asserts current broken behavior to document reproduction. After applying fixes, convert those assertions to expected secure behavior and move suitable tests into the main suite. It is not a post-remediation regression suite as written.

From frontend: run `npm run build`, `npm run lint`, `npm run typecheck`. From backend, the attempted suite was:

```sh
../ragfusion_env/bin/python -m pytest tests/test_database.py tests/test_auth.py tests/test_history.py tests/test_settings.py tests/test_security.py tests/test_rate_limiter.py -q --disable-warnings --maxfail=8
```

It exited 4 during conftest collection. After A25, run that suite and broaden to all active tests in a disposable environment, plus real PostgreSQL migration/concurrency tests and browser checks listed above.
