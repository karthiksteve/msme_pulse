from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import NeedPrediction, MSME, NeedCategory
from app.schemas import NeedPredictionCreate, NeedPredictionResponse

router = APIRouter(prefix="/predictions", tags=["Need Predictions"])


@router.post("", response_model=NeedPredictionResponse, status_code=201)
async def create_need_prediction(prediction: NeedPredictionCreate, db: AsyncSession = Depends(get_db)):
    msme_result = await db.execute(select(MSME).where(MSME.id == prediction.msme_id))
    if not msme_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="MSME not found")

    db_prediction = NeedPrediction(**prediction.model_dump())
    db.add(db_prediction)
    await db.commit()
    await db.refresh(db_prediction)
    return db_prediction


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
        raise HTTPException(status_code=404, detail="No need prediction found")
    return prediction


@router.get("/{prediction_id}", response_model=NeedPredictionResponse)
async def get_need_prediction(prediction_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NeedPrediction).where(NeedPrediction.id == prediction_id))
    prediction = result.scalar_one_or_none()
    if not prediction:
        raise HTTPException(status_code=404, detail="Need prediction not found")
    return prediction


@router.get("/distribution", response_model=List[dict])
async def get_need_distribution(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NeedPrediction.top_need, NeedPrediction.confidence_score)
    )
    predictions = result.all()

    if not predictions:
        return []

    from collections import Counter
    category_counts = Counter(p[0] for p in predictions if p[0])
    avg_confidence = {}

    for cat, conf in predictions:
        if cat:
            if cat not in avg_confidence:
                avg_confidence[cat] = []
            avg_confidence[cat].append(conf)

    return [
        {
            "category": cat.value if hasattr(cat, 'value') else str(cat),
            "count": count,
            "percentage": count / len(predictions) * 100,
            "avg_confidence": sum(avg_confidence.get(cat, [0])) / len(avg_confidence.get(cat, [1])),
        }
        for cat, count in category_counts.items()
    ]