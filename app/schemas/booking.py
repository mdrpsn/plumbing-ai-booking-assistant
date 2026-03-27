from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookingRequestCreate(BaseModel):
    lead_id: int = Field(gt=0)


class BookingRequestRead(BaseModel):
    id: int
    lead_id: int
    customer_id: int
    urgency: str
    available_slots: list[str]
    provider: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
