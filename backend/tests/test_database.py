"""Database integration tests using a disposable async SQLite file."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import check_database_connection, transactional_session
from app.models.base import Base
from app.models.entities import MessageRole
from app.repositories import (
    ChatSessionRepository,
    DocumentRepository,
    EmbeddingRepository,
    MessageRepository,
    SettingRepository,
    UserRepository,
    WebsiteRepository,
    YouTubeSourceRepository,
)


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'database.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_async_connection(tmp_path) -> None:
    assert await check_database_connection(
        f"sqlite+aiosqlite:///{tmp_path / 'connection.db'}"
    )


@pytest.mark.asyncio
async def test_repositories_crud_and_relationships(session_factory) -> None:
    async with session_factory() as session:
        users = UserRepository(session)
        user = await users.create(email="ada@example.com", display_name="Ada")
        document = await DocumentRepository(session).create(
            user_id=user.id,
            filename="guide.pdf",
            storage_key="users/ada/guide.pdf",
            metadata_={"pages": 2},
        )
        website = await WebsiteRepository(session).create(
            user_id=user.id, url="https://example.test", metadata_={}
        )
        source = await YouTubeSourceRepository(session).create(
            user_id=user.id,
            video_id="abc123",
            url="https://youtube.com/watch?v=abc123",
            metadata_={},
        )
        chat = await ChatSessionRepository(session).create(
            user_id=user.id, title="Questions"
        )
        message = await MessageRepository(session).create(
            chat_session_id=chat.id, role=MessageRole.user, content="Summarize this"
        )
        setting = await SettingRepository(session).create(
            user_id=user.id, key="model", value="text-embedding-3-small"
        )
        embedding = await EmbeddingRepository(session).create(
            document_id=document.id,
            chunk_index=0,
            content="First chunk",
            vector=[0.1, 0.2],
            model_name="text-embedding-3-small",
            metadata_={},
        )
        await session.commit()

        found_user = await users.by_email("ada@example.com")
        assert found_user is not None
        assert found_user.id == user.id
        assert [
            item.id for item in await DocumentRepository(session).for_user(user.id)
        ] == [document.id]
        found_website = await WebsiteRepository(session).get(website.id)
        assert found_website is not None
        assert found_website.url == "https://example.test"
        found_source = await YouTubeSourceRepository(session).get(source.id)
        assert found_source is not None
        assert found_source.video_id == "abc123"
        assert [
            item.id for item in await MessageRepository(session).for_chat(chat.id)
        ] == [message.id]
        found_setting = await SettingRepository(session).get_value(user.id, "model")
        assert found_setting is not None
        assert found_setting.id == setting.id
        found_embedding = await EmbeddingRepository(session).get(embedding.id)
        assert found_embedding is not None
        assert found_embedding.vector == [
            0.1,
            0.2,
        ]

        await users.update(user, display_name="Ada Lovelace")
        await users.delete(user)
        await session.commit()
        assert await users.get(user.id) is None


@pytest.mark.asyncio
async def test_transactional_session_rolls_back(tmp_path) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path / 'rollback.db'}"
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    with pytest.raises(RuntimeError):
        async with transactional_session(url) as session:
            await UserRepository(session).create(email="rollback@example.com")
            raise RuntimeError("force rollback")

    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        assert await UserRepository(session).by_email("rollback@example.com") is None
    await engine.dispose()
