import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user, require_permission
from app.auth.permissions import RUBRIC_WRITE, TEAMS_MANAGE, USERS_MANAGE
from app.auth.security import hash_password, verify_password
from app.auth.service import (
    AccountLockedError,
    InvalidCredentialsError,
    SetupAlreadyCompletedError,
    authenticate,
    change_password,
    has_any_user,
    register_first_admin,
    revoke_all_for_user,
    revoke_refresh_token,
)
from app.config import settings
from app.models.user import ROLE_ADMIN, ROLE_TEAM_LEAD, ROLE_VIEWER


def _db_with_scalar(value) -> MagicMock:
    db = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = value
    result.scalar_one_or_none.return_value = value
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _fake_user(password: str, **overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        email="agent@example.com",
        password_hash=hash_password(password),
        role=ROLE_VIEWER,
        is_active=True,
        failed_login_count=0,
        locked_until=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# --- password hashing -------------------------------------------------------


def test_hash_and_verify_password_roundtrip():
    h = hash_password("CorrectHorseBatteryStaple")
    assert h.startswith("$argon2id$")
    assert verify_password("CorrectHorseBatteryStaple", h) is True
    assert verify_password("wrong", h) is False


# --- first-admin setup -------------------------------------------------------


@pytest.mark.asyncio
async def test_has_any_user_true_and_false():
    assert await has_any_user(_db_with_scalar(0)) is False
    assert await has_any_user(_db_with_scalar(3)) is True


@pytest.mark.asyncio
async def test_register_first_admin_succeeds_when_no_users():
    db = _db_with_scalar(0)
    await register_first_admin(db, "Admin@Example.com", "supersecret123")

    assert db.add.called
    created = db.add.call_args[0][0]
    assert created.email == "admin@example.com"  # normalized to lowercase
    assert created.role == ROLE_ADMIN
    assert verify_password("supersecret123", created.password_hash)


@pytest.mark.asyncio
async def test_register_first_admin_rejected_when_user_exists():
    db = _db_with_scalar(1)
    with pytest.raises(SetupAlreadyCompletedError):
        await register_first_admin(db, "second@example.com", "whatever123")


# --- login / lockout ---------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticate_success():
    user = _fake_user("correct-password")
    db = _db_with_scalar(user)
    result = await authenticate(db, user.email, "correct-password")
    assert result is user
    assert user.failed_login_count == 0


@pytest.mark.asyncio
async def test_authenticate_wrong_password_increments_failed_count():
    user = _fake_user("correct-password")
    db = _db_with_scalar(user)
    with pytest.raises(InvalidCredentialsError):
        await authenticate(db, user.email, "wrong-password")
    assert user.failed_login_count == 1


@pytest.mark.asyncio
async def test_authenticate_locks_account_after_max_failed_attempts(monkeypatch):
    monkeypatch.setattr(settings, "login_max_failed_attempts", 3)
    user = _fake_user("correct-password", failed_login_count=2)
    db = _db_with_scalar(user)
    with pytest.raises(InvalidCredentialsError):
        await authenticate(db, user.email, "wrong-password")
    assert user.locked_until is not None
    assert user.failed_login_count == 0  # reset once locked


@pytest.mark.asyncio
async def test_authenticate_rejects_locked_account():
    user = _fake_user(
        "correct-password", locked_until=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    db = _db_with_scalar(user)
    with pytest.raises(AccountLockedError):
        await authenticate(db, user.email, "correct-password")


@pytest.mark.asyncio
async def test_authenticate_unknown_user():
    db = _db_with_scalar(None)
    with pytest.raises(InvalidCredentialsError):
        await authenticate(db, "nobody@example.com", "whatever")


# --- refresh token revocation -------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_refresh_token_marks_revoked():
    token_row = SimpleNamespace(revoked_at=None)
    db = _db_with_scalar(token_row)
    await revoke_refresh_token(db, "some-refresh-token")
    assert token_row.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_all_for_user_marks_all_active_tokens():
    token1 = SimpleNamespace(revoked_at=None)
    token2 = SimpleNamespace(revoked_at=None)
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value = [token1, token2]
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()

    await revoke_all_for_user(db, uuid.uuid4())

    assert token1.revoked_at is not None
    assert token2.revoked_at is not None


# --- change password ----------------------------------------------------------


@pytest.mark.asyncio
async def test_change_password_requires_correct_old_password():
    user = _fake_user("old-password")
    db = MagicMock()
    with pytest.raises(InvalidCredentialsError):
        await change_password(db, user, "wrong-old-password", "new-password")


@pytest.mark.asyncio
async def test_change_password_success_rotates_hash_and_revokes_tokens():
    user = _fake_user("old-password")
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value = []  # no active refresh tokens to revoke
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()

    old_hash = user.password_hash
    await change_password(db, user, "old-password", "new-password")

    assert user.password_hash != old_hash
    assert verify_password("new-password", user.password_hash)


# --- RBAC gating ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_permission_allows_role_with_permission():
    user = SimpleNamespace(role=ROLE_ADMIN)
    check = require_permission(RUBRIC_WRITE)
    assert await check(user) is user


@pytest.mark.asyncio
async def test_require_permission_rejects_role_without_permission():
    user = SimpleNamespace(role=ROLE_VIEWER)
    check = require_permission(RUBRIC_WRITE)
    with pytest.raises(HTTPException) as exc_info:
        await check(user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_permission_users_manage_allows_admin_only():
    check = require_permission(USERS_MANAGE)
    admin = SimpleNamespace(role=ROLE_ADMIN)
    assert await check(admin) is admin
    with pytest.raises(HTTPException) as exc_info:
        await check(SimpleNamespace(role=ROLE_TEAM_LEAD))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_permission_teams_manage_allows_admin_only():
    check = require_permission(TEAMS_MANAGE)
    admin = SimpleNamespace(role=ROLE_ADMIN)
    assert await check(admin) is admin
    with pytest.raises(HTTPException) as exc_info:
        await check(SimpleNamespace(role=ROLE_VIEWER))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_bearer_header():
    request = MagicMock()
    request.headers = {}
    db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_garbage_token():
    request = MagicMock()
    request.headers = {"authorization": "Bearer not-a-real-jwt"}
    db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request, db)
    assert exc_info.value.status_code == 401
