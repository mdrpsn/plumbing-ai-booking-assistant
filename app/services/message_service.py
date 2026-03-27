from datetime import datetime, timezone

from fastapi import HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Conversation, Customer, Lead, Message
from app.schemas.message import InboundMessageWebhook
from app.services.phone_normalization import normalize_phone


def process_inbound_message(
    db: Session,
    payload: InboundMessageWebhook,
    *,
    provider_name: str,
    response: Response | None = None,
) -> Message:
    idempotency_key = build_inbound_idempotency_key(provider_name, payload.provider_message_id)
    existing_message = db.scalar(
        select(Message).where(Message.idempotency_key == idempotency_key)
    )
    if existing_message is not None:
        if response is not None:
            response.status_code = status.HTTP_200_OK
        return existing_message

    customer = db.scalar(
        select(Customer).where(Customer.normalized_phone == normalize_phone(payload.from_phone))
    )
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found for phone number",
        )

    lead = _resolve_lead(db, customer, payload.lead_id)
    conversation = _get_or_create_conversation(db, customer, lead)
    inbound_message = Message(
        conversation_id=conversation.id,
        customer_id=customer.id,
        lead_id=lead.id if lead is not None else None,
        direction="inbound",
        channel=conversation.channel,
        provider=provider_name,
        idempotency_key=idempotency_key,
        recipient=payload.from_phone,
        body=payload.body,
        status="received",
        provider_message_id=payload.provider_message_id,
    )
    db.add(inbound_message)
    db.flush()

    inbound_message.created_at = inbound_message.created_at or datetime.now(timezone.utc)
    conversation.status = "customer_replied"
    conversation.last_message_direction = inbound_message.direction
    conversation.last_message_at = inbound_message.created_at
    db.add(
        AuditLog(
            event_type="message.received",
            entity_type="message",
            entity_id=inbound_message.id,
            details={
                "conversation_id": conversation.id,
                "customer_id": customer.id,
                "lead_id": lead.id if lead is not None else None,
                "provider": inbound_message.provider,
                "status": inbound_message.status,
            },
        )
    )
    db.commit()
    db.refresh(inbound_message)
    return inbound_message


def build_inbound_idempotency_key(provider_name: str, provider_message_id: str) -> str:
    return f"inbound:{provider_name}:{provider_message_id}"


def _resolve_lead(db: Session, customer: Customer, lead_id: int | None) -> Lead | None:
    if lead_id is not None:
        lead = db.get(Lead, lead_id)
        if lead is None or lead.customer_id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found for customer",
            )
        return lead

    return db.scalar(
        select(Lead)
        .where(Lead.customer_id == customer.id)
        .order_by(Lead.created_at.desc(), Lead.id.desc())
    )


def _get_or_create_conversation(db: Session, customer: Customer, lead: Lead | None) -> Conversation:
    lead_id = lead.id if lead is not None else None
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.customer_id == customer.id,
            Conversation.lead_id == lead_id,
            Conversation.channel == "sms",
        )
    )
    if conversation is None:
        conversation = Conversation(
            customer_id=customer.id,
            lead_id=lead_id,
            channel="sms",
            status="open",
        )
        db.add(conversation)
        db.flush()

    return conversation
