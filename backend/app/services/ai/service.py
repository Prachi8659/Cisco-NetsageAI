from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.case import Case
from app.models.evidence import CiscoEvidence
from app.services.pkt.analyzer import pkt_analyzer_service
from app.services.rules.engine import rule_engine
from app.services.ai.models import AiDiagnosisResult, AiDiagnosisStatus
from app.services.ai.base import BaseAiProvider
from app.services.ai.prompts import SYSTEM_DIAGNOSIS_PROMPT, build_case_evidence_prompt
from app.services.ai.providers.mock_provider import MockAiProvider
from app.services.ai.providers.gemini_provider import GeminiAiProvider
from app.services.ai.providers.openai_provider import OpenAiProvider

class AiDiagnosisService:
    """
    Orchestrates evidence collection, prompt construction, and strict schema validation
    for AI-assisted network troubleshooting diagnosis.
    """

    def __init__(self, provider_override: Optional[BaseAiProvider] = None):
        self._provider_override = provider_override

    def get_provider(self) -> Optional[BaseAiProvider]:
        if self._provider_override:
            return self._provider_override

        provider_name = (settings.AI_PROVIDER or "").lower().strip()
        api_key = settings.AI_API_KEY

        if provider_name == "mock":
            return MockAiProvider()

        if not api_key:
            return None

        if provider_name == "gemini":
            return GeminiAiProvider(api_key=api_key)
        elif provider_name in ["openai", "azure", "anthropic_openai"]:
            return OpenAiProvider(api_key=api_key)

        return None

    def diagnose_case(self, case_id: int, db: Session) -> AiDiagnosisResult:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return AiDiagnosisResult(
                case_id=case_id,
                status=AiDiagnosisStatus.FAILED,
                explanation=f"Case #{case_id} not found in database.",
                confidence=0,
                model_name=settings.AI_MODEL,
            )

        provider = self.get_provider()
        if not provider:
            return AiDiagnosisResult(
                case_id=case_id,
                status=AiDiagnosisStatus.AI_UNAVAILABLE,
                explanation="AI diagnosis service is unavailable because no valid AI API key or provider is configured. The deterministic Python Rule Engine remains fully active.",
                confidence=0,
                model_name=settings.AI_MODEL,
                reasoning_summary="AI_API_KEY is not configured in backend environment."
            )

        # 1. Gather .pkt facts if available
        pkt_facts_dict: Dict[str, Any] = {}
        if case.pkt_file:
            try:
                pkt_analysis = pkt_analyzer_service.analyze_case_pkt(case_id=case_id, db=db)
                if pkt_analysis and pkt_analysis.facts:
                    pkt_facts_dict = pkt_analysis.facts.model_dump()
            except Exception:
                pass

        # 2. Gather Cisco show-command evidence
        evidence_list = db.query(CiscoEvidence).filter(CiscoEvidence.case_id == case_id).all()
        cisco_evidence_dicts = [
            {
                "device": ev.device,
                "command": ev.command,
                "raw_output": ev.raw_output,
                "parsed_facts": ev.parsed_facts,
            }
            for ev in evidence_list
        ]

        # 3. Gather Python Rule Engine findings
        python_findings_dicts: list[Dict[str, Any]] = []
        try:
            py_res = rule_engine.diagnose_case(case_id=case_id, db=db)
            python_findings_dicts = [
                f.model_dump() for f in py_res.faults_detected
            ]
        except Exception:
            pass

        # 4. Check for absolute minimum evidence
        if not pkt_facts_dict and not cisco_evidence_dicts:
            return AiDiagnosisResult(
                case_id=case_id,
                status=AiDiagnosisStatus.INSUFFICIENT_EVIDENCE,
                explanation="No Packet Tracer topology facts or Cisco show-command evidence have been uploaded for this case.",
                recommended_correction="Upload a .pkt topology file or submit Cisco CLI show-command outputs to enable diagnosis.",
                confidence=0,
                model_name=settings.AI_MODEL,
                reasoning_summary="Insufficient evidence to evaluate network operational state."
            )

        # 5. Build prompt payload
        user_prompt = build_case_evidence_prompt(
            case_title=case.title,
            symptom=case.symptom,
            topology_notes=case.topology_notes,
            pkt_facts=pkt_facts_dict,
            cisco_evidence=cisco_evidence_dicts,
            python_findings=python_findings_dicts,
        )

        # 6. Call AI provider
        try:
            raw_response = provider.generate_diagnosis(
                system_prompt=SYSTEM_DIAGNOSIS_PROMPT,
                user_prompt=user_prompt,
                model=settings.AI_MODEL,
                timeout=settings.AI_TIMEOUT_SECONDS,
            )

            # 7. Validate and parse response
            status_val = raw_response.get("status", "SUCCESS")
            if status_val not in [s.value for s in AiDiagnosisStatus]:
                status_val = "SUCCESS"

            # Parse confidence
            raw_conf = raw_response.get("confidence", 0)
            try:
                confidence_int = max(0, min(100, int(raw_conf)))
            except Exception:
                confidence_int = 50

            return AiDiagnosisResult(
                case_id=case_id,
                status=AiDiagnosisStatus(status_val),
                root_cause=raw_response.get("root_cause"),
                fault_type=raw_response.get("fault_type"),
                affected_device=raw_response.get("affected_device"),
                affected_interface=raw_response.get("affected_interface"),
                evidence=raw_response.get("evidence", []),
                explanation=raw_response.get("explanation"),
                recommended_correction=raw_response.get("recommended_correction"),
                confidence=confidence_int,
                reasoning_summary=raw_response.get("reasoning_summary"),
                model_name=settings.AI_MODEL,
            )

        except Exception as e:
            return AiDiagnosisResult(
                case_id=case_id,
                status=AiDiagnosisStatus.FAILED,
                explanation=f"AI diagnosis failed: {str(e)}",
                confidence=0,
                model_name=settings.AI_MODEL,
                reasoning_summary="Error occurred during AI inference or response schema parsing."
            )


ai_diagnosis_service = AiDiagnosisService()
