from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from datetime import UTC, datetime, timedelta

from app.db.models import AuditLog, BookingRequest, Conversation, Customer, Lead, Message, WorkflowRun
from app.db.session import Base, engine
from app.main import app
from app.services.mock_sms_provider import MockSmsProvider
from app.services.notification_service import NotificationService
from app.services.phone_normalization import normalize_phone
from app.services.sms_provider_factory import get_notification_service, get_sms_provider
from app.services.twilio_sms_provider import TwilioSmsProvider
from app.services.workflow_execution import WorkflowExecutionService
from app.core.config import get_settings


client = TestClient(app)


def setup_function() -> None:
    get_settings.cache_clear()
    get_sms_provider.cache_clear()
    get_notification_service.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_function() -> None:
    get_settings.cache_clear()
    get_sms_provider.cache_clear()
    get_notification_service.cache_clear()
    Base.metadata.drop_all(bind=engine)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_lead_persists_and_assigns_urgency() -> None:
    response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["id"] > 0
    assert body["customer_id"] > 0
    assert body["urgency"] == "emergency"

    with engine.connect() as connection:
        customer_count = connection.execute(select(func.count()).select_from(Customer)).scalar_one()
        lead_count = connection.execute(select(func.count()).select_from(Lead)).scalar_one()
        conversation_count = connection.execute(select(func.count()).select_from(Conversation)).scalar_one()
        message_count = connection.execute(select(func.count()).select_from(Message)).scalar_one()
        workflow_count = connection.execute(select(func.count()).select_from(WorkflowRun)).scalar_one()
        audit_count = connection.execute(select(func.count()).select_from(AuditLog)).scalar_one()

    assert customer_count == 1
    assert lead_count == 1
    assert conversation_count == 1
    assert message_count == 1
    assert workflow_count == 1
    assert audit_count == 3


def test_create_lead_creates_confirmation_message_and_audit_log() -> None:
    response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )

    lead_id = response.json()["id"]
    customer_id = response.json()["customer_id"]

    with Session(engine) as session:
        message = session.execute(select(Message)).scalar_one()
        conversation = session.execute(select(Conversation)).scalar_one()
        customer = session.execute(select(Customer)).scalar_one()
        workflow_run = session.execute(select(WorkflowRun)).scalar_one()
        audit_logs = session.execute(
            select(AuditLog).where(AuditLog.event_type == "notification.sent")
        ).scalars().all()

    assert message.conversation_id == conversation.id
    assert message.customer_id == customer_id
    assert message.lead_id == lead_id
    assert message.direction == "outbound"
    assert message.channel == "sms"
    assert message.provider == "mock-sms"
    assert message.status == "sent"
    assert message.recipient == "5551234567"
    assert "classified it as emergency" in message.body
    assert message.provider_message_id.startswith("mock-sms-5551234567-")
    assert customer.normalized_phone == normalize_phone("5551234567")
    assert conversation.status == "open"
    assert conversation.last_message_direction == "outbound"
    assert workflow_run.workflow_type == "no_response_follow_up"
    assert workflow_run.status == "pending"
    assert workflow_run.conversation_id == conversation.id
    assert len(audit_logs) == 1
    assert audit_logs[0].entity_type == "message"
    assert audit_logs[0].entity_id == message.id


def test_create_lead_reuses_existing_customer() -> None:
    first_response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )
    second_response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Bathroom faucet leak",
            "address": "123 Main St",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["customer_id"] == second_response.json()["customer_id"]

    with engine.connect() as connection:
        customer_count = connection.execute(select(func.count()).select_from(Customer)).scalar_one()
        lead_count = connection.execute(select(func.count()).select_from(Lead)).scalar_one()
        conversation_count = connection.execute(select(func.count()).select_from(Conversation)).scalar_one()
        message_count = connection.execute(select(func.count()).select_from(Message)).scalar_one()
        workflow_count = connection.execute(select(func.count()).select_from(WorkflowRun)).scalar_one()
        audit_count = connection.execute(select(func.count()).select_from(AuditLog)).scalar_one()

    assert customer_count == 1
    assert lead_count == 2
    assert conversation_count == 2
    assert message_count == 2
    assert workflow_count == 2
    assert audit_count == 6


