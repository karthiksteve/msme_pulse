from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models import MSME, GSTReturn, AAAccount, NeedPrediction, ProductRecommendation, MSMEStatus, NeedCategory
from app.schemas import (
    MSMECreate, MSMEUpdate, MSMEResponse, MSMEListResponse,
    MSMESearchFilters, MSMEDashboardSummary,
    GSTReturnCreate, GSTReturnResponse,
    AAAccountCreate, AAAccountResponse,
    NeedPredictionCreate, NeedPredictionResponse,
    ProductRecommendationCreate, ProductRecommendationResponse,
)

router = APIRouter(prefix="/msmes", tags=["MSMEs"])


@router.post("/", response_model=MSMEResponse, status_code=201)
async def create_msme(msme: MSMECreate, db: AsyncSession = Depends(get_db)):
    db_msme = MSME(**msme.model_dump())
    db.add(db_msme)
    await db.commit()
    await db.refresh(db_msme)
    return db_msme


@router.get("/{msme_id}", response_model=MSMEResponse)
async def get_msme(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MSME).where(MSME.id == msme_id)
    )
    msme = result.scalar_one_or_none()
    if not msme:
        raise HTTPException(status_code=404, detail="MSME not found")
    return msme


@router.get("/gstin/{gstin}", response_model=MSMEResponse)
async def get_msme_by_gstin(gstin: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MSME).where(MSME.gstin == gstin)
    )
    msme = result.scalar_one_or_none()
    if not msme:
        raise HTTPException(status_code=404, detail="MSME not found")
    return msme


@router.get("/pan/{pan}", response_model=MSMEResponse)
async def get_msme_by_pan(pan: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MSME).where(MSME.pan == pan)
    )
    msme = result.scalar_one_or_none()
    if not msme:
        raise HTTPException(status_code=404, detail="MSME not found")
    return msme


@router.get("/", response_model=MSMEListResponse)
async def list_msmes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    gstin: Optional[str] = None,
    pan: Optional[str] = None,
    legal_name: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    nic_code: Optional[str] = None,
    status: Optional[MSMEStatus] = None,
    has_need_prediction: Optional[bool] = None,
    top_need: Optional[NeedCategory] = None,
    min_revenue: Optional[float] = None,
    max_revenue: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(MSME)
    count_query = select(func.count(MSME.id))

    filters = []
    if gstin:
        filters.append(MSME.gstin.ilike(f"%{gstin}%"))
    if pan:
        filters.append(MSME.pan.ilike(f"%{pan}%"))
    if legal_name:
        filters.append(MSME.legal_name.ilike(f"%{legal_name}%"))
    if city:
        filters.append(MSME.city.ilike(f"%{city}%"))
    if state:
        filters.append(MSME.state.ilike(f"%{state}%"))
    if nic_code:
        filters.append(MSME.nic_code == nic_code)
    if status:
        filters.append(MSME.status == status)
    if has_need_prediction is not None:
        if has_need_prediction:
            filters.append(MSME.need_predictions.any())
        else:
            filters.append(~MSME.need_predictions.any())
    if top_need:
        filters.append(MSME.need_predictions.any(NeedPrediction.top_need == top_need))
    if min_revenue is not None or max_revenue is not None:
        gst_subquery = select(GSTReturn.msme_id, func.max(GSTReturn.total_revenue).label("max_revenue")).group_by(GSTReturn.msme_id).subquery()
        query = query.outerjoin(gst_subquery, MSME.id == gst_subquery.c.msme_id)
        count_query = count_query.outerjoin(gst_subquery, MSME.id == gst_subquery.c.msme_id)
        if min_revenue is not None:
            filters.append(gst_subquery.c.max_revenue >= min_revenue)
        if max_revenue is not None:
            filters.append(gst_subquery.c.max_revenue <= max_revenue)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(MSME.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    msmes = result.scalars().all()

    return MSMEListResponse(msmes=msmes, total=total, page=page, page_size=page_size)


@router.patch("/{msme_id}", response_model=MSMEResponse)
async def update_msme(msme_id: UUID, msme_update: MSMEUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MSME).where(MSME.id == msme_id))
    msme = result.scalar_one_or_none()
    if not msme:
        raise HTTPException(status_code=404, detail="MSME not found")

    update_data = msme_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(msme, field, value)
    msme.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(msme)
    return msme


@router.delete("/{msme_id}", status_code=204)
async def delete_msme(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MSME).where(MSME.id == msme_id))
    msme = result.scalar_one_or_none()
    if not msme:
        raise HTTPException(status_code=404, detail="MSME not found")

    await db.delete(msme)
    await db.commit()


@router.get("/{msme_id}/dashboard", response_model=MSMEDashboardSummary)
async def get_msme_dashboard(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MSME).where(MSME.id == msme_id)
    )
    msme = result.scalar_one_or_none()
    if not msme:
        raise HTTPException(status_code=404, detail="MSME not found")

    gst_result = await db.execute(
        select(GSTReturn)
        .where(GSTReturn.msme_id == msme_id)
        .order_by(GSTReturn.tax_period.desc())
        .limit(1)
    )
    latest_gst = gst_result.scalar_one_or_none()

    aa_result = await db.execute(
        select(AAAccount).where(AAAccount.msme_id == msme_id)
    )
    aa_accounts = aa_result.scalars().all()

    aa_summary = {
        "total_accounts": len(aa_accounts),
        "total_sanctioned": sum(a.sanctioned_limit for a in aa_accounts),
        "total_outstanding": sum(a.outstanding_amount for a in aa_accounts),
        "total_overdue": sum(a.overdue_amount for a in aa_accounts),
        "accounts_by_type": {},
        "npas": sum(1 for a in aa_accounts if a.repayment_status == "NPA"),
    }
    for acc in aa_accounts:
        aa_summary["accounts_by_type"][acc.account_type] = aa_summary["accounts_by_type"].get(acc.account_type, 0) + 1

    np_result = await db.execute(
        select(NeedPrediction)
        .where(NeedPrediction.msme_id == msme_id)
        .order_by(NeedPrediction.prediction_date.desc())
        .limit(1)
    )
    need_prediction = np_result.scalar_one_or_none()

    pr_result = await db.execute(
        select(ProductRecommendation)
        .where(ProductRecommendation.msme_id == msme_id)
        .order_by(ProductRecommendation.rank)
    )
    product_recommendations = pr_result.scalars().all()

    risk_score = None
    if aa_accounts:
        total_outstanding = sum(a.outstanding_amount for a in aa_accounts)
        total_overdue = sum(a.overdue_amount for a in aa_accounts)
        if total_outstanding > 0:
            risk_score = min(100, (total_overdue / total_outstanding) * 100)

    return MSMEDashboardSummary(
        msme=msme,
        latest_gst=latest_gst,
        aa_summary=aa_summary,
        need_prediction=need_prediction,
        product_recommendations=product_recommendations,
        risk_score=risk_score,
    )