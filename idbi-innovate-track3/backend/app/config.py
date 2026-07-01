from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "MSME Pulse API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/msme_pulse")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ML Models
    MODEL_PATH: str = os.getenv("MODEL_PATH", "/app/models")
    NEED_DETECTION_MODEL: str = "need_detection_v1.onnx"
    CREDIT_RISK_MODEL: str = "credit_risk_v1.onnx"
    PRODUCT_RANKING_MODEL: str = "product_ranking_v1.onnx"
    
    # External APIs
    GST_API_URL: str = os.getenv("GST_API_URL", "https://api.sandbox.gst.gov.in")
    AA_API_URL: str = os.getenv("AA_API_URL", "https://api.sandbox.accountaggregator.gov.in")
    
    # Feature Store
    FEAST_REPO_PATH: str = os.getenv("FEAST_REPO_PATH", "/app/feature_store")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()