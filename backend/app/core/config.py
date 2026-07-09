from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = ""
    JWT_SECRET_KEY: str = ""

    DEBUG: bool = False
    TESTING: bool = False

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    ANTHROPIC_API_KEY: Optional[str] = None
    CLOVA_CLIENT_ID: Optional[str] = None
    CLOVA_CLIENT_SECRET: Optional[str] = None
    CLOVA_SECRET_KEY: Optional[str] = None   # 추가
    CLOVA_INVOKE_URL: Optional[str] = None   # 추가
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


settings = Settings()