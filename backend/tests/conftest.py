"""Pytest configuration for backend tests."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# ---------------------------------------------------------------------
# Add the backend directory to the Python path
# ---------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------
# Import application objects
# ---------------------------------------------------------------------

from app.db import session as db_module  # noqa: E402
from app.db.session import get_db_session  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.entities import User, UserRole  # noqa: E402
from main import app  # noqa: E402
from app.core.rate_limiter import InMemoryRateLimiter  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_test_rate_limiter(monkeypatch):
    """Business tests use isolated quotas; dedicated tests exercise real Redis."""
    monkeypatch.setattr("main.RedisRateLimiter", lambda *args, **kwargs: InMemoryRateLimiter())
    monkeypatch.setattr(app.state, "rate_limiter", InMemoryRateLimiter())

# ---------------------------------------------------------------------
# Database fixture
# ---------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_db(tmp_path, monkeypatch):
    """Create a temporary SQLite database."""

    database_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"

    engine = create_async_engine(
        database_url,
        future=True,
        echo=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    original_get_session_factory = db_module.get_session_factory

    def patched_factory(database_url=None):
        return session_factory

    # Patch aliases already loaded by the application, without importing disabled
    # integrations just to configure test discovery.
    for name, module in list(sys.modules.items()):
        if (
            name.startswith("app.")
            and getattr(module, "get_session_factory", None) is original_get_session_factory
        ):
            monkeypatch.setattr(module, "get_session_factory", patched_factory)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db_session] = override_get_db

    try:
        yield session_factory
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        await engine.dispose()


# ---------------------------------------------------------------------
# Test client fixture
# ---------------------------------------------------------------------


@pytest.fixture
def client(test_db):
    """Create a FastAPI test client."""

    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------
# Database session fixture
# ---------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session(test_db):
    """Create a database session for testing."""

    async with test_db() as session:
        yield session


# ---------------------------------------------------------------------
# Test user fixture
# ---------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user in the database."""
    from app.services.auth import hash_password

    user = User(
        id=uuid4(),
        email="test@example.com",
        display_name="Test User",
        password_hash=hash_password("testpassword"),
        role=UserRole.user,
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


# ---------------------------------------------------------------------
# Auth headers fixture
# ---------------------------------------------------------------------


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Create authentication headers for testing."""
    from app.services.auth import create_access_token

    # Add the 'role' argument here!
    token = create_access_token(test_user.id, role=test_user.role, auth_version=test_user.auth_version)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------
# Mock user fixture (for unit tests without DB)
# ---------------------------------------------------------------------


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""

    return User(
        id=uuid4(),
        email="test@example.com",
        display_name="Test User",
        role=UserRole.user,
        is_active=True,
        avatar_color='slate',
    )
