import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import queries
from app.api.deps import get_current_user
from app.auth.scoping import ScopeDenied, analytics_scope, check_agent_in_analytics_scope
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import AgentSummary, OrgOverview, ScoreByCriterion, TrendPoint

router = APIRouter(
    prefix="/api/v1/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)]
)

ALLOWED_INTERVALS = {"day", "week", "month"}


async def _require_agent_in_scope(agent_id: uuid.UUID, db: AsyncSession, user: User) -> None:
    if not await check_agent_in_analytics_scope(db, user, agent_id):
        raise HTTPException(status_code=403, detail="You do not have access to this agent's analytics")


@router.get("/agents/{agent_id}/summary", response_model=AgentSummary)
async def get_agent_summary(
    agent_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    await _require_agent_in_scope(agent_id, db, user)
    return await queries.agent_summary(db, agent_id)


@router.get("/agents/{agent_id}/score-by-criterion", response_model=list[ScoreByCriterion])
async def get_agent_score_by_criterion(
    agent_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    await _require_agent_in_scope(agent_id, db, user)
    return await queries.agent_score_by_criterion(db, agent_id)


@router.get("/agents/{agent_id}/trend", response_model=list[TrendPoint])
async def get_agent_trend(
    agent_id: uuid.UUID,
    interval: str = Query("week"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if interval not in ALLOWED_INTERVALS:
        raise HTTPException(
            status_code=400, detail=f"interval must be one of {sorted(ALLOWED_INTERVALS)}"
        )
    await _require_agent_in_scope(agent_id, db, user)
    return await queries.agent_trend(db, agent_id, interval)


@router.get("/overview", response_model=OrgOverview)
async def get_overview(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        scope = analytics_scope(user)
    except ScopeDenied as exc:
        raise HTTPException(status_code=403, detail="You do not have access to analytics") from exc

    team_id = user.team_id if scope == "team" else None
    return await queries.org_overview(db, team_id=team_id)
