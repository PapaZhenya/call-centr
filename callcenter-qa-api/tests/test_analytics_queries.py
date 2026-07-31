import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.analytics import queries


@pytest.mark.asyncio
async def test_agent_summary_maps_row_to_dict():
    agent_id = uuid.uuid4()
    db = AsyncMock()
    result = MagicMock()
    result.one.return_value = (3, 4.25)
    db.execute.return_value = result

    summary = await queries.agent_summary(db, agent_id)

    assert summary == {"agent_id": agent_id, "call_count": 3, "average_score": 4.25}


@pytest.mark.asyncio
async def test_agent_summary_handles_no_evaluations():
    agent_id = uuid.uuid4()
    db = AsyncMock()
    result = MagicMock()
    result.one.return_value = (0, None)
    db.execute.return_value = result

    summary = await queries.agent_summary(db, agent_id)

    assert summary == {"agent_id": agent_id, "call_count": 0, "average_score": None}


@pytest.mark.asyncio
async def test_agent_score_by_criterion_maps_rows():
    agent_id = uuid.uuid4()
    criterion_id = uuid.uuid4()
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = [(criterion_id, "politeness", "Politeness", 4.5, 2)]
    db.execute.return_value = result

    rows = await queries.agent_score_by_criterion(db, agent_id)

    assert rows == [
        {
            "rubric_criterion_id": criterion_id,
            "key": "politeness",
            "label": "Politeness",
            "average_score": 4.5,
            "count": 2,
        }
    ]


@pytest.mark.asyncio
async def test_org_overview_picks_worst_and_best_criterion():
    db = AsyncMock()

    total_calls_result = MagicMock()
    total_calls_result.scalar_one.return_value = 10

    avg_result = MagicMock()
    avg_result.scalar_one.return_value = 3.5

    criteria_result = MagicMock()
    criteria_result.all.return_value = [
        ("compliance_disclosure", "Compliance Disclosure", 2.0),
        ("politeness", "Politeness", 4.8),
    ]

    db.execute.side_effect = [total_calls_result, avg_result, criteria_result]

    overview = await queries.org_overview(db)

    assert overview["total_calls"] == 10
    assert overview["average_score"] == 3.5
    assert overview["worst_criterion"]["key"] == "compliance_disclosure"
    assert overview["best_criterion"]["key"] == "politeness"
