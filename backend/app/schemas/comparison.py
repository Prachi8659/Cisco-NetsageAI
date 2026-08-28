from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.services.comparison.models import ComparisonStatus
from backend.app.schemas.rules import RuleDiagnosisResponse
from backend.app.schemas.ai import AiDiagnosisResponse

class DiagnosisComparisonResponse(BaseModel):
    case_id: int
    status: ComparisonStatus
    verdict_title: str
    explanation: str
    recommended_action: str
    confidence_score: int = Field(default=0, ge=0, le=100)
    aligned_fault_type: Optional[str] = None
    aligned_device: Optional[str] = None
    aligned_interface: Optional[str] = None
    human_review_required: bool = True
    python_summary: str
    ai_summary: str
    python_result: Optional[RuleDiagnosisResponse] = None
    ai_result: Optional[AiDiagnosisResponse] = None
    compared_at: datetime

    model_config = ConfigDict(from_attributes=True)
