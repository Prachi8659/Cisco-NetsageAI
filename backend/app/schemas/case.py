from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.pkt import PktFileResponse

class CaseBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Brief descriptive title of the case")
    category: str = Field("General", max_length=100, description="Network domain e.g. VLAN, Routing, DHCP, Gateway, ACL, NAT")
    severity: str = Field("MEDIUM", description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")
    symptom: str = Field(..., min_length=5, description="Observed network fault or failure symptom")
    topology_notes: str | None = Field(None, description="Known topology details, device names, or notes")

class CaseCreate(CaseBase):
    case_number: str | None = Field(None, description="Optional custom case number like CASE-001. Auto-generated if omitted.")

class CaseUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    severity: str | None = None
    symptom: str | None = None
    topology_notes: str | None = None
    status: str | None = None

class CaseResponse(CaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_number: str
    status: str
    created_at: datetime
    updated_at: datetime
    pkt_file: PktFileResponse | None = None
