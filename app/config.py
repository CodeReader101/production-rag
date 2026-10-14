"""
Centralized Configuration
uses pydantic-settings for validated environment variables.
"""

# pydantic settings validates the config at load times and crash when not validated 
# so we find about missing parameter at the start 
# and not between the requests 


import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration settings.
    Environment variables will override defaults
    """

    # Server settings
    SERVER_HOST: str = ""

    # LLM Configuration
    openrouter_api_key: str
    primary_model: str = "gpt-4o-mini"
    fallback_model: str = "gpt-4o-mini"

    # LANGSMITH
    langsmith_tracing: bool = True
    langsmith_api_key: str = ""
    langsmith_project: str = "production-api"

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    rate_limit: str = "20/minute"
    cache_ttl_seconds: int = 300
    max_retries: int = 3

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


def _export_langsmith_env(settings: "Settings") -> None:
    """
    pydantic-settings reads .env directly into the Settings object and
    never touches os.environ. The langsmith SDK (and LangChain's own
    tracing callback) read os.environ directly, so without this step
    LANGSMITH_TRACING / LANGSMITH_API_KEY are invisible to them even
    though Settings loaded correctly.
    """
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project


# lru_cache so once the settings is loaded it stays in the cache don't need to reload it
@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - loaded once, reused everywhere."""
    settings = Settings()
    _export_langsmith_env(settings)
    return settings