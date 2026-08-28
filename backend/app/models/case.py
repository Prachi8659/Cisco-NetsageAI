import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    category = Column(String(100), default="General", index=True)
    severity = Column(String(50), default="MEDIUM")
    symptom = Column(Text, nullable=False)
    topology_notes = Column(Text, nullable=True)
    status = Column(String(50), default="OPEN", index=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # Relationship to uploaded PKT file
    pkt_file = relationship("PktFile", back_populates="case", uselist=False, cascade="all, delete-orphan")

    # Relationship to Cisco command evidence
    evidence = relationship("CiscoEvidence", back_populates="case", cascade="all, delete-orphan", order_by="CiscoEvidence.created_at.desc()")

    # Relationship to Human-in-the-Loop Reviews and Audit Records
    reviews = relationship("HumanReview", back_populates="case", cascade="all, delete-orphan", order_by="HumanReview.created_at.desc()")

    def __repr__(self):
        return f"<Case(id={self.id}, case_number='{self.case_number}', title='{self.title}')>"
