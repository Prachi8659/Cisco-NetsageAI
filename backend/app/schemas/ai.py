from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.services.ai.models import AiDiagnosisStatus

class AiDiagnosisResponse(BaseModel):
    case_id: int
    status: AiDiagnosisStatus
    root_cause: Optional[str] = None
    fault_type: Optional[str] = None
    affected_device: Optional[str] = None
    affected_interface: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    recommended_correction: Optional[str] = None
    confidence: int = Field(default=0, ge=0, le=100)
    reasoning_summary: Optional[str] = None
    model_name: str
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
