# MSME Pulse ⚡
### AI-Powered Proactive MSME Lending Intelligence Platform
**IDBI Innovate 2026 · Track 3 — MSME Business Needs Identification**

---

> **Moving IDBI Bank from reactive (wait-for-application) to proactive (detect-need-signal) lending**
> by aggregating GST data, Account Aggregator liability streams, and AI/ML to identify unserved MSME credit needs in real time.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    MSME Pulse Platform                   │
├──────────────┬─────────────────┬───────────────────────┤
│  Data Layer  │   AI/ML Layer   │    Application Layer   │
│              │                 │                        │
│  GST Returns │ Need Detection  │  React Dashboard       │
│  (GSTR-1/3B) │ (XGBoost +      │  (RM Portfolio View)   │
│              │  Multi-label)   │                        │
│  Account     │ Credit Risk PD  │  FastAPI Backend       │
│  Aggregator  │ (LightGBM +     │  (REST API + ONNX)     │
│  (AA Consent)│  Early Warning) │                        │
│              │                 │  PostgreSQL + Redis    │
│  Synthetic   │ Product Ranker  │  (Data + Cache)        │
│  Data Gen.   │ (LambdaMART)    │                        │
└──────────────┴─────────────────┴───────────────────────┘
```

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

### 1. Clone & Setup Environment
```bash
git clone https://github.com/your-team/msme-pulse
cd msme-pulse
cp .env.example .env
```

### 2. Generate Synthetic Data
```bash
pip install -r backend/requirements.txt
python scripts/data_generation/generate_synthetic_data.py --msmes 10000
```
This generates `synthetic_data/` with 10,000 MSMEs, ~150K GST returns, and ~25K AA accounts.

### 3. Train ML Models
```bash
python ml/train_models.py
```
Outputs `backend/models/need_detection_v1.onnx`, `credit_risk_v1.onnx`, `product_ranking_v1.onnx`.

### 4. Start Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
API docs at: http://localhost:8000/docs

### 5. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Dashboard at: http://localhost:3000

---

## Docker Compose (Full Stack)

```bash
# Build and start all services
docker compose up --build

# Services:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   API Docs:  http://localhost:8000/docs
#   Postgres:  localhost:5432
#   Redis:     localhost:6379
```

---

## Project Structure

```
idbi-innovate-track3/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── models.py            # SQLAlchemy ORM models (6 tables)
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── database.py          # Async SQLAlchemy engine + session
│   │   ├── config.py            # Settings (Pydantic BaseSettings)
│   │   ├── api/                 # 13 API route files
│   │   │   ├── msme.py          # MSME CRUD + search
│   │   │   ├── gst_returns.py   # GST return management
│   │   │   ├── aa_accounts.py   # Account Aggregator accounts
│   │   │   ├── need_predictions.py  # Need prediction endpoints
│   │   │   ├── product_recommendations.py  # Recommendation lifecycle
│   │   │   └── dashboard.py     # Portfolio analytics
│   │   └── services/
│   │       └── ml_service.py    # ONNX model serving + mock fallbacks
│   ├── models/                  # ONNX model files (after training)
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── App.tsx              # Root app with routing
│       ├── index.css            # Global design system
│       ├── api/client.ts        # Axios API client
│       ├── types/index.ts       # TypeScript type definitions
│       ├── components/
│       │   ├── Sidebar.tsx      # Navigation sidebar
│       │   └── Topbar.tsx       # Top header bar
│       └── pages/
│           ├── DashboardPage.tsx     # Portfolio KPIs + charts
│           ├── MSMESearchPage.tsx    # Filterable MSME directory
│           ├── MSMEProfilePage.tsx   # 360° profile + XAI panel
│           ├── NeedAnalyticsPage.tsx # Need category analytics
│           └── ConversionFunnelPage.tsx  # Recommendation funnel
│
├── ml/
│   └── train_models.py          # ML training + ONNX export pipeline
│
├── scripts/
│   └── data_generation/
│       └── generate_synthetic_data.py  # 10K MSME synthetic data
│
├── synthetic_data/              # Generated data output
├── deployment/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
└── docs/
    └── ppt_structure.md         # 12-slide presentation template
```

---

## AI/ML Models

| Model | Algorithm | Task | Key Features |
|-------|-----------|------|-------------|
| Need Detection | XGBoost Multi-Output | 6-label classification | GST trends, AA utilization, sector |
| Credit Risk (PD) | LightGBM Binary | Probability of Default | NPA/SMA indicators, overdue ratios |
| Product Ranker | LambdaMART | Learning-to-Rank | Need alignment, eligibility rules |

All models export to **ONNX format** for zero-latency inference via ONNX Runtime.
**SHAP TreeExplainer** provides per-prediction feature importance for regulatory explainability.

---

## Need Categories → IDBI Products

| Need Signal | Data Indicators | IDBI Product |
|-------------|----------------|-------------|
| Working Capital | Rising CC utilization, declining ITC | CC/OD Enhancement |
| Machinery/Capex | Capital goods HSN codes, export growth | Machinery Term Loan |
| Business Expansion | New GSTINs, revenue growth >20% | Business Expansion Loan |
| Inventory Funding | High B2C ratio, revenue volatility | Inventory Funding Loan |
| Trade Finance | Export ratio >20%, high B2B | Trade Finance |
| Digital Transformation | IT sector, young Pvt Ltd companies | Digital Business Loan |

---

## API Reference

Full Swagger documentation at `/docs` when running.

Key endpoints:
- `GET /api/v1/dashboard/portfolio/summary` — Portfolio KPIs
- `GET /api/v1/dashboard/portfolio/need-distribution` — Need category breakdown
- `GET /api/v1/msmes/?` — Search/filter MSMEs
- `GET /api/v1/dashboard/msme/{id}/full` — Full 360° MSME profile
- `POST /api/v1/needs/need-predictions/` — Create need prediction
- `PATCH /api/v1/products/recommendations/{id}/status` — Update recommendation lifecycle

---

## Team

Built for **IDBI Innovate Hackathon 2026 — Track 3**

---

*Detect · Match · Outreach · Lend*
