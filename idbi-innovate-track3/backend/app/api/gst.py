from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models import GSTReturn, MSME
from app.schemas import GSTReturnCreate, GSTReturnResponse

router = APIRouter(prefix="", tags=["GST Returns"])


@router.post("/", response_model=GSTReturnResponse, status_code=201)
async def create_gst_return(gst_return: GSTReturnCreate, db: AsyncSession = Depends(get_db)):
    msme_result = await db.execute(select(MSME).where(MSME.id == gst_return.msme_id))
    if not msme_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="MSME not found")

    db_gst = GSTReturn(**gst_return.model_dump())
    db_gst.total_revenue = gst_return.outward_supplies + gst_return.inward_supplies
    db_gst.gst_liability = gst_return.igst + gst_return.cgst + gst_return.sgst + gst_return.cess
    db_gst.itc_available = gst_return.itc_claimed - gst_return.itc_reversed

    db.add(db_gst)
    await db.commit()
    await db.refresh(db_gst)
    return db_gst


@router.get("/msme/{msme_id}", response_model=List[GSTReturnResponse])
async def get_gst_returns_by_msme(
    msme_id: UUID,
    financial_year: Optional[str] = None,
    return_type: Optional[str] = None,
    limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(GSTReturn).where(GSTReturn.msme_id == msme_id)

    if financial_year:
        query = query.where(GSTReturn.financial_year == financial_year)
    if return_type:
        query = query.where(GSTReturn.return_type == return_type)

    query = query.order_by(GSTReturn.tax_period.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{gst_return_id}", response_model=GSTReturnResponse)
async def get_gst_return(gst_return_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GSTReturn).where(GSTReturn.id == gst_return_id))
    gst_return = result.scalar_one_or_none()
    if not gst_return:
        raise HTTPException(status_code=404, detail="GST Return not found")
    return gst_return


@router.get("/msme/{msme_id}/summary")
async def get_gst_summary(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GSTReturn)
        .where(GSTReturn.msme_id == msme_id)
        .order_by(GSTReturn.tax_period.desc())
        .limit(12)
    )
    returns = result.scalars().all()

    if not returns:
        return {"message": "No GST returns found"}

    latest = returns[0]
    total_revenue_12m = sum(r.total_revenue for r in returns)
    avg_monthly = total_revenue_12m / len(returns) if returns else 0

    return {
        "msme_id": str(msme_id),
        "latest_return": latest,
        "last_12_months": {
            "total_revenue": total_revenue_12m,
            "avg_monthly_revenue": avg_monthly,
            "total_gst_paid": sum(r.tax_paid for r in returns),
            "total_itc_claimed": sum(r.itc_claimed for r in returns),
            "filing_compliance": sum(1 for r in returns if r.filing_status == "FILED") / len(returns) * 100,
        },
        "trend": [
            {"period": r.tax_period, "revenue": r.total_revenue, "liability": r.gst_liability}
            for r in reversed(returns)
        ],
    }