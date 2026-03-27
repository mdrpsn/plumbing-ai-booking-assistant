from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import AuditLog, BookingRequest, Customer, Lead
from app.db.session import Base, engine
from app.main import app


client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_function() -> None:
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
        audit_count = connection.execute(select(func.count()).select_from(AuditLog)).scalar_one()

    assert customer_count == 1
    assert lead_count == 1
    assert audit_count == 1


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
        audit_count = connection.execute(select(func.count()).select_from(AuditLog)).scalar_one()

    assert customer_count == 1
    assert lead_count == 2
    assert audit_count == 2


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
    assert audit_count == 2


def test_booking_request_validates_lead_id() -> None:
    response = client.post("/api/bookings/request", json={"lead_id": 999999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"
