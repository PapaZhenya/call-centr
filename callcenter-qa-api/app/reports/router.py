import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.auth.scoping import ScopeDenied, scope_calls_query
from app.database import get_db
from app.models.agent import Agent
from app.models.call import Call
from app.models.qa_evaluation import STATUS_IN_PROGRESS, QAEvaluation, QAEvaluationScore
from app.models.team import Team
from app.models.user import User
from app.reports.csv_builder import ReportRow, build_calls_csv

router = APIRouter(prefix="/api/v1/reports", tags=["reports"], dependencies=[Depends(get_current_user)])


@router.get("/calls.csv")
async def export_calls_csv(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    agent_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Same visibility as GET /calls (scoped by role), flattened to CSV with
    one dynamic column per rubric criterion. UTF-8 with BOM so Excel opens
    Cyrillic correctly on double-click."""
    stmt = select(Call)
    try:
        stmt = scope_calls_query(stmt, user)
    except ScopeDenied as exc:
        raise HTTPException(status_code=403, detail="You do not have access to any calls") from exc

    if date_from is not None:
        stmt = stmt.where(Call.call_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Call.call_date <= date_to)
    if agent_id is not None:
        stmt = stmt.where(Call.agent_id == agent_id)
    stmt = stmt.order_by(Call.call_date)

    calls = (await db.execute(stmt)).scalars().all()

    agents = {
        a.id: a for a in (await db.execute(select(Agent))).scalars().all()
    }
    teams = {t.id: t.name for t in (await db.execute(select(Team))).scalars().all()}

    call_ids = [c.id for c in calls]
    evaluations_by_call: dict[uuid.UUID, QAEvaluation] = {}
    if call_ids:
        eval_stmt = (
            select(QAEvaluation)
            .where(
                QAEvaluation.call_id.in_(call_ids),
                QAEvaluation.status != STATUS_IN_PROGRESS,
            )
            .options(
                selectinload(QAEvaluation.scores).selectinload(QAEvaluationScore.rubric_criterion)
            )
            .order_by(QAEvaluation.created_at)
        )
        for evaluation in (await db.execute(eval_stmt)).scalars().all():
            evaluations_by_call[evaluation.call_id] = evaluation  # later rows win: latest kept

    rows = []
    for call in calls:
        agent = agents.get(call.agent_id)
        evaluation = evaluations_by_call.get(call.id)
        criterion_scores = {}
        if evaluation is not None:
            for score in evaluation.scores:
                criterion = score.rubric_criterion
                criterion_scores[criterion.key] = (criterion.label, float(score.score))
        rows.append(
            ReportRow(
                call_date=call.call_date,
                agent=agent.display_name if agent else str(call.agent_id),
                team=teams.get(agent.team_id) if agent and agent.team_id else None,
                direction=call.direction,
                queue=call.queue,
                status=call.status,
                overall_score=(
                    float(evaluation.overall_score)
                    if evaluation is not None and evaluation.overall_score is not None
                    else None
                ),
                flags=list(evaluation.flags or []) if evaluation is not None else [],
                notes=evaluation.notes if evaluation is not None else None,
                criterion_scores=criterion_scores,
            )
        )

    csv_text = build_calls_csv(rows)
    filename = f"calls-report-{datetime.now().date().isoformat()}.csv"
    return Response(
        content="﻿" + csv_text,  # BOM: Excel needs it to detect UTF-8
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
