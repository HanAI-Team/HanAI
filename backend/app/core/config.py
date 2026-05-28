from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    JWT_SECRET_KEY: str

    DEBUG: bool = False

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    ANTHROPIC_API_KEY: Optional[str] = None
    CLOVA_CLIENT_ID: Optional[str] = None
    CLOVA_CLIENT_SECRET: Optional[str] = None
    CODEF_CLIENT_ID: Optional[str] = None
    CODEF_CLIENT_SECRET: Optional[str] = None
    CODEF_PUBLIC_KEY: Optional[str] = None
    UPSTASH_REDIS_URL: Optional[str] = None
    UPSTASH_REDIS_TOKEN: Optional[str] = None
    ADMIN_API_KEY: str = ""


settings = Settings()
