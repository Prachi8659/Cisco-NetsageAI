from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.services.rules.models import RuleEngineResult
from backend.app.services.ai.models import AiDiagnosisResult

class ComparisonStatus(str, Enum):
    AGREEMENT = "AGREEMENT"
    DISAGREEMENT = "DISAGREEMENT"
    PYTHON_ONLY = "PYTHON_ONLY"
    AI_ONLY = "AI_ONLY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class DiagnosisComparisonResult(BaseModel):
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
    python_result: Optional[RuleEngineResult] = None
    ai_result: Optional[AiDiagnosisResult] = None
    compared_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
