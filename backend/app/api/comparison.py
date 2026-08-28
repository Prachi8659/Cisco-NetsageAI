from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.case import Case
from backend.app.schemas.comparison import DiagnosisComparisonResponse
from backend.app.services.comparison.service import comparison_service

router = APIRouter(tags=["Diagnosis Comparison"])

@router.post("/cases/{case_id}/diagnose/compare", response_model=DiagnosisComparisonResponse)
def compare_case_diagnosis(
    case_id: int,
    db: Session = Depends(get_db)
):
    """
    Independently evaluate and compare deterministic Python Rule Engine findings
    against AI diagnosis for the same troubleshooting case.
    Determines AGREEMENT, DISAGREEMENT, PYTHON_ONLY, AI_ONLY, or INSUFFICIENT_EVIDENCE.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot run diagnosis comparison: Case #{case_id} not found."
        )

    result = comparison_service.compare_case(case_id=case_id, db=db)
    return result
