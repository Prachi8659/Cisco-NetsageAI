from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class AiDiagnosisStatus(str, Enum):
    SUCCESS = "SUCCESS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    FAILED = "FAILED"

class AiDiagnosisResult(BaseModel):
    case_id: int
    status: AiDiagnosisStatus
    root_cause: Optional[str] = Field(default=None, description="Primary technical root cause of the network issue")
    fault_type: Optional[str] = Field(default=None, description="Standard fault classification (e.g. Interface Down, Duplicate IP, Gateway Mismatch)")
    affected_device: Optional[str] = Field(default=None, description="Name of the affected network host or device")
    affected_interface: Optional[str] = Field(default=None, description="Name of the affected port or interface if applicable")
    evidence: List[str] = Field(default_factory=list, description="Exact evidence bullet points supporting the diagnosis")
    explanation: Optional[str] = Field(default=None, description="Detailed explanation of how the fault impacts traffic flow")
    recommended_correction: Optional[str] = Field(default=None, description="Manual steps to perform in Cisco Packet Tracer to resolve the issue")
    confidence: int = Field(default=0, ge=0, le=100, description="AI confidence score between 0 and 100")
    reasoning_summary: Optional[str] = Field(default=None, description="Concise summary of evidence-based reasoning without hidden chain-of-thought")
    model_name: str = Field(default="gemini-2.0-flash", description="AI model that generated this diagnosis")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
