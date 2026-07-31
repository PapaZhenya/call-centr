import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.ingestion.service import ingest_call


def _mock_db(get_return=None) -> MagicMock:
    # AsyncSession.add() is synchronous; only commit/flush/refresh/execute are async.
    db = MagicMock()
    db.get = AsyncMock(return_value=get_return)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _upload_file(filename="call.wav", content_type="audio/wav", content=b"fake-audio-bytes"):
    upload = MagicMock()
    upload.filename = filename
    upload.content_type = content_type
    upload.read = AsyncMock(return_value=content)
    return upload


@pytest.mark.asyncio
async def test_ingest_call_rejects_unknown_agent():
    db = _mock_db(get_return=None)
    storage = AsyncMock()
    arq_pool = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await ingest_call(
            db, storage, arq_pool, _upload_file(), uuid.uuid4(), datetime.now(timezone.utc), None, None
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_ingest_call_rejects_unsupported_content_type():
    db = _mock_db(get_return=MagicMock())  # agent exists
    storage = AsyncMock()
    arq_pool = AsyncMock()

    upload = _upload_file(content_type="application/octet-stream")

    with pytest.raises(HTTPException) as exc_info:
        await ingest_call(
            db, storage, arq_pool, upload, uuid.uuid4(), datetime.now(timezone.utc), None, None
        )
    assert exc_info.value.status_code == 415


@pytest.mark.asyncio
async def test_ingest_call_rejects_empty_file():
    db = _mock_db(get_return=MagicMock())
    storage = AsyncMock()
    arq_pool = AsyncMock()

    upload = _upload_file(content=b"")

    with pytest.raises(HTTPException) as exc_info:
        await ingest_call(
            db, storage, arq_pool, upload, uuid.uuid4(), datetime.now(timezone.utc), None, None
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_ingest_call_enqueues_transcription_job():
    db = _mock_db(get_return=MagicMock())
    storage = AsyncMock()
    storage.save = AsyncMock(return_value="stored-key.wav")
    arq_pool = AsyncMock()

    upload = _upload_file()

    call = await ingest_call(
        db,
        storage,
        arq_pool,
        upload,
        uuid.uuid4(),
        datetime.now(timezone.utc),
        "inbound",
        "sales",
    )

    storage.save.assert_awaited_once()
    db.add.assert_called_once()
    db.commit.assert_awaited()
    arq_pool.enqueue_job.assert_awaited_once_with("transcribe_call", call.id)
