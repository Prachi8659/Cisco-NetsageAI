import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base

class PktFile(Base):
    __tablename__ = "pkt_files"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    pkt_filename = Column(String(255), nullable=False)
    pkt_storage_path = Column(String(500), nullable=False)
    pkt_file_size = Column(Integer, nullable=False)  # in bytes
    pkt_uploaded_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    pkt_upload_status = Column(String(50), default="STORED", nullable=False)
    sha256_hash = Column(String(64), nullable=True)

    # Relationship back to case
    case = relationship("Case", back_populates="pkt_file")

    def __repr__(self):
        return f"<PktFile(id={self.id}, case_id={self.case_id}, filename='{self.pkt_filename}', status='{self.pkt_upload_status}')>"
