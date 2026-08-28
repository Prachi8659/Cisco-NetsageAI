from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from backend.app.services.pkt.models import FactSource

class RuleSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RuleStatus(str, Enum):
    DETECTED = "DETECTED"
    NO_FAULT = "NO_FAULT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class RuleFinding(BaseModel):
    rule_id: str = Field(..., description="Unique identifier of the rule, e.g. DUPLICATE_IP")
    fault_type: str = Field(..., description="Human-readable fault name, e.g. Duplicate IP Address")
    severity: RuleSeverity = RuleSeverity.HIGH
    device: str = Field(..., description="Target device name affected by fault")
    interface: str | None = Field(default=None, description="Specific interface if applicable")
    description: str = Field(..., description="Clear explanation of the detected issue")
    evidence: str = Field(..., description="Exact facts/observations demonstrating the fault")
    suggested_correction: str = Field(..., description="Manual corrective action to take in Packet Tracer")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence rating between 0.0 and 1.0")
    source: str = Field(default="PYTHON_RULE", description="Supporting fact origin: PKT_EXTRACTED, CISCO_EVIDENCE, or MIXED")
    status: RuleStatus = RuleStatus.DETECTED

class RuleEngineResult(BaseModel):
    case_id: int
    total_rules_evaluated: int = 0
    faults_detected: list[RuleFinding] = Field(default_factory=list)
    insufficient_evidence: list[RuleFinding] = Field(default_factory=list)
    no_fault_rules: list[str] = Field(default_factory=list)
    summary: str = "Analysis complete."
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
