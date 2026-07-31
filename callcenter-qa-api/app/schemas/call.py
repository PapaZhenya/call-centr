import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    call_date: datetime
    direction: str | None
    queue: str | None
    duration_seconds: int | None
    original_filename: str
    status: str
    created_at: datetime
    updated_at: datetime


class TranscriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    call_id: uuid.UUID
    full_text: str
    segments: list
    engine: str
    engine_model: str
    language: str | None
