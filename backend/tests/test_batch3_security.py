"""Session concurrency, migration compatibility, and crawler transport regressions."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from alembic import command
from sqlalchemy import inspect, select, text

from app.core.exceptions import UnauthorizedError
from app.models.entities import User
from app.schemas.auth import RefreshRequest
from app.services import auth
from app.services import crawler_service as crawler
from test_batch2_integrity import database, owner, migration_config


async def test_parallel_refresh_has_one_winner(database, owner):
    token = auth.create_refresh_token(owner.id, auth_version=owner.auth_version)
    async def refresh():
        async with database.factory() as session:
            try:
                return await auth.refresh(session, RefreshRequest(refresh_token=token))
            except UnauthorizedError:
                return None
    responses = await asyncio.wait_for(asyncio.gather(*(refresh() for _ in range(6))), timeout=15)
    assert sum(response is not None for response in responses) == 1
    winner = next(response for response in responses if response is not None)
    async with database.factory() as session:
        user = await auth.get_current_user(session, winner.access_token)
        assert user.auth_version == 1
        with pytest.raises(UnauthorizedError):
            await auth.refresh(session, RefreshRequest(refresh_token=token))


async def test_logout_and_refresh_compete_atomically(database, owner):
    access = auth.create_access_token(owner.id, owner.role, auth_version=owner.auth_version)
    refresh = auth.create_refresh_token(owner.id, auth_version=owner.auth_version)
    async def invoke(logout):
        async with database.factory() as session:
            try:
                if logout:
                    await auth.logout(session, access)
                else:
                    await auth.refresh(session, RefreshRequest(refresh_token=refresh))
                return True
            except UnauthorizedError:
                return False
    outcomes = await asyncio.wait_for(asyncio.gather(invoke(True), invoke(False)), timeout=10)
    assert sum(outcomes) == 1
    async with database.factory() as session:
        assert (await session.get(User, owner.id)).auth_version == 1
        with pytest.raises(UnauthorizedError):
            await auth.get_current_user(session, access)


async def test_account_revocation_does_not_affect_another_user(database, owner):
    async with database.factory() as session:
        other = User(email='another-user@example.invalid')
        session.add(other)
        await session.commit()
        token = auth.create_access_token(other.id, other.role, auth_version=other.auth_version)
        owner_token = auth.create_access_token(owner.id, owner.role, auth_version=owner.auth_version)
        await auth.logout(session, owner_token)
        assert (await auth.get_current_user(session, token)).id == other.id
        with pytest.raises(UnauthorizedError):
            await auth.get_current_user(session, owner_token)


async def test_auth_version_migration_backfills_existing_users(database, owner):
    config = migration_config(database.migration_url)
    await asyncio.to_thread(command.downgrade, config, '20261005_0001')
    async with database.engine.connect() as connection:
        columns = await connection.run_sync(lambda sync: inspect(sync).get_columns('users'))
        assert 'auth_version' not in {column['name'] for column in columns}
    await asyncio.to_thread(command.upgrade, config, 'head')
    async with database.factory() as session:
        user = await session.get(User, owner.id)
        assert user.auth_version == 0
        assert await session.scalar(text('SELECT version_num FROM alembic_version')) == '20261006_0001'


@pytest.mark.parametrize('address', ['127.0.0.1', '10.1.1.1', '169.254.169.254', '::1', 'fd00::1', '::ffff:127.0.0.1', '100.64.0.1', '224.0.0.1', '64:ff9b::7f00:1', '::127.0.0.1', '2002:7f00:1::'])
async def test_resolver_rejects_private_or_mixed_dns_results(monkeypatch, address):
    resolve = AsyncMock(return_value=[{'host': '8.8.8.8'}, {'host': address}])
    monkeypatch.setattr(aiohttp.DefaultResolver, 'resolve', resolve)
    resolver = crawler.PublicResolver()
    try:
        with pytest.raises(crawler.CrawlerValidationError):
            await resolver.resolve('untrusted.example', 443)
        resolve.assert_awaited_once()
    finally:
        await resolver.close()


async def test_resolver_rechecks_addresses_on_each_resolution(monkeypatch):
    monkeypatch.setattr(aiohttp.DefaultResolver, 'resolve', AsyncMock(side_effect=[
        [{'host': '8.8.8.8'}], [{'host': '127.0.0.1'}],
    ]))
    resolver = crawler.PublicResolver()
    try:
        assert await resolver.resolve('changing.example') == [{'host': '8.8.8.8'}]
        with pytest.raises(crawler.CrawlerValidationError):
            await resolver.resolve('changing.example')
    finally:
        await resolver.close()


@pytest.mark.parametrize('url', ['http://127.0.0.1/', 'http://[::ffff:127.0.0.1]/', 'http://localhost./', 'http://[fd00::1]/', 'http://169.254.169.254/', 'http://name:password@example.com/'])
async def test_literal_and_credential_urls_never_reach_http_client(url):
    session = SimpleNamespace(get=Mock(side_effect=AssertionError('Network access attempted')))
    with pytest.raises(crawler.CrawlerValidationError):
        await crawler.fetch_page(session, url, 10, True)
    session.get.assert_not_called()


class HTTPResponse:
    def __init__(self, chunks=(), status=200, length=None, encoding=None):
        self.status = status
        self.content_length = length
        self.headers = {'Content-Type': 'text/html'}
        if encoding:
            self.headers['Content-Encoding'] = encoding
        self.content = self
        self.chunks = chunks
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def iter_chunked(self, size):
        for chunk in self.chunks:
            yield chunk


@pytest.mark.parametrize('response', [
    HTTPResponse(status=302), HTTPResponse(length=crawler.MAX_RESPONSE_BYTES + 1),
    HTTPResponse(chunks=[b'x' * crawler.MAX_RESPONSE_BYTES, b'x']),
    HTTPResponse(encoding='gzip'),
])
async def test_response_redirect_and_size_limits(response):
    session = SimpleNamespace(get=Mock(return_value=response))
    with pytest.raises(crawler.CrawlerValidationError):
        await crawler.fetch_page(session, 'https://example.com/', 300, True)
    options = session.get.call_args.kwargs
    assert options['allow_redirects'] is False
    assert options['auto_decompress'] is False
    assert options['timeout'].total == 30
    assert options['timeout'].connect == 5
    assert response.closed


async def test_small_response_and_timeout_handling():
    response = HTTPResponse(chunks=[b'<a href="/page">Page</a>'])
    session = SimpleNamespace(get=Mock(return_value=response))
    result = await crawler.fetch_page(session, 'https://example.com/', 10, True)
    assert result[0] == 200 and result[3] == ['https://example.com/page']
    session.get.side_effect = asyncio.TimeoutError()
    with pytest.raises(crawler.CrawlerTimeoutError):
        await crawler.fetch_page(session, 'https://example.com/', 10, False)


def test_vector_configuration_honors_persistent_path(monkeypatch, tmp_path):
    from app.core.rag_config import RAGConfig
    configured = tmp_path / 'vectorstore'
    monkeypatch.setenv('RAG_VECTOR_STORE_PATH', str(configured))
    assert RAGConfig(_env_file=None).vector_store_path == configured
