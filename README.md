# MSME Pulse
### AI-Powered Proactive MSME Lending Intelligence Platform
**IDBI Innovate 2026 · Track 3 — MSME Business Needs Identification**

---

## Overview

MSME Pulse addresses a core problem in institutional lending: most banks evaluate MSME credit using traditional financial documents — balance sheets, ITRs — that a significant portion of New-to-Credit (NTC) and New-to-Bank (NTB) enterprises either do not have or maintain inadequately.

This platform aggregates alternate data sources — GST returns, Account Aggregator (AA) bank feeds, EPFO signals — to compute a multidimensional financial health score, detect unserved credit needs, and generate explainable loan eligibility decisions in near real time. The goal is to move IDBI Bank from a reactive lending posture (wait for the customer to apply) to a proactive one (identify the need signal before the customer walks in).

---

## Problem Statement

> Bank's MSME credit evaluation relies on traditional financial documents, which many New-to-Credit and New-to-Bank enterprises lack or maintain inadequately. Despite the availability of rich alternate data (GST, UPI, AA, EPFO), the absence of a unified assessment framework leads to high rejection rates, missed viable borrowers, limited portfolio diversification, and slower financial inclusion progress.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      MSME Pulse Platform                      │
├────────────────┬──────────────────────┬──────────────────────┤
│   Data Layer   │     AI / ML Layer    │   Application Layer  │
│                │                      │                      │
│  GST Returns   │  Need Detection      │  React Dashboard     │
│  (GSTR-1/3B)  │  (XGBoost Multi-     │  (RM Portfolio View) │
│                │   label Classifier)  │                      │
│  Account       │  Credit Risk PD      │  FastAPI Backend     │
│  Aggregator    │  (LightGBM Binary)   │  (REST API + ONNX)   │
│  (AA Consent)  │                      │                      │
│                │  XAI Loan Engine     │  PostgreSQL + Redis   │
│  Synthetic     │  (Rule-based + SHAP  │  (Data + Cache)      │
│  Data Gen.     │   Contributions)     │                      │
└────────────────┴──────────────────────┴──────────────────────┘
```

---

## Features

### Core Platform
- Portfolio dashboard with KPI cards, need distribution, and geographic heatmap
- MSME search and 360-degree profile view
- Need prediction using alternate data (GST + AA signals)
- Product recommendation engine with eligibility scoring
- Recommendation lifecycle tracking (generated → sent → applied → approved)
- Conversion funnel analytics

### XAI Loan Eligibility Engine
The centerpiece feature built for this submission. Given an MSME ID and an asking loan amount, the system:

1. Fetches 12 months of GST returns and all linked AA accounts
2. Computes six sub-scores across financial health dimensions
3. Produces a composite eligibility score (0–100) with a named band
4. Sizes the maximum loan the MSME qualifies for based on turnover and repayment history
5. Flags a higher amount suggestion for top-tier borrowers who are undervaluing themselves
6. Generates a score slab comparison table — user's actual metrics versus healthy benchmarks
7. Outputs SHAP-style feature contributions showing what is helping and hurting the score
8. Lists specific, actionable improvement areas and key strengths
9. Suggests up to four loan products with tenure, rate, and EMI estimates

---

## Scoring Dimensions

| Dimension | Weight | Data Source | Key Signals |
|---|---|---|---|
| GST Compliance | 20% | GST Returns | Filing consistency, ITC utilization ratio |
| Revenue Health | 25% | GST Returns | Annual turnover, YoY growth, B2B mix |
| Repayment Behavior | 25% | AA Accounts | Days Past Due, NPA/SMA flags, overdue ratio |
| Credit Utilization | 15% | AA Accounts | Outstanding / Sanctioned limit |
| Business Stability | 10% | MSME Registration | Vintage in years, constitution type |
| Cash Flow Health | 5% | GST Returns | Net tax paid consistency |

### Eligibility Bands

| Score | Band | Eligibility |
|---|---|---|
| 85 – 100 | EXCELLENT | Eligible — Premium offer unlocked |
| 70 – 84 | GOOD | Eligible — Standard products |
| 55 – 69 | FAIR | Eligible with conditions |
| 40 – 54 | POOR | Not eligible currently |
| 0 – 39 | INELIGIBLE | Reapply after improvement |

---

## Tech Stack

**Backend**
- Python 3.11, FastAPI 0.109, SQLAlchemy 2.0 (async)
- PostgreSQL 15 with asyncpg driver
- Redis 7 for caching
- XGBoost, LightGBM, CatBoost for model training
- ONNX + ONNX Runtime for zero-latency inference
- Pydantic v2 for schema validation

**Frontend**
- React 18, TypeScript, Vite
- React Router v6
- TanStack Query (React Query) for data fetching
- Axios for HTTP
- Lucide React for icons
- Vanilla CSS design system

**Infrastructure**
- Docker + Docker Compose (full stack)
- Nginx reverse proxy

---

## Project Structure

```
idbi-innovate-track3/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI application entry
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   ├── database.py               # Async engine and session
│   │   ├── config.py                 # Environment settings
│   │   ├── api/
│   │   │   ├── msme.py               # MSME CRUD and search
│   │   │   ├── gst_returns.py        # GST return endpoints
│   │   │   ├── aa_accounts.py        # AA account endpoints
│   │   │   ├── need_predictions.py   # Need prediction endpoints
│   │   │   ├── product_recommendations.py
│   │   │   ├── dashboard.py          # Portfolio analytics
│   │   │   └── xai.py                # XAI loan eligibility endpoint
│   │   └── services/
│   │       ├── ml_service.py         # ONNX model serving
│   │       └── xai_service.py        # XAI scoring and explanation engine
│   ├── models/                       # ONNX model files (post training)
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── index.css                 # Global design system
│       ├── api/client.ts             # Centralized Axios client
│       ├── components/
│       │   ├── Sidebar.tsx
│       │   └── Topbar.tsx
│       └── pages/
│           ├── DashboardPage.tsx
│           ├── MSMESearchPage.tsx
│           ├── MSMEProfilePage.tsx
│           ├── NeedAnalyticsPage.tsx
│           ├── ConversionFunnelPage.tsx
│           └── LoanEligibilityPage.tsx   # XAI Loan Eligibility UI
│
├── ml/
│   └── train_models.py               # Training and ONNX export pipeline
│
├── scripts/
│   └── data_generation/
│       └── generate_synthetic_data.py
│
├── synthetic_data/
├── deployment/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docker-compose.yml
└── .env.example
```

---

## Quick Start — Local Development

### Prerequisites
- Python 3.11 or higher
- Node.js 20 or higher
- PostgreSQL 15 or higher
- Redis 7 or higher

### 1. Clone and configure

```bash
git clone https://github.com/your-team/msme-pulse
cd msme-pulse/idbi-innovate-track3
cp .env.example .env
# Edit .env with your database credentials
```

### 2. Install Python dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Generate synthetic data

```bash
python scripts/data_generation/generate_synthetic_data.py --msmes 10000
```

This creates `synthetic_data/` with 10,000 MSMEs, approximately 150,000 GST return records, and 25,000 AA accounts.

### 4. Train and export ML models

```bash
python ml/train_models.py
```

Outputs `backend/models/need_detection_v1.onnx`, `credit_risk_v1.onnx`, and `product_ranking_v1.onnx`.

> If you skip this step, the system falls back to rule-based mock predictions automatically.

### 5. Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Interactive API documentation is available at `http://localhost:8000/docs`.

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard is available at `http://localhost:3000`.

