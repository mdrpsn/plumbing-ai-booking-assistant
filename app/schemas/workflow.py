from datetime import datetime

from pydantic import BaseModel, Field


class FollowUpProcessRequest(BaseModel):
    now_at: datetime | None = None


class FollowUpProcessResponse(BaseModel):
    evaluated: int
    sent: int
    skipped: int
    workflow_ids: list[int] = Field(default_factory=list)
