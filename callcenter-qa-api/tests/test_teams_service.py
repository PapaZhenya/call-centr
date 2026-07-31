import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.team import TeamCreate, TeamUpdate
from app.teams.service import create_team, get_team, list_teams, update_team


@pytest.mark.asyncio
async def test_create_team_adds_and_returns_team():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    team = await create_team(db, TeamCreate(name="Sales"))

    assert db.add.called
    added = db.add.call_args[0][0]
    assert added.name == "Sales"
    assert team is added


@pytest.mark.asyncio
async def test_list_teams_returns_ordered_results():
    teams = [SimpleNamespace(name="A"), SimpleNamespace(name="B")]
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = teams
    db.execute = AsyncMock(return_value=result)

    assert await list_teams(db) == teams


@pytest.mark.asyncio
async def test_get_team_returns_none_when_missing():
    db = MagicMock()
    db.get = AsyncMock(return_value=None)
    assert await get_team(db, uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_update_team_renames_existing_team():
    existing = SimpleNamespace(name="Old Name")
    db = MagicMock()
    db.get = AsyncMock(return_value=existing)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = await update_team(db, uuid.uuid4(), TeamUpdate(name="New Name"))

    assert result is existing
    assert existing.name == "New Name"


@pytest.mark.asyncio
async def test_update_team_returns_none_when_missing():
    db = MagicMock()
    db.get = AsyncMock(return_value=None)
    result = await update_team(db, uuid.uuid4(), TeamUpdate(name="New Name"))
    assert result is None
