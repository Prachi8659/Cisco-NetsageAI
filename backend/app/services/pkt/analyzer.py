from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.case import Case
from app.models.pkt import PktFile
from app.services.pkt.extractor import pkt_extractor
from app.services.pkt.storage import pkt_storage_service
from app.services.pkt.models import PktAnalysisResult, AnalysisStatus

class PktAnalyzerService:
    def __init__(self, extractor=pkt_extractor, storage=pkt_storage_service):
        self.extractor = extractor
        self.storage = storage

    def analyze_case_pkt(self, case_id: int, db: Session) -> PktAnalysisResult:
        """
        Analyze the .pkt file associated with a troubleshooting case.
        Returns normalized facts, topology connections, and extraction status.
        Never fabricates facts.
        """
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot analyze .pkt: Troubleshooting case #{case_id} not found."
            )

        pkt_file = db.query(PktFile).filter(PktFile.case_id == case_id).first()
        if not pkt_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No Cisco Packet Tracer (.pkt) file is associated with case #{case_id}. Please upload a .pkt file first."
            )

        # Resolve storage file path
        try:
            file_path = self.storage.get_file_path(pkt_file.pkt_storage_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stored .pkt file missing on filesystem: {str(e)}"
            )

        # Run extraction
        result = self.extractor.extract(file_path)

        # Update pkt_file upload status in DB based on extraction
        if result.status == AnalysisStatus.SUCCESS:
            pkt_file.pkt_upload_status = "EXTRACTED"
        elif result.status == AnalysisStatus.PARTIAL:
            pkt_file.pkt_upload_status = "PARTIAL"
        elif result.status == AnalysisStatus.UNAVAILABLE:
            pkt_file.pkt_upload_status = "STORED_ENCRYPTED"
        else:
            pkt_file.pkt_upload_status = "FAILED"

        db.commit()
        db.refresh(pkt_file)

        return result

pkt_analyzer_service = PktAnalyzerService()
