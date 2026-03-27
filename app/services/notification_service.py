from dataclasses import dataclass
from typing import Protocol

from app.db.models import Customer, Lead


@dataclass(frozen=True)
class NotificationResult:
    provider: str
    status: str
    provider_message_id: str


class SmsProvider(Protocol):
    def send_sms(self, recipient: str, body: str) -> NotificationResult:
        ...


class NotificationService:
    def __init__(self, sms_provider: SmsProvider) -> None:
        self.sms_provider = sms_provider

    def build_lead_confirmation(self, customer: Customer, lead: Lead) -> str:
        return (
            f"Hi {customer.name}, we received your plumbing request "
            f"and classified it as {lead.urgency}. "
            "A team member will follow up shortly."
        )

    def send_lead_confirmation(self, customer: Customer, lead: Lead) -> tuple[str, NotificationResult]:
        message_body = self.build_lead_confirmation(customer, lead)
        result = self.sms_provider.send_sms(customer.phone, message_body)
        return message_body, result
