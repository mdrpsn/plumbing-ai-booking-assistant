from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.workflow import FollowUpProcessRequest, FollowUpProcessResponse
from app.services.sms_provider_factory import get_notification_service
from app.services.workflow_execution import WorkflowExecutionService


router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("/follow-ups/process", response_model=FollowUpProcessResponse)
def process_follow_ups(
    payload: FollowUpProcessRequest,
    db: Session = Depends(get_db),
) -> FollowUpProcessResponse:
    execution_service = WorkflowExecutionService(
        notification_service=get_notification_service()
    )
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
