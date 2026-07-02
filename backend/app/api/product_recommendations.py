from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models import ProductRecommendation, MSME, NeedPrediction, ProductType
from app.schemas import ProductRecommendationCreate, ProductRecommendationResponse, ProductMatchStats

router = APIRouter(prefix="/recommendations", tags=["Product Recommendations"])


@router.post("/", response_model=ProductRecommendationResponse, status_code=201)
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


@router.post("/batch", response_model=List[ProductRecommendationResponse], status_code=201)
async def create_batch_recommendations(
    recommendations: List[ProductRecommendationCreate], db: AsyncSession = Depends(get_db)
):
    db_recs = [ProductRecommendation(**r.model_dump()) for r in recommendations]
    db.add_all(db_recs)
    await db.commit()
    for rec in db_recs:
        await db.refresh(rec)
    return db_recs


@router.get("/msme/{msme_id}", response_model=List[ProductRecommendationResponse])
async def get_recommendations_by_msme(
    msme_id: UUID,
    status: Optional[str] = None,
    product_type: Optional[ProductType] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ProductRecommendation).where(ProductRecommendation.msme_id == msme_id)

    if status:
        query = query.where(ProductRecommendation.status == status)
    if product_type:
        query = query.where(ProductRecommendation.product_type == product_type)

    query = query.order_by(ProductRecommendation.rank)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{recommendation_id}", response_model=ProductRecommendationResponse)
async def get_recommendation(recommendation_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProductRecommendation).where(ProductRecommendation.id == recommendation_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Product recommendation not found")
    return rec


@router.patch("/{recommendation_id}/status", response_model=ProductRecommendationResponse)
async def update_recommendation_status(
    recommendation_id: UUID, status: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProductRecommendation).where(ProductRecommendation.id == recommendation_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Product recommendation not found")

    rec.status = status
    await db.commit()
    await db.refresh(rec)
    return rec


@router.get("/analytics/stats", response_model=List[ProductMatchStats])
async def get_product_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            ProductRecommendation.product_type,
            func.count(ProductRecommendation.id).label("count"),
            func.avg(ProductRecommendation.eligibility_score).label("avg_eligibility"),
            func.avg(ProductRecommendation.ranking_score).label("avg_ranking"),
            func.sum(ProductRecommendation.suggested_amount).label("total_amount"),
        )
        .group_by(ProductRecommendation.product_type)
    )

    return [
        ProductMatchStats(
            product_type=r.product_type,
            recommendations=r.count,
            avg_eligibility=float(r.avg_eligibility) if r.avg_eligibility else 0,
            avg_ranking_score=float(r.avg_ranking) if r.avg_ranking else 0,
            estimated_disbursement_cr=float(r.total_amount) / 1e7 if r.total_amount else 0,
        )
        for r in result.all()
    ]


@router.get("/analytics/conversion-funnel")
async def get_conversion_funnel(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            ProductRecommendation.status,
            func.count(ProductRecommendation.id).label("count"),
        ).group_by(ProductRecommendation.status)
    )
    return {r.status: r.count for r in result.all()}