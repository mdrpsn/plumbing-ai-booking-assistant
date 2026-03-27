from functools import lru_cache

from app.core.config import get_settings
from app.services.mock_sms_provider import MockSmsProvider
from app.services.notification_service import NotificationService, SmsProvider
from app.services.twilio_sms_provider import TwilioSmsProvider


@lru_cache
def get_sms_provider() -> SmsProvider:
    settings = get_settings()
    provider_name = settings.sms_provider.strip().lower()

    if provider_name == "mock":
        return MockSmsProvider()
    if provider_name == "twilio":
        return TwilioSmsProvider(settings)

    raise ValueError(f"Unsupported SMS provider: {settings.sms_provider}")


@lru_cache
def get_notification_service() -> NotificationService:
    return NotificationService(sms_provider=get_sms_provider())
