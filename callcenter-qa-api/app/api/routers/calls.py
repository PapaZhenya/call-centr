import mimetypes
import uuid
from datetime import datetime

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_storage, require_permission
from app.auth.permissions import CALLS_RETRY
from app.auth.scoping import ScopeDenied, check_call_visible, scope_calls_query
from app.database import get_db
from app.ingestion.storage import StorageBackend
from app.models.call import (
    STATUS_EVALUATION_FAILED,
    STATUS_TRANSCRIPTION_FAILED,
    Call,
)
from app.models.qa_evaluation import QAEvaluation, QAEvaluationScore
from app.models.transcript import Transcript
from app.models.user import User
from app.schemas.call import CallRead, TranscriptRead
from app.schemas.qa_evaluation import QAEvaluationRead
from app.workers.queue import get_arq_pool

router = APIRouter(prefix="/api/v1/calls", tags=["calls"], dependencies=[Depends(get_current_user)])


async def _get_visible_call(call_id: uuid.UUID, db: AsyncSession, user: User) -> Call:
    call = await db.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    if not await check_call_visible(db, user, call):
        raise HTTPException(status_code=403, detail="You do not have access to this call")
    return call


@router.get("", response_model=list[CallRead])
async def list_calls(
    agent_id: uuid.UUID | None = None,
    status: str | None = None,
    queue: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Call)
    try:
        stmt = scope_calls_query(stmt, user)
    except ScopeDenied as exc:
        raise HTTPException(status_code=403, detail="You do not have access to any calls") from exc

    if agent_id is not None:
        stmt = stmt.where(Call.agent_id == agent_id)
    if status is not None:
        stmt = stmt.where(Call.status == status)
    if queue is not None:
        stmt = stmt.where(Call.queue == queue)
    if date_from is not None:
        stmt = stmt.where(Call.call_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Call.call_date <= date_to)
    stmt = stmt.order_by(Call.call_date.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{call_id}", response_model=CallRead)
async def get_call(
    call_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    return await _get_visible_call(call_id, db, user)


@router.get("/{call_id}/audio")
async def get_call_audio(
    call_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    user: User = Depends(get_current_user),
):
    call = await _get_visible_call(call_id, db, user)

    audio_path = storage.resolve_path(call.audio_storage_key)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found in storage")

    media_type = mimetypes.guess_type(str(audio_path))[0] or "application/octet-stream"
    return FileResponse(audio_path, media_type=media_type, filename=call.original_filename)


@router.get("/{call_id}/transcript", response_model=TranscriptRead)
async def get_call_transcript(
    call_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    await _get_visible_call(call_id, db, user)

    stmt = select(Transcript).where(Transcript.call_id == call_id)
    result = await db.execute(stmt)
    transcript = result.scalar_one_or_none()
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@router.get("/{call_id}/qa", response_model=QAEvaluationRead)
async def get_call_qa(
    call_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    await _get_visible_call(call_id, db, user)

    stmt = (
        select(QAEvaluation)
        .where(QAEvaluation.call_id == call_id)
        .options(selectinload(QAEvaluation.scores).selectinload(QAEvaluationScore.rubric_criterion))
        .order_by(QAEvaluation.created_at.desc())
    )
    result = await db.execute(stmt)
    evaluation = result.scalars().first()
    if evaluation is None:
        raise HTTPException(status_code=404, detail="QA evaluation not found")
    return evaluation


@router.post(
    "/{call_id}/retry",
    response_model=CallRead,
    dependencies=[Depends(require_permission(CALLS_RETRY))],
)
async def retry_call(
    call_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
    user: User = Depends(get_current_user),
):
    call = await _get_visible_call(call_id, db, user)

    if call.status == STATUS_TRANSCRIPTION_FAILED:
        await arq_pool.enqueue_job("transcribe_call", call.id)
    elif call.status == STATUS_EVALUATION_FAILED:
        await arq_pool.enqueue_job("evaluate_call_qa", call.id)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Call is not in a failed state (status={call.status})",
        )

    return call
