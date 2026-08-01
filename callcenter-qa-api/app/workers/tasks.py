import dataclasses
import logging

from sqlalchemy import select

from app.api.deps import get_storage
from app.database import async_session_factory
from app.models.call import (
    STATUS_COMPLETED,
    STATUS_EVALUATING,
    STATUS_EVALUATION_FAILED,
    STATUS_TRANSCRIBED,
    STATUS_TRANSCRIBING,
    STATUS_TRANSCRIPTION_FAILED,
    Call,
)
from app.models.transcript import Transcript
from app.qa_evaluation.service import evaluate_call
from app.transcription.diarization import map_speakers_to_roles
from app.transcription.service import get_transcription_engine

logger = logging.getLogger(__name__)


async def ping(ctx) -> str:
    """Trivial task used to confirm the worker container is consuming jobs."""
    logger.info("arq worker ping received")
    return "pong"


async def transcribe_call(ctx, call_id) -> None:
    async with async_session_factory() as db:
        call = await db.get(Call, call_id)
        if call is None:
            logger.error("transcribe_call: call %s not found", call_id)
            return

        call.status = STATUS_TRANSCRIBING
        await db.commit()

        storage = get_storage()
        audio_path = storage.resolve_path(call.audio_storage_key)
        engine = get_transcription_engine()

        try:
            result = await engine.transcribe(audio_path)
        except Exception:
            logger.exception("transcribe_call failed for call %s", call_id)
            call.status = STATUS_TRANSCRIPTION_FAILED
            await db.commit()
            raise

        map_speakers_to_roles(result.segments, call.direction)

        db.add(
            Transcript(
                call_id=call.id,
                full_text=result.full_text,
                segments=[dataclasses.asdict(s) for s in result.segments],
                engine=result.engine,
                engine_model=result.engine_model,
                language=result.language,
            )
        )
        call.status = STATUS_TRANSCRIBED
        await db.commit()

    await ctx["redis"].enqueue_job("evaluate_call_qa", call_id)


async def evaluate_call_qa(ctx, call_id) -> None:
    async with async_session_factory() as db:
        call = await db.get(Call, call_id)
        if call is None:
            logger.error("evaluate_call_qa: call %s not found", call_id)
            return

        result = await db.execute(select(Transcript).where(Transcript.call_id == call.id))
        transcript = result.scalar_one_or_none()
        if transcript is None:
            logger.error("evaluate_call_qa: no transcript for call %s", call_id)
            call.status = STATUS_EVALUATION_FAILED
            await db.commit()
            return

        call.status = STATUS_EVALUATING
        await db.commit()

        try:
            await evaluate_call(db, call, transcript.full_text, segments=transcript.segments)
        except Exception:
            logger.exception("evaluate_call_qa failed for call %s", call_id)
            call.status = STATUS_EVALUATION_FAILED
            await db.commit()
            raise

        call.status = STATUS_COMPLETED
        await db.commit()
