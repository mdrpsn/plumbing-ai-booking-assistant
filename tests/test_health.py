from fastapi.testclient import TestClient

from app.db.session import Base, engine
from app.main import app


client = TestClient(app)


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)


def teardown_module() -> None:
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
    assert body["urgency"] == "emergency"


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
    assert body["lead_id"] == lead_id
    assert body["urgency"] == "standard"
    assert len(body["available_slots"]) == 3
    assert body["provider"] == "mock-calendar"


def test_booking_request_validates_lead_id() -> None:
    response = client.post("/api/bookings/request", json={"lead_id": 999999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"
