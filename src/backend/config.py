from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    environment: str = Field(default="development", description="Runtime environment")
    llm_provider: str = Field(default="openai", description="LLM service provider")
    embedding_provider: str = Field(default="openai", description="Embedding service provider")

    class Config:
        env_file = ".env"


settings = Settings()