def test_create_lead_reuses_customer_across_phone_formats() -> None:
    first_response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "(555) 123-4567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )
    second_response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "+1 555-123-4567",
            "issue": "Bathroom faucet leak",
            "address": "123 Main St",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["customer_id"] == second_response.json()["customer_id"]

    with Session(engine) as session:
        customer = session.execute(select(Customer)).scalar_one()

    assert customer.normalized_phone == "+15551234567"
    assert customer.phone == "+1 555-123-4567"


def test_booking_request_returns_mock_availability() -> None:
    lead_response = client.post(
        "/api/leads",
        json={
            "name": "Alex Doe",
            "phone": "5557654321",
            "issue": "Kitchen sink drain clogged",
        },
    )
    lead_id = lead_response.json()["id"]

    response = client.post("/api/bookings/request", json={"lead_id": lead_id})

    body = response.json()
    assert response.status_code == 200
    assert body["id"] > 0
    assert body["lead_id"] == lead_id
    assert body["customer_id"] == lead_response.json()["customer_id"]
    assert body["urgency"] == "standard"
    assert len(body["available_slots"]) == 3
    assert body["provider"] == "mock-calendar"
    assert body["status"] == "pending_dispatch"

    with engine.connect() as connection:
        booking_request_count = connection.execute(
            select(func.count()).select_from(BookingRequest)
        ).scalar_one()
        audit_count = connection.execute(select(func.count()).select_from(AuditLog)).scalar_one()

    assert booking_request_count == 1
    assert audit_count == 4


