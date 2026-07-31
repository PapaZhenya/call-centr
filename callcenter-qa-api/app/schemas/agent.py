import uuid

from pydantic import BaseModel, ConfigDict


class AgentCreate(BaseModel):
    display_name: str
    external_agent_id: str | None = None
    team_id: uuid.UUID | None = None


class AgentUpdate(BaseModel):
    display_name: str | None = None
    external_agent_id: str | None = None
    team_id: uuid.UUID | None = None
    is_active: bool | None = None


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    external_agent_id: str | None
    team_id: uuid.UUID | None
    is_active: bool
