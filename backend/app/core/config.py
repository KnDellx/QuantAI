"""Application configuration loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the stock agent."""

    model_config = SettingsConfigDict(
        env_file=".env.example",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://gw-stg.tradingbase.ai/v1",
        alias="OPENAI_BASE_URL",
    )
    openai_model: str = Field(default="gpt-4.1", alias="OPENAI_MODEL")
    tushare_token: str | None = Field(default=None, alias="TUSHARE_TOKEN")
    tool_top_k: int = Field(default=5, ge=1, le=8)


def get_settings() -> Settings:
    """Load application settings."""

    return Settings()
