"""Authentication middleware adversarial tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.environment import SecurityEnvironment
from app.core.jwt_manager import JWTManager
from app.middleware.auth_middleware import AuthenticationMiddleware


def test_auth_middleware_blocks_header_smuggling_and_refresh_tokens() -> None:
    environment = SecurityEnvironment(jwt_secret="long-test-secret-for-middleware")
    manager = JWTManager(environment)
    app = FastAPI()
    app.add_middleware(AuthenticationMiddleware, jwt_manager=manager, public_paths=())

    @app.get("/protected")
    async def protected() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    assert (
        client.get(
            "/protected", headers={"Authorization": "Basic anything"}
        ).status_code
        == 401
    )
    refresh = manager.issue_refresh_token("subject")
    assert (
        client.get(
            "/protected", headers={"Authorization": f"Bearer {refresh}"}
        ).status_code
        == 401
    )
    access = manager.issue_access_token("subject", "user")
    assert (
        client.get(
            "/protected", headers={"Authorization": f"Bearer {access}"}
        ).status_code
        == 200
    )
