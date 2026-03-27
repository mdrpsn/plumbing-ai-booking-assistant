import base64
import hashlib
import hmac
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


def verify_twilio_request_or_raise(request: Request, form_data: dict[str, str]) -> None:
    settings = get_settings()
    if settings.sms_provider.strip().lower() == "mock":
        return
    if not settings.twilio_webhook_verification_enabled:
        return
    if settings.sms_provider.strip().lower() != "twilio":
        return
    if not settings.twilio_auth_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twilio webhook verification is enabled but TWILIO_AUTH_TOKEN is not configured",
        )

    provided_signature = request.headers.get("X-Twilio-Signature")
    if not provided_signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing Twilio signature",
        )

    expected_signature = _build_twilio_signature(
        auth_token=settings.twilio_auth_token,
        url=str(request.url),
        form_data=form_data,
    )
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature",
        )


def _build_twilio_signature(auth_token: str, url: str, form_data: dict[str, str]) -> str:
    canonical_url = _canonicalize_url(url)
    payload = canonical_url + "".join(
        f"{key}{form_data[key]}"
        for key in sorted(form_data)
    )
    digest = hmac.new(
        auth_token.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
