from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Plumbing AI Booking Assistant"
    database_url: str = "sqlite:///./plumbing_assistant.db"
    follow_up_delay_minutes: int = 30
    sms_provider: str = "mock"
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_phone: str | None = None
    twilio_api_base_url: str = "https://api.twilio.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
