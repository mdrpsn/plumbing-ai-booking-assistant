from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.workflow import FollowUpProcessRequest, FollowUpProcessResponse
from app.services.mock_sms_provider import MockSmsProvider
from app.services.notification_service import NotificationService
from app.services.workflow_execution import WorkflowExecutionService


router = APIRouter(prefix="/api/workflows", tags=["workflows"])
execution_service = WorkflowExecutionService(
    notification_service=NotificationService(sms_provider=MockSmsProvider())
)


@router.post("/follow-ups/process", response_model=FollowUpProcessResponse)
def process_follow_ups(
    payload: FollowUpProcessRequest,
    db: Session = Depends(get_db),
) -> FollowUpProcessResponse:
    result = execution_service.process_due_workflows(
        db,
        now_at=payload.now_at,
    )
    return FollowUpProcessResponse(
        evaluated=result.evaluated,
        sent=result.sent,
        skipped=result.skipped,
        workflow_ids=result.workflow_ids,
    )
