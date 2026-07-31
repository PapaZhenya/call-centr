import uuid

from pydantic import BaseModel, EmailStr

from app.models.user import ALL_ROLES


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str
    team_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None

    def validated_role(self) -> str:
        if self.role not in ALL_ROLES:
            raise ValueError(f"Unknown role: {self.role!r}. Must be one of {ALL_ROLES}")
        return self.role


class UserUpdate(BaseModel):
    role: str | None = None
    team_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    is_active: bool | None = None
