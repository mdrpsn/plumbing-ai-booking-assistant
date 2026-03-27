from fastapi import APIRouter, Depends, Form, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Message
from app.db.session import get_db
from app.schemas.message import InboundMessageRead, InboundMessageWebhook
from app.services.mock_sms_provider import MockSmsProvider
from app.services.message_service import process_inbound_message
from app.services.provider_webhook_security import verify_twilio_request_or_raise
from app.services.twilio_sms_provider import TwilioSmsProvider


router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("/inbound", response_model=InboundMessageRead, status_code=status.HTTP_201_CREATED)
def receive_inbound_message(
    payload: InboundMessageWebhook,
    response: Response,
    db: Session = Depends(get_db),
) -> Message:
    return process_inbound_message(
        db,
        payload,
        provider_name=MockSmsProvider.provider_name,
        response=response,
    )


@router.post("/providers/twilio/inbound", response_model=InboundMessageRead, status_code=status.HTTP_201_CREATED)
async def receive_twilio_inbound_message(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
    LeadId: int | None = Form(default=None),
) -> Message:
    form_payload = {
        "From": From,
        "Body": Body,
        "MessageSid": MessageSid,
    }
    if LeadId is not None:
        form_payload["LeadId"] = str(LeadId)
    verify_twilio_request_or_raise(request, form_payload)
    return process_inbound_message(
        db,
        InboundMessageWebhook(
            from_phone=From,
            body=Body,
            provider_message_id=MessageSid,
            lead_id=LeadId,
        ),
        provider_name=TwilioSmsProvider.provider_name,
        response=response,
    )


@router.post("/providers/twilio/status")
async def receive_twilio_status_callback(
    request: Request,
    db: Session = Depends(get_db),
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    ErrorCode: str | None = Form(default=None),
) -> dict[str, str]:
    form_payload = {
        "MessageSid": MessageSid,
        "MessageStatus": MessageStatus,
    }
    if ErrorCode:
        form_payload["ErrorCode"] = ErrorCode
    verify_twilio_request_or_raise(request, form_payload)

    message = db.scalar(
        select(Message).where(
            Message.provider == TwilioSmsProvider.provider_name,
            Message.provider_message_id == MessageSid,
        )
    )
    if message is None:
        db.add(
            AuditLog(
                event_type="provider.callback.missing_message",
                entity_type="message",
                entity_id=0,
                details={
                    "provider": TwilioSmsProvider.provider_name,
                    "provider_message_id": MessageSid,
                    "status": MessageStatus,
                },
            )
        )
        db.commit()
        return {"status": "ignored"}

    message.status = MessageStatus
    db.add(
        AuditLog(
            event_type="provider.callback.processed",
            entity_type="message",
            entity_id=message.id,
            details={
                "provider": TwilioSmsProvider.provider_name,
                "provider_message_id": MessageSid,
                "status": MessageStatus,
                "error_code": ErrorCode,
            },
        )
    )
    db.commit()
    return {"status": "ok"}