def test_booking_request_validates_lead_id() -> None:
    response = client.post("/api/bookings/request", json={"lead_id": 999999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


def test_inbound_message_creates_or_updates_conversation() -> None:
    lead_response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )

    lead_id = lead_response.json()["id"]
    response = client.post(
        "/api/messages/inbound",
        json={
            "from_phone": "(555) 123-4567",
            "body": "Can someone come this afternoon?",
            "provider_message_id": "provider-inbound-001",
            "lead_id": lead_id,
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["conversation_id"] > 0
    assert body["customer_id"] == lead_response.json()["customer_id"]
    assert body["lead_id"] == lead_id
    assert body["direction"] == "inbound"
    assert body["channel"] == "sms"
    assert body["provider"] == "mock-sms"
    assert body["status"] == "received"

    with Session(engine) as session:
        conversation = session.execute(select(Conversation)).scalar_one()
        messages = session.execute(select(Message).order_by(Message.id.asc())).scalars().all()
        inbound_audit = session.execute(
            select(AuditLog).where(AuditLog.event_type == "message.received")
        ).scalar_one()

    assert len(messages) == 2
    assert conversation.id == body["conversation_id"]
    assert conversation.status == "customer_replied"
    assert conversation.last_message_direction == "inbound"
    assert messages[1].conversation_id == conversation.id
    assert inbound_audit.entity_id == messages[1].id


def test_inbound_message_webhook_replay_is_idempotent() -> None:
    lead_response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )

    payload = {
        "from_phone": "5551234567",
        "body": "Checking in again.",
        "provider_message_id": "provider-inbound-replay-001",
        "lead_id": lead_response.json()["id"],
    }
    first_response = client.post("/api/messages/inbound", json=payload)
    second_response = client.post("/api/messages/inbound", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert first_response.json()["id"] == second_response.json()["id"]

    with Session(engine) as session:
        inbound_messages = session.execute(
            select(Message).where(Message.direction == "inbound")
        ).scalars().all()
        inbound_audits = session.execute(
            select(AuditLog).where(AuditLog.event_type == "message.received")
        ).scalars().all()

    assert len(inbound_messages) == 1
    assert len(inbound_audits) == 1


def test_inbound_message_returns_404_for_unknown_customer_phone() -> None:
    response = client.post(
        "/api/messages/inbound",
        json={
            "from_phone": "5550000000",
            "body": "Hello?",
            "provider_message_id": "provider-inbound-404",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found for phone number"


def test_follow_up_process_sends_message_when_no_customer_reply_exists() -> None:
    lead_response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )
    lead_id = lead_response.json()["id"]

    with Session(engine) as session:
        workflow_run = session.execute(select(WorkflowRun)).scalar_one()
        workflow_run.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

    response = client.post(
        "/api/workflows/follow-ups/process",
        json={"now_at": datetime.now(UTC).isoformat()},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["evaluated"] == 1
    assert body["sent"] == 1
    assert body["skipped"] == 0

    with Session(engine) as session:
        conversation = session.execute(select(Conversation)).scalar_one()
        messages = session.execute(select(Message).order_by(Message.id.asc())).scalars().all()
        workflow_run = session.execute(select(WorkflowRun)).scalar_one()
        completion_audit = session.execute(
            select(AuditLog).where(AuditLog.event_type == "workflow.completed")
        ).scalar_one()

    assert len(messages) == 2
    assert messages[1].lead_id == lead_id
    assert messages[1].direction == "outbound"
    assert messages[1].status == "sent"
    assert "following up on your plumbing request" in messages[1].body
    assert conversation.status == "follow_up_sent"
    assert workflow_run.status == "completed"
    assert workflow_run.result_message_id == messages[1].id
    assert completion_audit.entity_id == workflow_run.id


def test_follow_up_process_is_safe_to_rerun() -> None:
    client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )

    with Session(engine) as session:
        workflow_run = session.execute(select(WorkflowRun)).scalar_one()
        workflow_run.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

    first_response = client.post(
        "/api/workflows/follow-ups/process",
        json={"now_at": datetime.now(UTC).isoformat()},
    )
    second_response = client.post(
        "/api/workflows/follow-ups/process",
        json={"now_at": datetime.now(UTC).isoformat()},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["sent"] == 1
    assert second_response.json()["evaluated"] == 0
    assert second_response.json()["sent"] == 0

    with Session(engine) as session:
        outbound_follow_ups = session.execute(
            select(Message).where(Message.idempotency_key.like("workflow:%:follow_up"))
        ).scalars().all()

    assert len(outbound_follow_ups) == 1


def test_workflow_execution_service_is_reusable_outside_api_route() -> None:
    client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )

    with Session(engine) as session:
        workflow_run = session.execute(select(WorkflowRun)).scalar_one()
        workflow_run.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

    with Session(engine) as session:
        execution_service = WorkflowExecutionService(
            notification_service=NotificationService(sms_provider=MockSmsProvider())
        )
        result = execution_service.process_due_workflows(
            session,
            now_at=datetime.now(UTC),
        )

    assert result.evaluated == 1
    assert result.sent == 1
    assert result.skipped == 0


def test_follow_up_process_skips_when_customer_replied() -> None:
    lead_response = client.post(
        "/api/leads",
        json={
            "name": "Jordan Smith",
            "phone": "5551234567",
            "email": "jordan@example.com",
            "issue": "Burst pipe flooding the kitchen",
            "address": "123 Main St",
        },
    )
    lead_id = lead_response.json()["id"]
    client.post(
        "/api/messages/inbound",
        json={
            "from_phone": "5551234567",
            "body": "Yes, I still need help.",
            "provider_message_id": "provider-inbound-skip",
            "lead_id": lead_id,
        },
    )

    with Session(engine) as session:
        workflow_run = session.execute(select(WorkflowRun)).scalar_one()
        workflow_run.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

    response = client.post(
        "/api/workflows/follow-ups/process",
        json={"now_at": datetime.now(UTC).isoformat()},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["evaluated"] == 1
    assert body["sent"] == 0
    assert body["skipped"] == 1

    with Session(engine) as session:
        conversation = session.execute(select(Conversation)).scalar_one()
        messages = session.execute(select(Message).order_by(Message.id.asc())).scalars().all()
        workflow_run = session.execute(select(WorkflowRun)).scalar_one()
        skip_audit = session.execute(
            select(AuditLog).where(AuditLog.event_type == "workflow.skipped")
        ).scalar_one()

    assert len(messages) == 2
    assert conversation.status == "customer_replied"
    assert workflow_run.status == "skipped"
    assert workflow_run.result_message_id is None
    assert skip_audit.entity_id == workflow_run.id


def test_sms_provider_defaults_to_mock() -> None:
    provider = get_sms_provider()
    notification_service = get_notification_service()

    assert isinstance(provider, MockSmsProvider)
    assert isinstance(notification_service.sms_provider, MockSmsProvider)


def test_sms_provider_can_select_twilio_from_configuration(monkeypatch) -> None:
    monkeypatch.setenv("SMS_PROVIDER", "twilio")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("TWILIO_FROM_PHONE", "+15550001111")
    get_settings.cache_clear()
    get_sms_provider.cache_clear()
    get_notification_service.cache_clear()

    provider = get_sms_provider()
    notification_service = get_notification_service()

    assert isinstance(provider, TwilioSmsProvider)
    assert isinstance(notification_service.sms_provider, TwilioSmsProvider)
