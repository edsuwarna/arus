from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "arus"
    db_password: str = "arus_secret"
    db_name: str = "arus_warehouse"

    jwt_secret: str = "change-me-in-production"
    encryption_key: str = ""

    log_level: str = "INFO"
    default_schedule: str = "*/5 * * * *"
    batch_size: int = 10000
    retry_max: int = 3

    # Phase 2: Retry + backoff
    max_retries: int = 3
    initial_backoff: int = 2  # seconds

    # Phase 2: Schema drift
    auto_alter_schema: bool = False

    # Phase 2: Data quality
    quality_check_threshold: float = 5.0  # percentage

    # Phase 2: Alert / Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Admin seed credentials
    admin_email: str = "admin@arus.io"
    admin_password: str = "admin123"

    tz: str = "UTC"

    model_config = {"env_prefix": "arus_"}


settings = Settings()
