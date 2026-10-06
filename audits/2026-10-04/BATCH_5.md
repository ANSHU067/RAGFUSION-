# Batch 5 checkpoint

Branch: `audit-remediation`. No migration is required for this batch.

Implemented A16, A17, A23 and A24, plus transcript deadlines, shared local
embedding models and complete Chroma/PostHog telemetry opt-out.

## Source changes

- `backend/app/core/exceptions.py`: one handler for FastAPI request and Pydantic
  validation failures, separate application errors, safe 409/500 responses.
  Validation responses omit input, validator exception context and arbitrary
  validator messages. FastAPI debug traceback responses are disabled.
- `backend/app/services/chat_service.py`: provider failures produce a 502,
  timeouts a 504, and neither creates an assistant turn containing an error.
  SSE failures emit safe text. Database exceptions reach the central handler.
- `backend/app/services/history_service.py`: message counts are outer-joined
  before sorting and pagination. Listings execute two SQL statements regardless
  of page size; searches execute one. Zero-message sessions remain visible.
- `backend/app/services/memory_service.py`: active-session predicates on normal
  access; atomic active-session checks before message writes; locked metadata
  updates; bounded message pages; bulk message clearing without eager loading.
- `backend/app/api/chat.py`: explicit 404 for trashed sessions on normal and
  streaming routes; history supports `limit=1..100` and `offset>=0`, with total
  message count independent of the page size.
- Document, YouTube, history and settings routes: safe public messages; database
  errors are not converted to raw HTTP details. Document processing responses
  reload persisted state.
- `backend/app/services/youtube_service.py`: one 20-second deadline covers fetch,
  transcript listing and language fallback. Each HTTP request has connect/read
  timeouts and a redirect cap. Only language absence permits fallback. Two
  worker slots remain held until actual completion, including abandoned callers.
  Timed-out Python threads cannot be forcibly killed; socket timeouts bound
  normal network waits and the worker bound prevents unlimited accumulation.
- `backend/app/core/embedding_runtime.py`: a locked process-wide model cache
  shared by the LangChain adapter and the ingestion embedding provider. Successful
  initialization happens once per model/device per process. Chroma encoding
  normalization remains unchanged so existing collections remain compatible.
- `backend/main.py`: model warmup runs in a bounded worker thread on startup.
  A missing local cache is logged; authentication remains available and ingestion
  reports a safe failure until the cache is provisioned.
- `backend/app/core/telemetry.py`: Chroma's telemetry implementation never invokes
  PostHog, avoiding capture-signature crashes even when telemetry flags alone
  do not prevent the invocation.

## Local model provisioning

Runtime defaults to `DOCPRO_EMBEDDING_LOCAL_FILES_ONLY=true` and
`DOCPRO_EMBEDDING_WARMUP=true`. Provision MiniLM once as the same OS user that runs
the application, or use an accessible shared cache directory:

```bash
HF_HUB_ETAG_TIMEOUT=5 HF_HUB_DOWNLOAD_TIMEOUT=30 ragfusion_env/bin/python -c 'from sentence_transformers import SentenceTransformer; SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", cache_folder="backend/data/models")'
```

Set `DOCPRO_EMBEDDING_CACHE_DIR` to the absolute path of `backend/data/models` in
the runtime environment. In Docker, provision/copy that cache into the image or
mount it read-only and point the variable at the mounted path. The default Hugging
Face cache is used if this setting is omitted. This turn did not download models
or call live YouTube/Groq services.

`ANONYMIZE_TELEMETRY=False`, `CHROMA_TELEMETRY=False` and Chroma's native
`ANONYMIZED_TELEMETRY=False` are documented in `.env.example`. Application-created
Chroma clients also explicitly disable telemetry with the opt-out implementation.

## Verification

```bash
ragfusion_env/bin/python audits/2026-10-04/verify_findings.py --batch 5
ragfusion_env/bin/python -m pytest -q backend/tests/test_history.py backend/tests/test_chat.py backend/tests/test_security.py
ragfusion_env/bin/python -m pytest -q backend/tests
git diff --check
```

The positive Batch 5 verifier records results in `batch-5-verification.json`.
It includes behavioral tests for error leakage, history query count and ordering,
trash access, pagination, timeout responsiveness, concurrent model initialization
and actual Chroma writes without PostHog capture. External provider boundaries
are replaced by deterministic test doubles; no paid or live provider calls are
required by the verification suite.

## Cleanup

Removed the unreferenced Redis embedding-cache implementation. Its only remaining
references were archived reports, not runtime imports or tests. Equivalent command
(already applied):

```bash
rm -- backend/app/services/embedding_cache.py
```

Also removed the obsolete transcript timeout helper and the incorrectly registered
duplicate validation handler. Active security/cache utilities with tests were kept.
Pre-existing root report and frontend documentation deletions were not changed.

Recommended commit message after review and staging this batch's files:

```bash
git commit -m "fix(audit): complete batch 5 - safe errors history and ingestion stability"
```

Stop at this checkpoint; Batch 6 requires the user's confirmation.
