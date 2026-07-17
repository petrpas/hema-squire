from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEMA_SQUIRE_", env_file=".env")

    database_url: str = "sqlite:///./hema_squire.sqlite"


settings = Settings()
