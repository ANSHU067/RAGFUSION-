"""Website ingestion, source isolation, and live workspace overview contracts."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, func

from app.core.exceptions import AppException, NotFoundError
from app.models.entities import User, Website, SourceStatus, Embedding, ChatSession, Message, MessageRole, Document, YouTubeSource
from app.schemas.website import CrawledPage, WebsiteMetadata
from app.services import website_service as service
from app.services.chat_service import ChatService
from app.rag.pipelines.rag_pipeline import RAGPipeline


@pytest.fixture
def indexer(monkeypatch):
    page = CrawledPage(url='https://example.com/article', status_code=200, text_content='Public research about coral reefs and ocean ecosystems. ' * 80, metadata=WebsiteMetadata(url='https://example.com/article', title='Ocean research'))
    crawl = AsyncMock(return_value=page)
    async def embed(chunks, model, dimensions):
        assert model == service.MODEL and dimensions == 384
        return [[0.1] * dimensions for _ in chunks]
    store = Mock()
    monkeypatch.setattr(service, 'crawl_single_page', crawl)
    monkeypatch.setattr(service, 'generate_embeddings', embed)
    monkeypatch.setattr(service, 'store_vectors', store)
    return SimpleNamespace(crawl=crawl, store=store)


@pytest.mark.parametrize('url', ['http://127.0.0.1', 'http://169.254.169.254/latest/meta-data', 'http://[::1]', 'http://2130706433', 'http://0x7f000001', 'http://[2002:7f00:1::]', 'http://user:pass@example.com', 'file:///etc/passwd'])
def test_ingestion_rejects_nonpublic_urls(client, auth_headers, url):
    response = client.post('/api/v1/website/ingest', headers=auth_headers, json={'url': url})
    assert response.status_code == 422


async def test_website_create_process_sources_and_delete(client, auth_headers, db_session, test_user, indexer, monkeypatch):
    created = client.post('/api/v1/website/ingest', headers=auth_headers, json={'url': 'https://example.com/article'})
    assert created.status_code == 201, created.text
    item = created.json()
    assert item['status'] == 'pending'
    assert client.get('/api/v1/chat/sources', headers=auth_headers).json()['sources'] == []
    duplicate = client.post('/api/v1/website/ingest', headers=auth_headers, json={'url': item['url']})
    assert duplicate.status_code == 409
    result = client.post(f"/api/v1/website/{item['id']}/process", headers=auth_headers)
    assert result.status_code == 200, result.text
    ready = result.json()
    assert ready['status'] == 'ready' and ready['metadata']['total_chunks'] > 0
    indexer.store.assert_called_once()
    assert indexer.store.call_args.args[1] == test_user.id
    chunks = (await db_session.scalars(select(Embedding).where(Embedding.website_id == UUID(item['id'])))).all()
    assert len(chunks) == ready['metadata']['total_chunks']
    assert all(chunk.metadata_['user_id'] == str(test_user.id) and len(chunk.vector) == 384 for chunk in chunks)
    assert client.get('/api/v1/chat/sources', headers=auth_headers).json()['sources'] == [{'id': item['id'], 'type': 'website', 'title': 'Ocean research'}]
    assert client.post(f"/api/v1/website/{item['id']}/process", headers=auth_headers).status_code == 409
    delete = Mock()
    monkeypatch.setattr('app.api.website.remove_vectors', delete)
    assert client.delete(f"/api/v1/website/{item['id']}", headers=auth_headers).status_code == 204
    delete.assert_called_once_with(UUID(item['id']), test_user.id)
    assert client.get('/api/v1/chat/sources', headers=auth_headers).json()['sources'] == []


def test_index_failure_is_persisted_and_sanitized(client, auth_headers, indexer):
    item = client.post('/api/v1/website/ingest', headers=auth_headers, json={'url': 'https://example.com/article'}).json()
    indexer.store.side_effect = RuntimeError('private-storage-password')
    result = client.post(f"/api/v1/website/{item['id']}/process", headers=auth_headers)
    assert result.status_code == 502 and 'private-storage-password' not in result.text
    assert client.get(f"/api/v1/website/{item['id']}", headers=auth_headers).json()['status'] == 'failed'
    assert client.get('/api/v1/chat/sources', headers=auth_headers).json()['sources'] == []
    indexer.store.side_effect = None
    assert client.post(f"/api/v1/website/{item['id']}/process", headers=auth_headers).json()['status'] == 'ready'


async def test_website_owner_boundaries(client, auth_headers, db_session):
    other = User(email='outsider@example.invalid')
    db_session.add(other)
    await db_session.flush()
    source = Website(user_id=other.id, url='https://example.com/private', status=SourceStatus.ready)
    db_session.add(source)
    await db_session.commit()
    for method, suffix in [('get', ''), ('post', '/process'), ('delete', '')]:
        assert getattr(client, method)(f'/api/v1/website/{source.id}{suffix}', headers=auth_headers).status_code == 404
    assert client.get('/api/v1/website', headers=auth_headers).json()['items'] == []


async def test_claim_allows_one_processor(test_db, db_session, test_user, indexer):
    source = Website(user_id=test_user.id, url='https://example.com/concurrency', status=SourceStatus.pending)
    db_session.add(source)
    await db_session.commit()
    entered = asyncio.Event()
    release = asyncio.Event()
    page = indexer.crawl.return_value
    async def crawl(*args, **kwargs):
        entered.set()
        await release.wait()
        return page
    indexer.crawl.side_effect = crawl
    async with test_db() as first, test_db() as second:
        task = asyncio.create_task(service.process_website(first, source.id, test_user.id))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            with pytest.raises(AppException) as error:
                await service.process_website(second, source.id, test_user.id)
            assert error.value.status_code == 409
            release.set()
            assert (await task).status == SourceStatus.ready
        finally:
            release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    assert indexer.crawl.await_count == 1


async def test_source_selection_and_dashboard_are_tenant_scoped(client, auth_headers, db_session, test_user):
    other = User(email='other-workspace@example.invalid')
    db_session.add(other)
    await db_session.flush()
    own = Website(user_id=test_user.id, url='https://example.com/own', title='Own source', status=SourceStatus.ready)
    foreign = Website(user_id=other.id, url='https://example.com/foreign', title='Foreign source', status=SourceStatus.ready)
    failed = Website(user_id=test_user.id, url='https://example.com/failed', status=SourceStatus.failed)
    session = ChatSession(user_id=test_user.id, title='Coral questions')
    db_session.add_all([own, foreign, failed, session,
        ChatSession(user_id=test_user.id, title='Deleted', deleted_at=datetime.now(timezone.utc)),
        ChatSession(user_id=other.id, title='Not yours'),
        Document(user_id=test_user.id, filename='ready.pdf', storage_key='safe/key', status=SourceStatus.ready),
        Document(user_id=test_user.id, filename='pending.pdf', storage_key='safe/pending', status=SourceStatus.pending),
        YouTubeSource(user_id=test_user.id, video_id='12345678901', url='https://youtube.com/watch?v=12345678901', status=SourceStatus.ready),
    ])
    await db_session.flush()
    for row in [own, foreign, failed]:
        db_session.add(Embedding(website_id=row.id, chunk_index=0, content=row.title or 'failed', model_name=service.MODEL, vector=[0.1] * 384))
    db_session.add_all([Message(chat_session_id=session.id, role=MessageRole.user, content='hello', token_count=2), Message(chat_session_id=session.id, role=MessageRole.assistant, content='answer', token_count=5)])
    await db_session.commit()
    sources = client.get('/api/v1/chat/sources', headers=auth_headers).json()['sources']
    assert sources == [{'id': str(own.id), 'type': 'website', 'title': 'Own source'}]
    chat = ChatService(db=db_session, user_id=test_user.id)
    with pytest.raises(NotFoundError):
        await chat.select_sources({'website': [str(foreign.id)]})
    with pytest.raises(NotFoundError):
        await chat.select_sources({'website': [str(failed.id)]})
    await chat.select_sources({'website': [str(own.id)]})
    allowed = await chat._get_authorized_source_ids()
    assert allowed == {'document': [], 'website': [str(own.id)], 'youtube': []}
    pipeline = object.__new__(RAGPipeline)
    pipeline.retriever = SimpleNamespace(retrieve=Mock(return_value=[]))
    pipeline._retrieve_documents({'question': 'What is on the site?', 'metadata': {'user_id': str(test_user.id), 'authorized_source_ids': allowed, 'top_k': 3}})
    options = pipeline.retriever.retrieve.call_args.kwargs
    assert options['top_k'] == 3 and {'website_id': str(own.id)} in options['filter_dict']['$or']
    assert str(foreign.id) not in str(options)
    overview = client.get('/api/v1/dashboard', headers=auth_headers)
    assert overview.status_code == 200, overview.text
    assert overview.json()['stats'] == {'documents': 1, 'youtube': 1, 'websites': 1, 'conversations': 1}
    recent = overview.json()['recent_sessions']
    assert len(recent) == 1 and recent[0]['message_count'] == 2 and recent[0]['token_count'] == 7
    assert await db_session.scalar(select(func.count()).select_from(ChatSession)) == 3


def test_invalid_source_selection_does_not_create_chat(client, auth_headers):
    response = client.post('/api/v1/chat', headers=auth_headers, json={'message': 'hello', 'source_ids': {'website': [str(uuid4())]}})
    assert response.status_code == 404
    assert client.get('/api/v1/chat/sessions', headers=auth_headers).json()['total'] == 0


async def test_canceled_ingestion_is_failed_and_retryable(test_db, db_session, test_user, indexer):
    source = Website(user_id=test_user.id, url='https://example.com/cancel', status=SourceStatus.pending,
                     metadata_={'chunking': {'strategy': 'fixed', 'chunk_size': 600, 'chunk_overlap': 100}})
    db_session.add(source)
    await db_session.commit()
    entered = asyncio.Event()
    async def crawl(*args, **kwargs):
        entered.set()
        await asyncio.Event().wait()
    indexer.crawl.side_effect = crawl
    async with test_db() as connection:
        task = asyncio.create_task(service.process_website(connection, source.id, test_user.id))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    await db_session.refresh(source)
    assert source.status == SourceStatus.failed
    assert source.metadata_['chunking']['chunk_size'] == 600
    indexer.store.assert_not_called()


def test_real_html_extraction_embeddings_and_chroma_round_trip(client, auth_headers, monkeypatch, tmp_path):
    """Only HTTP is controlled; extraction, shared MiniLM, SQL, and Chroma are real."""
    import chromadb
    from chromadb.config import Settings
    from app.services import crawler_service
    from app.core.embedding_runtime import get_sentence_transformer
    model = get_sentence_transformer()
    client_store = chromadb.PersistentClient(path=str(tmp_path / 'vectors'), settings=Settings(
        anonymized_telemetry=False,
        chroma_product_telemetry_impl='app.core.telemetry.DisabledProductTelemetry',
        chroma_telemetry_impl='app.core.telemetry.DisabledProductTelemetry',
    ))
    collection = client_store.get_or_create_collection('rag_documents')
    monkeypatch.setattr(service, 'RetrieverManager', lambda: SimpleNamespace(client=client_store))
    html = '<html><head><title>Coral ecology</title></head><body><article>' + '<p>Coral reefs shelter many fish species. Ocean warming causes coral bleaching and damages marine ecosystems.</p>' * 15 + '</article></body></html>'
    monkeypatch.setattr(crawler_service, 'fetch_page', AsyncMock(return_value=(200, 'text/html', html, [])))
    source = client.post('/api/v1/website/ingest', headers=auth_headers, json={'url': 'https://example.com/ecology'}).json()
    response = client.post(f"/api/v1/website/{source['id']}/process", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'ready'
    stored = collection.get(where={'website_id': source['id']}, include=['embeddings', 'documents', 'metadatas'])
    assert len(stored['ids']) == response.json()['metadata']['total_chunks'] > 0
    assert len(stored['embeddings'][0]) == 384
    assert 'Coral' in stored['documents'][0]
    assert stored['metadatas'][0]['source_type'] == 'website'
    query = model.encode(['What damages coral reefs?']).tolist()
    results = collection.query(query_embeddings=query, n_results=1, where={'website_id': source['id']})
    assert results['ids'][0][0] in stored['ids']
    # Another tenant's/source's filter cannot retrieve this content.
    assert collection.query(query_embeddings=query, n_results=1, where={'website_id': str(uuid4())})['ids'] == [[]]
    assert get_sentence_transformer() is model
    service.remove_vectors(UUID(source['id']), UUID(stored['metadatas'][0]['user_id']))
    assert collection.count() == 0
