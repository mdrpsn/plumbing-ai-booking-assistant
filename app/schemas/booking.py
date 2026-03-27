from pydantic import BaseModel, Field


class BookingRequest(BaseModel):
    lead_id: int = Field(gt=0)


class BookingResponse(BaseModel):
    lead_id: int
    urgency: str
    available_slots: list[str]
    provider: str
