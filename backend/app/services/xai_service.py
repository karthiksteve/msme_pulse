"""
XAI Loan Eligibility & Recommendation Service
==============================================
Computes multidimensional MSME financial health scores using alternate data
(GST, Account Aggregator) and generates explainable AI insights per the
IDBI Innovate Track-3 problem statement.

Score Dimensions:
  1. GST Compliance Score        (0-100)  – Filing consistency, ITC utilization
  2. Revenue Health Score        (0-100)  – Turnover trend, B2B/B2C mix, growth
  3. Repayment Behavior Score    (0-100)  – DPD, NPA flags, overdue ratio
  4. Credit Utilization Score    (0-100)  – Utilization ratio vs healthy band
  5. Business Stability Score    (0-100)  – Vintage, constitution, sector
  6. Cash Flow Score             (0-100)  – Net tax liability trend, ITC ratio

Composite Eligibility Score = weighted average of sub-scores
"""

from __future__ import annotations

import math
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.schemas import (
    XAILoanResponse,
    LoanProductSuggestion,
    ScoreSlabRow,
    FeatureContribution,
)
from app.services.llm_service import llm_explainer_service, LLMUnavailableError, LLMResponseParseError

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

SCORE_WEIGHTS = {
    "gst_compliance":   0.20,
    "revenue_health":   0.25,
    "repayment":        0.25,
    "credit_util":      0.15,
    "biz_stability":    0.10,
    "cash_flow":        0.05,
}

ELIGIBILITY_BANDS = [
    (85, 100, "EXCELLENT", "Exceptional Profile – Premium Loan Products Available", True),
    (70,  85, "GOOD",      "Strong Profile – Standard Loan Products Available",     True),
    (55,  70, "FAIR",      "Moderate Profile – Loan Eligible with Conditions",      True),
    (40,  55, "POOR",      "Weak Profile – Limited Eligibility, Collateral May Help", False),
    ( 0,  40, "INELIGIBLE","Insufficient Score – Improve Financials Before Applying", False),
]

# Product templates keyed by dominant business need
PRODUCT_TEMPLATES = [
    {
        "product_type": "cc_od",
        "product_name": "Cash Credit / Overdraft (CC/OD)",
        "tenure_months": 12,
        "rate": 10.5,
        "multiplier": 0.40,           # % of annual turnover
        "rationale": "Ideal for working capital management and short-term liquidity needs.",
    },
    {
        "product_type": "machinery_term_loan",
        "product_name": "Machinery & Equipment Term Loan",
        "tenure_months": 60,
        "rate": 11.0,
        "multiplier": 0.35,
        "rationale": "Structured repayment for capital expenditure on machinery/equipment.",
    },
    {
        "product_type": "business_expansion_loan",
        "product_name": "Business Expansion Loan",
        "tenure_months": 84,
        "rate": 11.5,
        "multiplier": 0.50,
        "rationale": "Long-tenure loan for expanding operations, new units or branches.",
    },
    {
        "product_type": "inventory_funding",
        "product_name": "Inventory Funding / Bill Discounting",
        "tenure_months": 6,
        "rate": 10.0,
        "multiplier": 0.20,
        "rationale": "Short-tenure facility to fund inventory purchases and smooth trade cycles.",
    },
    {
        "product_type": "digital_business_loan",
        "product_name": "Digital Business Loan",
        "tenure_months": 36,
        "rate": 12.0,
        "multiplier": 0.30,
        "rationale": "Unsecured digital loan for digitisation, marketing, or working capital.",
    },
]

HEALTHY_SLABS = [
    {
        "metric_name": "gst_filing_consistency",
        "description": "GST Return Filing Consistency (% months filed on time)",
        "healthy_min": "80%",
        "healthy_max": "100%",
        "weight": 20,
    },
    {
        "metric_name": "revenue_growth_yoy",
        "description": "Annual Revenue Growth (YoY %)",
        "healthy_min": "10%",
        "healthy_max": "50%+",
        "weight": 25,
    },
    {
        "metric_name": "credit_utilization",
        "description": "Credit Utilization Ratio (Outstanding / Sanctioned Limit)",
        "healthy_min": "10%",
        "healthy_max": "60%",
        "weight": 15,
    },
    {
        "metric_name": "dpd_days",
        "description": "Days Past Due (DPD) – Lower is Better",
        "healthy_min": "0 days",
        "healthy_max": "30 days",
        "weight": 25,
    },
    {
        "metric_name": "itc_utilization",
        "description": "ITC Utilization Ratio (ITC Claimed / GST Liability)",
        "healthy_min": "40%",
        "healthy_max": "90%",
        "weight": 10,
    },
    {
        "metric_name": "business_vintage_years",
        "description": "Business Vintage (Years in Operation)",
        "healthy_min": "3 years",
        "healthy_max": "20+ years",
        "weight": 5,
    },
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _fmt_inr(amount: float) -> str:
    """Format a float rupee amount into a human-readable INR string."""
    if amount >= 1e7:
        return f"₹{amount / 1e7:.2f} Cr"
    if amount >= 1e5:
        return f"₹{amount / 1e5:.2f} Lakh"
    return f"₹{amount:,.0f}"


def _emi(principal: float, annual_rate_pct: float, months: int) -> float:
    """Calculate flat-rate EMI. Returns 0 if inputs invalid."""
    if months <= 0 or principal <= 0:
        return 0.0
    r = annual_rate_pct / (12 * 100)
    if r == 0:
        return principal / months
    emi = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)
    return round(emi, 2)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _score_status(score: float) -> str:
    if score >= 75:
        return "HEALTHY"
    if score >= 45:
        return "CAUTION"
    return "CRITICAL"


