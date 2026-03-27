from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.models import Lead
from app.db.session import get_db
from app.schemas.lead import LeadCreate, LeadRead
from app.services.triage import determine_urgency


router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> Lead:
    lead = Lead(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        issue=payload.issue,
        address=payload.address,
        urgency=determine_urgency(payload.issue),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead
