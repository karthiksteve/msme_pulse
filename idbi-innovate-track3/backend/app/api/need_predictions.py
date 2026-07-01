from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.models import NeedPrediction, MSME, NeedCategory
from app.schemas import NeedPredictionCreate, NeedPredictionResponse, NeedDistribution

router = APIRouter(prefix="/need-predictions", tags=["Need Predictions"])


@router.post("/", response_model=NeedPredictionResponse, status_code=201)
async def create_need_prediction(prediction: NeedPredictionCreate, db: AsyncSession = Depends(get_db)):
    msme_result = await db.execute(select(MSME).where(MSME.id == prediction.msme_id))
    if not msme_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="MSME not found")

    db_pred = NeedPrediction(**prediction.model_dump())
    db.add(db_pred)
    await db.commit()
    await db.refresh(db_pred)
    return db_pred


@router.get("/msme/{msme_id}", response_model=List[NeedPredictionResponse])
async def get_need_predictions_by_msme(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NeedPrediction)
        .where(NeedPrediction.msme_id == msme_id)
        .order_by(NeedPrediction.prediction_date.desc())
    )
    return result.scalars().all()


@router.get("/msme/{msme_id}/latest", response_model=NeedPredictionResponse)
async def get_latest_need_prediction(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NeedPrediction)
        .where(NeedPrediction.msme_id == msme_id)
        .order_by(NeedPrediction.prediction_date.desc())
        .limit(1)
    )
    prediction = result.scalar_one_or_none()
    if not prediction:
        raise HTTPException(status_code=404, detail="No need prediction found for this MSME")
    return prediction


@router.get("/{prediction_id}", response_model=NeedPredictionResponse)
async def get_need_prediction(prediction_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NeedPrediction).where(NeedPrediction.id == prediction_id))
    prediction = result.scalar_one_or_none()
    if not prediction:
        raise HTTPException(status_code=404, detail="Need prediction not found")
    return prediction


@router.get("/analytics/distribution", response_model=List[NeedDistribution])
async def get_need_distribution(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            NeedPrediction.top_need,
            func.count(NeedPrediction.id).label("count"),
            func.avg(NeedPrediction.confidence_score).label("avg_confidence"),
        )
        .where(NeedPrediction.prediction_date >= cutoff)
        .where(NeedPrediction.top_need.isnot(None))
        .group_by(NeedPrediction.top_need)
    )

    rows = result.all()
    total = sum(r.count for r in rows)
    return [
        NeedDistribution(
            category=r.top_need,
            count=r.count,
            percentage=r.count / total * 100 if total > 0 else 0,
            avg_confidence=float(r.avg_confidence) if r.avg_confidence else 0,
        )
        for r in rows
    ]


@router.get("/analytics/trends")
async def get_need_trends(
    days: int = Query(90, ge=1, le=365),
    category: Optional[NeedCategory] = None,
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = select(
        func.date_trunc("day", NeedPrediction.prediction_date).label("date"),
        NeedPrediction.top_need,
        func.count(NeedPrediction.id).label("count"),
    ).where(NeedPrediction.prediction_date >= cutoff)

    if category:
        query = query.where(NeedPrediction.top_need == category)

    query = query.group_by("date", NeedPrediction.top_need).order_by("date")

    result = await db.execute(query)
    return [
        {"date": r.date, "category": r.top_need, "count": r.count}
        for r in result.all()
    ]