# ─── Sub-score Calculators ────────────────────────────────────────────────────

def _calc_gst_compliance(gst_data: List[Dict]) -> Tuple[float, Dict]:
    """Score: filing regularity, ITC discipline."""
    if not gst_data:
        return 0.0, {"filed_months": 0, "itc_ratio": 0.0, "filing_gap_months": 12}

    filed = len(gst_data)
    expected = 12  # trailing 12 months expected
    filing_pct = min(filed / expected, 1.0)

    # ITC utilization
    total_gst_liability = sum(float(g.get("gst_liability", 0)) for g in gst_data)
    total_itc = sum(float(g.get("itc_available", 0)) for g in gst_data)
    itc_ratio = total_itc / total_gst_liability if total_gst_liability > 0 else 0.0
    itc_ratio = min(itc_ratio, 1.0)

    # Penalise if revenue suddenly drops
    revenues = [float(g.get("total_revenue", 0)) for g in gst_data]
    volatility_penalty = 0.0
    if len(revenues) > 1 and revenues[0] > 0:
        std_pct = (max(revenues) - min(revenues)) / max(revenues)
        volatility_penalty = min(std_pct * 20, 20)

    score = _clamp(
        filing_pct * 50               # 50 pts for filing consistency
        + itc_ratio * 30              # 30 pts for ITC health
        + 20                          # 20 pts base
        - volatility_penalty
    )
    return score, {
        "filed_months": filed,
        "itc_ratio": round(itc_ratio * 100, 1),
        "filing_pct": round(filing_pct * 100, 1),
    }


def _calc_revenue_health(gst_data: List[Dict]) -> Tuple[float, Dict]:
    """Score: turnover size, growth trend, B2B mix."""
    if not gst_data:
        return 0.0, {"avg_monthly_revenue": 0, "yoy_growth_pct": 0, "b2b_pct": 0}

    revenues = [float(g.get("total_revenue", 0)) for g in gst_data]
    avg_monthly = sum(revenues) / len(revenues)
    annual_rev = avg_monthly * 12

    # Turnover size score (scale to 5 Cr being 100)
    turnover_score = min(annual_rev / 5e7, 1.0) * 40

    # YoY growth
    yoy_growth = 0.0
    if len(revenues) >= 2 and revenues[-1] > 0:
        yoy_growth = (revenues[0] - revenues[-1]) / revenues[-1] * 100
    growth_score = _clamp((yoy_growth + 10) * 2, 0, 40)  # 10%+ growth -> full 40pts

    # B2B ratio (more B2B = more formal economy = better)
    latest = gst_data[0]
    total_rev = float(latest.get("total_revenue", 1)) or 1
    b2b_pct = float(latest.get("b2b_revenue", 0)) / total_rev * 100
    b2b_score = _clamp(b2b_pct * 0.2, 0, 20)

    score = _clamp(turnover_score + growth_score + b2b_score)
    return score, {
        "avg_monthly_revenue": round(avg_monthly, 0),
        "annual_revenue": round(annual_rev, 0),
        "yoy_growth_pct": round(yoy_growth, 1),
        "b2b_pct": round(b2b_pct, 1),
    }


def _calc_repayment(aa_data: List[Dict]) -> Tuple[float, Dict]:
    """Score: DPD, NPA/SMA flags, overdue ratio."""
    if not aa_data:
        return 55.0, {"max_dpd": 0, "npa_count": 0, "sma_count": 0, "overdue_ratio": 0}

    max_dpd = max((int(a.get("days_past_due", 0)) for a in aa_data), default=0)
    npa_count = sum(1 for a in aa_data if a.get("repayment_status") == "NPA")
    sma_count = sum(1 for a in aa_data if str(a.get("repayment_status", "")).startswith("SMA"))
    total_outstanding = sum(float(a.get("outstanding_amount", 0)) for a in aa_data)
    total_overdue = sum(float(a.get("overdue_amount", 0)) for a in aa_data)
    overdue_ratio = total_overdue / total_outstanding if total_outstanding > 0 else 0.0

    # Hard penalties
    npa_penalty = npa_count * 30
    sma_penalty = sma_count * 15
    dpd_penalty = min(max_dpd * 0.5, 40)
    overdue_penalty = min(overdue_ratio * 100 * 0.4, 30)

    score = _clamp(100 - npa_penalty - sma_penalty - dpd_penalty - overdue_penalty)
    return score, {
        "max_dpd": max_dpd,
        "npa_count": npa_count,
        "sma_count": sma_count,
        "overdue_ratio": round(overdue_ratio * 100, 1),
    }


