import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.config import settings
from app.models.user import ROLE_ADMIN, LoginAttempt, RefreshToken, User


class AuthError(Exception):
    """Base class for auth failures the router translates into HTTP errors."""


class SetupAlreadyCompletedError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class AccountLockedError(AuthError):
    def __init__(self, locked_until: datetime):
        self.locked_until = locked_until


async def has_any_user(db: AsyncSession) -> bool:
    result = await db.execute(select(func.count(User.id)))
    return (result.scalar_one() or 0) > 0


async def register_first_admin(db: AsyncSession, email: str, password: str) -> User:
    if await has_any_user(db):
        raise SetupAlreadyCompletedError()
    user = User(email=email.lower(), password_hash=hash_password(password), role=ROLE_ADMIN)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _log_attempt(db: AsyncSession, email: str, success: bool, ip_address: str | None) -> None:
    db.add(LoginAttempt(email=email.lower(), success=success, ip_address=ip_address))
    await db.commit()


async def authenticate(
    db: AsyncSession, email: str, password: str, ip_address: str | None = None
) -> User:
    email = email.lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if user is None or not user.is_active:
        await _log_attempt(db, email, False, ip_address)
        raise InvalidCredentialsError()

    if user.locked_until is not None and user.locked_until > now:
        await _log_attempt(db, email, False, ip_address)
        raise AccountLockedError(user.locked_until)

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.login_max_failed_attempts:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_count = 0
        await db.commit()
        await _log_attempt(db, email, False, ip_address)
        raise InvalidCredentialsError()

    user.failed_login_count = 0
    user.locked_until = None
    await db.commit()
    await _log_attempt(db, email, True, ip_address)
    return user


async def issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    access_token = create_access_token(str(user.id), user.role)
    refresh_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_ttl_days)
    db.add(
        RefreshToken(
            user_id=user.id, token_hash=hash_refresh_token(refresh_token), expires_at=expires_at
        )
    )
    await db.commit()
    return access_token, refresh_token


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    token_hash = hash_refresh_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token_row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if token_row is None or token_row.revoked_at is not None or token_row.expires_at < now:
        raise InvalidCredentialsError()

    user = await db.get(User, token_row.user_id)
    if user is None or not user.is_active:
        raise InvalidCredentialsError()

    # Rotate: revoke the presented token, issue a fresh pair. A reused
    # (already-revoked) refresh token is rejected above, catching replay.
    token_row.revoked_at = now
    await db.commit()
    return await issue_tokens(db, user)


async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token_row = result.scalar_one_or_none()
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(timezone.utc)
        await db.commit()


async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
    )
    for token_row in result.scalars():
        token_row.revoked_at = now
    await db.commit()


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash):
        raise InvalidCredentialsError()
    user.password_hash = hash_password(new_password)
    await db.commit()
    await revoke_all_for_user(db, user.id)  # force re-login on every device
