# Batch 1 checkpoint

Branch: `audit-remediation`. Audit baseline: `d5daa5dadc8af8ee29ad13e11cf5ef05a8ba95f9`.
Scope: A02 and A25 only. No Batch 2 changes or commits have been made.

## Changes

- `.gitignore`: exempt application library, model, and embedding source from
  broad generated-directory rules; remove duplicate ignore entries. Stage the
  eight existing source files without changing their implementation.
- `backend/requirements/base.txt`: declare Argon2, multipart, Groq, Hugging Face,
  and community integrations; use the YouTube v1 API; include embedding runtime
  dependencies. Keep the LangChain adapters within the 0.3 family used by the
  application's existing imports.
- `backend/requirements/embeddings.txt`: require NumPy 1.26 or later within 1.x
  and Transformers 4.x for the supported sentence-transformers 3.x providers.
- `backend/requirements/crawling.txt`: move the optional browser engine out of
  the default runtime. The website router remains disabled.
- `backend/Dockerfile`: copy all nested requirement files, install the complete
  runtime, run `pip check`, and install native libmagic/OpenMP runtime libraries.
  Non-root execution, persistence, and `.dockerignore` remain Batch 3 work.
- `backend/tests/conftest.py`: remove eager ingestion/crawler import; patch only
  already-loaded session factory aliases; restore overrides and dispose test
  engines in `finally`; match production commit/rollback behavior.
- `backend/app/services/crawler_service.py`: import Crawl4AI only inside the
  browser execution function, allowing URL utility tests to collect independently.
- Root/backend pytest configuration: consistent async fixture mode and loop scope.
- `verify_findings.py`: default to positive A02/A25 checks. Check source tracking,
  dependency declarations and installed versions, `pip check`, app startup,
  Argon2, YouTube instance methods, and collection with crawler imports blocked.
  Historical defect probes require `--baseline`; their results no longer
  overwrite the original audit evidence. Later findings await their batches.
- `backend/README.md`: document the supported backend installation and checks.

## Verification actually performed

Using the pre-existing `ragfusion_env` environment:

- `python -m pytest --collect-only -q`: **281 tests collected, no errors**.
- Targeted app, authentication, URL-validation, and URL-utility tests:
  **34 passed**. Dependency/application deprecation warnings remain.
- App startup and URL-helper import with a finder that rejects every Crawl4AI
  import: **passed**. Argon2 hash, correct-password verification, and rejection
  of an incorrect password: **passed**.
- `verify_findings.py --batch 1 --source-only`: **passed**; eight source files
  are staged and no longer ignored; required dependency declarations are present.
- `git diff --check`: **passed**.

## Outstanding verification

The existing environment is not a supported dependency installation: its
LangChain 0.3 package conflicts with installed LangChain Core/Text Splitters 1.x.
The full positive probe fails on installed `langchain-groq==1.1.3`, outside the
declared compatible 0.3 range. It must not be represented as passing.

A clean `.venv` was created, but dependency resolution from PyPI suffered repeated
DNS/read/download timeouts. An elevated retry made only partial progress and was
interrupted. Dependencies were not installed in `.venv`; the user's existing
environment was not modified. Fresh dependency resolution, the full positive
probe, and YouTube v1 runtime verification remain unverified. Docker is unavailable
on this host, so the container build has not been tested. The complete backend
suite has not been run; collection and targeted tests do not establish that all
28 findings are remediated or that the application is production-ready.

## Reproduce and finish verification

Run from the repository root:

```bash
ragfusion_env/bin/python -m pytest --collect-only -q
ragfusion_env/bin/python audits/2026-10-04/verify_findings.py --batch 1 --source-only
.venv/bin/python -m pip install -r backend/requirements/base.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest --collect-only -q
.venv/bin/python audits/2026-10-04/verify_findings.py --batch 1
.venv/bin/python -m pytest -q backend/tests/test_app.py backend/tests/test_auth.py backend/tests/test_website.py::TestURLValidation backend/tests/test_website.py::TestURLUtilities
docker build -t ragfusion-api:batch-1 backend
git diff --cached --check
git diff --cached
```

Recommended commit after review and remaining verification:

```bash
git commit -m "fix(audit): complete batch 1 - tooling and dependencies"
```

Proceed to Batch 2 only after user confirmation.
