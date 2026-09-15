from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, BookingRequest, Lead
from app.db.session import get_db
from app.schemas.booking import BookingRequestCreate, BookingRequestRead
from app.services.calendar_provider import get_mock_availability


router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.get("", response_model=list[BookingRequestRead])
def list_bookings(db: Session = Depends(get_db)) -> list[BookingRequest]:
    return list(
        db.scalars(
            select(BookingRequest).order_by(
                BookingRequest.created_at.desc(), BookingRequest.id.desc()
            )
        )
    )


@router.post("/request", response_model=BookingRequestRead)
def request_booking(payload: BookingRequestCreate, db: Session = Depends(get_db)) -> BookingRequest:
    lead = db.get(Lead, payload.lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    slots = get_mock_availability(lead.urgency)
    booking_request = BookingRequest(
        lead_id=lead.id,
        customer_id=lead.customer_id,
        urgency=lead.urgency,
        available_slots=slots,
        provider="mock-calendar",
        status="pending_dispatch",
    )
    db.add(booking_request)
    db.flush()
    db.add(
        AuditLog(
            event_type="booking_request.created",
            entity_type="booking_request",
            entity_id=booking_request.id,
            details={
                "lead_id": lead.id,
                "customer_id": lead.customer_id,
                "urgency": lead.urgency,
            },
        )
    )
    db.commit()
    db.refresh(booking_request)
    return booking_request
