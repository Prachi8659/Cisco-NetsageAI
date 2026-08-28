from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.case import Case
from app.models.evidence import CiscoEvidence
from app.schemas.evidence import (
    CiscoEvidenceCreate,
    CiscoEvidenceResponse,
    EvidenceParseResponse,
)
from app.services.evidence.parser_service import evidence_parser_service

router = APIRouter(tags=["Cisco Show-Command Evidence"])

@router.post("/cases/{case_id}/evidence", response_model=CiscoEvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_case_evidence(
    case_id: int,
    payload: CiscoEvidenceCreate,
    db: Session = Depends(get_db)
):
    """
    Store raw Cisco show-command evidence for a troubleshooting case and automatically parse it.
    Preserves unmodified raw output while extracting normalized facts with zero fabrication.
    """
    # 1. Verify case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot add evidence: Case #{case_id} not found."
        )

    # 2. Parse evidence using modular parser service
    parse_result = evidence_parser_service.parse_evidence(
        device=payload.device,
        command=payload.command,
        raw_output=payload.raw_output,
    )

    # 3. Create database record
    evidence = CiscoEvidence(
        case_id=case_id,
        device=payload.device.strip(),
        command=payload.command.strip(),
        raw_output=payload.raw_output,
        parser_status=parse_result.status.value,
        parsed_facts=parse_result.facts.model_dump(),
        warnings=parse_result.warnings,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence

@router.get("/cases/{case_id}/evidence", response_model=list[CiscoEvidenceResponse])
def get_case_evidence_list(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve all Cisco show-command evidence records attached to a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case #{case_id} not found."
        )
    return case.evidence

@router.get("/cases/{case_id}/evidence/{evidence_id}", response_model=CiscoEvidenceResponse)
def get_single_evidence(
    case_id: int,
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve a specific Cisco evidence record with raw output and parsed facts."""
    evidence = db.query(CiscoEvidence).filter(
        CiscoEvidence.id == evidence_id,
        CiscoEvidence.case_id == case_id
    ).first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence #{evidence_id} not found for case #{case_id}."
        )
    return evidence

@router.delete("/cases/{case_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_single_evidence(
    case_id: int,
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Delete a Cisco evidence record from a case."""
    evidence = db.query(CiscoEvidence).filter(
        CiscoEvidence.id == evidence_id,
        CiscoEvidence.case_id == case_id
    ).first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence #{evidence_id} not found for case #{case_id}."
        )
    db.delete(evidence)
    db.commit()
    return None

@router.post("/cases/{case_id}/evidence/{evidence_id}/parse", response_model=EvidenceParseResponse)
def parse_single_evidence(
    case_id: int,
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Re-parse an existing raw Cisco command output and update stored facts."""
    evidence = db.query(CiscoEvidence).filter(
        CiscoEvidence.id == evidence_id,
        CiscoEvidence.case_id == case_id
    ).first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence #{evidence_id} not found for case #{case_id}."
        )

    parse_result = evidence_parser_service.parse_evidence(
        device=evidence.device,
        command=evidence.command,
        raw_output=evidence.raw_output,
    )

    evidence.parser_status = parse_result.status.value
    evidence.parsed_facts = parse_result.facts.model_dump()
    evidence.warnings = parse_result.warnings
    db.commit()
    db.refresh(evidence)

    return EvidenceParseResponse(
        evidence_id=evidence.id,
        case_id=case_id,
        device=evidence.device,
        command=evidence.command,
        status=parse_result.status.value,
        facts=parse_result.facts,
        warnings=parse_result.warnings,
    )
