from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

class MSMEStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    NPA = "npa"
    CLOSED = "closed"

class NeedCategory(str, Enum):
    WORKING_CAPITAL = "working_capital"
    MACHINERY_CAPEX = "machinery_capex"
    BUSINESS_EXPANSION = "business_expansion"
    INVENTORY_FUNDING = "inventory_funding"
    TRADE_FINANCE = "trade_finance"
    DIGITAL_TRANSFORMATION = "digital_transformation"

class ProductType(str, Enum):
    CC_OD = "cc_od"
    MACHINERY_TERM_LOAN = "machinery_term_loan"
    BUSINESS_EXPANSION_LOAN = "business_expansion_loan"
    INVENTORY_FUNDING = "inventory_funding"
    TRADE_FINANCE = "trade_finance"
    DIGITAL_BUSINESS_LOAN = "digital_business_loan"

# Request/Response Models
class MSMEBase(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15)
    pan: str = Field(..., min_length=10, max_length=10)
    cin: Optional[str] = Field(None, min_length=21, max_length=21)
    legal_name: str = Field(..., min_length=1, max_length=255)
    trade_name: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    nic_code: Optional[str] = Field(None, min_length=5, max_length=5)
    nic_description: Optional[str] = None
    incorporation_date: Optional[datetime] = None
    constitution: Optional[str] = None

class MSMECreate(MSMEBase):
    pass

class MSMEUpdate(BaseModel):
    legal_name: Optional[str] = Field(None, min_length=1, max_length=255)
    trade_name: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    status: Optional[MSMEStatus] = None

class MSMEResponse(MSMEBase):
    id: UUID
    status: MSMEStatus
    gst_registration_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MSMEListResponse(BaseModel):
    msmes: List[MSMEResponse]
    total: int
    page: int
    page_size: int

# GST Return Models
class GSTReturnBase(BaseModel):
    return_type: str = Field(..., pattern="^(GSTR-1|GSTR-3B)$")
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    tax_period: str = Field(..., pattern=r"^\d{4}-\d{2}$")

class GSTReturnCreate(GSTReturnBase):
    msme_id: UUID
    b2b_invoices: Dict[str, Any] = {}
    b2c_invoices: Dict[str, Any] = {}
    export_invoices: Dict[str, Any] = {}
    credit_debit_notes: Dict[str, Any] = {}
    hsn_summary: Dict[str, Any] = {}
    doc_issued: Dict[str, Any] = {}
    outward_supplies: float = 0
    inward_supplies: float = 0
    taxable_value: float = 0
    igst: float = 0
    cgst: float = 0
    sgst: float = 0
    cess: float = 0
    itc_claimed: float = 0
    itc_reversed: float = 0
    net_tax_payable: float = 0
    tax_paid: float = 0
    filing_date: Optional[datetime] = None
    filing_status: str = "FILED"

class GSTReturnResponse(GSTReturnBase):
    id: UUID
    msme_id: UUID
    total_revenue: float
    b2b_revenue: float
    b2c_revenue: float
    export_revenue: float
    gst_liability: float
    itc_available: float
    filing_status: str
    filing_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# AA Account Models
class AAAccountBase(BaseModel):
    fi_type: str
    fi_name: str
    account_type: str
    account_number_masked: str
    sanctioned_limit: float = 0
    outstanding_amount: float = 0
    drawing_power: float = 0
    interest_rate: float = 0
    repayment_status: str
    days_past_due: int = 0
    overdue_amount: float = 0
    account_open_date: Optional[datetime] = None
    last_review_date: Optional[datetime] = None
    maturity_date: Optional[datetime] = None
    consent_id: Optional[str] = None
    consent_status: str = "ACTIVE"
    consent_start: Optional[datetime] = None
    consent_expiry: Optional[datetime] = None
    data_as_of: Optional[datetime] = None

class AAAccountCreate(AAAccountBase):
    msme_id: UUID

class AAAccountResponse(AAAccountBase):
    id: UUID
    msme_id: UUID
    fetched_at: datetime
    
    class Config:
        from_attributes = True

# Need Prediction Models
class NeedPredictionBase(BaseModel):
    need_categories: Dict[str, float] = {}
    top_need: Optional[NeedCategory] = None
    confidence_score: float = Field(..., ge=0, le=1)
    shap_values: Dict[str, float] = {}
    key_drivers: List[str] = []
    model_version: str
    data_as_of: Optional[datetime] = None

class NeedPredictionCreate(NeedPredictionBase):
    msme_id: UUID

class NeedPredictionResponse(NeedPredictionBase):
    id: UUID
    msme_id: UUID
    prediction_date: datetime
    
    class Config:
        from_attributes = True

# Product Recommendation Models
class ProductRecommendationBase(BaseModel):
    product_type: ProductType
    eligibility_score: float = Field(..., ge=0, le=1)
    ranking_score: float = 0
    rank: int = 0
    suggested_amount: float = 0
    suggested_tenure_months: int = 0
    suggested_rate: float = 0
    eligibility_rules_passed: List[str] = []
    eligibility_rules_failed: List[str] = []
    shap_explanation: Dict[str, float] = {}
    business_rationale: Optional[str] = None

class ProductRecommendationCreate(ProductRecommendationBase):
    msme_id: UUID
    need_prediction_id: Optional[UUID] = None

class ProductRecommendationResponse(ProductRecommendationBase):
    id: UUID
    msme_id: UUID
    need_prediction_id: Optional[UUID] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Dashboard/Analytics Models
class MSMEDashboardSummary(BaseModel):
    msme: MSMEResponse
    latest_gst: Optional[GSTReturnResponse] = None
    aa_summary: Dict[str, Any] = {}
    need_prediction: Optional[NeedPredictionResponse] = None
    product_recommendations: List[ProductRecommendationResponse] = []
    risk_score: Optional[float] = None

class PortfolioHeatmap(BaseModel):
    state: str
    district: Optional[str] = None
    nic_code: str
    total_msmes: int
    unserved_msmes: int
    avg_need_score: float
    top_need_category: NeedCategory
    estimated_opportunity_cr: float

class NeedDistribution(BaseModel):
    category: NeedCategory
    count: int
    percentage: float
    avg_confidence: float

class ProductMatchStats(BaseModel):
    product_type: ProductType
    recommendations: int
    avg_eligibility: float
    avg_ranking_score: float
    estimated_disbursement_cr: float

# Search/Filter Models
class MSMESearchFilters(BaseModel):
    gstin: Optional[str] = None
    pan: Optional[str] = None
    legal_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    nic_code: Optional[str] = None
    status: Optional[MSMEStatus] = None
    has_need_prediction: Optional[bool] = None
    top_need: Optional[NeedCategory] = None
    min_revenue: Optional[float] = None
    max_revenue: Optional[float] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

# Health Check
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    models_loaded: bool
    timestamp: datetime