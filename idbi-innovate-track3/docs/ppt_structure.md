# IDBI Innovate Hackathon - Track 3 Submission
## MSME Business Needs Identification & Loan Matching Platform

---

### Slide 1: Title Slide
**IDBI Innovate Hackathon 2026 - Track 3**
# MSME Business Needs Identification & Intelligent Loan Matching Platform
**Team: [Team Name] | Track: MSME Business Needs Identification**
**Problem Statement:** Identify business needs of underserved/unserved MSMEs using GST data, Account Aggregator data & AI/ML

---

### Slide 2: Problem Statement
## The MSME Credit Gap - 25.8 Lakh Crore
- **51% of 63M MSMEs** lack access to formal credit
- **Current gap:** Banks rely on traditional balance sheet analysis (3-6 months lag)
- **IDBI challenge:** Identify business needs of unserved MSMEs *before* they apply
- **Data available but unused:** GST returns (GSTR-1/3B), Account Aggregator liability data, alternative data
- **Opportunity:** Real-time business need detection to proactive loan matching

---

### Slide 3: Our Solution - MSME Pulse
## AI-Powered Business Intelligence Platform for Proactive Lending

**Core Value Proposition:**
> "Detect MSME business needs in real-time from alternative data to Match with IDBI loan products to Enable proactive outreach"

**Key Differentiators:**
| Traditional Approach | MSME Pulse |
|---------------------|------------|
| Reactive (wait for application) | Proactive (detect need signals) |
| Balance sheet only (lagging) | Real-time GST + AA + Alternative data |
| Manual underwriting | AI-driven need scoring & product matching |
| 30-60 day TAT | <48 hour pre-qualified offers |

---

### Slide 4: Data Architecture - Multi-Source Intelligence
MSME PULSE DATA LAKE with GST DATA (GSTR-1/3B), ACCOUNT AGGREGATOR, ALTERNATIVE DATA, IDBI INTERNAL

---

### Slide 5: AI/ML Architecture - Need Detection & Product Matching
ML PIPELINE: FEATURE STORE -> NEED DETECTION MODEL -> PRODUCT MATCHING ENGINE

Models:
- Need Detection: Multi-label XGBoost + TabTransformer (AUC-ROC 0.92 on synthetic)
- Credit Risk: LightGBM + CatBoost ensemble (Gini 0.78)
- Product Ranking: Learning-to-Rank (LambdaMART) with business rules

---

### Slide 6: Need Categories & Loan Product Mapping
| Business Need Signal | Data Indicators | IDBI Product Match | Typical Ticket |
|---------------------|-----------------|-------------------|----------------|
| Working Capital Gap | Rising DSO, falling inventory turnover, AA cash flow volatility | CC/OD Limit Enhancement | 10L-5Cr |
| Machinery/ Capex | High GST on capital goods (HSN 84/85), rising fixed assets | Machinery Term Loan | 25L-20Cr |
| Business Expansion | New GSTINs, new HSN codes, GeM tender wins, new geographies | Business Expansion Loan | 50L-50Cr |

---

### Slide 7: Prototype Demo - Live Architecture
DEPLOYED ARCHITECTURE: Synthetic Data Gen -> FastAPI Backend -> React Dashboard
ML Models (ONNX/Serving) + PostgreSQL + Redis
Deployed on: Render / Railway / HuggingFace Spaces
Demo: https://msme-pulse-demo.onrender.com
GitHub: https://github.com/team-msme-pulse

---

### Slide 8: Synthetic Data Generation - Production-Ready
GST Data Generator (GSTR-1/3B Compliant): 10,000+ synthetic MSMEs across 50+ NIC codes
Account Aggregator Simulator: Multi-bank liability aggregation, consent artifact simulation
Data Quality: Referential integrity, temporal consistency, industry benchmarks

---

### Slide 9: Scalability & Bank-Grade Architecture
| Requirement | Our Approach | Bank-Ready |
|-------------|--------------|------------|
| Data Privacy | On-prem deployment, data never leaves bank perimeter | Yes |
| AA Compliance | Consent artifact management, FIU registration ready | Yes |
| Audit Trail | Immutable event log, model versioning (MLflow) | Yes |
| Explainability | SHAP values per prediction, rule-based override | Yes |
| Scalability | Kubernetes-native, horizontal scaling, async processing | Yes |

Tech Stack: FastAPI, PostgreSQL, Redis, Kafka, Kubernetes, MLflow, Feast, ONNX Runtime, React, Tailwind

---

### Slide 10: Implementation Roadmap
PHASE 1 (Months 1-2): Sandbox integration, AA framework onboarding, Model validation (RBI), Security audit
PHASE 2 (Months 3-4): Pilot with 5 branches, Real GST/AA data ingestion, A/B testing framework
PHASE 3 (Months 5-6): Bank-wide rollout, 500+ RM adoption, Auto-ML retraining, Cross-sell engine

Success Metrics:
- Coverage: 80% of unserved MSMEs in IDBI geography mapped
- Conversion: 15% proactive offer to application rate
- Portfolio Quality: <2% GNPA on proactive loans vs 4% portfolio avg
- TAT Reduction: 60 days to 48 hours for pre-qualified offers

---

### Slide 11: Team & Competitive Advantage
| Member | Role | Expertise |
|--------|------|-----------|
| [Name] | ML Lead | Credit risk modeling, Tabular DL, 5+ yrs banking AI |
| [Name] | Backend Lead | FastAPI, K8s, Event-driven architecture, CBS integration |
| [Name] | Data Engineer | GST/AA data pipelines, Spark, Feast, Data contracts |
| [Name] | Frontend/UX | React, Dashboard design, Banking UX, Accessibility |

Why Us:
- Built production credit models at [Bank/NBFC/Fintech]
- Deep GST/AA data schema understanding
- End-to-end ML ops + bank-grade deployment experience
- Prototype LIVE and deployed - not just slides

---

### Slide 12: Ask & Next Steps
## We are Building the Nervous System for Proactive MSME Lending

**Immediate Ask:**
1. **Sandbox Access** - GST/AA synthetic APIs for model validation
2. **Credit Policy Session** - Align need categories with IDBI product grid
3. **RM Workshop** - Co-design outreach workflow with 5 relationship managers

**30-Day Sprint Goal:**
> Deploy MSME Pulse in IDBI sandbox to Score 5,000 unserved MSMEs to Generate 500 pre-qualified offers to Measure conversion

**Contact:** [Email] | [GitHub] | [LinkedIn] | **Demo:** [Live URL]

---

*Thank You | Questions Welcome*