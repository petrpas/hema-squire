from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEMA_SQUIRE_", env_file=".env")

    database_url: str = "sqlite:///./hema_squire.sqlite"
    secret_key: str = "dev-secret-change-in-production"
    token_ttl_hours: int = 24 * 14


settings = Settings()
