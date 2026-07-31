import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.schemas.team import TeamCreate, TeamUpdate


async def create_team(db: AsyncSession, data: TeamCreate) -> Team:
    team = Team(**data.model_dump())
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


async def list_teams(db: AsyncSession) -> list[Team]:
    result = await db.execute(select(Team).order_by(Team.name))
    return list(result.scalars().all())


async def get_team(db: AsyncSession, team_id: uuid.UUID) -> Team | None:
    return await db.get(Team, team_id)


async def update_team(db: AsyncSession, team_id: uuid.UUID, data: TeamUpdate) -> Team | None:
    team = await db.get(Team, team_id)
    if team is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    await db.commit()
    await db.refresh(team)
    return team
