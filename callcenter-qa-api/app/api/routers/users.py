import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.auth.permissions import USERS_MANAGE
from app.database import get_db
from app.schemas.auth import UserRead
from app.schemas.user import UserCreate, UserUpdate
from app.users import service

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(get_current_user), Depends(require_permission(USERS_MANAGE))],
)


@router.get("", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db)):
    return await service.list_users(db)


@router.post("", response_model=UserRead, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await service.create_user(db, data)
    except service.EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=409, detail="A user with this email already exists"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: uuid.UUID, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    try:
        user = await service.update_user(db, user_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
