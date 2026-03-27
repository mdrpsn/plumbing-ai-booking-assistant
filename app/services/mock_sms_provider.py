from app.services.notification_service import NotificationResult


class MockSmsProvider:
    provider_name = "mock-sms"

    def send_sms(self, recipient: str, body: str) -> NotificationResult:
        normalized_recipient = "".join(character for character in recipient if character.isdigit()) or "unknown"
        body_fingerprint = sum(ord(character) for character in body) % 10000
        provider_message_id = f"{self.provider_name}-{normalized_recipient}-{body_fingerprint:04d}"
        return NotificationResult(
            provider=self.provider_name,
            status="sent",
            provider_message_id=provider_message_id,
        )
