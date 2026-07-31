import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.security import verify_password
from app.models.user import ROLE_AGENT, ROLE_TEAM_LEAD
from app.schemas.user import UserCreate, UserUpdate
from app.users.service import EmailAlreadyExistsError, create_user, update_user


def _db_with_scalar(value) -> MagicMock:
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_normalizes_email():
    db = _db_with_scalar(None)
    team_id = uuid.uuid4()
    data = UserCreate(
        email="Agent@Example.com", password="supersecret123", role=ROLE_AGENT, team_id=team_id
    )

    user = await create_user(db, data)

    assert db.add.called
    added = db.add.call_args[0][0]
    assert added.email == "agent@example.com"
    assert added.role == ROLE_AGENT
    assert added.team_id == team_id
    assert verify_password("supersecret123", added.password_hash)
    assert user is added


@pytest.mark.asyncio
async def test_create_user_rejects_unknown_role():
    db = _db_with_scalar(None)
    data = UserCreate(email="x@example.com", password="supersecret123", role="not-a-real-role")
    with pytest.raises(ValueError):
        await create_user(db, data)
    assert not db.add.called


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email():
    db = _db_with_scalar(SimpleNamespace(email="dupe@example.com"))
    data = UserCreate(email="dupe@example.com", password="supersecret123", role=ROLE_AGENT)
    with pytest.raises(EmailAlreadyExistsError):
        await create_user(db, data)
    assert not db.add.called


@pytest.mark.asyncio
async def test_update_user_applies_only_provided_fields():
    team_id = uuid.uuid4()
    existing = SimpleNamespace(role=ROLE_AGENT, team_id=None, agent_id=None, is_active=True)
    db = MagicMock()
    db.get = AsyncMock(return_value=existing)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = await update_user(db, uuid.uuid4(), UserUpdate(team_id=team_id))

    assert result is existing
    assert existing.team_id == team_id
    assert existing.role == ROLE_AGENT  # untouched


@pytest.mark.asyncio
async def test_update_user_rejects_unknown_role():
    existing = SimpleNamespace(role=ROLE_AGENT, team_id=None, agent_id=None, is_active=True)
    db = MagicMock()
    db.get = AsyncMock(return_value=existing)
    with pytest.raises(ValueError):
        await update_user(db, uuid.uuid4(), UserUpdate(role="not-a-real-role"))


@pytest.mark.asyncio
async def test_update_user_can_change_role_and_deactivate():
    existing = SimpleNamespace(role=ROLE_AGENT, team_id=None, agent_id=None, is_active=True)
    db = MagicMock()
    db.get = AsyncMock(return_value=existing)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = await update_user(db, uuid.uuid4(), UserUpdate(role=ROLE_TEAM_LEAD, is_active=False))

    assert result.role == ROLE_TEAM_LEAD
    assert result.is_active is False


@pytest.mark.asyncio
async def test_update_user_returns_none_when_not_found():
    db = MagicMock()
    db.get = AsyncMock(return_value=None)
    result = await update_user(db, uuid.uuid4(), UserUpdate(role=ROLE_TEAM_LEAD))
    assert result is None
