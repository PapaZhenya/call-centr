import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.call import Call
from app.models.qa_evaluation import STATUS_COMPLETED, QAEvaluation, QAEvaluationScore
from app.models.rubric import RubricCriterion


async def agent_summary(db: AsyncSession, agent_id: uuid.UUID) -> dict:
    stmt = (
        select(func.count(QAEvaluation.id), func.avg(QAEvaluation.overall_score))
        .select_from(QAEvaluation)
        .join(Call, Call.id == QAEvaluation.call_id)
        .where(Call.agent_id == agent_id, QAEvaluation.status == STATUS_COMPLETED)
    )
    call_count, avg_score = (await db.execute(stmt)).one()
    return {
        "agent_id": agent_id,
        "call_count": call_count or 0,
        "average_score": float(avg_score) if avg_score is not None else None,
    }


async def agent_score_by_criterion(db: AsyncSession, agent_id: uuid.UUID) -> list[dict]:
    stmt = (
        select(
            RubricCriterion.id,
            RubricCriterion.key,
            RubricCriterion.label,
            func.avg(QAEvaluationScore.score),
            func.count(QAEvaluationScore.id),
        )
        .select_from(QAEvaluationScore)
        .join(QAEvaluation, QAEvaluation.id == QAEvaluationScore.qa_evaluation_id)
        .join(Call, Call.id == QAEvaluation.call_id)
        .join(RubricCriterion, RubricCriterion.id == QAEvaluationScore.rubric_criterion_id)
        .where(Call.agent_id == agent_id)
        .group_by(RubricCriterion.id, RubricCriterion.key, RubricCriterion.label)
        .order_by(RubricCriterion.key)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "rubric_criterion_id": row[0],
            "key": row[1],
            "label": row[2],
            "average_score": float(row[3]) if row[3] is not None else None,
            "count": row[4],
        }
        for row in rows
    ]


async def agent_trend(db: AsyncSession, agent_id: uuid.UUID, interval: str) -> list[dict]:
    bucket = func.date_trunc(interval, Call.call_date).label("bucket")
    stmt = (
        select(bucket, func.avg(QAEvaluation.overall_score), func.count(QAEvaluation.id))
        .select_from(QAEvaluation)
        .join(Call, Call.id == QAEvaluation.call_id)
        .where(Call.agent_id == agent_id, QAEvaluation.status == STATUS_COMPLETED)
        .group_by(bucket)
        .order_by(bucket)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "period": row[0],
            "average_score": float(row[1]) if row[1] is not None else None,
            "call_count": row[2],
        }
        for row in rows
    ]


async def org_overview(db: AsyncSession, team_id: uuid.UUID | None = None) -> dict:
    total_calls_stmt = select(func.count(Call.id))
    avg_score_stmt = select(func.avg(QAEvaluation.overall_score)).where(
        QAEvaluation.status == STATUS_COMPLETED
    )
    criterion_stmt = (
        select(RubricCriterion.key, RubricCriterion.label, func.avg(QAEvaluationScore.score))
        .select_from(QAEvaluationScore)
        .join(RubricCriterion, RubricCriterion.id == QAEvaluationScore.rubric_criterion_id)
        .group_by(RubricCriterion.key, RubricCriterion.label)
        .order_by(func.avg(QAEvaluationScore.score))
    )

    if team_id is not None:
        total_calls_stmt = total_calls_stmt.join(Agent, Agent.id == Call.agent_id).where(
            Agent.team_id == team_id
        )
        avg_score_stmt = avg_score_stmt.join(Call, Call.id == QAEvaluation.call_id).join(
            Agent, Agent.id == Call.agent_id
        ).where(Agent.team_id == team_id)
        criterion_stmt = (
            criterion_stmt.join(QAEvaluation, QAEvaluation.id == QAEvaluationScore.qa_evaluation_id)
            .join(Call, Call.id == QAEvaluation.call_id)
            .join(Agent, Agent.id == Call.agent_id)
            .where(Agent.team_id == team_id)
        )

    total_calls = (await db.execute(total_calls_stmt)).scalar_one()
    avg_score = (await db.execute(avg_score_stmt)).scalar_one()
    criterion_rows = (await db.execute(criterion_stmt)).all()
    per_criterion = [
        {"key": row[0], "label": row[1], "average_score": float(row[2]) if row[2] is not None else None}
        for row in criterion_rows
    ]

    return {
        "total_calls": total_calls,
        "average_score": float(avg_score) if avg_score is not None else None,
        "worst_criterion": per_criterion[0] if per_criterion else None,
        "best_criterion": per_criterion[-1] if per_criterion else None,
        "criteria": per_criterion,
    }
