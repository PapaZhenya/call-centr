import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.auth.scoping import (
    ScopeDenied,
    analytics_scope,
    check_agent_in_analytics_scope,
    check_call_visible,
    scope_calls_query,
)
from app.models.agent import Agent
from app.models.call import Call
from app.models.user import ROLE_ADMIN, ROLE_AGENT, ROLE_TEAM_LEAD, ROLE_VIEWER


def _sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


def _user(role: str, **overrides) -> SimpleNamespace:
    defaults = dict(id=uuid.uuid4(), role=role, team_id=None, agent_id=None)
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# --- scope_calls_query (list endpoint) --------------------------------------


def test_view_all_permission_applies_no_filter():
    user = _user(ROLE_ADMIN)
    stmt = scope_calls_query(select(Call), user)
    assert stmt.whereclause is None


def test_view_team_permission_joins_agent_and_filters_by_team_id():
    team_id = uuid.uuid4()
    user = _user(ROLE_TEAM_LEAD, team_id=team_id)
    stmt = scope_calls_query(select(Call), user)
    sql = _sql(stmt)
    assert "agents" in sql
    assert "team_id" in sql


def test_view_team_permission_with_no_team_assigned_sees_nothing():
    user = _user(ROLE_TEAM_LEAD, team_id=None)
    stmt = scope_calls_query(select(Call), user)
    sql = _sql(stmt)
    assert "calls.id IS NULL" in sql


def test_view_own_permission_filters_by_agent_id():
    agent_id = uuid.uuid4()
    user = _user(ROLE_AGENT, agent_id=agent_id)
    stmt = scope_calls_query(select(Call), user)
    sql = _sql(stmt)
    assert "calls.agent_id" in sql


def test_view_own_permission_with_no_agent_linked_sees_nothing():
    user = _user(ROLE_AGENT, agent_id=None)
    stmt = scope_calls_query(select(Call), user)
    sql = _sql(stmt)
    assert "calls.id IS NULL" in sql


def test_no_view_permission_raises_scope_denied():
    user = _user("not-a-real-role")
    with pytest.raises(ScopeDenied):
        scope_calls_query(select(Call), user)


# --- check_call_visible (single-call endpoints) -----------------------------


@pytest.mark.asyncio
async def test_view_all_can_see_any_call():
    user = _user(ROLE_ADMIN)
    call = SimpleNamespace(agent_id=uuid.uuid4())
    db = MagicMock()
    assert await check_call_visible(db, user, call) is True


@pytest.mark.asyncio
async def test_view_team_can_see_call_of_agent_on_own_team():
    team_id = uuid.uuid4()
    user = _user(ROLE_TEAM_LEAD, team_id=team_id)
    call = SimpleNamespace(agent_id=uuid.uuid4())
    db = MagicMock()
    db.get = AsyncMock(return_value=SimpleNamespace(team_id=team_id))
    assert await check_call_visible(db, user, call) is True


@pytest.mark.asyncio
async def test_view_team_cannot_see_call_of_agent_on_other_team():
    user = _user(ROLE_TEAM_LEAD, team_id=uuid.uuid4())
    call = SimpleNamespace(agent_id=uuid.uuid4())
    db = MagicMock()
    db.get = AsyncMock(return_value=SimpleNamespace(team_id=uuid.uuid4()))
    assert await check_call_visible(db, user, call) is False


@pytest.mark.asyncio
async def test_view_own_can_see_own_call_only():
    agent_id = uuid.uuid4()
    user = _user(ROLE_AGENT, agent_id=agent_id)
    own_call = SimpleNamespace(agent_id=agent_id)
    other_call = SimpleNamespace(agent_id=uuid.uuid4())
    db = MagicMock()
    assert await check_call_visible(db, user, own_call) is True
    assert await check_call_visible(db, user, other_call) is False


@pytest.mark.asyncio
async def test_no_permission_cannot_see_any_call():
    user = _user("not-a-real-role")
    call = SimpleNamespace(agent_id=uuid.uuid4())
    db = MagicMock()
    assert await check_call_visible(db, user, call) is False


# --- analytics_scope / check_agent_in_analytics_scope -----------------------


def test_analytics_scope_all_for_view_all_role():
    assert analytics_scope(_user(ROLE_VIEWER)) == "all"


def test_analytics_scope_team_for_view_team_role_with_team():
    assert analytics_scope(_user(ROLE_TEAM_LEAD, team_id=uuid.uuid4())) == "team"


def test_analytics_scope_denied_for_view_team_role_without_team():
    with pytest.raises(ScopeDenied):
        analytics_scope(_user(ROLE_TEAM_LEAD, team_id=None))


def test_analytics_scope_denied_for_role_without_analytics_permission():
    with pytest.raises(ScopeDenied):
        analytics_scope(_user(ROLE_AGENT))


@pytest.mark.asyncio
async def test_check_agent_in_analytics_scope_all_permission_allows_any_agent():
    user = _user(ROLE_VIEWER)
    db = MagicMock()
    assert await check_agent_in_analytics_scope(db, user, uuid.uuid4()) is True


@pytest.mark.asyncio
async def test_check_agent_in_analytics_scope_team_permission_matches_team():
    team_id = uuid.uuid4()
    user = _user(ROLE_TEAM_LEAD, team_id=team_id)
    db = MagicMock()
    db.get = AsyncMock(return_value=SimpleNamespace(team_id=team_id))
    assert await check_agent_in_analytics_scope(db, user, uuid.uuid4()) is True


@pytest.mark.asyncio
async def test_check_agent_in_analytics_scope_team_permission_rejects_other_team():
    user = _user(ROLE_TEAM_LEAD, team_id=uuid.uuid4())
    db = MagicMock()
    db.get = AsyncMock(return_value=SimpleNamespace(team_id=uuid.uuid4()))
    assert await check_agent_in_analytics_scope(db, user, uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_check_agent_in_analytics_scope_no_permission_rejects():
    user = _user(ROLE_AGENT)
    db = MagicMock()
    assert await check_agent_in_analytics_scope(db, user, uuid.uuid4()) is False
