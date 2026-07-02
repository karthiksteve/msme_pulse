from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
from datetime import datetime

from app.database import get_db, engine
from app.config import settings
from app.schemas import HealthResponse

router = APIRouter(prefix="", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "healthy"
    redis_status = "healthy"
    models_loaded = False

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        await r.ping()
        await r.close()
    except Exception:
        redis_status = "unhealthy"

    try:
        from app.services.ml_service import ml_service
        models_loaded = ml_service.is_ready()
    except Exception:
        models_loaded = False

    overall = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.VERSION,
        database=db_status,
        redis=redis_status,
        models_loaded=models_loaded,
        timestamp=datetime.utcnow(),
    )


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return {"status": "not ready"}, 503


@router.get("/live")
async def liveness_check():
    return {"status": "alive"}