def _calc_credit_util(aa_data: List[Dict]) -> Tuple[float, Dict]:
    """Score: credit utilization ratio (outstanding / sanctioned)."""
    if not aa_data:
        return 70.0, {"utilization_pct": 0}

    total_outstanding = sum(float(a.get("outstanding_amount", 0)) for a in aa_data)
    total_sanctioned = sum(float(a.get("sanctioned_limit", 0)) for a in aa_data)
    util_pct = total_outstanding / total_sanctioned * 100 if total_sanctioned > 0 else 0.0

    # Healthy band: 20-60% utilization
    if util_pct <= 10:
        score = 60   # very low – perhaps no credit history
    elif util_pct <= 60:
        score = 100 - abs(util_pct - 35) * 1.5   # peak at 35%
    else:
        score = _clamp(100 - (util_pct - 60) * 2.5)  # penalise overuse

    return _clamp(score), {"utilization_pct": round(util_pct, 1)}


def _calc_biz_stability(msme_data: Dict) -> Tuple[float, Dict]:
    """Score: business vintage, constitution type, registration quality."""
    vintage_years = 0
    if msme_data.get("incorporation_date"):
        try:
            inc = msme_data["incorporation_date"]
            if isinstance(inc, str):
                inc = datetime.fromisoformat(inc.replace("Z", "+00:00"))
            vintage_years = (datetime.utcnow().replace(tzinfo=inc.tzinfo) - inc).days / 365.25
        except Exception:
            vintage_years = 0

    vintage_score = _clamp(min(vintage_years / 10, 1.0) * 60)  # 10+ years → 60 pts

    constitution = (msme_data.get("constitution") or "").lower()
    const_score = 40 if "private" in constitution or "pvt" in constitution else \
                  30 if "llp" in constitution else \
                  20 if "partnership" in constitution else 10

    score = _clamp(vintage_score + const_score)
    return score, {
        "vintage_years": round(vintage_years, 1),
        "constitution": msme_data.get("constitution", "Proprietorship"),
    }


def _calc_cash_flow(gst_data: List[Dict]) -> Tuple[float, Dict]:
    """Score: net tax paid consistency, ITC trend."""
    if not gst_data:
        return 50.0, {"avg_net_tax": 0}

    net_taxes = [float(g.get("net_tax_payable", 0)) for g in gst_data]
    avg_net_tax = sum(net_taxes) / len(net_taxes)
    paid_taxes = [float(g.get("tax_paid", 0)) for g in gst_data]
    paid_ratio = sum(paid_taxes) / max(sum(net_taxes), 1)

    score = _clamp(paid_ratio * 80 + (20 if avg_net_tax > 0 else 0))
    return score, {
        "avg_net_tax": round(avg_net_tax, 0),
        "tax_paid_ratio": round(paid_ratio * 100, 1),
    }


# ─── Loan Amount Computation ─────────────────────────────────────────────────

def _compute_max_loan(
    eligibility_score: float,
    revenue_meta: Dict,
    repayment_meta: Dict,
    aa_data: List[Dict],
) -> float:
    """
    Rule-based loan sizing:
    - Base = 4x average monthly revenue (proxy for cash flow)
    - Adjusted down for NPA / DPD
    - Adjusted up for high eligibility
    """
    annual_rev = revenue_meta.get("annual_revenue", 0)
    if annual_rev <= 0:
        return 500_000  # minimum 5L for new-to-credit MSMEs

    # Base: 40% of annual turnover
    base = annual_rev * 0.40

    # Eligibility multiplier
    elig_mult = 0.5 + (eligibility_score / 100) * 1.0   # 0.5 to 1.5×

    # Repayment discount
    npa_count = repayment_meta.get("npa_count", 0)
    sma_count = repayment_meta.get("sma_count", 0)
    repayment_mult = max(0.3, 1.0 - npa_count * 0.3 - sma_count * 0.1)

    computed = base * elig_mult * repayment_mult

    # Cap at 10 Cr for SMEs, floor at 1L
    return _clamp(round(computed, -4), 100_000, 100_000_000)


# ─── Score Slab Builder ───────────────────────────────────────────────────────

