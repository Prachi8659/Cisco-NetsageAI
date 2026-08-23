from fastapi import APIRouter
from backend.app.api.cases import router as cases_router
from backend.app.api.pkt import router as pkt_router

api_router = APIRouter()
api_router.include_router(cases_router)
api_router.include_router(pkt_router)
