import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from arq import ArqRedis

from app.api.deps import get_current_user, get_storage, require_permission
from app.auth.permissions import CALLS_UPLOAD
from app.database import get_db
from app.ingestion import service
from app.ingestion.storage import StorageBackend
from app.schemas.call import CallRead
from app.workers.queue import get_arq_pool

router = APIRouter(prefix="/api/v1/calls", tags=["calls"], dependencies=[Depends(get_current_user)])


@router.post(
    "",
    response_model=CallRead,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission(CALLS_UPLOAD))],
)
async def upload_call(
    file: UploadFile,
    agent_id: uuid.UUID = Form(...),
    call_date: datetime = Form(...),
    direction: str | None = Form(None),
    queue: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    arq_pool: ArqRedis = Depends(get_arq_pool),
):
    return await service.ingest_call(
        db, storage, arq_pool, file, agent_id, call_date, direction, queue
    )