def _build_score_slab(
    meta: Dict,
    sub_scores: Dict[str, float],
) -> List[ScoreSlabRow]:
    gst_meta = meta.get("gst_compliance", {})
    rev_meta = meta.get("revenue_health", {})
    rep_meta = meta.get("repayment", {})
    util_meta = meta.get("credit_util", {})
    biz_meta = meta.get("biz_stability", {})

    filing_pct = gst_meta.get("filing_pct", 0)
    filing_status = "HEALTHY" if filing_pct >= 80 else "CAUTION" if filing_pct >= 50 else "CRITICAL"

    yoy_growth = rev_meta.get("yoy_growth_pct", 0)
    growth_status = "HEALTHY" if yoy_growth >= 10 else "CAUTION" if yoy_growth >= 0 else "CRITICAL"

    util_pct = util_meta.get("utilization_pct", 0)
    util_status = "HEALTHY" if 10 <= util_pct <= 60 else "CAUTION" if util_pct <= 75 else "CRITICAL"

    dpd = rep_meta.get("max_dpd", 0)
    dpd_status = "HEALTHY" if dpd == 0 else "CAUTION" if dpd <= 30 else "CRITICAL"

    itc_ratio = gst_meta.get("itc_ratio", 0)
    itc_status = "HEALTHY" if 40 <= itc_ratio <= 90 else "CAUTION" if itc_ratio >= 20 else "CRITICAL"

    vintage = biz_meta.get("vintage_years", 0)
    vintage_status = "HEALTHY" if vintage >= 3 else "CAUTION" if vintage >= 1 else "CRITICAL"

    def impact(score: float) -> str:
        pts = round(score * 0.2 - 10, 0)
        return f"+{int(pts)} pts" if pts >= 0 else f"{int(pts)} pts"

    return [
        ScoreSlabRow(
            metric_name="GST Filing Consistency",
            description="Percentage of months where GST returns were filed on time",
            your_value=f"{filing_pct:.0f}%",
            healthy_min="80%",
            healthy_max="100%",
            status=filing_status,
            impact_on_score=impact(sub_scores.get("gst_compliance", 0)),
            improvement_tip="File all pending GSTR-1 and GSTR-3B returns immediately. Consistent filing is the #1 factor banks check.",
        ),
        ScoreSlabRow(
            metric_name="Revenue Growth (YoY)",
            description="Year-over-year business revenue growth rate",
            your_value=f"{yoy_growth:+.1f}%",
            healthy_min="10%",
            healthy_max="50%+",
            status=growth_status,
            impact_on_score=impact(sub_scores.get("revenue_health", 0)),
            improvement_tip="Growing top-line revenue signals business health. Document all B2B transactions via proper invoicing to show GST-trackable turnover.",
        ),
        ScoreSlabRow(
            metric_name="Credit Utilization",
            description="Outstanding loan balance as % of total sanctioned credit limit",
            your_value=f"{util_pct:.1f}%",
            healthy_min="10%",
            healthy_max="60%",
            status=util_status,
            impact_on_score=impact(sub_scores.get("credit_util", 0)),
            improvement_tip="Maintain utilization between 20–50%. Very high (>70%) signals stress; very low (<10%) may indicate underuse of credit.",
        ),
        ScoreSlabRow(
            metric_name="Days Past Due (DPD)",
            description="Maximum number of days a payment was delayed across all accounts",
            your_value=f"{dpd} days",
            healthy_min="0 days",
            healthy_max="30 days",
            status=dpd_status,
            impact_on_score=impact(sub_scores.get("repayment", 0)),
            improvement_tip="Zero DPD is the gold standard. Even one missed EMI creates an SMA flag. Set up auto-debit mandates for all loan repayments.",
        ),
        ScoreSlabRow(
            metric_name="ITC Utilization",
            description="Input Tax Credit claimed as % of GST liability — shows supply chain formalization",
            your_value=f"{itc_ratio:.0f}%",
            healthy_min="40%",
            healthy_max="90%",
            status=itc_status,
            impact_on_score=impact(sub_scores.get("gst_compliance", 0) * 0.5),
            improvement_tip="Claim all eligible ITC. Reconcile your GSTR-2B monthly. High ITC utilization demonstrates formal supply chain engagement.",
        ),
        ScoreSlabRow(
            metric_name="Business Vintage",
            description="Number of years the business has been in operation",
            your_value=f"{vintage:.1f} years",
            healthy_min="3 years",
            healthy_max="10+ years",
            status=vintage_status,
            impact_on_score=impact(sub_scores.get("biz_stability", 0)),
            improvement_tip="Business age builds trust. Ensure GST registration, Udyam certificate, and MCA filings are all current and reflect actual incorporation date.",
        ),
    ]


# ─── Feature Contributions (SHAP-like) ───────────────────────────────────────

