import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.auth.router import router as auth_router
from app.diagnosis.router import router as diagnosis_router
from app.core.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.1,
        environment="production" if not settings.DEBUG else "development",
    )

from app.charting.router import router as charting_router
from app.patients.router import router as patients_router
from app.subscription.router import router as subscription_router

async def notify_discord(message: str):
    if not settings.DISCORD_WEBHOOK_URL:
        return
    async with httpx.AsyncClient() as client:
        await client.post(settings.DISCORD_WEBHOOK_URL, json={"content": message})


app = FastAPI(title="HanAI API")


@app.middleware("http")
async def discord_error_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            await notify_discord(f"🚨 500 에러 발생\nPath: {request.method} {request.url.path}")
        return response
    except Exception as e:
        await notify_discord(f"🚨 서버 에러\nPath: {request.method} {request.url.path}\nError: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": "서버 오류가 발생했습니다."})

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(diagnosis_router, prefix="/api/diagnosis", tags=["diagnosis"])
app.include_router(charting_router, prefix="/api/charting", tags=["charting"])
app.include_router(patients_router, prefix="/api/patients", tags=["patients"])
app.include_router(
    subscription_router, prefix="/api/subscription", tags=["subscription"]
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
