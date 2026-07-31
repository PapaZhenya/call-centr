from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service as auth_service
from app.auth.service import AccountLockedError, InvalidCredentialsError, SetupAlreadyCompletedError
from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SetupRequest,
    TokenResponse,
    UserRead,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/setup-required")
async def setup_required(db: AsyncSession = Depends(get_db)):
    return {"setup_required": not await auth_service.has_any_user(db)}


@router.post("/setup", response_model=TokenResponse, status_code=201)
async def setup(data: SetupRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.register_first_admin(db, data.email, data.password)
    except SetupAlreadyCompletedError as exc:
        raise HTTPException(
            status_code=409, detail="Setup already completed - an admin account exists"
        ) from exc
    access_token, refresh_token = await auth_service.issue_tokens(db, user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip_address = request.client.host if request.client else None
    try:
        user = await auth_service.authenticate(db, data.email, data.password, ip_address)
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=423, detail=f"Account locked until {exc.locked_until.isoformat()}"
        ) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail="Invalid email or password") from exc

    access_token, refresh_token = await auth_service.issue_tokens(db, user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        access_token, refresh_token = await auth_service.refresh_access_token(
            db, data.refresh_token
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from exc
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
async def logout(data: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.revoke_refresh_token(db, data.refresh_token)


@router.post("/logout-all", status_code=204)
async def logout_all(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    await auth_service.revoke_all_for_user(db, user.id)


@router.post("/change-password", status_code=204)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        await auth_service.change_password(db, user, data.old_password, data.new_password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail="Old password is incorrect") from exc


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)):
    return user
