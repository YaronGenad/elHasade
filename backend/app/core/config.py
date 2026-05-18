from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Redis (optional – required for Sprint 3 caching)
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # LLM Providers
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    GEMINI_API_KEY_2: str = Field(default="", env="GEMINI_API_KEY_2")
    ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")

    # Image providers
    PEXELS_API_KEY: str = Field(default="", env="PEXELS_API_KEY")

    # File Storage
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    MAX_FILE_SIZE: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    OUTPUT_DIR: str = Field(default="./output", env="OUTPUT_DIR")
    MAX_FILE_AGE_HOURS: int = Field(default=24, env="MAX_FILE_AGE_HOURS")

    # Search
    VECTOR_SIMILARITY_THRESHOLD: float = Field(default=0.15, env="VECTOR_SIMILARITY_THRESHOLD")

    # CORS – comma-separated list of allowed origins
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        env="CORS_ORIGINS",
    )

    # Rate limiting (slowapi format: "N/period")
    AUTH_RATE_LIMIT: str = Field(default="10/minute", env="AUTH_RATE_LIMIT")
    GENERATION_RATE_LIMIT: str = Field(default="5/minute", env="GENERATION_RATE_LIMIT")

    # Application
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()