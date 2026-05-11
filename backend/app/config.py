from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ClinicAI Sentinel API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    google_client_id: str = ""
    database_url: str = "sqlite:///./clinicai_sentinel.db"
    model_artifact_path: str = "backend/artifacts/clinicai_baseline_model.json"
    app_jwt_secret: str = "change-me-in-production"
    app_jwt_algorithm: str = "HS256"
    app_jwt_expiration_hours: int = 24
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_sender: str = "alerts@clinicai-sentinel.local"
    smtp_use_tls: bool = True
    email_outbox_path: str = "backend/outbox"
    sms_provider_url: str = ""
    sms_api_key: str = ""
    sms_sender_id: str = "ClinicAI"
    sms_outbox_path: str = "backend/outbox/sms"
    whatsapp_provider_url: str = ""
    whatsapp_api_key: str = ""
    whatsapp_sender_id: str = "ClinicAI"
    whatsapp_outbox_path: str = "backend/outbox/whatsapp"
    termii_base_url: str = ""
    termii_api_key: str = ""
    termii_sender_id: str = "ClinicAI"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_sms_from: str = ""
    twilio_whatsapp_from: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def allowed_frontend_origins() -> list[str]:
    origins = [item.strip() for item in settings.frontend_origins.split(",") if item.strip()]
    if settings.frontend_origin not in origins:
        origins.append(settings.frontend_origin)
    return origins
