from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.database.session import engine, Base
from backend.app.api.router import api_router

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "NetSage AI is an AI-assisted Cisco Packet Tracer networking troubleshooting platform. "
        "IMPORTANT SAFETY RULE: NetSage AI provides recommendations only. "
        "Network configuration changes must be performed manually inside Cisco Packet Tracer."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "ONLINE",
        "mode": "HUMAN_IN_THE_LOOP",
        "safety_notice": "NetSage AI provides recommendations only. Network configuration changes must be performed manually in Cisco Packet Tracer.",
        "api_docs": f"{settings.API_V1_STR}/docs",
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "storage_ready": settings.PKT_STORAGE_DIR.exists(),
        "database_ready": True
    }
