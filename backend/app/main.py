from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, close_db
from app.api import msme, gst_returns, aa_accounts, need_predictions, product_recommendations, dashboard, health, xai


from app.services.ml_service import ml_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        await ml_service.initialize()
    except Exception as e:
        print(f"Failed to initialize ML models on startup: {e}")
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(msme.router, prefix="/api/v1/msmes", tags=["MSMEs"])
app.include_router(gst_returns.router, prefix="/api/v1/gst", tags=["GST Returns"])
app.include_router(aa_accounts.router, prefix="/api/v1/aa", tags=["Account Aggregator"])
app.include_router(need_predictions.router, prefix="/api/v1/needs", tags=["Need Predictions"])
app.include_router(product_recommendations.router, prefix="/api/v1/products", tags=["Product Recommendations"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(xai.router, prefix="/api/v1", tags=["XAI – Explainable Loan Eligibility"])


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
    }