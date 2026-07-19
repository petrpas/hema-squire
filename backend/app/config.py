from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEMA_SQUIRE_", env_file=".env")

    database_url: str = "sqlite:///./hema_squire.sqlite"
    secret_key: str = "dev-only-secret-change-me-in-production!"
    # the deployment Owner's account email; computed, never stored, so the
    # designation applies even when the account signs up after deployment
    owner_email: str = ""
    token_ttl_hours: int = 24 * 14
    email_outbox_dir: str = "./outbox"
    email_sender: str = "noreply@hemasquire.local"
    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 300
    # LLM is used only on the table-import path (parse, match, dedup)
    anthropic_api_key: str = ""
    llm_model: str = "anthropic:claude-sonnet-5"
    # service-account JSON for the Google Sheets export
    google_credentials_path: str = ""
    # fighters index auto-population at startup when empty (Decision 8)
    hr_auto_refresh: bool = True
    hr_fetch_delay_seconds: float = 0.3


settings = Settings()
