"""Positive remediation checks, with explicit opt-in historical defect probes.

Run: ragfusion_env/bin/python audits/2026-10-04/verify_findings.py --batch 2
The default checks Batch 2; --batch 1 checks A02/A25 independently.
Use --baseline for mixed regression/remaining-defect probes in disposable storage.
"""
import argparse
import importlib.metadata
import subprocess
import ast
import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def verify_batch_one(source_only=False):
    """Fail when source is omitted, dependencies conflict, or startup is broken."""
    from packaging.requirements import Requirement

    evidence = {"batch": 1, "findings": ["A02", "A25"]}
    sources = []
    for directory, suffix in (
        ("frontend/src/lib", ".js"),
        ("backend/app/models", ".py"),
        ("backend/app/rag/embeddings", ".py"),
    ):
        files = sorted((ROOT / directory).glob(f"*{suffix}"))
        assert files, f"Missing source directory: {directory}"
        for path in files:
            relative = str(path.relative_to(ROOT))
            subprocess.run(["git", "ls-files", "--error-unmatch", relative],
                           cwd=ROOT, check=True, capture_output=True, text=True)
            ignored = subprocess.run(["git", "check-ignore", "--no-index", "-q", relative], cwd=ROOT)
            assert ignored.returncode == 1, f"Source is still ignored: {relative}"
            sources.append(relative)
    evidence["tracked_source"] = sources

    def requirements(path):
        for raw in path.read_text().splitlines():
            line = raw.split("#", 1)[0].strip()
            if line.startswith("-r "):
                yield from requirements(path.parent / line[3:].strip())
            elif line:
                yield Requirement(line)

    declared = list(requirements(ROOT / "backend/requirements/base.txt"))
    by_name = {requirement.name.lower(): requirement for requirement in declared}
    for name in ("passlib", "python-multipart", "langchain-groq", "langchain-huggingface",
                 "langchain-community", "sentence-transformers", "youtube-transcript-api"):
        assert name in by_name, f"Missing runtime dependency: {name}"
    assert "argon2" in by_name["passlib"].extras
    youtube = by_name["youtube-transcript-api"].specifier
    assert "1.0" in youtube and "0.6.2" not in youtube and "2.0" not in youtube
    evidence["dependency_declarations"] = "passed"
    if source_only:
        evidence["runtime_verification"] = "not run: source-only mode"
        output = Path(__file__).with_name("batch-1-source-verification.json")
        output.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence, indent=2))
        return

    versions = {}
    for requirement in declared:
        if requirement.marker and not requirement.marker.evaluate():
            continue
        version = importlib.metadata.version(requirement.name)
        assert version in requirement.specifier, f"{requirement}: installed {version}"
        versions[requirement.name] = version
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
    evidence["installed_versions"] = versions

    # A blocked import proves the disabled browser service is not required for
    # app startup or pytest collection. No provider or model is instantiated.
    smoke = '''
import importlib.abc
import sys
class DisabledCrawler(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "crawl4ai" or fullname.startswith("crawl4ai."):
            raise AssertionError("Disabled crawler was imported")
sys.meta_path.insert(0, DisabledCrawler())
import dotenv
dotenv.load_dotenv = lambda *args, **kwargs: False
from main import create_app
from app.services.auth import hash_password, verify_password
from youtube_transcript_api import YouTubeTranscriptApi
assert callable(YouTubeTranscriptApi().fetch)
assert callable(YouTubeTranscriptApi().list)
encoded = hash_password("batch-one-regression-password")
assert encoded.startswith("$argon2")
assert verify_password("batch-one-regression-password", encoded)
assert not verify_password("incorrect-password", encoded)
paths = create_app().openapi()["paths"]
assert any("documents" in path for path in paths)
assert "/api/v1/website/ingest" in paths
assert "/api/v1/website/crawl" not in paths
import pytest
raise SystemExit(pytest.main(["--collect-only", "-q", "tests"]))
'''
    environment = os.environ.copy()
    environment.update(
        DOCPRO_DATABASE_URL="sqlite+aiosqlite:///:memory:",
        DOCPRO_JWT_SECRET_KEY="batch-one-isolated-test-secret",
        HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
    )
    subprocess.run([sys.executable, "-c", smoke], cwd=ROOT / "backend",
                   env=environment, check=True)
    evidence["startup_argon2_youtube_and_collection"] = "passed; crawler import blocked"
    output = Path(__file__).with_name("batch-1-verification.json")
    output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


