from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.workflow import FollowUpProcessRequest, FollowUpProcessResponse
from app.services.follow_up import process_due_follow_ups
from app.services.mock_sms_provider import MockSmsProvider
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/api/workflows", tags=["workflows"])
notification_service = NotificationService(sms_provider=MockSmsProvider())


@router.post("/follow-ups/process", response_model=FollowUpProcessResponse)
def process_follow_ups(
    payload: FollowUpProcessRequest,
    db: Session = Depends(get_db),
) -> FollowUpProcessResponse:
    result = process_due_follow_ups(
        db,
        notification_service,
        now_at=payload.now_at,
    )
    return FollowUpProcessResponse(**result)
