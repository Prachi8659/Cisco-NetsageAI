import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class CiscoEvidence(Base):
    __tablename__ = "cisco_evidence"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    device = Column(String(100), nullable=False, index=True)
    command = Column(String(200), nullable=False)
    raw_output = Column(Text, nullable=False)
    parser_status = Column(String(50), default="UNKNOWN", nullable=False)
    parsed_facts = Column(JSON, nullable=True)  # Normalized facts dictionary
    warnings = Column(JSON, nullable=True)      # Parser warnings / notes list
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # Relationship back to Case
    case = relationship("Case", back_populates="evidence")

    def __repr__(self):
        return f"<CiscoEvidence(id={self.id}, case_id={self.case_id}, device='{self.device}', command='{self.command}', status='{self.parser_status}')>"
