from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Customer, Lead
from app.db.session import get_db
from app.schemas.lead import LeadCreate, LeadRead
from app.services.triage import determine_urgency


router = APIRouter(prefix="/api/leads", tags=["leads"])


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
    db.commit()
    db.refresh(lead)
    return lead
