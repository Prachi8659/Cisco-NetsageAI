import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.case import Case
from app.models.review import HumanReview
from app.schemas.remediation import HumanReviewCreate, RemediationConfirmInput, VerificationStatus
from app.services.rules.engine import rule_engine

class RemediationVerificationService:
    """
    Manages Human-in-the-Loop review decisions, manual remediation audit records,
    and deterministic 'Verify After Fix' evaluations.
    """

    def submit_review(
        self,
        case_id: int,
        review_in: HumanReviewCreate,
        db: Session
    ) -> HumanReview:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot submit review: Troubleshooting case #{case_id} not found."
            )

        # Create audit review record
        review = HumanReview(
            case_id=case_id,
            decision=review_in.decision.value,
            reviewer_name=review_in.reviewer_name,
            reviewer_notes=review_in.reviewer_notes,
            previous_fault_type=review_in.previous_fault_type,
            previous_fault_device=review_in.previous_fault_device,
            verification_status=VerificationStatus.PENDING.value
        )
        db.add(review)

        # Update case lifecycle status according to human decision
        if review_in.decision.value == "ACCEPT":
            case.status = "VERIFIED"
        elif review_in.decision.value == "NEEDS_REVIEW":
            case.status = "REVIEW_REQUIRED"
        elif review_in.decision.value == "REJECT":
            case.status = "OPEN"

        db.commit()
        db.refresh(review)
        return review

    def confirm_remediation(
        self,
        case_id: int,
        review_id: int,
        confirm_in: RemediationConfirmInput,
        db: Session
    ) -> HumanReview:
        review = db.query(HumanReview).filter(
            HumanReview.id == review_id,
            HumanReview.case_id == case_id
        ).first()

        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review #{review_id} for case #{case_id} not found."
            )

        review.remediation_confirmed = True
        review.remediation_applied_at = datetime.datetime.now(datetime.timezone.utc)
        if confirm_in.remediation_notes:
            review.remediation_notes = confirm_in.remediation_notes

        db.commit()
        db.refresh(review)
        return review

    def verify_remediation(
        self,
        case_id: int,
        review_id: int,
        db: Session
    ) -> Dict[str, Any]:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot verify: Case #{case_id} not found."
            )

        review = db.query(HumanReview).filter(
            HumanReview.id == review_id,
            HumanReview.case_id == case_id
        ).first()

        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review #{review_id} for case #{case_id} not found."
            )

        # 1. Re-run deterministic Python Rule Engine against current evidence
        py_res = rule_engine.diagnose_case(case_id=case_id, db=db)
        remaining_faults = [f.model_dump() for f in py_res.faults_detected]
        insufficient_rules = [f.model_dump() for f in py_res.insufficient_evidence]

        # 2. Check if evidence is missing
        if not case.pkt_file and not case.evidence:
            v_status = VerificationStatus.INSUFFICIENT_EVIDENCE
            msg = "Verification Inconclusive: No updated .pkt topology or Cisco CLI show commands available to evaluate."
        elif len(remaining_faults) == 0:
            # 3. All rules passed -> RESOLVED
            v_status = VerificationStatus.RESOLVED
            msg = "Remediation Successfully Verified: All deterministic network rules passed with 0 active violations."
            case.status = "VERIFIED"
        else:
            # 4. Faults still detected -> STILL_PRESENT
            v_status = VerificationStatus.STILL_PRESENT
            fault_names = ", ".join(f.get("fault_type", "Fault") for f in remaining_faults)
            msg = f"Fault Still Present: Detected {len(remaining_faults)} active violation(s): {fault_names}."
            case.status = "INVESTIGATING"

        # Update review record with audit snapshot
        now = datetime.datetime.now(datetime.timezone.utc)
        review.verification_status = v_status.value
        review.verified_at = now
        review.verification_findings = {
            "status": v_status.value,
            "verdict_message": msg,
            "before_fault": review.previous_fault_type,
            "remaining_faults": remaining_faults,
            "total_rules_evaluated": py_res.total_rules_evaluated,
            "insufficient_evidence": insufficient_rules,
            "verified_at": now.isoformat()
        }

        db.commit()
        db.refresh(review)

        return {
            "review_id": review.id,
            "case_id": case_id,
            "verification_status": v_status,
            "verdict_message": msg,
            "before_fault": review.previous_fault_type,
            "after_findings_count": len(remaining_faults),
            "remaining_faults": remaining_faults,
            "verified_at": now
        }

    def get_case_reviews(
        self,
        case_id: int,
        db: Session
    ) -> List[HumanReview]:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case #{case_id} not found."
            )
        return db.query(HumanReview).filter(
            HumanReview.case_id == case_id
        ).order_by(HumanReview.created_at.desc()).all()

remediation_service = RemediationVerificationService()
