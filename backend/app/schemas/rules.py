from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.services.rules.models import RuleFinding, RuleSeverity, RuleStatus

class RuleDiagnosisResponse(BaseModel):
    case_id: int
    total_rules_evaluated: int
    faults_detected: list[RuleFinding]
    insufficient_evidence: list[RuleFinding]
    no_fault_rules: list[str]
    summary: str
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
