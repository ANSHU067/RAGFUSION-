"""Security-unit tests for token, encryption, CORS, and authorization controls."""

from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.encryption import APIKeyCipher, APIKeyManager, EncryptionError
from app.core.environment import EnvironmentValidationError, SecurityEnvironment
from app.core.jwt_manager import JWTManager, TokenValidationError
from app.core.security import require_roles, sanitize_response
from app.middleware.auth_middleware import AuthenticationMiddleware
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


def protected_client() -> tuple[TestClient, JWTManager]:
    environment = security_environment()
    manager = JWTManager(environment)
    app = FastAPI()
    app.add_middleware(
        AuthenticationMiddleware, jwt_manager=manager, public_paths=("/public",)
    )
    app.add_middleware(SecurityHeadersMiddleware, environment=environment)

    @app.get("/public")
    async def public() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/private")
    async def private() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/admin", dependencies=[Depends(require_roles("admin"))])
    async def admin() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app), manager


def test_valid_authentication_and_rbac() -> None:
    client, manager = protected_client()
    token = manager.issue_access_token("user-1", "admin")
    assert (
        client.get("/private", headers={"Authorization": f"Bearer {token}"}).status_code
        == 200
    )
    assert (
        client.get("/admin", headers={"Authorization": f"Bearer {token}"}).status_code
        == 200
    )


def test_missing_invalid_and_expired_tokens_are_rejected() -> None:
    client, manager = protected_client()
    assert client.get("/private").status_code == 401
    assert (
        client.get(
            "/private", headers={"Authorization": "Bearer altered.token.value"}
        ).status_code
        == 401
    )
    expired = manager.issue_access_token(
        "user-1", "user", expires_in=timedelta(seconds=-1)
    )
    assert (
        client.get(
            "/private", headers={"Authorization": f"Bearer {expired}"}
        ).status_code
        == 401
    )


def test_permission_validation_rejects_wrong_role() -> None:
    client, manager = protected_client()
    token = manager.issue_access_token("user-1", "user")
    assert (
        client.get("/admin", headers={"Authorization": f"Bearer {token}"}).status_code
        == 403
    )


def test_issuer_audience_revocation_and_key_rotation() -> None:
    manager = JWTManager(security_environment())
    token = manager.issue_access_token("user-1", "user")
    assert manager.verify(token)["sub"] == "user-1"
    manager.rotate_signing_key("next", "another-long-test-secret", make_active=True)
    assert manager.verify(token)["sub"] == "user-1"
    manager.revoke(token)
    with pytest.raises(TokenValidationError):
        manager.verify(token)


def test_cors_and_security_headers() -> None:
    client, _ = protected_client()
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
