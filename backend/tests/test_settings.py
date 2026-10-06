"""Settings module tests."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import UserSettings
from app.schemas.settings import (
    DEFAULT_SETTINGS,
    SettingsCreate,
    SettingsResetResponse,
    SettingsResponse,
    SettingsUpdate,
)
from app.services.settings_service import (
    SettingsNotFoundError,
    SettingsService,
    SettingsValidationError,
    create_settings_service,
)
from app.repositories.settings_repository import SettingsRepository


class TestSettingsSchemas:
    """Tests for settings Pydantic schemas."""

    def test_default_settings_constants(self):
        """Test DEFAULT_SETTINGS contains expected keys."""
        expected_keys = {
            "provider",
            "model_name",
            "embedding_provider",
            "embedding_model",
            "temperature",
            "top_k",
            "max_tokens",
            "chunk_size",
            "chunk_overlap",
            "similarity_threshold",
            "reranking_enabled",
        }
        assert set(DEFAULT_SETTINGS.keys()) == expected_keys

    def test_settings_create_valid(self):
        """Test SettingsCreate with valid data."""
        data = SettingsCreate(
            provider="openai",
            model_name="gpt-4o",
            embedding_provider="openai",
            embedding_model="text-embedding-3-large",
            temperature=0.5,
            top_k=10,
            max_tokens=4000,
            chunk_size=2000,
            chunk_overlap=400,
            similarity_threshold=0.8,
            reranking_enabled=False,
        )
        assert data.provider == "openai"
        assert data.temperature == 0.5

    def test_settings_create_defaults(self):
        """Test SettingsCreate uses defaults."""
        data = SettingsCreate()
        assert data.provider == "openai"
        assert data.model_name == "gpt-4o-mini"
        assert data.temperature == 0.7
        assert data.top_k == 5
        assert data.chunk_size == 1000
        assert data.chunk_overlap == 200

    def test_settings_update_partial(self):
        """Test SettingsUpdate with partial fields."""
        data = SettingsUpdate(temperature=0.9, top_k=20)
        assert data.temperature == 0.9
        assert data.top_k == 20
        assert data.provider is None
        assert data.model_name is None

    def test_temperature_validation(self):
        """Test temperature validation bounds."""
        # Valid
        SettingsCreate(temperature=0.0)
        SettingsCreate(temperature=1.0)
        SettingsCreate(temperature=2.0)

        # Invalid - too low
        with pytest.raises(ValueError):
            SettingsCreate(temperature=-0.1)

        # Invalid - too high
        with pytest.raises(ValueError):
            SettingsCreate(temperature=2.1)

    def test_top_k_validation(self):
        """Test top_k validation bounds."""
        SettingsCreate(top_k=1)
        SettingsCreate(top_k=100)

        with pytest.raises(ValueError):
            SettingsCreate(top_k=0)

        with pytest.raises(ValueError):
            SettingsCreate(top_k=101)

    def test_max_tokens_validation(self):
        """Test max_tokens validation bounds."""
        SettingsCreate(max_tokens=100)
        SettingsCreate(max_tokens=32000)

        with pytest.raises(ValueError):
            SettingsCreate(max_tokens=99)

        with pytest.raises(ValueError):
            SettingsCreate(max_tokens=32001)

    def test_chunk_size_validation(self):
        """Test chunk_size validation bounds."""
        SettingsCreate(chunk_size=128)
        SettingsCreate(chunk_size=4096)

        with pytest.raises(ValueError):
            SettingsCreate(chunk_size=127)

        with pytest.raises(ValueError):
            SettingsCreate(chunk_size=4097)

    def test_chunk_overlap_validation(self):
        """Test chunk_overlap validation bounds."""
        SettingsCreate(chunk_overlap=0)
        SettingsCreate(chunk_overlap=100)

        with pytest.raises(ValueError):
            SettingsCreate(chunk_overlap=-1)

    def test_chunk_overlap_less_than_chunk_size(self):
        """Test chunk_overlap must be less than chunk_size."""
        # Valid
        SettingsCreate(chunk_size=1000, chunk_overlap=200)
        SettingsCreate(chunk_size=500, chunk_overlap=499)

        # Invalid - overlap >= chunk_size
        with pytest.raises(ValueError):
            SettingsCreate(chunk_size=1000, chunk_overlap=1000)

        with pytest.raises(ValueError):
            SettingsCreate(chunk_size=1000, chunk_overlap=1500)

    def test_similarity_threshold_validation(self):
        """Test similarity_threshold validation bounds."""
        SettingsCreate(similarity_threshold=0.0)
        SettingsCreate(similarity_threshold=0.5)
        SettingsCreate(similarity_threshold=1.0)

        with pytest.raises(ValueError):
            SettingsCreate(similarity_threshold=-0.1)

        with pytest.raises(ValueError):
            SettingsCreate(similarity_threshold=1.1)

    def test_provider_validation(self):
        """Test provider validation."""
        valid_providers = [
            "openai",
            "anthropic",
            "ollama",
            "groq",
            "together",
            "custom",
        ]
        for p in valid_providers:
            SettingsCreate(provider=p)

        with pytest.raises(ValueError):
            SettingsCreate(provider="invalid_provider")

    def test_embedding_provider_validation(self):
        """Test embedding provider validation."""
        valid_providers = [
            "openai",
            "huggingface",
            "cohere",
            "voyage",
            "ollama",
            "custom",
        ]
        for p in valid_providers:
            SettingsCreate(embedding_provider=p)

        with pytest.raises(ValueError):
            SettingsCreate(embedding_provider="invalid_embedding")

    def test_model_name_not_empty(self):
        """Test model_name cannot be empty."""
        with pytest.raises(ValueError):
            SettingsCreate(model_name="")

        with pytest.raises(ValueError):
            SettingsCreate(model_name="   ")

    def test_embedding_model_not_empty(self):
        """Test embedding_model cannot be empty."""
        with pytest.raises(ValueError):
            SettingsCreate(embedding_model="")

        with pytest.raises(ValueError):
            SettingsCreate(embedding_model="   ")

    def test_settings_update_chunk_overlap_validation(self):
        """Test SettingsUpdate validates chunk_overlap < chunk_size."""
        # Valid when chunk_size not provided (can't validate cross-field)
        SettingsUpdate(chunk_overlap=500)

        # Valid when both provided and valid
        SettingsUpdate(chunk_size=1000, chunk_overlap=200)

        # Invalid when both provided and invalid
        with pytest.raises(ValueError):
            SettingsUpdate(chunk_size=500, chunk_overlap=500)


class TestSettingsService:
    """Tests for SettingsService business logic."""

    @pytest_asyncio.fixture
    async def service(self, db_session: AsyncSession) -> SettingsService:
        """Create settings service with test database."""
        return create_settings_service(db_session)

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create a test user."""
        from app.models.entities import User, UserRole
        from app.services.auth import hash_password
        import uuid

        user = User(
            id=uuid.uuid4(),
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

    @pytest.mark.asyncio
    async def test_get_settings_creates_defaults(
        self, service: SettingsService, test_user
    ):
        """Test get_settings creates defaults when none exist."""
        settings = await service.get_settings(test_user.id)

        assert isinstance(settings, SettingsResponse)
        assert settings.user_id == test_user.id
        assert settings.provider == DEFAULT_SETTINGS["provider"]
        assert settings.model_name == DEFAULT_SETTINGS["model_name"]
        assert settings.temperature == DEFAULT_SETTINGS["temperature"]
        assert settings.top_k == DEFAULT_SETTINGS["top_k"]
        assert settings.chunk_size == DEFAULT_SETTINGS["chunk_size"]
        assert settings.chunk_overlap == DEFAULT_SETTINGS["chunk_overlap"]

    @pytest.mark.asyncio
    async def test_get_settings_returns_existing(
        self, service: SettingsService, test_user, db_session
    ):
        """Test get_settings returns existing settings."""
        # Create custom settings
        from app.models.settings import LLMProvider

        custom = UserSettings(
            user_id=test_user.id,
            provider=LLMProvider.anthropic,
            model_name="claude-3-opus",
            temperature=0.5,
            top_k=10,
        )
        db_session.add(custom)
        await db_session.commit()

        settings = await service.get_settings(test_user.id)

        assert settings.provider == "anthropic"
        assert settings.model_name == "claude-3-opus"
        assert settings.temperature == 0.5
        assert settings.top_k == 10

    @pytest.mark.asyncio
    async def test_update_settings(self, service: SettingsService, test_user):
        """Test updating settings."""
        updates = SettingsUpdate(
            provider="anthropic",
            model_name="claude-3-sonnet",
            temperature=0.3,
            top_k=15,
        )

        updated = await service.update_settings(test_user.id, updates)

        assert updated.provider == "anthropic"
        assert updated.model_name == "claude-3-sonnet"
        assert updated.temperature == 0.3
        assert updated.top_k == 15
        # Unchanged fields remain default
        assert updated.max_tokens == DEFAULT_SETTINGS["max_tokens"]

    @pytest.mark.asyncio
    async def test_update_settings_partial(self, service: SettingsService, test_user):
        """Test partial settings update."""
        # First update
        await service.update_settings(test_user.id, SettingsUpdate(temperature=0.9))

        # Second update - only change top_k
        updated = await service.update_settings(test_user.id, SettingsUpdate(top_k=20))

        assert updated.temperature == 0.9  # Preserved
        assert updated.top_k == 20  # Changed

    @pytest.mark.asyncio
    async def test_update_settings_no_changes(
        self, service: SettingsService, test_user
    ):
        """Test update with no changes returns current settings."""
        updated = await service.update_settings(test_user.id, SettingsUpdate())

        assert updated.temperature == DEFAULT_SETTINGS["temperature"]

    @pytest.mark.asyncio
    async def test_update_settings_validation_error(
        self, service: SettingsService, test_user
    ):
        """Test update with invalid data raises validation error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await service.update_settings(
                test_user.id, SettingsUpdate(temperature=5.0)  # Invalid
            )

    @pytest.mark.asyncio
    async def test_update_settings_chunk_overlap_validation(
        self, service: SettingsService, test_user
    ):
        """Test update validates chunk_overlap < chunk_size."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await service.update_settings(
                test_user.id, SettingsUpdate(chunk_size=500, chunk_overlap=500)
            )

    @pytest.mark.asyncio
    async def test_update_settings_validates_existing_chunk_overlap(
        self, service: SettingsService, test_user
    ):
        """Test a partial chunk_size update preserves the overlap invariant."""
        with pytest.raises(SettingsValidationError):
            await service.update_settings(test_user.id, SettingsUpdate(chunk_size=128))

    @pytest.mark.asyncio
    async def test_reset_settings(
        self, service: SettingsService, test_user, db_session
    ):
        """Test resetting settings to defaults."""
        # Create custom settings
        custom = UserSettings(
            user_id=test_user.id,
            provider="anthropic",
            model_name="claude-3-opus",
            temperature=0.5,
        )
        db_session.add(custom)
        await db_session.commit()

        # Reset
        result = await service.reset_settings(test_user.id)

        assert isinstance(result, SettingsResetResponse)
        assert result.settings.provider == DEFAULT_SETTINGS["provider"]
        assert result.settings.model_name == DEFAULT_SETTINGS["model_name"]
        assert result.settings.temperature == DEFAULT_SETTINGS["temperature"]

    @pytest.mark.asyncio
    async def test_reset_settings_not_found(self, service: SettingsService, test_user):
        """Test reset on non-existent settings raises error."""
        # Don't create any settings
        with pytest.raises(SettingsNotFoundError):
            await service.reset_settings(test_user.id)

    @pytest.mark.asyncio
    async def test_validate_settings(self, service: SettingsService):
        """Test validate_settings method."""
        validated = service.validate_settings(
            SettingsCreate(
                provider="anthropic",
                temperature=0.5,
                top_k=10,
                chunk_size=2000,
                chunk_overlap=400,
            )
        )

        assert validated["provider"] == "anthropic"
        assert validated["temperature"] == 0.5
        assert validated["top_k"] == 10

    @pytest.mark.asyncio
    async def test_validate_settings_cross_field(self, service: SettingsService):
        """Test validate_settings catches cross-field issues."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            service.validate_settings(SettingsCreate(chunk_size=500, chunk_overlap=500))

    @pytest.mark.asyncio
    async def test_get_default_settings(self, service: SettingsService):
        """Test get_default_settings static method."""
        defaults = SettingsService.get_default_settings()

        assert defaults == DEFAULT_SETTINGS
        # Ensure it's a copy
        assert defaults is not DEFAULT_SETTINGS


class TestSettingsRepository:
    """Tests for SettingsRepository."""

    @pytest_asyncio.fixture
    async def repo(self, db_session: AsyncSession) -> SettingsRepository:
        """Create settings repository."""
        return SettingsRepository(db_session)

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create a test user."""
        from app.models.entities import User, UserRole
        from app.services.auth import hash_password
        import uuid

        user = User(
            id=uuid.uuid4(),
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

    @pytest.mark.asyncio
    async def test_get_by_user_id_not_found(self, repo: SettingsRepository, test_user):
        """Test get_by_user_id returns None when not found."""
        result = await repo.get_by_user_id(test_user.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_default(self, repo: SettingsRepository, test_user):
        """Test create_default creates settings with defaults."""
        settings = await repo.create_default(test_user.id)

        assert settings.user_id == test_user.id
        assert settings.provider.value == DEFAULT_SETTINGS["provider"]
        assert settings.model_name == DEFAULT_SETTINGS["model_name"]
        assert settings.temperature == DEFAULT_SETTINGS["temperature"]

    @pytest.mark.asyncio
    async def test_create_default_duplicate_raises(
        self, repo: SettingsRepository, test_user
    ):
        """Test create_default raises on duplicate."""
        await repo.create_default(test_user.id)

        with pytest.raises(Exception):  # IntegrityError
            await repo.create_default(test_user.id)

    @pytest.mark.asyncio
    async def test_get_or_create_creates_if_missing(
        self, repo: SettingsRepository, test_user
    ):
        """Test get_or_create creates if missing."""
        settings = await repo.get_or_create(test_user.id)
        assert settings is not None
        assert settings.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(
        self, repo: SettingsRepository, test_user, db_session
    ):
        """Test get_or_create returns existing."""
        from app.models.settings import LLMProvider

        custom = UserSettings(user_id=test_user.id, provider=LLMProvider.anthropic)
        db_session.add(custom)
        await db_session.commit()

        settings = await repo.get_or_create(test_user.id)
        assert settings.provider.value == "anthropic"

    @pytest.mark.asyncio
    async def test_update_settings(
        self, repo: SettingsRepository, test_user, db_session
    ):
        """Test update_settings."""
        # Create initial
        await repo.create_default(test_user.id)

        # Update
        updated = await repo.update_settings(
            test_user.id, {"temperature": 0.9, "top_k": 20}
        )

        assert updated is not None
        assert updated.temperature == 0.9
        assert updated.top_k == 20

    @pytest.mark.asyncio
    async def test_update_settings_not_found(self, repo: SettingsRepository, test_user):
        """Test update_settings returns None if not found."""
        result = await repo.update_settings(test_user.id, {"temperature": 0.9})
        assert result is None

    @pytest.mark.asyncio
    async def test_reset_to_defaults(
        self, repo: SettingsRepository, test_user, db_session
    ):
        """Test reset_to_defaults."""
        # Create custom settings
        from app.models.settings import LLMProvider

        custom = UserSettings(
            user_id=test_user.id,
            provider=LLMProvider.anthropic,
            model_name="claude-3-opus",
            temperature=0.5,
        )
        db_session.add(custom)
        await db_session.commit()

        # Reset
        settings = await repo.reset_to_defaults(test_user.id)

        assert settings is not None
        assert settings.provider.value == DEFAULT_SETTINGS["provider"]
        assert settings.temperature == DEFAULT_SETTINGS["temperature"]

    @pytest.mark.asyncio
    async def test_reset_to_defaults_not_found(
        self, repo: SettingsRepository, test_user
    ):
        """Test reset_to_defaults returns None if not found."""
        result = await repo.reset_to_defaults(test_user.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, repo: SettingsRepository, test_user, db_session):
        """Test delete settings."""
        await repo.create_default(test_user.id)

        deleted = await repo.delete_by_user_id(test_user.id)
        assert deleted is True

        # Verify deleted
        result = await repo.get_by_user_id(test_user.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo: SettingsRepository, test_user):
        """Test delete returns False if not found."""
        deleted = await repo.delete_by_user_id(test_user.id)
        assert deleted is False


class TestSettingsAPI:
    """Tests for Settings API endpoints."""

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create a test user."""
        from app.models.entities import User, UserRole
        from app.services.auth import hash_password
        import uuid

        user = User(
            id=uuid.uuid4(),
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

    @pytest.fixture
    def auth_client(self, client: TestClient, test_user) -> TestClient:
        """Create authenticated client."""
        from app.services.auth import create_access_token

        token = create_access_token(test_user.id, role=test_user.role, auth_version=test_user.auth_version)
        client.headers = {"Authorization": f"Bearer {token}"}
        return client

    def test_get_settings_success(self, auth_client: TestClient, test_user):
        """Test GET /settings returns settings."""
        response = auth_client.get("/api/v1/settings")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["provider"] == DEFAULT_SETTINGS["provider"]
        assert data["temperature"] == DEFAULT_SETTINGS["temperature"]

    def test_get_settings_creates_defaults(self, auth_client: TestClient, test_user):
        """Test GET /settings creates defaults if missing."""
        response = auth_client.get("/api/v1/settings")
        assert response.status_code == 200

        data = response.json()
        assert data["provider"] == DEFAULT_SETTINGS["provider"]
        assert data["model_name"] == DEFAULT_SETTINGS["model_name"]
        assert data["temperature"] == DEFAULT_SETTINGS["temperature"]

    def test_update_settings_success(self, auth_client: TestClient, test_user):
        """Test PUT /settings updates settings."""
        updates = {
            "provider": "anthropic",
            "model_name": "claude-3-sonnet",
            "temperature": 0.5,
            "top_k": 10,
        }
        response = auth_client.put("/api/v1/settings", json=updates)

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "anthropic"
        assert data["model_name"] == "claude-3-sonnet"
        assert data["temperature"] == 0.5
        assert data["top_k"] == 10

    def test_update_settings_partial(self, auth_client: TestClient, test_user):
        """Test PUT /settings with partial updates."""
        # First update
        auth_client.put("/api/v1/settings", json={"temperature": 0.9})

        # Second update - only top_k
        response = auth_client.put("/api/v1/settings", json={"top_k": 20})

        assert response.status_code == 200
        data = response.json()
        assert data["temperature"] == 0.9  # Preserved
        assert data["top_k"] == 20  # Changed

    def test_update_settings_empty(self, auth_client: TestClient, test_user):
        """Test PUT /settings with empty body returns current."""
        response = auth_client.put("/api/v1/settings", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["temperature"] == DEFAULT_SETTINGS["temperature"]

    def test_update_settings_invalid_temperature(
        self, auth_client: TestClient, test_user
    ):
        """Test PUT /settings rejects invalid temperature."""
        response = auth_client.put("/api/v1/settings", json={"temperature": 5.0})

        assert response.status_code == 422
        error_data = response.json()
        assert "error" in error_data
        assert "details" in error_data["error"]
        errors = error_data["error"]["details"].get("errors", [])
        assert any("temperature" in e.get("field", "").lower() for e in errors)

    def test_update_settings_invalid_top_k(self, auth_client: TestClient, test_user):
        """Test PUT /settings rejects invalid top_k."""
        response = auth_client.put("/api/v1/settings", json={"top_k": 150})

        assert response.status_code == 422
        error_data = response.json()
        assert "error" in error_data
        assert "details" in error_data["error"]
        errors = error_data["error"]["details"].get("errors", [])
        assert any("top_k" in e.get("field", "").lower() for e in errors)

    def test_update_settings_invalid_max_tokens(
        self, auth_client: TestClient, test_user
    ):
        """Test PUT /settings rejects invalid max_tokens."""
        response = auth_client.put("/api/v1/settings", json={"max_tokens": 50000})

        assert response.status_code == 422

    def test_update_settings_invalid_chunk_size(
        self, auth_client: TestClient, test_user
    ):
        """Test PUT /settings rejects invalid chunk_size."""
        response = auth_client.put("/api/v1/settings", json={"chunk_size": 5000})

        assert response.status_code == 422

    def test_update_settings_chunk_overlap_validation(
        self, auth_client: TestClient, test_user
    ):
        """Test PUT /settings rejects chunk_overlap >= chunk_size."""
        response = auth_client.put(
            "/api/v1/settings", json={"chunk_size": 500, "chunk_overlap": 500}
        )

        assert response.status_code == 422
        error_data = response.json()
        assert "error" in error_data
        assert "details" in error_data["error"]
        errors = error_data["error"]["details"].get("errors", [])
        assert any("chunk_overlap" in e.get("field", "").lower() for e in errors)

    def test_update_settings_invalid_provider(self, auth_client: TestClient, test_user):
        """Test PUT /settings rejects invalid provider."""
        response = auth_client.put("/api/v1/settings", json={"provider": "invalid"})

        assert response.status_code == 422

    def test_update_settings_invalid_embedding_provider(
        self, auth_client: TestClient, test_user
    ):
        """Test PUT /settings rejects invalid embedding provider."""
        response = auth_client.put(
            "/api/v1/settings", json={"embedding_provider": "invalid"}
        )

        assert response.status_code == 422

    def test_update_settings_invalid_similarity_threshold(
        self, auth_client: TestClient, test_user
    ):
        """Test PUT /settings rejects invalid similarity_threshold."""
        response = auth_client.put(
            "/api/v1/settings", json={"similarity_threshold": 1.5}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reset_settings_success(
        self, auth_client: TestClient, test_user, db_session
    ):
        """Test POST /settings/reset resets to defaults."""
        # First set custom settings
        from app.models.settings import LLMProvider

        custom = UserSettings(
            user_id=test_user.id,
            provider=LLMProvider.anthropic,
            model_name="claude-3-opus",
            temperature=0.3,
        )
        db_session.add(custom)
        await db_session.commit()

        response = auth_client.post("/api/v1/settings/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Settings reset to defaults successfully"
        assert data["settings"]["provider"] == DEFAULT_SETTINGS["provider"]
        assert data["settings"]["model_name"] == DEFAULT_SETTINGS["model_name"]
        assert data["settings"]["temperature"] == DEFAULT_SETTINGS["temperature"]

    def test_reset_settings_not_found(self, auth_client: TestClient, test_user):
        """Test POST /settings/reset fails if no settings exist."""
        # Don't create settings
        response = auth_client.post("/api/v1/settings/reset")

        assert response.status_code == 404

    def test_settings_requires_auth(self, client: TestClient):
        """Test settings endpoints require authentication."""
        response = client.get("/api/v1/settings")
        assert response.status_code == 401

        response = client.put("/api/v1/settings", json={"temperature": 0.5})
        assert response.status_code == 401

        response = client.post("/api/v1/settings/reset")
        assert response.status_code == 401


class TestSettingsEdgeCases:
    """Edge case tests for settings."""

    @pytest.mark.asyncio
    async def test_settings_model_repr(self, db_session: AsyncSession):
        """Test UserSettings __repr__."""
        from app.models.entities import User, UserRole
        from app.models.settings import LLMProvider
        from app.services.auth import hash_password
        import uuid

        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            password_hash=hash_password("testpassword"),
            role=UserRole.user,
        )
        db_session.add(user)
        await db_session.commit()

        settings = UserSettings(
            user_id=user.id, provider=LLMProvider.openai, model_name="gpt-4"
        )
        repr_str = repr(settings)
        assert "UserSettings" in repr_str
        assert str(user.id) in repr_str
        assert "openai" in repr_str
        assert "gpt-4" in repr_str

    @pytest.mark.asyncio
    async def test_settings_enum_values(self):
        """Test enum values are correct."""
        from app.models.settings import LLMProvider, EmbeddingProvider

        assert LLMProvider.openai.value == "openai"
        assert LLMProvider.anthropic.value == "anthropic"
        assert LLMProvider.ollama.value == "ollama"

        assert EmbeddingProvider.openai.value == "openai"
        assert EmbeddingProvider.huggingface.value == "huggingface"
        assert EmbeddingProvider.cohere.value == "cohere"
