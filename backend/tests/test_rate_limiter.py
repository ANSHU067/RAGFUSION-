"""Rate-limit and brute-force protection tests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limiter import InMemoryRateLimiter, RateLimitPolicy
from app.middleware.rate_limit_middleware import RateLimitMiddleware


@pytest.mark.asyncio
async def test_limiter_enforces_burst_and_reports_retry_after() -> None:
    limiter = InMemoryRateLimiter()
    policy = RateLimitPolicy(limit=2, window_seconds=60, burst=1)
    assert (await limiter.check("ip:one", policy)).allowed
    assert (await limiter.check("ip:one", policy)).allowed
    assert (await limiter.check("ip:one", policy)).allowed
    denied = await limiter.check("ip:one", policy)
    assert not denied.allowed
    assert denied.retry_after >= 1


def test_login_brute_force_protection_is_ip_based() -> None:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        limiter=InMemoryRateLimiter(),
        policies={
            "auth": RateLimitPolicy(1, 60),
            "chat": RateLimitPolicy(3, 60),
            "ingestion": RateLimitPolicy(3, 60),
            "api": RateLimitPolicy(3, 60),
        },
    )

    @app.post("/api/v1/auth/login")
    async def login() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    assert (
        client.post(
            "/api/v1/auth/login", headers={"X-Forwarded-For": "198.51.100.10"}
        ).status_code
        == 200
    )
    blocked = client.post(
        "/api/v1/auth/login", headers={"X-Forwarded-For": "198.51.100.10"}
    )
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"]
    assert (
        client.post(
            "/api/v1/auth/login", headers={"X-Forwarded-For": "198.51.100.11"}
        ).status_code
        == 429
    )


def test_trusted_proxy_chain_is_walked_from_verified_peer():
    from starlette.requests import Request
    middleware = RateLimitMiddleware(FastAPI(), limiter=InMemoryRateLimiter(), trusted_proxies=('10.0.0.0/8',))
    def identity(peer, forwarded):
        request = Request({'type': 'http', 'client': (peer, 123), 'headers': [(b'x-forwarded-for', forwarded.encode())]})
        return middleware._identity(request)
    assert identity('192.0.2.9', '1.1.1.1') == 'ip:192.0.2.9'
    assert identity('10.0.0.2', '1.1.1.1, 192.0.2.9, 10.0.0.1') == 'ip:192.0.2.9'
    assert identity('10.0.0.2', 'not-an-ip') == 'ip:10.0.0.2'


def test_real_app_mounts_limiter_and_shares_auth_budget():
    from main import create_app
    app = create_app(rate_limiter=InMemoryRateLimiter())
    client = TestClient(app)
    for index in range(7):
        response = client.post('/api/v1/auth/' + ('login' if index % 2 else 'signup'), json={})
        assert response.status_code == 422
    assert client.post('/api/v1/auth/refresh', json={}).status_code == 429
    assert client.post('/api/v1/chat', json={}).status_code != 429
    assert client.post('/api/v1/documents/upload', json={}).status_code != 429


def test_redis_failure_returns_sanitized_503_without_running_endpoint(monkeypatch):
    from unittest.mock import AsyncMock
    from redis.exceptions import ConnectionError
    from app.core.rate_limiter import RedisRateLimiter
    from main import create_app
    limiter = RedisRateLimiter('redis://127.0.0.1:1/0')
    monkeypatch.setattr(limiter.redis, 'eval', AsyncMock(side_effect=ConnectionError('private Redis address and credentials')))
    app = create_app(rate_limiter=limiter)
    invoked = []
    @app.get('/sensitive-work')
    def work():
        invoked.append(True)
        return {'ok': True}
    response = TestClient(app).get('/sensitive-work', headers={'Origin': 'http://localhost:5173'})
    assert response.status_code == 503
    assert response.headers['retry-after'] == '5'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert response.json() == {'error': {'message': 'Service temporarily unavailable'}}
    assert not invoked


@pytest.mark.asyncio
async def test_real_redis_is_atomic_shared_and_expires():
    import asyncio
    import os
    from uuid import uuid4
    from app.core.rate_limiter import RedisRateLimiter
    url = os.environ.get('BATCH3_REDIS_URL')
    if not url:
        pytest.skip('Set BATCH3_REDIS_URL for real Redis Lua verification')
    prefix = 'batch3-test:' + uuid4().hex
    workers = [RedisRateLimiter(url, prefix=prefix, timeout=5) for _ in range(2)]
    try:
        results = await asyncio.gather(*(workers[i % 2].check('same-client', RateLimitPolicy(7, 60)) for i in range(60)))
        assert sum(result.allowed for result in results) == 7
        keys = [key async for key in workers[0].redis.scan_iter(match=prefix + ':*')]
        assert len(keys) == 2
        for key in keys:
            assert 0 < await workers[0].redis.pttl(key) <= 60000
        short = RateLimitPolicy(1, .08)
        assert (await workers[0].check('expiry', short)).allowed
        assert not (await workers[1].check('expiry', short)).allowed
        await asyncio.sleep(.12)
        assert (await workers[1].check('expiry', short)).allowed
    finally:
        keys = [key async for key in workers[0].redis.scan_iter(match=prefix + ':*')]
        if keys:
            await workers[0].redis.delete(*keys)
        await asyncio.gather(*(worker.aclose() for worker in workers))
