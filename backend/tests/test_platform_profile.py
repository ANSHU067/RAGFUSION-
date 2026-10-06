"""Profile ownership, branding compatibility, UTC persistence, and chat continuation."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from alembic import command
from sqlalchemy import select, text, func

from app.config.settings import Settings
from app.core.environment import SecurityEnvironment
from app.models.entities import User, ChatSession, Message, MessageRole
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.services.memory_service import MemoryService
from test_batch2_integrity import database, owner, migration_config


def test_profile_patch_persists_and_preserves_session(client, auth_headers):
    response = client.patch('/api/v1/auth/me', headers=auth_headers, json={
        'full_name': '  Ada Stone  ', 'bio': 'Researcher', 'workspace': 'Ocean research', 'avatar_color': 'indigo',
    })
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated['display_name'] == 'Ada Stone' and updated['avatar_color'] == 'indigo'
    assert 'password_hash' not in updated and 'auth_version' not in updated
    fetched = client.get('/api/v1/auth/me', headers=auth_headers)
    assert fetched.status_code == 200 and fetched.json()['bio'] == 'Researcher'
    partial = client.patch('/api/v1/auth/me', headers=auth_headers, json={'bio': None})
    assert partial.json()['bio'] is None and partial.json()['workspace'] == 'Ocean research'
    assert partial.json()['avatar_color'] == 'indigo'


@pytest.mark.parametrize('payload', [
    {'role': 'admin'}, {'email': 'other@example.invalid'}, {'auth_version': 0}, {'id': 'another-user'},
    {'display_name': ''}, {'display_name': '  '}, {'name': None}, {'display_name': 'a' * 121},
    {'bio': 'x' * 1001}, {'workspace': 'x' * 121}, {'avatar_color': 'url(http://private)'},
])
def test_profile_rejects_unsafe_or_invalid_fields(client, auth_headers, payload):
    response = client.patch('/api/v1/auth/me', headers=auth_headers, json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()['error']['details']['errors'], list)


async def test_profile_update_only_changes_authenticated_owner(client, auth_headers, test_user, db_session):
    other = User(email='profile-other@example.invalid', display_name='Unchanged')
    db_session.add(other)
    await db_session.commit()
    version = test_user.auth_version
    assert client.patch('/api/v1/auth/me', json={'name': 'Anonymous'}).status_code == 401
    assert client.patch('/api/v1/auth/me', headers=auth_headers, json={'name': 'Updated'}).status_code == 200
    await db_session.refresh(other)
    await db_session.refresh(test_user)
    assert other.display_name == 'Unchanged'
    assert test_user.display_name == 'Updated' and test_user.auth_version == version


async def test_profile_migration_preserves_existing_users(database, owner):
    config = migration_config(database.migration_url)
    await asyncio.to_thread(command.downgrade, config, '20261005_0002')
    await asyncio.to_thread(command.upgrade, config, 'head')
    async with database.factory() as db:
        user = await db.get(User, owner.id)
        assert user.avatar_color == 'slate' and user.bio is None and user.workspace is None
        assert user.auth_version == owner.auth_version


async def test_messages_reload_as_utc_and_continue_existing_session(client, auth_headers, db_session, test_user, monkeypatch):
    session = ChatSession(user_id=test_user.id, title='A long conversation')
    db_session.add(session)
    await db_session.flush()
    base = datetime(2026, 10, 4, 10, tzinfo=timezone.utc)
    db_session.add_all([Message(chat_session_id=session.id, role=MessageRole.user, content=f'Turn {number}',
                               created_at=base + timedelta(seconds=number)) for number in range(105)])
    await db_session.commit()
    first = client.get(f'/api/v1/chat/sessions/{session.id}', headers=auth_headers).json()
    second = client.get(f'/api/v1/chat/sessions/{session.id}?offset=100', headers=auth_headers).json()
    assert first['session']['message_count'] == 105
    assert len(first['messages']) == 100 and len(second['messages']) == 5
    assert second['messages'][-1]['content'] == 'Turn 104'
    assert datetime.fromisoformat(first['messages'][0]['created_at'].replace('Z', '+00:00')).utcoffset() == timedelta(0)
    monkeypatch.setattr(ChatService, '_run_rag_pipeline', AsyncMock(return_value={'response': 'Continuing the same conversation', 'citations': [], 'token_usage': None}))
    response = client.post('/api/v1/chat', headers=auth_headers, json={'chat_session_id': str(session.id), 'message': 'Continue this discussion'})
    assert response.status_code == 200, response.text
    assert response.json()['session_id'] == str(session.id)
    assert await db_session.scalar(select(func.count()).select_from(ChatSession).where(ChatSession.user_id == test_user.id)) == 1
    memory = MemoryService(db_session)
    assert await memory.get_message_count(session.id) == 107
    last = (await memory.get_messages(session.id, offset=105))[-1]
    assert last.created_at.tzinfo is not None and last.created_at.utcoffset() == timedelta(0)


def test_canonical_environment_overrides_legacy_without_dropping_secrets(monkeypatch):
    monkeypatch.setenv('DOCPRO_JWT_SECRET_KEY', 'existing-private-secret')
    monkeypatch.setenv('DOCPRO_APP_NAME', 'DOCPRO V2 API')
    legacy = Settings(_env_file=None)
    assert legacy.jwt_secret_key == 'existing-private-secret'
    assert legacy.app_name == 'RAGFUSION API'
    monkeypatch.setenv('RAGFUSION_JWT_SECRET_KEY', 'new-explicit-secret')
    monkeypatch.setenv('RAGFUSION_DATABASE_URL', 'sqlite+aiosqlite:///canonical.db')
    assert Settings(_env_file=None).jwt_secret_key == 'new-explicit-secret'
    assert Settings(_env_file=None).database_url.endswith('canonical.db')
    assert SecurityEnvironment.from_environment().jwt_secret == 'new-explicit-secret'


def test_chat_session_aliases_are_compatible_but_not_ambiguous(test_user):
    from pydantic import ValidationError
    assert ChatRequest(message='Continue', chat_session_id=test_user.id).session_id == test_user.id
    assert ChatRequest(message='Continue', session_id=test_user.id).session_id == test_user.id
    with pytest.raises(ValidationError):
        ChatRequest(message='Continue', chat_session_id=test_user.id, session_id=None)