def _build_feature_contributions(
    sub_scores: Dict[str, float],
    meta: Dict,
) -> List[FeatureContribution]:
    contribs = []

    gst_score = sub_scores.get("gst_compliance", 50)
    gst_contrib = (gst_score - 50) * SCORE_WEIGHTS["gst_compliance"] * 2
    gst_meta = meta.get("gst_compliance", {})
    contribs.append(FeatureContribution(
        feature_name="gst_compliance",
        display_name="GST Filing & ITC Health",
        value=f"{gst_meta.get('filing_pct', 0):.0f}% returns filed, ITC ratio {gst_meta.get('itc_ratio', 0):.0f}%",
        contribution_score=round(gst_contrib, 1),
        direction="POSITIVE" if gst_contrib > 0 else "NEGATIVE" if gst_contrib < 0 else "NEUTRAL",
        explanation=f"GST compliance contributes {SCORE_WEIGHTS['gst_compliance']*100:.0f}% to your overall score. "
                    + ("Your filing consistency is strong." if gst_score >= 70 else
                       "Irregular filings are dragging your score down significantly."),
    ))

    rev_score = sub_scores.get("revenue_health", 50)
    rev_contrib = (rev_score - 50) * SCORE_WEIGHTS["revenue_health"] * 2
    rev_meta = meta.get("revenue_health", {})
    contribs.append(FeatureContribution(
        feature_name="revenue_health",
        display_name="Revenue Growth & Turnover",
        value=f"Annual Rev {_fmt_inr(rev_meta.get('annual_revenue', 0))}, YoY {rev_meta.get('yoy_growth_pct', 0):+.1f}%",
        contribution_score=round(rev_contrib, 1),
        direction="POSITIVE" if rev_contrib > 0 else "NEGATIVE" if rev_contrib < 0 else "NEUTRAL",
        explanation=f"Revenue health is the single largest factor ({SCORE_WEIGHTS['revenue_health']*100:.0f}%). "
                    + ("Your business is on a healthy growth trajectory." if rev_score >= 70 else
                       "Stagnant or declining revenues reduce loan eligibility. Focus on formalising sales through GST invoicing."),
    ))

    rep_score = sub_scores.get("repayment", 50)
    rep_contrib = (rep_score - 50) * SCORE_WEIGHTS["repayment"] * 2
    rep_meta = meta.get("repayment", {})
    contribs.append(FeatureContribution(
        feature_name="repayment",
        display_name="Repayment Track Record",
        value=f"DPD: {rep_meta.get('max_dpd', 0)} days, NPAs: {rep_meta.get('npa_count', 0)}, SMAs: {rep_meta.get('sma_count', 0)}",
        contribution_score=round(rep_contrib, 1),
        direction="POSITIVE" if rep_contrib > 0 else "NEGATIVE" if rep_contrib < 0 else "NEUTRAL",
        explanation=f"Repayment history is equally as important as revenue ({SCORE_WEIGHTS['repayment']*100:.0f}%). "
                    + ("Clean repayment history is a major strength." if rep_score >= 80 else
                       "SMA/NPA flags are severe negatives. Regularising existing loans before applying for new ones is critical."),
    ))

    util_score = sub_scores.get("credit_util", 50)
    util_contrib = (util_score - 50) * SCORE_WEIGHTS["credit_util"] * 2
    util_meta = meta.get("credit_util", {})
    contribs.append(FeatureContribution(
        feature_name="credit_util",
        display_name="Credit Utilization Ratio",
        value=f"{util_meta.get('utilization_pct', 0):.1f}% utilized",
        contribution_score=round(util_contrib, 1),
        direction="POSITIVE" if util_contrib > 0 else "NEGATIVE" if util_contrib < 0 else "NEUTRAL",
        explanation=f"Utilization ratio ({SCORE_WEIGHTS['credit_util']*100:.0f}% weight) shows credit discipline. "
                    + ("Optimal utilization demonstrates responsible borrowing." if 20 <= util_meta.get('utilization_pct', 0) <= 60 else
                       "Extremely high utilization signals over-leverage. Reduce existing debt before applying."),
    ))

    biz_score = sub_scores.get("biz_stability", 50)
    biz_contrib = (biz_score - 50) * SCORE_WEIGHTS["biz_stability"] * 2
    biz_meta = meta.get("biz_stability", {})
    contribs.append(FeatureContribution(
        feature_name="biz_stability",
        display_name="Business Vintage & Constitution",
        value=f"{biz_meta.get('vintage_years', 0):.1f} yrs, {biz_meta.get('constitution', 'N/A')}",
        contribution_score=round(biz_contrib, 1),
        direction="POSITIVE" if biz_contrib > 0 else "NEGATIVE" if biz_contrib < 0 else "NEUTRAL",
        explanation=f"Business stability ({SCORE_WEIGHTS['biz_stability']*100:.0f}% weight) validates longevity and formal structure. "
                    + ("Established vintage and formal constitution add credibility." if biz_score >= 70 else
                       "Newer businesses can compensate with strong GST and repayment records."),
    ))

    # Sort by absolute contribution (biggest impact first)
    contribs.sort(key=lambda c: abs(c.contribution_score), reverse=True)
    return contribs


# ─── Narrative Generator ──────────────────────────────────────────────────────

