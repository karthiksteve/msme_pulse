from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.models import MSME, GSTReturn, AAAccount, NeedPrediction, ProductRecommendation, MSMEStatus, NeedCategory, ProductType
from app.schemas import PortfolioHeatmap, NeedDistribution, ProductMatchStats, HealthResponse

router = APIRouter(prefix="", tags=["Dashboard"])


@router.get("/portfolio/heatmap", response_model=List[PortfolioHeatmap])
async def get_portfolio_heatmap(
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(
        MSME.state,
        MSME.nic_code,
        func.count(MSME.id).label("total_msmes"),
        func.sum(
            func.case((MSME.need_predictions.any(), 1), else_=0)
        ).label("served_msmes"),
    ).group_by(MSME.state, MSME.nic_code)

    if state:
        query = query.where(MSME.state == state)

    result = await db.execute(query)
    rows = result.all()

    heatmap = []
    for row in rows:
        total = row.total_msmes
        served = row.served_msmes or 0
        unserved = total - served

        need_result = await db.execute(
            select(
                func.avg(NeedPrediction.confidence_score).label("avg_score"),
                func.mode().within_group(NeedPrediction.top_need).label("top_need"),
            )
            .select_from(NeedPrediction)
            .join(MSME, NeedPrediction.msme_id == MSME.id)
            .where(and_(MSME.state == row.state, MSME.nic_code == row.nic_code))
        )
        need_row = need_result.first()

        avg_score = float(need_row.avg_score) if need_row and need_row.avg_score else 0
        top_need = need_row.top_need if need_row and need_row.top_need else NeedCategory.WORKING_CAPITAL

        heatmap.append(PortfolioHeatmap(
            state=row.state or "Unknown",
            nic_code=row.nic_code or "Unknown",
            total_msmes=total,
            unserved_msmes=unserved,
            avg_need_score=avg_score,
            top_need_category=top_need,
            estimated_opportunity_cr=unserved * 50 / 1e7,
        ))

    return heatmap


@router.get("/portfolio/need-distribution", response_model=List[NeedDistribution])
async def get_portfolio_need_distribution(
    state: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = select(
        NeedPrediction.top_need,
        func.count(NeedPrediction.id).label("count"),
        func.avg(NeedPrediction.confidence_score).label("avg_confidence"),
    ).where(
        and_(NeedPrediction.prediction_date >= cutoff, NeedPrediction.top_need.isnot(None))
    )

    if state:
        query = query.join(MSME, NeedPrediction.msme_id == MSME.id).where(MSME.state == state)

    query = query.group_by(NeedPrediction.top_need)
    result = await db.execute(query)
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


@router.get("/portfolio/product-stats", response_model=List[ProductMatchStats])
async def get_portfolio_product_stats(
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(
        ProductRecommendation.product_type,
        func.count(ProductRecommendation.id).label("count"),
        func.avg(ProductRecommendation.eligibility_score).label("avg_eligibility"),
        func.avg(ProductRecommendation.ranking_score).label("avg_ranking"),
        func.sum(ProductRecommendation.suggested_amount).label("total_amount"),
    )

    if state:
        query = query.join(MSME, ProductRecommendation.msme_id == MSME.id).where(MSME.state == state)

    query = query.group_by(ProductRecommendation.product_type)
    result = await db.execute(query)
    rows = result.all()

    return [
        ProductMatchStats(
            product_type=r.product_type,
            recommendations=r.count,
            avg_eligibility=float(r.avg_eligibility) if r.avg_eligibility else 0,
            avg_ranking_score=float(r.avg_ranking) if r.avg_ranking else 0,
            estimated_disbursement_cr=float(r.total_amount) / 1e7 if r.total_amount else 0,
        )
        for r in rows
    ]


@router.get("/portfolio/summary")
async def get_portfolio_summary(db: AsyncSession = Depends(get_db)):
    total_msmes = (await db.execute(select(func.count(MSME.id)))).scalar()
    active_msmes = (await db.execute(select(func.count(MSME.id)).where(MSME.status == MSMEStatus.ACTIVE))).scalar()

    gst_filed = (await db.execute(
        select(func.count(func.distinct(GSTReturn.msme_id)))
        .where(GSTReturn.filing_status == "FILED")
    )).scalar()

    aa_accounts = (await db.execute(select(func.count(AAAccount.id)))).scalar()

    need_predictions = (await db.execute(select(func.count(NeedPrediction.id)))).scalar()

    recommendations = (await db.execute(select(func.count(ProductRecommendation.id)))).scalar()
    approved_recs = (await db.execute(
        select(func.count(ProductRecommendation.id)).where(ProductRecommendation.status == "approved")
    )).scalar()

    return {
        "total_msmes": total_msmes,
        "active_msmes": active_msmes,
        "msmes_with_gst": gst_filed,
        "msmes_with_aa": (await db.execute(select(func.count(func.distinct(AAAccount.msme_id))))).scalar(),
        "need_predictions_generated": need_predictions,
        "product_recommendations": recommendations,
        "approved_recommendations": approved_recs,
        "conversion_rate": approved_recs / recommendations * 100 if recommendations > 0 else 0,
    }


@router.get("/msme/{msme_id}/full")
async def get_full_msme_profile(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    msme_result = await db.execute(select(MSME).where(MSME.id == msme_id))
    msme = msme_result.scalar_one_or_none()
    if not msme:
        return {"error": "MSME not found"}

    gst_result = await db.execute(
        select(GSTReturn).where(GSTReturn.msme_id == msme_id).order_by(GSTReturn.tax_period.desc()).limit(12)
    )
    gst_returns = gst_result.scalars().all()

    aa_result = await db.execute(select(AAAccount).where(AAAccount.msme_id == msme_id))
    aa_accounts = aa_result.scalars().all()

    need_result = await db.execute(
        select(NeedPrediction).where(NeedPrediction.msme_id == msme_id).order_by(NeedPrediction.prediction_date.desc()).limit(1)
    )
    latest_need = need_result.scalar_one_or_none()

    rec_result = await db.execute(
        select(ProductRecommendation).where(ProductRecommendation.msme_id == msme_id).order_by(ProductRecommendation.rank)
    )
    recommendations = rec_result.scalars().all()

    return {
        "msme": msme,
        "gst_returns": gst_returns,
        "aa_accounts": aa_accounts,
        "latest_need_prediction": latest_need,
        "product_recommendations": recommendations,
    }