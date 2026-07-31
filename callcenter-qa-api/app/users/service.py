import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.models.user import ALL_ROLES, User
from app.schemas.user import UserCreate, UserUpdate


class EmailAlreadyExistsError(Exception):
    pass


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    role = data.validated_role()
    email = data.email.lower()

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise EmailAlreadyExistsError()

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        role=role,
        team_id=data.team_id,
        agent_id=data.agent_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.email))
    return list(result.scalars().all())


async def update_user(db: AsyncSession, user_id: uuid.UUID, data: UserUpdate) -> User | None:
    user = await db.get(User, user_id)
    if user is None:
        return None

    updates = data.model_dump(exclude_unset=True)
    if updates.get("role") is not None and updates["role"] not in ALL_ROLES:
        raise ValueError(f"Unknown role: {updates['role']!r}. Must be one of {ALL_ROLES}")

    for field, value in updates.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
