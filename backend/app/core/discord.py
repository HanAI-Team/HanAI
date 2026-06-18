import httpx
from app.core.config import settings


async def notify_discord(message: str) -> None:
    if not settings.DISCORD_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(settings.DISCORD_WEBHOOK_URL, json={"content": message})
    except Exception:
        pass
