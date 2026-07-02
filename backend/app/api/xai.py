"""
XAI Loan Eligibility API Router
================================
POST /api/v1/xai/loan-explanation
  - Accepts msme_id + asking_amount
  - Returns full XAI breakdown: eligibility score, loan suggestion,
    score slab comparison, feature contributions, and improvement areas.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Dict, List

from app.database import get_db
from app.models import MSME, GSTReturn, AAAccount
from app.schemas import XAILoanRequest, XAILoanResponse
from app.services.xai_service import xai_service

router = APIRouter(prefix="/xai", tags=["XAI – Explainable Loan Eligibility"])


def _model_to_dict(obj: Any) -> Dict:
    """Convert SQLAlchemy model instance to dict."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.post(
    "/loan-explanation",
    response_model=XAILoanResponse,
    summary="Explainable AI Loan Eligibility & Suggestion",
    description=(
        "Computes a multidimensional MSME financial health score using GST returns and "
        "Account Aggregator data. Returns:\n"
        "- Eligibility score (0–100) and band\n"
        "- Computed maximum loan amount the MSME qualifies for\n"
        "- Comparison of asking amount vs computed limit\n"
        "- Higher amount suggestion for top-tier borrowers\n"
        "- Product-specific loan recommendations with EMI estimates\n"
        "- Score slab comparison table (your metrics vs healthy benchmarks)\n"
        "- SHAP-style feature contributions explaining the score\n"
        "- Areas of improvement and key strengths\n"
        "- Natural language XAI narrative"
    ),
)
async def get_loan_explanation(
    request: XAILoanRequest,
    db: AsyncSession = Depends(get_db),
) -> XAILoanResponse:
    # ── 1. Fetch MSME ──────────────────────────────────────────────────────────
    msme_result = await db.execute(select(MSME).where(MSME.id == request.msme_id))
    msme = msme_result.scalar_one_or_none()
    if not msme:
        raise HTTPException(status_code=404, detail=f"MSME with id '{request.msme_id}' not found.")

    msme_dict = _model_to_dict(msme)

    # ── 2. Fetch GST returns (last 12 months) ─────────────────────────────────
    gst_result = await db.execute(
        select(GSTReturn)
        .where(GSTReturn.msme_id == request.msme_id)
        .order_by(GSTReturn.tax_period.desc())
        .limit(12)
    )
    gst_rows = gst_result.scalars().all()
    gst_data: List[Dict] = [_model_to_dict(g) for g in gst_rows]

    # ── 3. Fetch AA accounts ──────────────────────────────────────────────────
    aa_result = await db.execute(
        select(AAAccount).where(AAAccount.msme_id == request.msme_id)
    )
    aa_rows = aa_result.scalars().all()
    aa_data: List[Dict] = [_model_to_dict(a) for a in aa_rows]

    # ── 4. Run XAI engine ─────────────────────────────────────────────────────
    explanation = await xai_service.compute_loan_explanation(
        msme_data=msme_dict,
        gst_data=gst_data,
        aa_data=aa_data,
        asking_amount=request.asking_amount,
        loan_purpose=request.loan_purpose,
    )

    return explanation


@router.get(
    "/loan-explanation/{msme_id}",
    response_model=XAILoanResponse,
    summary="Quick Loan Eligibility Check (GET)",
    description="GET version for quick eligibility checks. Uses a default asking amount of ₹25 Lakhs.",
)
async def get_loan_explanation_quick(
    msme_id: str,
    asking_amount: float = 2_500_000,
    loan_purpose: str = None,
    db: AsyncSession = Depends(get_db),
) -> XAILoanResponse:
    from uuid import UUID
    try:
        uid = UUID(msme_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid MSME ID format.")

    return await get_loan_explanation(
        request=XAILoanRequest(
            msme_id=uid,
            asking_amount=asking_amount,
            loan_purpose=loan_purpose,
        ),
        db=db,
    )
