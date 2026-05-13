from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://cove:cove-dev@localhost:5432/cove"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"

    model_config = {"env_prefix": "COVE_", "env_file": ".env"}


settings = Settings()
