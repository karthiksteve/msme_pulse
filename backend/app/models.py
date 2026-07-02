from sqlalchemy import Column, String, DateTime, Float, Integer, Text, Index, ForeignKey, Enum as SQLEnum, JSON, Uuid
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime

# CRITICAL: Import Base from database so all models share the same metadata.
# init_db() calls Base.metadata.create_all() — it must see all model classes.
from app.database import Base

class MSMEStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    NPA = "npa"
    CLOSED = "closed"

class NeedCategory(str, enum.Enum):
    WORKING_CAPITAL = "working_capital"
    MACHINERY_CAPEX = "machinery_capex"
    BUSINESS_EXPANSION = "business_expansion"
    INVENTORY_FUNDING = "inventory_funding"
    TRADE_FINANCE = "trade_finance"
    DIGITAL_TRANSFORMATION = "digital_transformation"

class ProductType(str, enum.Enum):
    CC_OD = "cc_od"
    MACHINERY_TERM_LOAN = "machinery_term_loan"
    BUSINESS_EXPANSION_LOAN = "business_expansion_loan"
    INVENTORY_FUNDING = "inventory_funding"
    TRADE_FINANCE = "trade_finance"
    DIGITAL_BUSINESS_LOAN = "digital_business_loan"

class MSME(Base):
    __tablename__ = "msmes"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gstin = Column(String(15), unique=True, index=True, nullable=False)
    pan = Column(String(10), unique=True, index=True, nullable=False)
    cin = Column(String(21), unique=True, index=True, nullable=True)
    legal_name = Column(String(255), nullable=False)
    trade_name = Column(String(255), nullable=True)
    
    # Address
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))
    
    # Business Details
    nic_code = Column(String(5), index=True)
    nic_description = Column(String(255))
    incorporation_date = Column(DateTime)
    constitution = Column(String(50))  # Proprietorship, Partnership, Pvt Ltd, etc.
    
    # Status
    status = Column(SQLEnum(MSMEStatus), default=MSMEStatus.ACTIVE, index=True)
    gst_registration_date = Column(DateTime)
    
    # Alternate Data Signals (EPFO, AA, GST discipline)
    epfo_active_employees = Column(Integer, default=0)
    pf_compliance_score = Column(Float, default=0.0)
    avg_monthly_inflow = Column(Float, default=0.0)
    avg_monthly_outflow = Column(Float, default=0.0)
    disposable_income = Column(Float, default=0.0)
    gstr_3b_delay_days = Column(Integer, default=0)
    behavioral_tag = Column(String(255), default="")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    gst_returns = relationship("GSTReturn", back_populates="msme", cascade="all, delete-orphan")
    aa_accounts = relationship("AAAccount", back_populates="msme", cascade="all, delete-orphan")
    need_predictions = relationship("NeedPrediction", back_populates="msme", cascade="all, delete-orphan")
    product_recommendations = relationship("ProductRecommendation", back_populates="msme", cascade="all, delete-orphan")

class GSTReturn(Base):
    __tablename__ = "gst_returns"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    msme_id = Column(Uuid(as_uuid=True), ForeignKey("msmes.id"), nullable=False, index=True)
    
    # Return Details
    return_type = Column(String(10), nullable=False)  # GSTR-1, GSTR-3B
    financial_year = Column(String(9), nullable=False)  # 2023-24
    tax_period = Column(String(7), nullable=False)  # 2023-04
    
    # GSTR-1 Fields
    b2b_invoices = Column(JSON, default={})  # Detailed B2B invoice data
    b2c_invoices = Column(JSON, default={})  # B2C summary
    export_invoices = Column(JSON, default={})
    credit_debit_notes = Column(JSON, default={})
    hsn_summary = Column(JSON, default={})  # HSN-wise sales
    doc_issued = Column(JSON, default={})
    
    # GSTR-3B Fields
    outward_supplies = Column(Float, default=0)  # Table 3.1
    inward_supplies = Column(Float, default=0)   # Table 3.2
    taxable_value = Column(Float, default=0)
    igst = Column(Float, default=0)
    cgst = Column(Float, default=0)
    sgst = Column(Float, default=0)
    cess = Column(Float, default=0)
    itc_claimed = Column(Float, default=0)  # Table 4
    itc_reversed = Column(Float, default=0)
    net_tax_payable = Column(Float, default=0)
    tax_paid = Column(Float, default=0)
    
    # Computed Features
    total_revenue = Column(Float, default=0)
    b2b_revenue = Column(Float, default=0)
    b2c_revenue = Column(Float, default=0)
    export_revenue = Column(Float, default=0)
    gst_liability = Column(Float, default=0)
    itc_available = Column(Float, default=0)
    
    # Filing Status
    filing_date = Column(DateTime)
    filing_status = Column(String(20))  # FILED, PENDING, REVISED
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    msme = relationship("MSME", back_populates="gst_returns")
    
    __table_args__ = (
        Index('ix_gst_return_msme_period', 'msme_id', 'financial_year', 'tax_period'),
    )

