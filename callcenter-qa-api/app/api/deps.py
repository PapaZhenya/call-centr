import uuid
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import has_permission
from app.auth.security import decode_access_token
from app.config import settings
from app.database import get_db
from app.ingestion.storage import LocalDiskStorage, StorageBackend
from app.models.user import User


@lru_cache
def get_storage() -> StorageBackend:
    return LocalDiskStorage(settings.audio_storage_path)


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


def require_permission(permission: str):
    """FastAPI dependency factory: 403s unless the current user's role grants
    `permission` per app/auth/permissions.py. Use this instead of checking
    `user.role` directly - see that module for why."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return user

    return _check
