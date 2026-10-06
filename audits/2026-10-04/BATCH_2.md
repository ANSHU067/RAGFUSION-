# Batch 2 checkpoint — 5 October 2026

Branch: `audit-remediation`. Scope: A01, A03, A04, A10, A28 and local database
bootstrap. Batch 3 has not started. No Git commits were created.

## Implemented

- **A01:** UUID-backed `uploads/{user_id}/{document_id}/content` keys. Client
  filenames remain database display metadata. `resolve_storage_key` rejects
  absolute paths, traversal, and symlink escapes. Upload, checksum/validation,
  processing, reprocessing, cleanup, and deletion resolve stored keys within
  the upload root. Failed uploads remove their uncommitted file. Existing safe
  relative keys remain readable. API ownership checks remain in place.
- **A03:** async URL conversion uses `render_as_string(hide_password=False)`.
  Regression tests preserve reserved characters in passwords across supported
  PostgreSQL driver conversions.
- **A04:** revision `20261005_0001`, following the existing merged migration head,
  adds nullable `chat_sessions.deleted_at` and its index.
- **A10:** ingestion locks the owning document row, validates chunk/vector
  cardinality, and atomically deletes/replaces its SQL embeddings. Metadata maps
  to `metadata_`; chunk indices are preserved. A unique document/chunk constraint
  blocks duplicate writes. The migration retains the newest existing duplicate
  SQL row and preserves other source types. An injected insert failure verifies
  rollback restores the previous chunks.
- **A28:** settings initialization uses dialect-specific `ON CONFLICT DO NOTHING`
  and locks the row for validation/update. Locked reads refresh cached ORM state.
  Strict duplicate creation uses a savepoint and preserves unrelated transaction
  work. Database CHECK enforces `0 <= chunk_overlap < chunk_size`. Invalid legacy
  settings stop migration before schema changes. Corrected the existing
  `delete_by_user_id` repository contract used by its tests.
- **Connection configuration:** stable `backend/.env` location; prefixed and
  standard database variables; localhost default. Alembic and API share the URL
  configuration, with synchronous test URL overrides still supported. Compose
  explicitly uses service hostnames and publishes PostgreSQL on loopback 55432.

## Local runtime error resolved

Read-only inspection confirmed the local PostgreSQL server had neither role
`docpro` nor database `docpro`. The existing backend configuration already selected
localhost:5432 but used a password different from the example in the request.

Created the role with that existing configured password and
`NOSUPERUSER NOCREATEDB NOCREATEROLE`, then created database `docpro` owned by it.
The `.env` file and password were preserved. Applied the migrations to this new
database. Verified through the application's actual async engine:

- connection succeeds;
- current user/database are both `docpro`;
- migration revision is `20261005_0001`;
- role is not a superuser;
- `chat_sessions.deleted_at` exists.

Exact example bootstrap commands for a fresh installation are in
`backend/README.md`; do not recreate the workstation's now-existing role/database.

## Verification

- Positive Batch 2 probe: **27 passed, 2 skipped** against migrated SQLite and a
  disposable PostgreSQL 17 cluster. The skips are SQLite versions of the two
  PostgreSQL-only lock tests; both PostgreSQL versions passed.
- Existing document, settings, database, and migration suites: **97 passed**.
- Full backend collection: **310 tests, no collection errors**.
- `git diff --check`: passed.

Tests cover traversal filenames, external symlink paths, tenant denial, unsafe
legacy keys, uncommitted-file cleanup, password preservation, row replacement,
rollback, uniqueness, CHECK constraints, simultaneous first-use settings,
stale settings snapshots, simultaneous document writes, fresh migrations,
upgrade/downgrade, legacy duplicate cleanup, and invalid-settings preflight.

PostgreSQL tests create/drop uniquely named databases. The disposable test server
is stopped after verification; it is separate from the persistent local docpro
database created for the application.

## Reproduce

From the repository root:

```bash
ragfusion_env/bin/python audits/2026-10-04/verify_findings.py --batch 2
ragfusion_env/bin/python -m pytest -q backend/tests/test_documents.py backend/tests/test_settings.py backend/tests/test_database.py backend/tests/test_migrations.py
ragfusion_env/bin/python -m pytest --collect-only -q
ragfusion_env/bin/python -m alembic -c backend/alembic.ini current
git diff --check
git diff
```

Set `BATCH2_POSTGRES_URL` to a disposable test server with database-creation
privileges to reproduce the PostgreSQL cases. Without it, the probe explicitly
reports those cases skipped.

## Limits and next checkpoint

Batch 1's staged changes remain separate in the index. Batch 2 changes are left
unstaged for review; they also modify files added/staged in Batch 1. Commit the
existing Batch 1 index separately before staging Batch 2 if separate commits are
desired. Do not use `git commit -a` to preserve that separation.

Recommended Batch 2 commit message:

```text
fix(audit): complete batch 2 - storage and database integrity
```

The prior dependency-installation conflicts and unavailable Docker build remain
unverified Batch 1 concerns. Chroma indexing failure/readiness semantics remain
Batch 4 work. This checkpoint does not claim the entire application is yet
production-ready. Wait for confirmation before Batch 3.
