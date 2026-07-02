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

    # LLM Services
    LM_STUDIO_ENABLED: bool = os.getenv("LM_STUDIO_ENABLED", "true").lower() == "true"
    LM_STUDIO_BASE_URL: str = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    LM_STUDIO_MODEL: str = os.getenv("LM_STUDIO_MODEL", "qwen2.5-7b-instruct")
    LM_STUDIO_TIMEOUT_SECONDS: float = float(os.getenv("LM_STUDIO_TIMEOUT_SECONDS", "45"))
    LM_STUDIO_MAX_RETRIES: int = int(os.getenv("LM_STUDIO_MAX_RETRIES", "1"))

    # Google Gemini API
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()