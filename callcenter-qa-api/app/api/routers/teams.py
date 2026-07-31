import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.auth.permissions import TEAMS_MANAGE
from app.database import get_db
from app.schemas.team import TeamCreate, TeamRead, TeamUpdate
from app.teams import service

router = APIRouter(prefix="/api/v1/teams", tags=["teams"], dependencies=[Depends(get_current_user)])
_require_teams_manage = Depends(require_permission(TEAMS_MANAGE))


@router.get("", response_model=list[TeamRead])
async def list_teams(db: AsyncSession = Depends(get_db)):
    return await service.list_teams(db)


@router.post("", response_model=TeamRead, status_code=201, dependencies=[_require_teams_manage])
async def create_team(data: TeamCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_team(db, data)


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(team_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    team = await service.get_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.patch("/{team_id}", response_model=TeamRead, dependencies=[_require_teams_manage])
async def update_team(team_id: uuid.UUID, data: TeamUpdate, db: AsyncSession = Depends(get_db)):
    team = await service.update_team(db, team_id, data)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team
