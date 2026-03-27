from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Lead
from app.db.session import get_db
from app.schemas.booking import BookingRequest, BookingResponse
from app.services.calendar_provider import get_mock_availability


router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("/request", response_model=BookingResponse)
def request_booking(payload: BookingRequest, db: Session = Depends(get_db)) -> BookingResponse:
    lead = db.get(Lead, payload.lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    slots = get_mock_availability(lead.urgency)
    return BookingResponse(
        lead_id=lead.id,
        urgency=lead.urgency,
        available_slots=slots,
        provider="mock-calendar",
    )
