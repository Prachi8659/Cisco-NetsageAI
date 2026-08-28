from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.schemas.remediation import (
    HumanReviewCreate,
    RemediationConfirmInput,
    HumanReviewResponse,
    VerificationResponse
)
from backend.app.services.remediation.service import remediation_service

router = APIRouter(tags=["Human Review & Remediation Verification"])

@router.get("/cases/{case_id}/reviews", response_model=list[HumanReviewResponse])
def get_case_reviews(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve all Human-in-the-Loop review and remediation audit trail records for a case."""
    return remediation_service.get_case_reviews(case_id=case_id, db=db)

@router.post("/cases/{case_id}/reviews", response_model=HumanReviewResponse, status_code=status.HTTP_201_CREATED)
def submit_human_review(
    case_id: int,
    review_in: HumanReviewCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a human operator review decision (ACCEPT, REJECT, NEEDS_REVIEW) with audit notes.
    Updates the case lifecycle status accordingly.
    """
    return remediation_service.submit_review(case_id=case_id, review_in=review_in, db=db)

@router.post("/cases/{case_id}/reviews/{review_id}/confirm-remediation", response_model=HumanReviewResponse)
def confirm_remediation(
    case_id: int,
    review_id: int,
    confirm_in: RemediationConfirmInput,
    db: Session = Depends(get_db)
):
    """
    Record that the operator has manually applied the recommended corrective actions in Cisco Packet Tracer.
    Does NOT execute automatic modifications (strict recommendation-only policy).
    """
    return remediation_service.confirm_remediation(
        case_id=case_id,
        review_id=review_id,
        confirm_in=confirm_in,
        db=db
    )

@router.post("/cases/{case_id}/reviews/{review_id}/verify", response_model=VerificationResponse)
def verify_remediation(
    case_id: int,
    review_id: int,
    db: Session = Depends(get_db)
):
    """
    Perform a deterministic 'Verify After Fix' evaluation against the latest evidence.
    Compares BEFORE vs AFTER state to determine if the fault is RESOLVED or STILL_PRESENT.
    """
    return remediation_service.verify_remediation(
        case_id=case_id,
        review_id=review_id,
        db=db
    )
