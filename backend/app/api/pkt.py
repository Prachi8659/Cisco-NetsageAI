import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.case import Case
from backend.app.models.pkt import PktFile
from backend.app.schemas.pkt import PktFileResponse
from backend.app.services.pkt.models import PktAnalysisResult
from backend.app.services.pkt.storage import pkt_storage_service

router = APIRouter(tags=["Packet Tracer (.pkt)"])

@router.post("/cases/{case_id}/pkt", response_model=PktFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_pkt_file(
    case_id: int,
    file: UploadFile = File(..., description="Cisco Packet Tracer .pkt file"),
    db: Session = Depends(get_db)
):
    """
    Upload and associate a Cisco Packet Tracer .pkt file with a troubleshooting case.
    Validates file extension, size, non-emptiness, and stores securely.
    """
    # 1. Verify case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot upload .pkt file: Troubleshooting case #{case_id} not found."
        )

    # 2. Save and validate file through secure storage service
    storage_meta = await pkt_storage_service.save_pkt_file(case_id=case_id, upload_file=file)

    # 3. Check if existing PKT file record exists for this case
    existing_pkt = db.query(PktFile).filter(PktFile.case_id == case_id).first()
    if existing_pkt:
        # Clean up old file if different
        try:
            old_path = pkt_storage_service.get_file_path(existing_pkt.pkt_storage_path)
            if old_path.exists() and str(old_path) != storage_meta["storage_path"]:
                old_path.unlink()
        except Exception:
            pass  # Non-blocking cleanup

        # Update existing record
        existing_pkt.pkt_filename = storage_meta["original_filename"]
        existing_pkt.pkt_storage_path = storage_meta["storage_path"]
        existing_pkt.pkt_file_size = storage_meta["file_size"]
        existing_pkt.pkt_upload_status = "STORED"
        existing_pkt.sha256_hash = storage_meta["sha256_hash"]
        db.commit()
        db.refresh(existing_pkt)
        return existing_pkt
    else:
        # Create new record
        new_pkt = PktFile(
            case_id=case_id,
            pkt_filename=storage_meta["original_filename"],
            pkt_storage_path=storage_meta["storage_path"],
            pkt_file_size=storage_meta["file_size"],
            pkt_upload_status="STORED",
            sha256_hash=storage_meta["sha256_hash"]
        )
        db.add(new_pkt)
        db.commit()
        db.refresh(new_pkt)
        return new_pkt

@router.get("/cases/{case_id}/pkt", response_model=PktFileResponse)
def get_pkt_file_metadata(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve metadata of the .pkt file attached to a case."""
    pkt_file = db.query(PktFile).filter(PktFile.case_id == case_id).first()
    if not pkt_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No .pkt file associated with case #{case_id}."
        )
    return pkt_file

@router.get("/cases/{case_id}/pkt/download")
def download_pkt_file(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Safely download the uploaded .pkt file."""
    pkt_file = db.query(PktFile).filter(PktFile.case_id == case_id).first()
    if not pkt_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No .pkt file found for case #{case_id}."
        )

    file_path = pkt_storage_service.get_file_path(pkt_file.pkt_storage_path)
    return FileResponse(
        path=str(file_path),
        filename=pkt_file.pkt_filename,
        media_type="application/octet-stream"
    )

@router.delete("/cases/{case_id}/pkt", status_code=status.HTTP_204_NO_CONTENT)
def delete_pkt_file(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Remove the uploaded .pkt file from case and storage."""
    pkt_file = db.query(PktFile).filter(PktFile.case_id == case_id).first()
    if not pkt_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No .pkt file found for case #{case_id}."
        )

    # Validate file path through storage security guard (prevents deleting files outside authorized directory)
    try:
        file_path = pkt_storage_service.get_file_path(pkt_file.pkt_storage_path)
        if file_path.exists():
            file_path.unlink()
    except HTTPException as he:
        if he.status_code == status.HTTP_403_FORBIDDEN:
            raise he
        # If 404 (file already removed on disk), proceed to clean up the DB record
    except Exception:
        pass

    db.delete(pkt_file)
    db.commit()
    return None

@router.post("/cases/{case_id}/pkt/analyze", response_model=PktAnalysisResult)
def analyze_case_pkt(
    case_id: int,
    db: Session = Depends(get_db)
):
    """
    Analyze the Cisco Packet Tracer (.pkt) file associated with a troubleshooting case.
    Extracts normalized network facts, device types, interface configs, and topology connections when available.
    Truthfully reports UNKNOWN / UNAVAILABLE when encryption cannot be decoded.
    Never fabricates network data.
    """
    from backend.app.services.pkt.analyzer import pkt_analyzer_service
    return pkt_analyzer_service.analyze_case_pkt(case_id=case_id, db=db)

