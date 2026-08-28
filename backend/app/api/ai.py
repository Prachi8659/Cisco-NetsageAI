from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.case import Case
from app.schemas.ai import AiDiagnosisResponse
from app.services.ai.service import ai_diagnosis_service

router = APIRouter(tags=["AI Network Diagnosis"])

@router.post("/cases/{case_id}/diagnose/ai", response_model=AiDiagnosisResponse)
def diagnose_case_with_ai(
    case_id: int,
    db: Session = Depends(get_db)
):
    """
    Perform an independent, evidence-first AI diagnosis on a troubleshooting case.
    Evaluates Packet Tracer topology facts, Cisco CLI show outputs, Python findings,
    and observed symptoms with zero fact fabrication.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot run AI diagnosis: Case #{case_id} not found."
        )

    result = ai_diagnosis_service.diagnose_case(case_id=case_id, db=db)
    return result
