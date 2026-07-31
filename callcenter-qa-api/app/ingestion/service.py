import uuid
from datetime import datetime

from arq import ArqRedis
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.storage import StorageBackend
from app.models.agent import Agent
from app.models.call import Call

ALLOWED_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/ogg",
    "audio/flac",
}
MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB


async def ingest_call(
    db: AsyncSession,
    storage: StorageBackend,
    arq_pool: ArqRedis,
    file: UploadFile,
    agent_id: uuid.UUID,
    call_date: datetime,
    direction: str | None,
    queue: str | None,
) -> Call:
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415, detail=f"Unsupported content type: {file.content_type}"
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds maximum upload size")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    storage_key = await storage.save(file.filename or "call.audio", content)

    call = Call(
        agent_id=agent_id,
        call_date=call_date,
        direction=direction,
        queue=queue,
        audio_storage_key=storage_key,
        original_filename=file.filename or "call.audio",
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)

    await arq_pool.enqueue_job("transcribe_call", call.id)

    return call
