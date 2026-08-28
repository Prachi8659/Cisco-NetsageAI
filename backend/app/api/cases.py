from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.session import get_db
from app.models.case import Case
from app.schemas.case import CaseCreate, CaseResponse, CaseUpdate
from app.services.pkt.storage import pkt_storage_service

router = APIRouter(prefix="/cases", tags=["Cases"])

def generate_next_case_number(db: Session) -> str:
    """Generate automatic case number in format CASE-001, CASE-002, etc."""
    total_cases = db.query(func.count(Case.id)).scalar() or 0
    return f"CASE-{(total_cases + 1):03d}"

@router.get("", response_model=list[CaseResponse])
def list_cases(
    skip: int = 0,
    limit: int = 100,
    category: str | None = None,
    db: Session = Depends(get_db)
):
    """List all troubleshooting cases with optional category filtering."""
    query = db.query(Case)
    if category:
        query = query.filter(Case.category == category)
    cases = query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()
    return cases

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    case_in: CaseCreate,
    db: Session = Depends(get_db)
):
    """Create a new networking troubleshooting case."""
    case_number = case_in.case_number or generate_next_case_number(db)
    
    # Check uniqueness of case number
    existing = db.query(Case).filter(Case.case_number == case_number).first()
    if existing:
        # If user provided a duplicate, generate a unique one or raise 400
        if case_in.case_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Case number '{case_number}' already exists."
            )
        else:
            case_number = f"CASE-{(db.query(func.count(Case.id)).scalar() + 1):03d}_{int(func.now())}"

    new_case = Case(
        case_number=case_number,
        title=case_in.title,
        category=case_in.category,
        severity=case_in.severity,
        symptom=case_in.symptom,
        topology_notes=case_in.topology_notes,
        status="OPEN"
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return new_case

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve details for a specific case, including associated .pkt file."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Troubleshooting case #{case_id} not found."
        )
    return case

@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: int,
    case_update: CaseUpdate,
    db: Session = Depends(get_db)
):
    """Update case details or status."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Troubleshooting case #{case_id} not found."
        )

    update_data = case_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    db.commit()
    db.refresh(case)
    return case

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Delete a case and all associated files and evidence."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Troubleshooting case #{case_id} not found."
        )

    # Clean up physical .pkt file if present on storage
    if case.pkt_file:
        try:
            file_path = pkt_storage_service.get_file_path(case.pkt_file.pkt_storage_path)
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass

    db.delete(case)
    db.commit()
    return None
