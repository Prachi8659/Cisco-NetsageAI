from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from backend.app.services.pkt.models import NormalizedNetworkFacts

class CiscoEvidenceCreate(BaseModel):
    device: str = Field(..., min_length=1, max_length=100, description="Target device name, e.g. R1, Switch0")
    command: str = Field(..., min_length=1, max_length=200, description="Cisco show command executed, e.g. show ip interface brief")
    raw_output: str = Field(..., min_length=1, description="Raw copied CLI output from Cisco terminal")

class CiscoEvidenceResponse(BaseModel):
    id: int
    case_id: int
    device: str
    command: str
    raw_output: str
    parser_status: str
    parsed_facts: dict[str, Any] | None = None
    warnings: list[str] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EvidenceParseResponse(BaseModel):
    evidence_id: int
    case_id: int
    device: str
    command: str
    status: str
    facts: NormalizedNetworkFacts
    warnings: list[str]
