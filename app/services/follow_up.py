from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AuditLog, Conversation, Customer, Lead, Message, WorkflowRun
from app.services.notification_service import NotificationService


FOLLOW_UP_WORKFLOW_TYPE = "no_response_follow_up"


def register_no_response_follow_up(
    db: Session,
    customer: Customer,
    lead: Lead,
    conversation: Conversation,
) -> WorkflowRun:
    settings = get_settings()
    scheduled_for = _normalize_datetime(lead.created_at) + timedelta(minutes=settings.follow_up_delay_minutes)
    workflow_run = WorkflowRun(
        customer_id=customer.id,
        lead_id=lead.id,
        conversation_id=conversation.id,
        workflow_type=FOLLOW_UP_WORKFLOW_TYPE,
        status="pending",
        scheduled_for=scheduled_for,
        details={"delay_minutes": settings.follow_up_delay_minutes},
    )
    db.add(workflow_run)
    db.flush()
    db.add(
        AuditLog(
            event_type="workflow.registered",
            entity_type="workflow_run",
            entity_id=workflow_run.id,
            details={
                "workflow_type": workflow_run.workflow_type,
                "lead_id": lead.id,
                "conversation_id": conversation.id,
                "scheduled_for": workflow_run.scheduled_for.isoformat(),
            },
        )
    )
    return workflow_run


def process_due_follow_ups(
    db: Session,
    notification_service: NotificationService,
    *,
    now_at: datetime | None = None,
) -> dict[str, int | list[int]]:
    evaluation_time = _normalize_datetime(now_at or datetime.now(UTC))
    workflow_runs = db.scalars(
        select(WorkflowRun)
        .where(
            WorkflowRun.workflow_type == FOLLOW_UP_WORKFLOW_TYPE,
            WorkflowRun.status == "pending",
            WorkflowRun.scheduled_for <= evaluation_time,
        )
        .order_by(WorkflowRun.scheduled_for.asc(), WorkflowRun.id.asc())
    ).all()

    sent = 0
    skipped = 0
    workflow_ids: list[int] = []

    for workflow_run in workflow_runs:
        workflow_ids.append(workflow_run.id)
        conversation = db.get(Conversation, workflow_run.conversation_id)
        customer = db.get(Customer, workflow_run.customer_id)
        lead = db.get(Lead, workflow_run.lead_id)

        if conversation is None or customer is None or lead is None:
            workflow_run.status = "failed"
            workflow_run.processed_at = evaluation_time
            workflow_run.details = {**workflow_run.details, "reason": "missing_related_record"}
            db.add(
                AuditLog(
                    event_type="workflow.failed",
                    entity_type="workflow_run",
                    entity_id=workflow_run.id,
                    details={"reason": "missing_related_record"},
                )
            )
            continue

        has_inbound_reply = db.scalar(
            select(Message.id)
            .where(
                Message.conversation_id == conversation.id,
                Message.direction == "inbound",
            )
            .limit(1)
        )
        if has_inbound_reply is not None:
            workflow_run.status = "skipped"
            workflow_run.processed_at = evaluation_time
            workflow_run.details = {**workflow_run.details, "reason": "customer_replied"}
            skipped += 1
            db.add(
                AuditLog(
                    event_type="workflow.skipped",
                    entity_type="workflow_run",
                    entity_id=workflow_run.id,
                    details={
                        "reason": "customer_replied",
                        "conversation_id": conversation.id,
                    },
                )
            )
            continue

        follow_up_message = Message(
            conversation_id=conversation.id,
            customer_id=customer.id,
            lead_id=lead.id,
            direction="outbound",
            channel=conversation.channel,
            provider="mock-sms",
            recipient=customer.phone,
            body=build_no_response_follow_up(customer),
            status="queued",
            provider_message_id=None,
        )
        db.add(follow_up_message)
        db.flush()
        _, notification_result = notification_service.send_sms(customer.phone, follow_up_message.body)
        follow_up_message.provider = notification_result.provider
        follow_up_message.status = notification_result.status
        follow_up_message.provider_message_id = notification_result.provider_message_id
        follow_up_message.created_at = follow_up_message.created_at or evaluation_time

        conversation.status = "follow_up_sent"
        conversation.last_message_direction = follow_up_message.direction
        conversation.last_message_at = follow_up_message.created_at

        workflow_run.status = "completed"
        workflow_run.processed_at = evaluation_time
        workflow_run.result_message_id = follow_up_message.id
        workflow_run.details = {
            **workflow_run.details,
            "follow_up_message_id": follow_up_message.id,
            "processed_at": evaluation_time.isoformat(),
        }
        sent += 1
        db.add(
            AuditLog(
                event_type="notification.sent",
                entity_type="message",
                entity_id=follow_up_message.id,
                details={
                    "customer_id": customer.id,
                    "lead_id": lead.id,
                    "channel": conversation.channel,
                    "provider": notification_result.provider,
                    "status": notification_result.status,
                    "message_type": "follow_up",
                },
            )
        )
        db.add(
            AuditLog(
                event_type="workflow.completed",
                entity_type="workflow_run",
                entity_id=workflow_run.id,
                details={
                    "result_message_id": follow_up_message.id,
                    "conversation_id": conversation.id,
                },
            )
        )

    db.commit()
    return {
        "evaluated": len(workflow_runs),
        "sent": sent,
        "skipped": skipped,
        "workflow_ids": workflow_ids,
    }


def build_no_response_follow_up(customer: Customer) -> str:
    return (
        f"Hi {customer.name}, just following up on your plumbing request. "
        "Reply here if you still need help and we will prioritize the next step."
    )


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