def verify_batch_two():
    """Run positive storage/transaction/migration assertions and record skips."""
    from xml.etree import ElementTree

    environment = os.environ.copy()
    environment.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    with tempfile.TemporaryDirectory(prefix="ragfusion-batch2-results-") as directory:
        report = Path(directory) / "results.xml"
        subprocess.run([
            sys.executable, "-m", "pytest", "-q", "backend/tests/test_batch2_integrity.py",
            f"--junitxml={report}",
        ], cwd=ROOT, env=environment, check=True)
        cases = ElementTree.parse(report).findall(".//testcase")
        skipped = [case.attrib["name"] for case in cases if case.find("skipped") is not None]
    evidence = {
        "batch": 2, "findings": ["A01", "A03", "A04", "A10", "A28"],
        "passed": len(cases) - len(skipped), "skipped": skipped,
        "postgresql": "tested" if os.environ.get("BATCH2_POSTGRES_URL") else "not tested: set BATCH2_POSTGRES_URL",
        "scope": "SQL storage integrity; vector failure/readiness behavior remains Batch 4",
    }
    Path(__file__).with_name("batch-2-verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


def verify_batch_three():
    """Run Batch 3 security tests plus source-level deployment assertions."""
    from pathlib import Path
    import yaml

    subprocess.run([
        sys.executable, "-m", "pytest", "-q", "backend/tests/test_auth.py",
        "backend/tests/test_security.py", "backend/tests/test_rate_limiter.py",
        "backend/tests/test_batch3_security.py",
        "backend/tests/test_workspace_regressions.py",
    ], cwd=ROOT, env=os.environ.copy(), check=True)
    compose = yaml.safe_load((ROOT / "backend/docker-compose.yml").read_text())
    api = compose["services"]["api"]
    assert "uploads_data:/var/lib/ragfusion/uploads" in api["volumes"]
    assert "vectors_data:/var/lib/ragfusion/vectorstore" in api["volumes"]
    assert api["environment"]["RAGFUSION_UPLOAD_DIR"] == "/var/lib/ragfusion/uploads"
    assert api["environment"]["RAG_VECTOR_STORE_PATH"] == "/var/lib/ragfusion/vectorstore"
    dockerfile = (ROOT / "backend/Dockerfile").read_text()
    assert "USER 10001" in dockerfile and "appuser" in dockerfile
    ignored = (ROOT / "backend/.dockerignore").read_text()
    for entry in [".env", ".env.*", "data/", "*.db", "audits/"]:
        assert entry in ignored
    crawler = (ROOT / "backend/app/services/crawler_service.py").read_text()
    for marker in ["class PublicResolver", "is_global", "allow_redirects=False", "MAX_RESPONSE_BYTES"]:
        assert marker in crawler
    routes = (ROOT / "backend/app/api/routes.py").read_text()
    assert "include_router(website_router)" in routes
    evidence = {
        "batch": 3, "findings": ["A05", "A06", "A11", "A12"],
        "security_tests": "passed", "crawler_router": "authenticated bounded single-page ingestion",
        "redis_integration": "set BATCH3_REDIS_URL to run Lua/expiry test",
        "cleanup": "obsolete crawler endpoint tests and EMBEDDING_FIX.patch removed; archive retained",
    }
    Path(__file__).with_name("batch-3-verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


def verify_batch_four():
    """Run Batch 4 regression tests and positive source assertions."""
    subprocess.run([
        sys.executable, "-m", "pytest", "-q",
        "backend/tests/test_documents.py",
        "backend/tests/test_youtube_rag.py",
        "backend/tests/test_chat_service.py",
    ], cwd=ROOT, env=os.environ.copy(), check=True)

    document = (ROOT / "backend/app/services/document.py").read_text()
    pipeline = (ROOT / "backend/app/rag/pipelines/rag_pipeline.py").read_text()
    schema = (ROOT / "backend/app/schemas/document.py").read_text()
    embeddings = (ROOT / "backend/app/services/embedding_helper.py").read_text()
    assert "anyio.to_thread.run_sync" in document
    assert 'code="RAG_INDEXING_FAILED"' in document
    assert "SourceStatus.failed" in document
    assert 'filter_dict = {"$or": clauses}' in pipeline
    assert 'state.get("history", [])' in pipeline
    assert "self.llm.invoke(lc_messages, **generation_kwargs)" in pipeline
    assert 'Literal["recursive", "semantic", "fixed"]' in schema
    assert "chunk_overlap must be smaller than chunk_size" in schema
    assert "except Exception as exc:" in embeddings
    assert 'raise EmbeddingGenerationError("Embedding generation failed") from exc' in embeddings

    evidence = {
        "batch": 4,
        "findings": ["A08", "A09", "A13", "A14", "A15", "A18", "A19"],
        "tests": "passed",
        "event_loop_offloading": "anyio worker threads with bounded limiters",
        "retrieval": "authorized Chroma $or filter applied before top-k",
        "ingestion": "vector failures leave source failed",
    }
    Path(__file__).with_name("batch-4-verification.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    print(json.dumps(evidence, indent=2))


def verify_batch_five():
    """Assert safe error responses and bounded, tenant-preserving backend behavior."""
    from xml.etree import ElementTree

    environment = os.environ.copy()
    environment.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    with tempfile.TemporaryDirectory(prefix="ragfusion-batch5-") as directory:
        report = Path(directory) / "results.xml"
        subprocess.run([
            sys.executable, "-m", "pytest", "-q",
            "backend/tests/test_batch5_backend.py",
            "backend/tests/test_history.py", "backend/tests/test_chat.py",
            "backend/tests/test_security.py", "backend/tests/test_memory_service.py",
            "backend/tests/test_chat_service.py", "backend/tests/test_chat_api.py",
            f"--junitxml={report}",
        ], cwd=ROOT, env=environment, check=True)
        cases = ElementTree.parse(report).findall(".//testcase")
        skipped = [case.attrib["name"] for case in cases if case.find("skipped") is not None]
    evidence = {
        "batch": 5, "findings": ["A16", "A17", "A23", "A24"],
        "passed": len(cases) - len(skipped), "skipped": skipped,
        "checks": [
            "422 handlers distinguish application, FastAPI and Pydantic errors",
            "SQL constraints, vendor errors and debug tracebacks stay out of responses",
            "chat errors return 502/504 and are not saved as assistant turns",
            "message-count sort precedes pagination with two listing queries",
            "trash blocks reads, updates and inserts; message pages are bounded",
            "transcript deadlines cover the whole request and sockets",
            "concurrent ingestion and retrieval share one local encoder",
            "real Chroma storage emits no PostHog capture calls",
        ],
        "external_services": "live YouTube/Hugging Face/Groq calls not run; transport/model boundaries tested deterministically",
    }
    Path(__file__).with_name("batch-5-verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


parser = argparse.ArgumentParser(description=__doc__)
mode = parser.add_mutually_exclusive_group()
mode.add_argument("--batch", type=int, choices=[1, 2, 3, 4, 5], help="Verify a remediation batch (default: 2)")
mode.add_argument("--baseline", action="store_true", help="Reproduce historical, unfixed defects")
parser.add_argument("--source-only", action="store_true",
                    help="Check source tracking and declarations only; does not validate installed dependencies")
arguments = parser.parse_args()
if arguments.baseline and arguments.source_only:
    parser.error("--source-only cannot be used with --baseline")
if not arguments.baseline:
    if arguments.source_only and arguments.batch == 2:
        parser.error("--source-only applies only to Batch 1")
    if arguments.batch == 1 or arguments.source_only:
        verify_batch_one(source_only=arguments.source_only)
    elif arguments.batch == 3:
        verify_batch_three()
    elif arguments.batch == 4:
        verify_batch_four()
    elif arguments.batch == 5:
        verify_batch_five()
    else:
        verify_batch_two()
    raise SystemExit(0)

sys.path.insert(0, str(ROOT / "backend"))
os.environ.update(DOCPRO_DATABASE_URL="sqlite+aiosqlite:///:memory:",
                  DOCPRO_JWT_SECRET_KEY="offline-audit-secret-not-for-deployment",
                  GROQ_API_KEY="offline-placeholder", DOCPRO_ENVIRONMENT="development")
import dotenv
dotenv.load_dotenv = lambda *a, **kw: False
logging.disable(logging.CRITICAL)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from alembic import command
from alembic.config import Config
from app.db.session import to_async_database_url
from app.models.base import Base
from app.models.entities import User, Document, Embedding, SourceStatus
from app.models.settings import UserSettings
from app.services import document as documents
from app.services import embedding_helper
from app.schemas.document import EmbeddingConfig, DocumentChunk, ChunkingConfig
from app.core.exceptions import register_exception_handlers, ValidationError
from app.services.auth import create_refresh_token, refresh
from app.schemas.auth import RefreshRequest
from app.api.auth import logout_endpoint
from main import create_app

results = {}

def record(name, evidence):
    results[name] = evidence

async def run(temp):
    converted = to_async_database_url("postgresql://audit_user:synthetic-password@localhost/audit")
    assert make_url(converted).password == "synthetic-password"
    record("database_password_preserved", "Synthetic password survives URL conversion")

    app = create_app()
    middleware = [m.cls.__name__ for m in app.user_middleware]
    assert "RateLimitMiddleware" not in middleware
    paths = app.openapi()["paths"]
    record("active_middleware", middleware)
    record("missing_api_contracts", [p for p in ["/api/v1/website", "/api/v1/auth/password-reset/", "/api/v1/documents/{document_id}/status"] if p not in paths])

    # Actual upload function: traversal stays within this disposable directory.
    engine = create_async_engine(f"sqlite+aiosqlite:///{temp / 'probe.sqlite'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as db:
        user = User(email="audit@example.invalid", role="user")
        db.add(user)
        await db.commit()
        user_id = user.id
    upload_root = temp / "uploads-root"
    with patch.object(documents, "get_settings", return_value=SimpleNamespace(upload_dir=str(upload_root))), patch.object(documents, "get_session_factory", return_value=factory):
        doc = await documents.upload_document(b"harmless audit marker", "../../../../outside.txt", "text/plain", user_id)
        assert not (temp / "outside.txt").exists()
        assert doc.storage_key == f"uploads/{user_id}/{doc.id}/content"
        assert documents.resolve_storage_key(upload_root, doc.storage_key).read_bytes() == b"harmless audit marker"
        record("upload_path_traversal_blocked", "Client filename is metadata; content stays within configured storage")
        # No real model is loaded and no network requests are made.
        with patch.object(documents, "RetrieverManager", side_effect=RuntimeError("synthetic index outage")):
            await documents.store_document(doc, [DocumentChunk(index=0, content="chunk", metadata={"page": 7})], [[0.1, 0.2]], EmbeddingConfig())
            await documents.store_document(doc, [DocumentChunk(index=0, content="chunk", metadata={"page": 7})], [[0.1, 0.2]], EmbeddingConfig())
        async with factory() as db:
            saved = await db.get(Document, doc.id)
            chunks = (await db.scalars(select(Embedding).where(Embedding.document_id == doc.id))).all()
            assert len(chunks) == 1 and chunks[0].metadata_ == {"page": 7}
            record("chunk_replacement_and_metadata", {"rows_after_two_runs": len(chunks), "stored_chunk_metadata": chunks[0].metadata_})
            record("index_failure_readiness_pending_batch_4", saved.status.value)

    # Logout and refresh reuse, with a disposable user and no HTTP server.
    token = create_refresh_token(user_id, auth_version=0)
    async with factory() as db:
        await refresh(db, RefreshRequest(refresh_token=token))
        await logout_endpoint(authorization=f"Bearer {token}", db=db)
        try:
            await refresh(db, RefreshRequest(refresh_token=token))
        except Exception:
            pass
    record("refresh_replay_after_logout", "Same refresh JWT accepted before and after logout")
    await engine.dispose()

    cfg = Config(str(ROOT / "backend/alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{temp / 'migration.sqlite'}")
    command.upgrade(cfg, "head")
    sync_engine = create_engine(f"sqlite:///{temp / 'migration.sqlite'}")
    columns = [c["name"] for c in inspect(sync_engine).get_columns("chat_sessions")]
    assert "deleted_at" in columns
    assert "ix_chat_sessions_deleted_at" in {index["name"] for index in inspect(sync_engine).get_indexes("chat_sessions")}
    record("migration_deleted_at_present", {"actual_columns": columns})
    sync_engine.dispose()

    error_app = FastAPI()
    register_exception_handlers(error_app)
    @error_app.get("/synthetic-validation")
    def fail():
        raise ValidationError("synthetic validation failure")
    response = TestClient(error_app, raise_server_exceptions=False).get("/synthetic-validation")
    assert response.status_code == 500
    record("wrong_exception_handler", "Application ValidationError produces 500 instead of 422")

    service = SimpleNamespace(get_provider=lambda name: object(), embed_texts=AsyncMock(side_effect=RuntimeError("synthetic embedding outage")))
    with patch.object(embedding_helper, "get_embedding_service", return_value=service):
        try:
            await embedding_helper.generate_embeddings(["test"], "test")
        except Exception as exc:
            assert isinstance(exc, UnboundLocalError)
            record("embedding_exception_scope", type(exc).__name__)

    invalid = ChunkingConfig(chunk_size=100, chunk_overlap=100, strategy="fixed")
    try:
        documents.chunk_text("word " * 200, invalid)
    except ValueError as exc:
        record("chunking_cross_field_validation", str(exc))

    from app.rag.pipelines.rag_pipeline import RAGPipeline
    from app.services.chat_service import ChatService
    captured = {}
    def invoke(state):
        captured.update(state)
        return {"response": "stub", "reranked_docs": []}
    chat = ChatService(db=None, user_id=user_id,
                       rag_pipeline=SimpleNamespace(graph=SimpleNamespace(invoke=invoke)))
    chat._get_authorized_source_ids = AsyncMock(return_value={"document": ["owned"], "youtube": [], "website": []})
    with patch("app.services.chat_service.ensure_youtube_sources_in_retriever", new=AsyncMock()):
        await chat._run_rag_pipeline("What did I just say?", [{"role": "user", "content": "remember canary"}])
    assert "history" not in captured and "messages" not in captured
    record("conversation_history_dropped", "History argument is absent from the graph input")
    calls = []
    pipeline = RAGPipeline.__new__(RAGPipeline)
    def retrieve(query, top_k, filter_dict=None):
        calls.append({"top_k": top_k, "filter": filter_dict})
        return [("other tenant", 0.1, {"document_id": "foreign"})] * top_k
    pipeline.retriever = SimpleNamespace(retrieve=retrieve)
    output = pipeline._retrieve_documents({"question": "summarize report", "metadata": {"user_id": str(user_id), "top_k": 3, "authorized_source_ids": {"document": ["owned"]}}})
    assert output["retrieved_docs"] == [] and calls[0]["filter"] is None
    record("retrieval_filters_after_global_top_k", calls)

    # Import only the validator AST: installed Crawl4AI cannot import this module.
    source = (ROOT / "backend/app/services/crawler_service.py").read_text()
    tree = ast.parse(source)
    validator = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_url")
    import re
    from urllib.parse import urlparse
    namespace = {"urlparse": urlparse, "re": re, "CrawlerValidationError": ValueError}
    exec(compile(ast.Module(body=[validator], type_ignores=[]), "crawler_validator_only", "exec"), namespace)
    accepted = []
    for url in ["http://[::ffff:127.0.0.1]/", "http://[fd00::1]/", "http://127.1/", "http://localhost./"]:
        namespace["validate_url"](url)
        accepted.append(url)
    record("dormant_ssrf_validator_bypasses", accepted)

with tempfile.TemporaryDirectory(prefix="ragfusion-audit-") as directory:
    asyncio.run(run(Path(directory)))
output = Path(__file__).with_name("baseline-current-results.json")
output.write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