def _generate_narratives(
    msme_data: Dict,
    eligibility_score: float,
    band: str,
    sub_scores: Dict[str, float],
    rep_meta: Dict,
    rev_meta: Dict,
    computed_max: float,
    asking_amount: float,
) -> Tuple[str, str, str]:
    name = msme_data.get("legal_name", "Your Business")
    annual_rev = rev_meta.get("annual_revenue", 0)
    npa = rep_meta.get("npa_count", 0)

    if band == "EXCELLENT":
        summary = (
            f"{name} has an **exceptional** financial health profile with a score of "
            f"**{eligibility_score:.1f}/100**. Based on GST returns and Account Aggregator data, "
            f"the business demonstrates strong revenue growth, pristine repayment history, and healthy "
            f"credit utilization — making it a preferred borrower for IDBI Bank. "
            f"The computed eligible loan amount is **{_fmt_inr(computed_max)}**, which "
            + ("exceeds your requested amount — you may consider a higher ticket size." if asking_amount < computed_max * 0.8 else
               "comfortably accommodates your request.")
        )
    elif band == "GOOD":
        summary = (
            f"{name} has a **strong** financial profile with a score of **{eligibility_score:.1f}/100**. "
            f"The business qualifies for standard loan products. "
            f"A few areas — like {'repayment regularity' if sub_scores.get('repayment', 0) < 70 else 'revenue diversification'} — "
            f"can be improved to unlock premium rates and higher amounts."
        )
    elif band == "FAIR":
        summary = (
            f"{name} has a **moderate** financial health score of **{eligibility_score:.1f}/100**. "
            f"Loan eligibility exists but with conditions. "
            f"{'The presence of SMA/NPA accounts is a concern. ' if npa > 0 else ''}"
            f"Strengthening GST filing consistency and ensuring zero overdue balances would significantly improve the profile."
        )
    else:
        summary = (
            f"{name} currently scores **{eligibility_score:.1f}/100**, which falls below the minimum "
            f"eligibility threshold for most loan products. Key issues include "
            f"{'NPA accounts, ' if npa > 0 else ''}irregular GST filings, and/or insufficient revenue history. "
            f"A 3–6 month improvement plan focusing on the areas highlighted below is recommended before reapplying."
        )

    breakdown = (
        f"**Score Breakdown:** GST Compliance ({sub_scores.get('gst_compliance', 0):.0f}/100) · "
        f"Revenue Health ({sub_scores.get('revenue_health', 0):.0f}/100) · "
        f"Repayment Behavior ({sub_scores.get('repayment', 0):.0f}/100) · "
        f"Credit Utilization ({sub_scores.get('credit_util', 0):.0f}/100) · "
        f"Business Stability ({sub_scores.get('biz_stability', 0):.0f}/100) · "
        f"Cash Flow ({sub_scores.get('cash_flow', 0):.0f}/100). "
        f"Annual GST-declared turnover is **{_fmt_inr(annual_rev)}**. "
        f"Loan sizing is based on 40% of annual turnover adjusted by eligibility multiplier."
    )

    if npa > 0:
        risk = (
            f"⚠️ **High Risk:** {npa} NPA account(s) detected. This is a critical negative that most lenders will "
            f"flag. Regularising NPAs before loan application is strongly advised."
        )
    elif sub_scores.get("repayment", 0) < 60:
        risk = (
            f"⚠️ **Moderate Risk:** Repayment history shows some stress (SMA flags or overdue amounts). "
            f"Clear all overdue obligations before applying to improve your odds significantly."
        )
    elif eligibility_score >= 75:
        risk = "✅ **Low Risk:** No major repayment concerns detected. The business presents a manageable credit risk profile."
    else:
        risk = (
            f"🟡 **Moderate Risk:** Score of {eligibility_score:.0f} suggests some vulnerabilities. "
            f"Focusing on the improvement areas will help unlock better loan terms."
        )

    return summary, breakdown, risk


# ─── Areas of Improvement & Strengths ────────────────────────────────────────

def _build_improvement_areas(sub_scores: Dict, meta: Dict, rep_meta: Dict) -> Tuple[List[str], List[str]]:
    improvements = []
    strengths = []

    if sub_scores.get("gst_compliance", 0) < 70:
        improvements.append(
            "📋 File all pending GST returns (GSTR-1 & GSTR-3B) immediately. Gaps in filing history are visible to lenders and reduce your score significantly."
        )
    else:
        strengths.append("✅ Excellent GST filing consistency — this is your strongest signal of financial discipline.")

    gst_meta = meta.get("gst_compliance", {})
    if gst_meta.get("itc_ratio", 0) < 40:
        improvements.append(
            "💰 Your ITC utilization is below 40%. Reconcile GSTR-2B monthly and claim all eligible input tax credits to demonstrate formal supply chain participation."
        )

    if sub_scores.get("revenue_health", 0) < 60:
        improvements.append(
            "📈 Revenue growth is below the healthy threshold. Formalise all sales through proper GST invoicing — cash transactions not captured in returns significantly lower your declared turnover."
        )
    else:
        strengths.append("📈 Strong revenue trajectory — your business shows healthy growth signals.")

    npa_count = rep_meta.get("npa_count", 0)
    sma_count = rep_meta.get("sma_count", 0)
    dpd = rep_meta.get("max_dpd", 0)

    if npa_count > 0:
        improvements.append(
            f"🚨 CRITICAL: {npa_count} NPA account(s) detected. This is a dealbreaker for most lenders. Regularise these accounts and maintain a clean repayment record for at least 6 months before reapplying."
        )
    elif sma_count > 0:
        improvements.append(
            f"⚠️ {sma_count} SMA-tagged account(s) found. Ensure all EMIs are paid on time. Setting up auto-debit mandates is the simplest fix."
        )
    elif dpd > 0:
        improvements.append(
            f"⏰ Days Past Due (DPD) of {dpd} days detected. Clear all overdue amounts and maintain 0 DPD for 3+ consecutive months."
        )
    else:
        strengths.append("✅ Clean repayment track record — zero DPD and no NPA/SMA flags detected.")

    util_pct = meta.get("credit_util", {}).get("utilization_pct", 0)
    if util_pct > 70:
        improvements.append(
            f"💳 Credit utilization is high ({util_pct:.0f}%). Reduce outstanding balances on CC/OD accounts before applying for new loans. High utilization signals potential cash flow stress."
        )
    elif 10 <= util_pct <= 60:
        strengths.append(f"💳 Healthy credit utilization at {util_pct:.0f}% — demonstrates responsible use of existing credit facilities.")

    biz_meta = meta.get("biz_stability", {})
    if biz_meta.get("vintage_years", 0) < 3:
        improvements.append(
            "🏢 Business vintage is under 3 years. Ensure your Udyam registration, GST registration, and bank account opening date are all documented. Strong GST data compensates for lower vintage."
        )
    else:
        strengths.append(f"🏢 Established business with {biz_meta.get('vintage_years', 0):.0f}+ years of operating history.")

    return improvements, strengths


