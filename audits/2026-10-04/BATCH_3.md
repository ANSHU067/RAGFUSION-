# Batch 3 checkpoint — 5 October 2026

Branch: `audit-remediation`. Scope: A05, A06, A11, A12, and the explicitly
unreferenced crawler endpoint cleanup. Batches 4–6 have not started.

## Implemented

- **A05:** `RedisRateLimiter` uses one atomic Redis Lua script with Redis server
  time, a sorted-set sliding window, `INCR`, and `PEXPIRE`. Event and sequence
  keys are hashed and share a cluster hash slot. Auth, chat, ingestion, and API
  budgets are separate. `RateLimitMiddleware` is mounted by `create_app`, and
  health/OPTIONS bypass quota accounting. Redis errors fail closed with a
  sanitized 503; there is no silent in-memory production fallback. Client IP is
  `request.client.host` unless that peer belongs to configured
  `trusted_proxies`; malformed or untrusted forwarded chains are ignored.
- **A06:** `users.auth_version` is non-null with default zero in migration
  `20261005_0002`. Access and refresh JWTs carry integer `ver` and unique `jti`
  claims. Access checks and refresh compare the claim to the database. Refresh
  and logout use one conditional `UPDATE ... WHERE auth_version = ver`, so only
  one concurrent operation wins and the committed increment invalidates prior
  tokens. Logout is database-backed; it no longer only clears client state.
- **A11:** Compose persists upload and vector directories through
  `uploads_data` and `vectors_data`, with matching runtime variables. The image
  creates UID/GID 10001 `appuser`, owns storage directories, and runs as that
  user with proxy-header trust disabled. `.dockerignore` excludes secrets,
  databases, caches, data, tests, and audit artifacts.
- **A12:** The website router remains absent from `routes.py`. The crawler now
  uses `PublicResolver`, checks every resolved address with `is_global`, rejects
  literal private/mapped/metadata addresses and credentials, disables redirects,
  rejects compressed responses, enforces a 2 MiB body limit and bounded connect
  and read timeouts, and disables the Crawl4AI fallback. The optional crawler
  dependency remains in `requirements/crawling.txt` but is never imported by
  startup or the disabled router.
- **Cleanup:** removed unreferenced `backend/app/api/website.py`, the stale
  `EMBEDDING_FIX.patch`, and stale endpoint tests that asserted disabled website
  routes would execute. Static URL/chunking/extraction tests remain.

## Verification

- Required command: `ragfusion_env/bin/python -m pytest -q backend/tests/test_auth.py backend/tests/test_security.py backend/tests/test_rate_limiter.py` — **39 passed, 1 skipped**.
- Extended offline security/crawler suite: **98 passed, 5 skipped**. Skips are
  optional real Redis/PostgreSQL integration cases when service URLs are absent.
- Real Redis Lua/atomic quota test with two limiter instances: **1 passed**;
  seven requests admitted across 60 concurrent attempts, generated keys expired.
- Batch 2 local PostgreSQL was upgraded to `20261005_0002` and verified through
  the application engine. Existing role `docpro` remains `NOSUPERUSER`.
- `python -m compileall -q backend/app backend/tests`: passed.
- `git diff --check`: passed after the final test cleanup.

Run the full Batch 3 probe:

```bash
ragfusion_env/bin/python audits/2026-10-04/verify_findings.py --batch 3
```

For full distributed verification, set disposable service URLs:

```bash
export BATCH3_REDIS_URL='redis://127.0.0.1:56379/15'
export BATCH2_POSTGRES_URL='postgresql+asyncpg://<test-admin>@<socket-or-host>/<admin-db>'
ragfusion_env/bin/python -m pytest -q backend/tests/test_batch3_security.py backend/tests/test_rate_limiter.py
```

The PostgreSQL fixture creates and drops uniquely named test databases. The
Redis test deletes only keys under its generated `batch3-test:` prefix.

## Dead-code cleanup commands

The following exact commands describe the reviewed, already completed removals:

```bash
rm -- backend/app/api/website.py
rm -- EMBEDDING_FIX.patch
```

Do not remove `audits/2026-10-04/*`, `archive/`, or project reports: they are
review evidence and historical documentation. Do not remove frontend website
reader/API files in this batch; A22 in Batch 6 owns those user-facing links and
their replacement with real backend flows.

## Remaining limits

Docker is not installed on this workstation, so `docker compose config` and an
image build remain unverified. The required tests use the explicit in-memory
limiter only in test fixtures; production `create_app()` constructs Redis.
Batch 1’s clean dependency installation remains an existing limitation. No
Batch 4 changes were made: indexing failure readiness, event-loop offload,
settings wiring, prompt history, retrieval tenancy, and embedding exception
handling remain pending.

Recommended commit:

```bash
git add backend audits/2026-10-04/BATCH_3.md
git commit -m "fix(audit): complete batch 3 - sessions throttling and SSRF"
```

Stop here for review and confirmation before Batch 4.
