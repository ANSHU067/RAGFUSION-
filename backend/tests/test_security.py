"""Security-unit tests for encryption, CORS, and environment validation."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.encryption import APIKeyCipher, APIKeyManager, EncryptionError
from app.core.environment import EnvironmentValidationError, SecurityEnvironment
from app.core.security import sanitize_response
from app.middleware.security_headers import SecurityHeadersMiddleware


def security_environment(
    *,
    environment: str = "development",
    jwt_secret: str = "a-test-secret-that-is-long-enough",
    jwt_algorithm: str = "HS256",
    jwt_issuer: str = "docpro-v2",
    jwt_audience: str = "docpro-api",
    jwt_private_key: str | None = None,
    jwt_public_key: str | None = None,
    encryption_key: str | None = None,
    cors_origins: tuple[str, ...] = ("https://app.example.test",),
    cors_methods: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    cors_headers: tuple[str, ...] = ("Authorization", "Content-Type", "X-API-Key", "X-Request-ID"),
    cors_credentials: bool = True,
) -> SecurityEnvironment:
    return SecurityEnvironment(
        environment=environment,
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        jwt_issuer=jwt_issuer,
        jwt_audience=jwt_audience,
        jwt_private_key=jwt_private_key,
        jwt_public_key=jwt_public_key,
        encryption_key=encryption_key,
        cors_origins=cors_origins,
        cors_methods=cors_methods,
        cors_headers=cors_headers,
        cors_credentials=cors_credentials,
    )


def test_cors_and_security_headers() -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, environment=security_environment())

    @app.get("/public")
    async def public() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    allowed = client.options("/public", headers={"Origin": "https://app.example.test"})
    assert allowed.status_code == 204
    assert allowed.headers["access-control-allow-origin"] == "https://app.example.test"
    denied = client.options("/public", headers={"Origin": "https://evil.example"})
    assert denied.status_code == 403
    response = client.get("/public")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in response.headers


def test_api_key_lifecycle_and_response_sanitization() -> None:
    cipher = APIKeyCipher(APIKeyCipher.generate_encryption_key())
    keys = APIKeyManager(cipher)
    key_id, secret = keys.generate()
    assert keys.validate(secret) == key_id
    assert cipher.decrypt(keys.encrypted_value(key_id)) == secret
    keys.revoke(key_id)
    assert keys.validate(secret) is None
    assert sanitize_response(
        {"api_key": "should-not-leak", "nested": {"token": "no"}}
    ) == {"api_key": "[REDACTED]", "nested": {"token": "[REDACTED]"}}
    with pytest.raises(EncryptionError):
        cipher.decrypt("invalid")


def test_production_environment_requires_safe_values() -> None:
    with pytest.raises(EnvironmentValidationError):
        SecurityEnvironment(environment="production", cors_origins=("*",)).validate()


@pytest.mark.parametrize("environment", ["production", "prod", " PRODUCTION "])
@pytest.mark.parametrize("secret", [
    "", "x", " " * 32, "x" * 31, "your-secret-key", "change-me-in-production",
    "  YOUR-SECRET-KEY  ", " " * 32 + "your-secret-key" + " " * 32,
])
def test_production_rejects_short_or_placeholder_jwt_secrets(environment, secret):
    with pytest.raises(EnvironmentValidationError, match="at least 32 characters"):
        security_environment(environment=environment, jwt_secret=secret).validate()


def test_production_accepts_32_character_jwt_secret():
    security_environment(
        environment="production", jwt_secret="0123456789abcdef0123456789ABCDEF",
    ).validate()


def test_development_keeps_local_secret_default():
    SecurityEnvironment(environment="development").validate()


def test_application_rejects_weak_production_jwt_secret(monkeypatch):
    import main
    from app.config.settings import Settings

    monkeypatch.setattr(main, "get_settings", lambda: Settings(
        _env_file=None, environment="production", jwt_secret_key="x",
        cors_origins=["https://app.example.test"],
    ))
    with pytest.raises(EnvironmentValidationError, match="at least 32 characters"):
        main.create_app()
