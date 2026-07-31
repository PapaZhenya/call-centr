import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import service
from app.api.deps import get_current_user, require_permission
from app.auth.permissions import TEAMS_MANAGE
from app.database import get_db
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate

router = APIRouter(prefix="/api/v1/agents", tags=["agents"], dependencies=[Depends(get_current_user)])

# Reads stay open to any authenticated user (agent names label the calls
# list); writes are org-structure management, same as teams.
_require_agents_manage = Depends(require_permission(TEAMS_MANAGE))


@router.post("", response_model=AgentRead, status_code=201, dependencies=[_require_agents_manage])
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_agent(db, data)


@router.get("", response_model=list[AgentRead])
async def list_agents(db: AsyncSession = Depends(get_db)):
    return await service.list_agents(db)


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    agent = await service.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentRead, dependencies=[_require_agents_manage])
async def update_agent(
    agent_id: uuid.UUID, data: AgentUpdate, db: AsyncSession = Depends(get_db)
):
    agent = await service.update_agent(db, agent_id, data)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
