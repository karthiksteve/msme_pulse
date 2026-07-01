from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models import MSME, MSMEStatus
from app.schemas import MSMECreate, MSMEUpdate, MSMEResponse, MSMEListResponse, MSMESearchFilters

router = APIRouter(prefix="", tags=["MSMEs"])


@router.post("/", response_model=MSMEResponse, status_code=201)
async def create_msme(msme: MSMECreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(MSME).where(or_(MSME.gstin == msme.gstin, MSME.pan == msme.pan))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="MSME with this GSTIN or PAN already exists")

    db_msme = MSME(**msme.model_dump())
    db.add(db_msme)
    await db.commit()
    await db.refresh(db_msme)
    return db_msme


@router.get("/", response_model=MSMEListResponse)
async def list_msmes(
    gstin: Optional[str] = None,
    pan: Optional[str] = None,
    legal_name: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    nic_code: Optional[str] = None,
    status: Optional[MSMEStatus] = None,
    has_need_prediction: Optional[bool] = None,
    min_revenue: Optional[float] = None,
    max_revenue: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(MSME)

    if gstin:
        query = query.where(MSME.gstin.ilike(f"%{gstin}%"))
    if pan:
        query = query.where(MSME.pan == pan)
    if legal_name:
        query = query.where(MSME.legal_name.ilike(f"%{legal_name}%"))
    if city:
        query = query.where(MSME.city.ilike(f"%{city}%"))
    if state:
        query = query.where(MSME.state.ilike(f"%{state}%"))
    if nic_code:
        query = query.where(MSME.nic_code == nic_code)
    if status:
        query = query.where(MSME.status == status)

    if min_revenue is not None or max_revenue is not None:
        from app.models import GSTReturn
        subq = select(GSTReturn.msme_id, func.max(GSTReturn.total_revenue).label("max_rev")).group_by(GSTReturn.msme_id)
        if min_revenue is not None:
            subq = subq.having(func.max(GSTReturn.total_revenue) >= min_revenue)
        if max_revenue is not None:
            subq = subq.having(func.max(GSTReturn.total_revenue) <= max_revenue)
        msme_ids = [r.msme_id for r in (await db.execute(subq)).all()]
        query = query.where(MSME.id.in_(msme_ids))

    if has_need_prediction is not None:
        from app.models import NeedPrediction
        subq = select(NeedPrediction.msme_id).distinct()
        if has_need_prediction:
            query = query.where(MSME.id.in_(subq))
        else:
            query = query.where(MSME.id.notin_(subq))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(MSME.created_at.desc())
    result = await db.execute(query)
    msmes = result.scalars().all()

    return MSMEListResponse(msmes=msmes, total=total, page=page, page_size=page_size)


@router.get("/{msme_id}", response_model=MSMEResponse)
async def get_msme(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MSME).where(MSME.id == msme_id))
    msme = result.scalar_one_or_none()
    if not msme:
        raise HTTPException(status_code=404, detail="MSME not found")
    return msme


@router.get("/by-gstin/{gstin}", response_model=MSMEResponse)
async def get_msme_by_gstin(gstin: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MSME).where(MSME.gstin == gstin))
    msme = result.scalar_one_or_none()
    if not msme:
        raise HTTPException(status_code=404, detail="MSME not found")
    return msme


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