# ─── Main XAI Engine ──────────────────────────────────────────────────────────

class XAILoanService:
    """
    Main service that orchestrates all sub-scoring, explanation, and
    product suggestion logic for MSME loan eligibility.
    """

    async def compute_loan_explanation(
        self,
        msme_data: Dict[str, Any],
        gst_data: List[Dict],
        aa_data: List[Dict],
        asking_amount: float,
        loan_purpose: Optional[str] = None,
    ) -> XAILoanResponse:
        """
        Full pipeline:
        1. Compute sub-scores
        2. Compute composite eligibility score
        3. Determine eligibility band
        4. Size the loan
        5. Build XAI artifacts (slab, contributions, narratives)
        6. Suggest loan products
        7. Flag higher amount opportunity
        """

        # ── Step 1: Sub-scores ────────────────────────────────────────────────
        gst_score, gst_meta = _calc_gst_compliance(gst_data)
        rev_score, rev_meta = _calc_revenue_health(gst_data)
        rep_score, rep_meta = _calc_repayment(aa_data)
        util_score, util_meta = _calc_credit_util(aa_data)
        biz_score, biz_meta = _calc_biz_stability(msme_data)
        cf_score, cf_meta = _calc_cash_flow(gst_data)

        sub_scores = {
            "gst_compliance":  round(gst_score, 1),
            "revenue_health":  round(rev_score, 1),
            "repayment":       round(rep_score, 1),
            "credit_util":     round(util_score, 1),
            "biz_stability":   round(biz_score, 1),
            "cash_flow":       round(cf_score, 1),
        }

        sub_score_labels = {
            "gst_compliance":  "GST Compliance",
            "revenue_health":  "Revenue Health",
            "repayment":       "Repayment Behavior",
            "credit_util":     "Credit Utilization",
            "biz_stability":   "Business Stability",
            "cash_flow":       "Cash Flow Health",
        }

        # ── Step 2: Composite score ───────────────────────────────────────────
        eligibility_score = _clamp(sum(
            sub_scores[k] * SCORE_WEIGHTS[k] for k in SCORE_WEIGHTS
        ))

        # ── Step 3: Eligibility band ──────────────────────────────────────────
        band, label, is_eligible = "INELIGIBLE", "Insufficient Score", False
        for lo, hi, b, lbl, elig in ELIGIBILITY_BANDS:
            if lo <= eligibility_score < hi or (hi == 100 and eligibility_score == 100):
                band, label, is_eligible = b, lbl, elig
                break

        # ── Step 4: Loan sizing ───────────────────────────────────────────────
        computed_max = _compute_max_loan(eligibility_score, rev_meta, rep_meta, aa_data)

        # ── Step 5: Higher amount suggestion ─────────────────────────────────
        higher_amount = None
        higher_label = None
        higher_rationale = None
        higher_eligible = eligibility_score >= 85

        if higher_eligible and asking_amount < computed_max * 0.75:
            # They're asking way less than they can get
            higher_amount = round(computed_max * 0.90, -4)
            higher_label = _fmt_inr(higher_amount)
            higher_rationale = (
                f"Your financial health score of {eligibility_score:.1f}/100 qualifies you for "
                f"significantly more than you requested. Based on your annual turnover of "
                f"{_fmt_inr(rev_meta.get('annual_revenue', 0))}, clean repayment history, and strong GST compliance, "
                f"we suggest upgrading your loan application to {_fmt_inr(higher_amount)} — "
                f"this could fund broader business expansion and improve your unit economics further."
            )
        elif higher_eligible:
            higher_amount = round(computed_max * 1.15, -4)
            higher_label = _fmt_inr(higher_amount)
            higher_rationale = (
                f"Given your exceptional profile (score: {eligibility_score:.1f}/100), you may qualify for a "
                f"premium loan of up to {_fmt_inr(higher_amount)} — 15% above the standard computed limit. "
                f"This premium offer is reserved for top-tier MSME borrowers with consistent GST compliance and "
                f"zero NPA history."
            )

        # ── Step 6: Loan products ─────────────────────────────────────────────
        loan_suggestions = self._build_loan_suggestions(
            computed_max, eligibility_score, loan_purpose
        )

        # ── Step 7: XAI artifacts ─────────────────────────────────────────────
        all_meta = {
            "gst_compliance": gst_meta,
            "revenue_health": rev_meta,
            "repayment": rep_meta,
            "credit_util": util_meta,
            "biz_stability": biz_meta,
            "cash_flow": cf_meta,
        }

        score_slab = _build_score_slab(all_meta, sub_scores)
        feature_contributions = _build_feature_contributions(sub_scores, all_meta)
        areas_of_improvement, strengths = _build_improvement_areas(sub_scores, all_meta, rep_meta)

        # ── Step 8: LLM Narrative Generation (Fail-Open to Templates) ─────────
        narrative_src = "template"
        try:
            llm_res = await llm_explainer_service.generate_xai_narrative(
                msme_data=msme_data,
                eligibility_score=eligibility_score,
                band=band,
                eligibility_label=label,
                sub_scores=sub_scores,
                sub_score_labels=sub_score_labels,
                all_meta=all_meta,
                rep_meta=rep_meta,
                rev_meta=rev_meta,
                computed_max_loan=computed_max,
                asking_amount=asking_amount,
                is_eligible=is_eligible,
            )
            summary = llm_res["executive_summary"]
            breakdown = llm_res["score_breakdown_narrative"]
            risk = llm_res["risk_summary"]
            if llm_res.get("areas_of_improvement"):
                areas_of_improvement = llm_res["areas_of_improvement"]
            if llm_res.get("strengths"):
                strengths = llm_res["strengths"]
            narrative_src = llm_res.get("narrative_source", "llm")
        except (LLMUnavailableError, LLMResponseParseError, Exception) as e:
            logger.warning("LLM narrative generation failed; failing open to templates. Error: %s", e)
            summary, breakdown, risk = _generate_narratives(
                msme_data, eligibility_score, band, sub_scores, rep_meta, rev_meta, computed_max, asking_amount
            )

        # ── Step 9: Repayment Capacity ───────────────────────────────────────
        disposable_inc = float(msme_data.get("disposable_income", 0.0))
        repayment_capacity = disposable_inc * 0.5

        # ── Data completeness ─────────────────────────────────────────────────
        data_sources = []
        completeness = 30.0
        if msme_data:
            completeness += 10
            data_sources.append("MSME Registration Data")
        if gst_data:
            completeness += min(len(gst_data) / 12 * 40, 40)
            data_sources.append(f"GST Returns ({len(gst_data)} months)")
        if aa_data:
            completeness += 20
            data_sources.append(f"Account Aggregator ({len(aa_data)} accounts)")

        return XAILoanResponse(
            msme_id=UUID(str(msme_data.get("id", "00000000-0000-0000-0000-000000000000"))),
            legal_name=msme_data.get("legal_name", "Unknown Business"),
            gstin=msme_data.get("gstin", ""),

            eligibility_score=round(eligibility_score, 1),
            eligibility_band=band,
            eligibility_label=label,
            is_eligible=is_eligible,

            computed_max_loan_amount=computed_max,
            computed_max_loan_label=_fmt_inr(computed_max),
            asking_amount=asking_amount,
            asking_amount_label=_fmt_inr(asking_amount),
            asking_vs_computed_pct=round(asking_amount / computed_max * 100, 1) if computed_max > 0 else 0,

            higher_amount_eligible=higher_eligible,
            higher_amount_suggestion=higher_amount,
            higher_amount_label=higher_label,
            higher_amount_rationale=higher_rationale,

            loan_suggestions=loan_suggestions,

            executive_summary=summary,
            score_breakdown_narrative=breakdown,
            risk_summary=risk,

            score_slab=score_slab,
            feature_contributions=feature_contributions,

            areas_of_improvement=areas_of_improvement,
            strengths=strengths,

            sub_scores=sub_scores,
            sub_score_labels=sub_score_labels,

            repayment_capacity=repayment_capacity,
            repayment_capacity_label=_fmt_inr(repayment_capacity),
            narrative_source=narrative_src,

            data_completeness_pct=round(min(completeness, 100), 1),
            data_sources_used=data_sources,
            as_of_date=datetime.utcnow(),
        )

    def _build_loan_suggestions(
        self,
        computed_max: float,
        eligibility_score: float,
        loan_purpose: Optional[str],
    ) -> List[LoanProductSuggestion]:
        """Return ranked loan product suggestions based on eligibility and purpose."""
        purpose_map = {
            "working_capital": ["cc_od", "inventory_funding"],
            "machinery": ["machinery_term_loan"],
            "expansion": ["business_expansion_loan"],
            "digital": ["digital_business_loan"],
            "inventory": ["inventory_funding", "cc_od"],
        }

        preferred = []
        if loan_purpose:
            for keyword, products in purpose_map.items():
                if keyword in (loan_purpose or "").lower():
                    preferred.extend(products)

        suggestions = []
        elig_mult = eligibility_score / 100

        for tmpl in PRODUCT_TEMPLATES:
            # Only show premium products for high scorers
            if tmpl["product_type"] == "business_expansion_loan" and eligibility_score < 65:
                continue

            amount = round(computed_max * tmpl["multiplier"] * elig_mult, -4)
            amount = max(amount, 100_000)  # floor 1L

            is_preferred = tmpl["product_type"] in preferred

            suggestions.append(LoanProductSuggestion(
                product_name=tmpl["product_name"],
                product_type=tmpl["product_type"],
                suggested_amount=amount,
                suggested_amount_label=_fmt_inr(amount),
                suggested_tenure_months=tmpl["tenure_months"],
                suggested_rate=tmpl["rate"],
                emi_estimate=_emi(amount, tmpl["rate"], tmpl["tenure_months"]),
                rationale=tmpl["rationale"] + (" ⭐ Recommended based on your stated purpose." if is_preferred else ""),
            ))

        # Sort: preferred first, then by amount descending
        suggestions.sort(key=lambda s: (
            s.product_type not in preferred,
            -s.suggested_amount,
        ))

        return suggestions[:4]  # top 4


# Singleton
xai_service = XAILoanService()
