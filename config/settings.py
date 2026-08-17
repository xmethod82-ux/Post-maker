"""
Bot configuration loaded from environment variables via pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    BOT_TOKEN: str
    DATABASE_PATH: str = "bot.db"
    LOG_LEVEL: str = "INFO"


settings = Settings()
