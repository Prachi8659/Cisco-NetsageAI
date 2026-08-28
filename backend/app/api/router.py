from fastapi import APIRouter
from backend.app.api.cases import router as cases_router
from backend.app.api.pkt import router as pkt_router
from backend.app.api.evidence import router as evidence_router
from backend.app.api.rules import router as rules_router
from backend.app.api.ai import router as ai_router
from backend.app.api.comparison import router as comparison_router
from backend.app.api.remediation import router as remediation_router

api_router = APIRouter()
api_router.include_router(cases_router)
api_router.include_router(pkt_router)
api_router.include_router(evidence_router)
api_router.include_router(rules_router)
api_router.include_router(ai_router)
api_router.include_router(comparison_router)
api_router.include_router(remediation_router)
