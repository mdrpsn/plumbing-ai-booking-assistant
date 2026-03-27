from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InboundMessageWebhook(BaseModel):
    from_phone: str = Field(min_length=5, max_length=50)
    body: str = Field(min_length=1, max_length=2000)
    provider_message_id: str = Field(min_length=1, max_length=100)
    lead_id: int | None = Field(default=None, gt=0)


class InboundMessageRead(BaseModel):
    id: int
    conversation_id: int
    customer_id: int
    lead_id: int | None
    direction: str
    channel: str
    provider: str
    recipient: str
    body: str
    status: str
    provider_message_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
