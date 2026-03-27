from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Customer, Lead, Message
from app.db.session import get_db
from app.schemas.lead import LeadCreate, LeadRead
from app.services.mock_sms_provider import MockSmsProvider
from app.services.notification_service import NotificationService
from app.services.triage import determine_urgency


router = APIRouter(prefix="/api/leads", tags=["leads"])
notification_service = NotificationService(sms_provider=MockSmsProvider())


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> Lead:
    customer = db.scalar(
        select(Customer).where(
            Customer.phone == payload.phone,
            Customer.email == payload.email,
        )
    )
    if customer is None:
        customer = Customer(
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            address=payload.address,
        )
        db.add(customer)
        db.flush()
    else:
        customer.name = payload.name
        customer.address = payload.address or customer.address

    lead = Lead(
        customer_id=customer.id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        issue=payload.issue,
        address=payload.address,
        urgency=determine_urgency(payload.issue),
    )
    db.add(lead)
    db.flush()
    db.add(
        AuditLog(
            event_type="lead.created",
            entity_type="lead",
            entity_id=lead.id,
            details={
                "customer_id": customer.id,
                "urgency": lead.urgency,
            },
        )
    )
    message = Message(
        customer_id=customer.id,
        lead_id=lead.id,
        direction="outbound",
        channel="sms",
        provider=MockSmsProvider.provider_name,
        recipient=customer.phone,
        body=notification_service.build_lead_confirmation(customer, lead),
        status="queued",
        provider_message_id=None,
    )
    db.add(message)
    db.flush()
    _, notification_result = notification_service.send_lead_confirmation(customer, lead)
    message.provider = notification_result.provider
    message.status = notification_result.status
    message.provider_message_id = notification_result.provider_message_id
    db.add(
        AuditLog(
            event_type="notification.sent",
            entity_type="message",
            entity_id=message.id,
            details={
                "customer_id": customer.id,
                "lead_id": lead.id,
                "channel": "sms",
                "provider": notification_result.provider,
                "status": notification_result.status,
            },
        )
    )
    db.commit()
    db.refresh(lead)
    return lead
