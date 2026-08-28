import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class HumanReview(Base):
    __tablename__ = "human_reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Review Decision: ACCEPT, REJECT, NEEDS_REVIEW
    decision = Column(String(50), nullable=False, default="NEEDS_REVIEW")
    reviewer_name = Column(String(100), default="Network Operator", nullable=False)
    reviewer_notes = Column(Text, nullable=True)
    
    # Manual Remediation Tracking (recommendation-only, manual execution)
    remediation_confirmed = Column(Boolean, default=False, nullable=False)
    remediation_notes = Column(Text, nullable=True)
    remediation_applied_at = Column(DateTime, nullable=True)
    
    # Verification After Fix Tracking
    verification_status = Column(String(50), default="PENDING", nullable=False) # PENDING, RESOLVED, STILL_PRESENT, INSUFFICIENT_EVIDENCE
    previous_fault_type = Column(String(100), nullable=True)
    previous_fault_device = Column(String(100), nullable=True)
    verification_findings = Column(JSON, nullable=True) # Full snapshot of findings post-verification
    verified_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # Relationship back to Case
    case = relationship("Case", back_populates="reviews")

    def __repr__(self):
        return f"<HumanReview(id={self.id}, case_id={self.case_id}, decision='{self.decision}', verification_status='{self.verification_status}')>"
