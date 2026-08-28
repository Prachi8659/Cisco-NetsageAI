import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
PKT_STORAGE_DIR = Path(os.getenv("PKT_STORAGE_DIR", str(DATA_DIR / "pkt_uploads")))

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PKT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "NetSage AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    PROJECT_ROOT: Path = PROJECT_ROOT
    BACKEND_DIR: Path = BACKEND_DIR
    DATA_DIR: Path = DATA_DIR
    PKT_STORAGE_DIR: Path = PKT_STORAGE_DIR
    
    # Database (Default: local SQLite; easily overridden via DATABASE_URL env var on Render)
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR}/netsage.db")    
    # Upload limits
    MAX_PKT_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_PKT_EXTENSIONS: list[str] = [".pkt"]
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    # AI Diagnosis Settings
    AI_PROVIDER: str = "gemini"
    AI_API_KEY: str | None = None
    AI_MODEL: str = "gemini-3.1-flash-lite"
    AI_TIMEOUT_SECONDS: int = 30
    
    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
