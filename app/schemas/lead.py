from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=50)
    email: EmailStr | None = None
    issue: str = Field(min_length=5, max_length=2000)
    address: str | None = Field(default=None, max_length=255)


class LeadRead(BaseModel):
    id: int
    name: str
    phone: str
    email: EmailStr | None
    issue: str
    address: str | None
    urgency: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
