from pydantic_settings import BaseSettings, SettingsConfigDict

# The signing key every dev checkout shares. It is published in this repository,
# so the application refuses to start on it unless debug is set explicitly
# (app.main); anyone who can read GitHub can otherwise forge any account's token.
DEV_SECRET_KEY = "dev-only-secret-change-me-in-production!"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEMA_SQUIRE_", env_file=".env")

    database_url: str = "sqlite:///./hema_squire.sqlite"
    secret_key: str = DEV_SECRET_KEY
    # set by dev.sh and the test suite; the only exemption from the startup
    # refusal above, and never set on a deployment
    debug: bool = False
    # the deployment Owner's account email; computed, never stored, so the
    # designation applies even when the account signs up after deployment
    owner_email: str = ""
    token_ttl_hours: int = 24 * 14
    email_outbox_dir: str = "./outbox"
    email_sender: str = "noreply@hemasquire.local"
    # Mail delivery is chosen by configuration presence, not by a mode flag: a
    # set smtp_host means mail is real (app.mail.get_mailer). Unset — every dev
    # checkout — keeps the file outbox.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    # login/signup throttling (app.ratelimit); off only in the test suite, where
    # many requests legitimately come from one address inside one minute
    rate_limit_enabled: bool = True
    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 300
    # startup recovery of operations a dead process left running (design D5);
    # off in the test suite, where the app boots against the configured
    # database while the tests themselves run on an in-memory one
    operations_sweep_enabled: bool = True
    # LLM is used only on the table-import path (parse, match, dedup)
    anthropic_api_key: str = ""
    # an identity-linked key acts inside one workspace and the API demands its
    # id on every request (app.llm); an organisation key needs no id
    anthropic_workspace_id: str = ""
    llm_model: str = "anthropic:claude-sonnet-5"
    # service-account JSON for the Google Sheets export
    google_credentials_path: str = ""
    # fighters index auto-population at startup when empty (Decision 8)
    hr_auto_refresh: bool = True
    hr_fetch_delay_seconds: float = 0.3


settings = Settings()
