from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.case import Case
from app.schemas.rules import RuleDiagnosisResponse
from app.services.rules.engine import rule_engine

router = APIRouter(tags=["Python Rule Fault Detection"])

@router.post("/cases/{case_id}/diagnose/rules", response_model=RuleDiagnosisResponse)
def diagnose_case_with_rules(
    case_id: int,
    db: Session = Depends(get_db)
):
    """
    Execute the deterministic Python Rule Engine for a troubleshooting case.
    Combines .pkt topology analysis facts with Cisco show-command evidence facts
    and evaluates 7 deterministic networking rules without fabricating facts.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot run rule diagnosis: Case #{case_id} not found."
        )

    result = rule_engine.diagnose_case(case_id=case_id, db=db)
    return result