class AAAccount(Base):
    __tablename__ = "aa_accounts"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    msme_id = Column(Uuid(as_uuid=True), ForeignKey("msmes.id"), nullable=False, index=True)
    
    # Account Details
    fi_type = Column(String(50))  # BANK, NBFC, INSURANCE
    fi_name = Column(String(100))  # Bank name
    account_type = Column(String(50))  # CC, OD, TERM_LOAN, BILL_DISCOUNTING
    account_number_masked = Column(String(50))
    
    # Financial Details
    sanctioned_limit = Column(Float, default=0)
    outstanding_amount = Column(Float, default=0)
    drawing_power = Column(Float, default=0)
    interest_rate = Column(Float, default=0)
    
    # Repayment Behavior
    repayment_status = Column(String(30))  # REGULAR, IRREGULAR, SMA_0, SMA_1, SMA_2, NPA
    days_past_due = Column(Integer, default=0)
    overdue_amount = Column(Float, default=0)
    
    # Account Timeline
    account_open_date = Column(DateTime)
    last_review_date = Column(DateTime)
    maturity_date = Column(DateTime, nullable=True)
    
    # AA Consent
    consent_id = Column(String(100))
    consent_status = Column(String(20))  # ACTIVE, EXPIRED, REVOKED
    consent_start = Column(DateTime)
    consent_expiry = Column(DateTime)
    
    # Data Freshness
    data_as_of = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    msme = relationship("MSME", back_populates="aa_accounts")

class NeedPrediction(Base):
    __tablename__ = "need_predictions"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    msme_id = Column(Uuid(as_uuid=True), ForeignKey("msmes.id"), nullable=False, index=True)
    
    # Predictions (multi-label)
    need_categories = Column(JSON, default={})  # {category: probability}
    top_need = Column(SQLEnum(NeedCategory), nullable=True)
    confidence_score = Column(Float, default=0)
    
    # Feature Importance (SHAP)
    shap_values = Column(JSON, default={})
    key_drivers = Column(JSON, default=[])
    
    # Model Metadata
    model_version = Column(String(50))
    prediction_date = Column(DateTime, default=datetime.utcnow)
    data_as_of = Column(DateTime)
    
    msme = relationship("MSME", back_populates="need_predictions")

class ProductRecommendation(Base):
    __tablename__ = "product_recommendations"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    msme_id = Column(Uuid(as_uuid=True), ForeignKey("msmes.id"), nullable=False, index=True)
    need_prediction_id = Column(Uuid(as_uuid=True), ForeignKey("need_predictions.id"), nullable=True)
    
    # Recommendation
    product_type = Column(SQLEnum(ProductType), nullable=False)
    eligibility_score = Column(Float, default=0)  # 0-1
    ranking_score = Column(Float, default=0)
    rank = Column(Integer)
    
    # Loan Terms (estimated)
    suggested_amount = Column(Float, default=0)
    suggested_tenure_months = Column(Integer, default=0)
    suggested_rate = Column(Float, default=0)
    
    # Eligibility Rules
    eligibility_rules_passed = Column(JSON, default=[])
    eligibility_rules_failed = Column(JSON, default=[])
    
    # Explainability
    shap_explanation = Column(JSON, default={})
    business_rationale = Column(Text)
    
    # Status
    status = Column(String(20), default="generated")  # generated, sent, viewed, applied, approved, rejected
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    msme = relationship("MSME", back_populates="product_recommendations")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50))
    entity_id = Column(Uuid(as_uuid=True))
    action = Column(String(50))
    user_id = Column(String(100))
    old_values = Column(JSON, default={})
    new_values = Column(JSON, default={})
    ip_address = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_audit_entity', 'entity_type', 'entity_id'),
        Index('ix_audit_timestamp', 'timestamp'),
    )