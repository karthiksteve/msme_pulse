from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import ProductRecommendation, MSME, NeedPrediction, ProductType
from app.schemas import ProductRecommendationCreate, ProductRecommendationResponse

router = APIRouter(prefix="/recommendations", tags=["Product Recommendations"])


@router.post("", response_model=ProductRecommendationResponse, status_code=201)
async def create_product_recommendation(
    recommendation: ProductRecommendationCreate, db: AsyncSession = Depends(get_db)
):
    msme_result = await db.execute(select(MSME).where(MSME.id == recommendation.msme_id))
    if not msme_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="MSME not found")

    if recommendation.need_prediction_id:
        np_result = await db.execute(
            select(NeedPrediction).where(NeedPrediction.id == recommendation.need_prediction_id)
        )
        if not np_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Need prediction not found")

    db_rec = ProductRecommendation(**recommendation.model_dump())
    db.add(db_rec)
    await db.commit()
    await db.refresh(db_rec)
    return db_rec


@router.get("/msme/{msme_id}", response_model=List[ProductRecommendationResponse])
async def get_recommendations_by_msme(
    msme_id: UUID,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ProductRecommendation).where(ProductRecommendation.msme_id == msme_id)

    if status:
        query = query.where(ProductRecommendation.status == status)

    query = query.order_by(ProductRecommendation.rank)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{rec_id}", response_model=ProductRecommendationResponse)
async def get_recommendation(rec_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProductRecommendation).where(ProductRecommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Product recommendation not found")
    return rec


@router.patch("/{rec_id}/status")
async def update_recommendation_status(
    rec_id: UUID, status: str, db: AsyncSession = Depends(get_db)
):
    valid_statuses = ["generated", "sent", "viewed", "applied", "approved", "rejected"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    result = await db.execute(select(ProductRecommendation).where(ProductRecommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Product recommendation not found")

    rec.status = status
    await db.commit()
    await db.refresh(rec)
    return {"message": f"Status updated to {status}", "recommendation_id": str(rec_id)}


@router.get("/stats/summary", response_model=List[dict])
async def get_product_match_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            ProductRecommendation.product_type,
            func.count(ProductRecommendation.id).label("count"),
            func.avg(ProductRecommendation.eligibility_score).label("avg_eligibility"),
            func.avg(ProductRecommendation.ranking_score).label("avg_ranking"),
            func.sum(ProductRecommendation.suggested_amount).label("total_amount"),
        ).group_by(ProductRecommendation.product_type)
    )
    stats = result.all()

    return [
        {
            "product_type": s.product_type.value if hasattr(s.product_type, 'value') else str(s.product_type),
            "recommendations": s.count,
            "avg_eligibility": round(s.avg_eligibility, 4) if s.avg_eligibility else 0,
            "avg_ranking_score": round(s.avg_ranking, 4) if s.avg_ranking else 0,
            "estimated_disbursement_cr": round(s.total_amount / 1e7, 2) if s.total_amount else 0,
        }
        for s in stats
    ]