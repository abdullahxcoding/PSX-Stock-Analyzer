from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_db: str = "psx_shariah_analyzer"

    # Telegram (placeholder for Phase 8)
    telegram_bot_token: str | None = None

    # Scraper hygiene
    scraper_user_agent: str = "PSX-Shariah-Analyzer/0.1 (personal research tool)"
    scraper_request_delay_seconds: float = 1.0
    scraper_max_retries: int = 3
    scraper_backoff_factor: float = 2.0
    scraper_timeout_seconds: int = 15

    # Scheduler
    intraday_poll_interval_seconds: int = 15
    market_open_time: str = "09:15"
    market_close_time: str = "15:30"
    market_timezone: str = "Asia/Karachi"

    # App
    log_level: str = "INFO"
    env: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )


settings = Settings()
