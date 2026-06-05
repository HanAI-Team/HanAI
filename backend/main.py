import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.redis import check_rate_limit
from app.auth.router import router as auth_router
from app.diagnosis.router import router as diagnosis_router
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://zinmac.ai",
        "https://zinmac.vercel.app",
    ],
    allow_origin_regex=r"https://zinmac.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def discord_error_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            await notify_discord(
                f"500 에러 발생\nPath: {request.method} {request.url.path}"
            )
        return response
    except Exception as e:
        await notify_discord(
            f"서버 에러\nPath: {request.method} {request.url.path}\nError: {str(e)}"
        )
        return JSONResponse(
            status_code=500, content={"detail": "서버 오류가 발생했습니다."}
        )


RATE_LIMIT_PATHS = {
    "/api/auth/login": {"limit": 5, "window_seconds": 60},
    "/api/diagnosis/ask": {"limit": 3, "window_seconds": 30},
    "/api/diagnosis/analyze": {"limit": 3, "window_seconds": 30},
}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in RATE_LIMIT_PATHS:
        ip = request.client.host if request.client else "unknown"
        config = RATE_LIMIT_PATHS[path]
        allowed = await check_rate_limit(
            key=f"{ip}:{path}",
            limit=config["limit"],
            window_seconds=config["window_seconds"],
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."},
            )
    response = await call_next(request)
    return response


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
