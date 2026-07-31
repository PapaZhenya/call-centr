import uuid

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import (
    ANALYTICS_VIEW_ALL,
    ANALYTICS_VIEW_TEAM,
    CALLS_VIEW_ALL,
    CALLS_VIEW_OWN,
    CALLS_VIEW_TEAM,
    has_permission,
)
from app.models.agent import Agent
from app.models.call import Call
from app.models.user import User


class ScopeDenied(Exception):
    """Raised when the user has none of the relevant scoped permissions."""


def scope_calls_query(stmt: Select, user: User) -> Select:
    """Applies calls:view:* visibility to a SELECT whose FROM clause includes
    Call. Joins Agent when team-scoping is required. Raises ScopeDenied if
    the user has none of the calls:view:* permissions."""
    if has_permission(user.role, CALLS_VIEW_ALL):
        return stmt
    if has_permission(user.role, CALLS_VIEW_TEAM):
        if user.team_id is None:
            return stmt.where(Call.id.is_(None))
        return stmt.join(Agent, Call.agent_id == Agent.id).where(Agent.team_id == user.team_id)
    if has_permission(user.role, CALLS_VIEW_OWN):
        if user.agent_id is None:
            return stmt.where(Call.id.is_(None))
        return stmt.where(Call.agent_id == user.agent_id)
    raise ScopeDenied()


async def check_call_visible(db: AsyncSession, user: User, call: Call) -> bool:
    """Checks whether `user` may view a single already-fetched `call`."""
    if has_permission(user.role, CALLS_VIEW_ALL):
        return True
    if has_permission(user.role, CALLS_VIEW_TEAM):
        if user.team_id is None or call.agent_id is None:
            return False
        agent = await db.get(Agent, call.agent_id)
        return agent is not None and agent.team_id == user.team_id
    if has_permission(user.role, CALLS_VIEW_OWN):
        return user.agent_id is not None and call.agent_id == user.agent_id
    return False


def analytics_scope(user: User) -> str:
    """Returns 'all' or 'team' for analytics endpoints, or raises ScopeDenied."""
    if has_permission(user.role, ANALYTICS_VIEW_ALL):
        return "all"
    if has_permission(user.role, ANALYTICS_VIEW_TEAM):
        if user.team_id is None:
            raise ScopeDenied()
        return "team"
    raise ScopeDenied()


async def check_agent_in_analytics_scope(db: AsyncSession, user: User, agent_id: uuid.UUID) -> bool:
    """For per-agent analytics endpoints: can `user` see this agent's data?"""
    if has_permission(user.role, ANALYTICS_VIEW_ALL):
        return True
    if has_permission(user.role, ANALYTICS_VIEW_TEAM):
        if user.team_id is None:
            return False
        agent = await db.get(Agent, agent_id)
        return agent is not None and agent.team_id == user.team_id
    return False
