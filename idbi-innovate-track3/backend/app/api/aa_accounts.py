from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import AAAccount, MSME
from app.schemas import AAAccountCreate, AAAccountResponse

router = APIRouter(prefix="/aa-accounts", tags=["Account Aggregator Accounts"])


@router.post("/", response_model=AAAccountResponse, status_code=201)
async def create_aa_account(aa_account: AAAccountCreate, db: AsyncSession = Depends(get_db)):
    msme_result = await db.execute(select(MSME).where(MSME.id == aa_account.msme_id))
    if not msme_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="MSME not found")

    db_account = AAAccount(**aa_account.model_dump())
    db.add(db_account)
    await db.commit()
    await db.refresh(db_account)
    return db_account


@router.get("/msme/{msme_id}", response_model=List[AAAccountResponse])
async def get_aa_accounts_by_msme(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AAAccount).where(AAAccount.msme_id == msme_id).order_by(AAAccount.fetched_at.desc())
    )
    return result.scalars().all()


@router.get("/{account_id}", response_model=AAAccountResponse)
async def get_aa_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AAAccount).where(AAAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="AA Account not found")
    return account


@router.get("/msme/{msme_id}/summary")
async def get_aa_summary(msme_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AAAccount).where(AAAccount.msme_id == msme_id))
    accounts = result.scalars().all()

    if not accounts:
        return {"message": "No AA accounts found"}

    total_sanctioned = sum(a.sanctioned_limit for a in accounts)
    total_outstanding = sum(a.outstanding_amount for a in accounts)
    total_drawing_power = sum(a.drawing_power for a in accounts)
    total_overdue = sum(a.overdue_amount for a in accounts)

    by_type = {}
    by_fi = {}
    npas = []
    smas = []

    for acc in accounts:
        by_type[acc.account_type] = by_type.get(acc.account_type, 0) + 1
        by_fi[acc.fi_name] = by_fi.get(acc.fi_name, 0) + 1
        if acc.repayment_status == "NPA":
            npas.append(acc)
        elif acc.repayment_status.startswith("SMA"):
            smas.append(acc)

    utilization_ratio = total_outstanding / total_sanctioned if total_sanctioned > 0 else 0

    return {
        "msme_id": str(msme_id),
        "total_accounts": len(accounts),
        "total_sanctioned_limit": total_sanctioned,
        "total_outstanding": total_outstanding,
        "total_drawing_power": total_drawing_power,
        "total_overdue_amount": total_overdue,
        "utilization_ratio": total_outstanding / total_sanctioned if total_sanctioned > 0 else 0,
        "overdue_ratio": total_overdue / total_outstanding if total_outstanding > 0 else 0,
        "accounts_by_type": by_type,
        "accounts_by_fi": by_fi,
        "npa_count": len(npas),
        "sma_count": len(smas),
        "npas": [{"id": str(a.id), "fi": a.fi_name, "outstanding": a.outstanding_amount} for a in npas],
    }