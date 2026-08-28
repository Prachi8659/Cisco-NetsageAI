from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class ReviewDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEEDS_REVIEW = "NEEDS_REVIEW"

class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    STILL_PRESENT = "STILL_PRESENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class HumanReviewCreate(BaseModel):
    decision: ReviewDecision = ReviewDecision.NEEDS_REVIEW
    reviewer_name: str = Field(default="Network Operator", min_length=1, max_length=100)
    reviewer_notes: Optional[str] = None
    previous_fault_type: Optional[str] = None
    previous_fault_device: Optional[str] = None

class RemediationConfirmInput(BaseModel):
    remediation_notes: Optional[str] = None

class HumanReviewResponse(BaseModel):
    id: int
    case_id: int
    decision: str
    reviewer_name: str
    reviewer_notes: Optional[str] = None
    remediation_confirmed: bool
    remediation_notes: Optional[str] = None
    remediation_applied_at: Optional[datetime] = None
    verification_status: str
    previous_fault_type: Optional[str] = None
    previous_fault_device: Optional[str] = None
    verification_findings: Optional[Any] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VerificationResponse(BaseModel):
    review_id: int
    case_id: int
    verification_status: VerificationStatus
    verdict_message: str
    before_fault: Optional[str] = None
    after_findings_count: int
    remaining_faults: List[Any] = Field(default_factory=list)
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)
