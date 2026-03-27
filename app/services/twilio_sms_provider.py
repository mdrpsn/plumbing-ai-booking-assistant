import httpx

from app.core.config import Settings
from app.services.notification_service import NotificationResult


class TwilioSmsProvider:
    provider_name = "twilio"

    def __init__(self, settings: Settings) -> None:
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_phone = settings.twilio_from_phone
        self.api_base_url = settings.twilio_api_base_url.rstrip("/")
        self.status_callback_url = settings.twilio_status_callback_url

        missing_fields = [
            field_name
            for field_name, value in (
                ("TWILIO_ACCOUNT_SID", self.account_sid),
                ("TWILIO_AUTH_TOKEN", self.auth_token),
                ("TWILIO_FROM_PHONE", self.from_phone),
            )
            if not value
        ]
        if missing_fields:
            raise ValueError(
                "Twilio SMS provider requires configuration for: "
                + ", ".join(missing_fields)
            )

    def send_sms(self, recipient: str, body: str) -> NotificationResult:
        request_data = {
            "From": self.from_phone,
            "To": recipient,
            "Body": body,
        }
        if self.status_callback_url:
            request_data["StatusCallback"] = self.status_callback_url

        response = httpx.post(
            f"{self.api_base_url}/2010-04-01/Accounts/{self.account_sid}/Messages.json",
            auth=(self.account_sid, self.auth_token),
            data=request_data,
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        return NotificationResult(
            provider=self.provider_name,
            status=payload.get("status", "queued"),
            provider_message_id=payload["sid"],
        )