---

## Quick Start — Docker (Full Stack)

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## API Reference

Full interactive documentation is available at `/docs` when the backend is running.

### XAI Loan Eligibility

```
POST /api/v1/xai/loan-explanation
```

Request body:

```json
{
  "msme_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "asking_amount": 2500000,
  "loan_purpose": "working_capital"
}
```

The response contains the eligibility score, band, computed maximum loan amount, score slab comparison table, SHAP-style feature contributions, loan product suggestions with EMI estimates, and a plain-language XAI narrative.

### Other Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/dashboard/portfolio/summary` | Portfolio-level KPIs |
| GET | `/api/v1/dashboard/portfolio/need-distribution` | Need category breakdown |
| GET | `/api/v1/msmes/` | Search and filter MSMEs |
| GET | `/api/v1/dashboard/msme/{id}/full` | Full 360-degree MSME profile |
| POST | `/api/v1/needs/need-predictions/` | Trigger need prediction |
| PATCH | `/api/v1/products/recommendations/{id}/status` | Update recommendation status |

---

## Need Categories and Product Mapping

| Need Signal | Key Data Indicators | IDBI Product |
|---|---|---|
| Working Capital | Rising CC utilization, falling ITC | CC / OD Enhancement |
| Machinery / Capex | Capital goods HSN codes, export growth | Machinery Term Loan |
| Business Expansion | Multi-GSTIN activity, revenue growth > 20% | Business Expansion Loan |
| Inventory Funding | High B2C ratio, seasonal revenue swings | Inventory Funding Loan |
| Trade Finance | Export ratio > 20%, high B2B concentration | Trade Finance Facility |
| Digital Transformation | IT sector NIC codes, young Pvt Ltd firms | Digital Business Loan |

---

## ML Models

| Model | Algorithm | Task | Explainability |
|---|---|---|---|
| Need Detection | XGBoost Multi-Output | 6-label classification | SHAP TreeExplainer |
| Credit Risk PD | LightGBM Binary | Probability of Default | SHAP values |
| Product Ranker | LambdaMART | Learning-to-Rank | Feature importance |

All models are exported to ONNX format for inference via ONNX Runtime, keeping the serving layer framework-agnostic and low-latency.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the following:

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/msme_pulse
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
MODEL_PATH=/path/to/backend/models
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "add: your feature description"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

This project was built for IDBI Innovate 2026 and is intended for demonstration and evaluation purposes.
