import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate


async def create_agent(db: AsyncSession, data: AgentCreate) -> Agent:
    agent = Agent(**data.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def update_agent(db: AsyncSession, agent_id: uuid.UUID, data: AgentUpdate) -> Agent | None:
    agent = await db.get(Agent, agent_id)
    if agent is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    await db.commit()
    await db.refresh(agent)
    return agent


async def list_agents(db: AsyncSession) -> list[Agent]:
    result = await db.execute(select(Agent).order_by(Agent.display_name))
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: uuid.UUID) -> Agent | None:
    return await db.get(Agent, agent_id)
