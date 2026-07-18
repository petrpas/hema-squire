from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEMA_SQUIRE_", env_file=".env")

    database_url: str = "sqlite:///./hema_squire.sqlite"
    secret_key: str = "dev-only-secret-change-me-in-production!"
    token_ttl_hours: int = 24 * 14
    email_outbox_dir: str = "./outbox"
    email_sender: str = "noreply@hemasquire.local"


settings = Settings()
