from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = ""
    JWT_SECRET_KEY: str = ""

    DEBUG: bool = False
    TESTING: bool = False

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    ANTHROPIC_API_KEY: Optional[str] = None
    CLOVA_CLIENT_ID: Optional[str] = None
    CLOVA_CLIENT_SECRET: Optional[str] = None
    CLOVA_SECRET_KEY: Optional[str] = None   # 추가
    CLOVA_INVOKE_URL: Optional[str] = None   # 추가
    RTZR_CLIENT_ID: Optional[str] = None
    RTZR_CLIENT_SECRET: Optional[str] = None
    CODEF_CLIENT_ID: Optional[str] = None
    CODEF_CLIENT_SECRET: Optional[str] = None
    CODEF_PUBLIC_KEY: Optional[str] = None
    UPSTASH_REDIS_URL: Optional[str] = None
    UPSTASH_REDIS_TOKEN: Optional[str] = None
    DATAHUB_TOKEN: Optional[str] = None
    DATAHUB_ENC_KEY: Optional[str] = None
    DATAHUB_ENC_IV: Optional[str] = None
    DATAHUB_URL: str = "https://datahub-dev.scraping.co.kr"
    ADMIN_API_KEY: str = ""
    SENTRY_DSN: str = ""
    DISCORD_WEBHOOK_URL: Optional[str] = None
    RRN_ENCRYPTION_KEY:str = ""
    TOSS_SECRET_KEY :Optional[str] = None
    TOSS_CLINET_KEY:Optional[str] = None
    TOSS_WEBHOOK_SECRET: Optional[str] = None
    PADDLE_API_KEY: Optional[str] = None
    PADDLE_API_BASE_URL: str = "https://sandbox-api.paddle.com"  # 정식 전환 시 https://api.paddle.com 로 교체

    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = ""
settings = Settings()