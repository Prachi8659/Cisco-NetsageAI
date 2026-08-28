import re
from typing import Optional, Tuple
from backend.app.services.rules.models import RuleEngineResult, RuleFinding
from backend.app.services.ai.models import AiDiagnosisResult, AiDiagnosisStatus
from backend.app.services.comparison.models import ComparisonStatus, DiagnosisComparisonResult

# Mapping canonical fault terms between Python rules and AI diagnosis text
FAULT_TYPE_CANONICAL_MAP = {
    "DUPLICATE_IP": "DUPLICATE_IP",
    "DUPLICATE IP": "DUPLICATE_IP",
    "DUPLICATE IP ADDRESS": "DUPLICATE_IP",
    "WRONG_SUBNET_MASK": "WRONG_SUBNET_MASK",
    "WRONG SUBNET MASK": "WRONG_SUBNET_MASK",
    "SUBNET MASK MISMATCH": "WRONG_SUBNET_MASK",
    "INVALID SUBNET": "WRONG_SUBNET_MASK",
    "GATEWAY_MISMATCH": "GATEWAY_MISMATCH",
    "GATEWAY MISMATCH": "GATEWAY_MISMATCH",
    "DEFAULT GATEWAY MISMATCH": "GATEWAY_MISMATCH",
    "WRONG GATEWAY": "GATEWAY_MISMATCH",
    "INTERFACE_DOWN": "INTERFACE_DOWN",
    "INTERFACE DOWN": "INTERFACE_DOWN",
    "ADMINISTRATIVELY DOWN": "INTERFACE_DOWN",
    "PORT DOWN": "INTERFACE_DOWN",
    "LINK DOWN": "INTERFACE_DOWN",
    "MISSING_VLAN": "MISSING_VLAN",
    "MISSING VLAN": "MISSING_VLAN",
    "VLAN MISMATCH": "MISSING_VLAN",
    "MISSING_ROUTE": "MISSING_ROUTE",
    "MISSING ROUTE": "MISSING_ROUTE",
    "NO ROUTE TO HOST": "MISSING_ROUTE",
    "ROUTING FAULT": "MISSING_ROUTE",
    "CONNECTION_FAULT": "CONNECTION_FAULT",
    "CONNECTION INCONSISTENCY": "CONNECTION_FAULT",
    "LINK STATE INCONSISTENCY": "CONNECTION_FAULT",
}

def normalize_fault_type(fault_str: Optional[str]) -> Optional[str]:
    if not fault_str:
        return None
    clean = re.sub(r'[^A-Z0-9_ ]', '', fault_str.upper()).strip()
    return FAULT_TYPE_CANONICAL_MAP.get(clean, clean)

def normalize_device_name(name: Optional[str]) -> str:
    if not name:
        return ""
    return re.sub(r'[\s_\-]', '', name.lower())

def normalize_interface_name(name: Optional[str]) -> str:
    if not name:
        return ""
    clean = name.lower().replace(" ", "").replace("/", "").replace("-", "")
    # Canonical abbreviations
    clean = re.sub(r'^fastethernet', 'fa', clean)
    clean = re.sub(r'^gigabitethernet', 'gi', clean)
    clean = re.sub(r'^serial', 'se', clean)
    clean = re.sub(r'^vlan', 'vl', clean)
    return clean

def devices_match(dev1: Optional[str], dev2: Optional[str]) -> bool:
    if not dev1 or not dev2:
        return False
    n1 = normalize_device_name(dev1)
    n2 = normalize_device_name(dev2)
    return n1 in n2 or n2 in n1

def interfaces_match(intf1: Optional[str], intf2: Optional[str]) -> bool:
    if not intf1 or not intf2:
        return True  # If either is unspecified, match on device level
    i1 = normalize_interface_name(intf1)
    i2 = normalize_interface_name(intf2)
    return i1 in i2 or i2 in i1

def to_pct_confidence(conf: float | int) -> int:
    if conf <= 1.0:
        return int(conf * 100)
    return min(100, int(conf))

class DiagnosisComparator:
    """
    Evaluates Python deterministic rule engine findings alongside AI diagnosis
    to produce a structured comparison verdict with zero bias.
    """

    def compare(
        self,
        case_id: int,
        py_result: RuleEngineResult,
        ai_result: AiDiagnosisResult
    ) -> DiagnosisComparisonResult:
        py_faults = py_result.faults_detected or []
        ai_success = ai_result.status == AiDiagnosisStatus.SUCCESS
        ai_insufficient = ai_result.status in [
            AiDiagnosisStatus.INSUFFICIENT_EVIDENCE,
            AiDiagnosisStatus.AI_UNAVAILABLE,
            AiDiagnosisStatus.FAILED
        ]

        # 1. Check if both sides lack evidence / found no faults
        if len(py_faults) == 0 and ai_insufficient:
            return DiagnosisComparisonResult(
                case_id=case_id,
                status=ComparisonStatus.INSUFFICIENT_EVIDENCE,
                verdict_title="Inconclusive: Insufficient Evidence",
                explanation="Neither the Python Rule Engine nor the AI diagnosis could confirm a fault due to lack of network facts or show-command evidence.",
                recommended_action="Upload a Packet Tracer .pkt file or paste Cisco CLI show commands to provide necessary troubleshooting context.",
                confidence_score=0,
                human_review_required=True,
                python_summary=py_result.summary,
                ai_summary=ai_result.explanation or "AI diagnosis unavailable or inconclusive.",
                python_result=py_result,
                ai_result=ai_result
            )

        # 2. Check if Python detected a fault but AI did not confirm it
        if len(py_faults) > 0 and not ai_success:
            first_py = py_faults[0]
            py_conf_pct = to_pct_confidence(first_py.confidence)
            return DiagnosisComparisonResult(
                case_id=case_id,
                status=ComparisonStatus.PYTHON_ONLY,
                verdict_title=f"Deterministic Fault: {first_py.fault_type} (Python Only)",
                explanation=f"The Python Rule Engine deterministically detected '{first_py.fault_type}' on {first_py.device}, but the AI diagnosis did not produce a confirmed root cause ({ai_result.status.value}).",
                recommended_action=f"Review Python rule finding on {first_py.device} ({first_py.suggested_correction}).",
                confidence_score=py_conf_pct,
                aligned_fault_type=first_py.fault_type,
                aligned_device=first_py.device,
                aligned_interface=first_py.interface,
                human_review_required=True,
                python_summary=f"Python detected {len(py_faults)} deterministic fault(s): {', '.join(f.fault_type for f in py_faults)}.",
                ai_summary=ai_result.explanation or f"AI returned {ai_result.status.value}.",
                python_result=py_result,
                ai_result=ai_result
            )

        # 3. Check if AI detected a fault while Python found 0 faults (e.g. unassigned IP on PC4)
        if len(py_faults) == 0 and ai_success:
            ai_conf_pct = to_pct_confidence(ai_result.confidence)
            return DiagnosisComparisonResult(
                case_id=case_id,
                status=ComparisonStatus.AI_ONLY,
                verdict_title=f"Novel Fault Detected: {ai_result.fault_type or 'Configuration Issue'} (AI Only)",
                explanation=(
                    f"The AI diagnosis identified '{ai_result.root_cause}' on {ai_result.affected_device or 'endpoint'}. "
                    f"The 7 deterministic Python rules evaluated 0 violations because this specific condition is currently outside the hardcoded rule set."
                ),
                recommended_action=ai_result.recommended_correction or "Inspect device configuration in Cisco Packet Tracer to verify AI observation.",
                confidence_score=ai_conf_pct,
                aligned_fault_type=ai_result.fault_type,
                aligned_device=ai_result.affected_device,
                aligned_interface=ai_result.affected_interface,
                human_review_required=True,
                python_summary=f"Python evaluated {py_result.total_rules_evaluated} deterministic rules with 0 violations.",
                ai_summary=ai_result.root_cause or "AI diagnosed configuration fault.",
                python_result=py_result,
                ai_result=ai_result
            )

        # 4. Both Python and AI produced positive diagnoses: Evaluate Agreement vs Disagreement
        ai_canon_fault = normalize_fault_type(ai_result.fault_type)
        matching_fault: Optional[RuleFinding] = None

        for py_f in py_faults:
            py_canon_fault = normalize_fault_type(py_f.fault_type)
            # Check fault compatibility
            faults_match = (
                py_canon_fault == ai_canon_fault or
                (py_canon_fault and ai_canon_fault and (py_canon_fault in ai_canon_fault or ai_canon_fault in py_canon_fault))
            )
            # Check device / interface match
            dev_match = devices_match(py_f.device, ai_result.affected_device)
            intf_match = interfaces_match(py_f.interface, ai_result.affected_interface)

            if faults_match and (dev_match or intf_match):
                matching_fault = py_f
                break

        if matching_fault:
            # Case 4A: AGREEMENT (Consensus)
            py_conf_pct = to_pct_confidence(matching_fault.confidence)
            ai_conf_pct = to_pct_confidence(ai_result.confidence)
            combined_conf = min(100, max(py_conf_pct, ai_conf_pct))
            dev_target = matching_fault.device or ai_result.affected_device or "Target Device"
            intf_target = matching_fault.interface or ai_result.affected_interface or ""

            return DiagnosisComparisonResult(
                case_id=case_id,
                status=ComparisonStatus.AGREEMENT,
                verdict_title=f"Consensus Achieved: {matching_fault.fault_type} on {dev_target}",
                explanation=(
                    f"High confidence alignment: Both deterministic Python rules and AI reasoning independently isolated "
                    f"'{matching_fault.fault_type}' on {dev_target} {f'({intf_target})' if intf_target else ''}."
                ),
                recommended_action=matching_fault.suggested_correction or ai_result.recommended_correction or "Apply verified correction in Cisco Packet Tracer.",
                confidence_score=combined_conf,
                aligned_fault_type=matching_fault.fault_type,
                aligned_device=dev_target,
                aligned_interface=intf_target or None,
                human_review_required=True,
                python_summary=f"Python Rule Engine ({matching_fault.rule_id}): {matching_fault.description}",
                ai_summary=f"AI Diagnosis ({ai_result.model_name}): {ai_result.root_cause}",
                python_result=py_result,
                ai_result=ai_result
            )
        else:
            # Case 4B: DISAGREEMENT (Divergent findings)
            first_py = py_faults[0]
            py_conf_pct = to_pct_confidence(first_py.confidence)
            ai_conf_pct = to_pct_confidence(ai_result.confidence)
            return DiagnosisComparisonResult(
                case_id=case_id,
                status=ComparisonStatus.DISAGREEMENT,
                verdict_title="Divergent Diagnoses: Python vs AI Discrepancy",
                explanation=(
                    f"Python Rule Engine detected '{first_py.fault_type}' on {first_py.device}, while AI diagnosis "
                    f"reasoned '{ai_result.fault_type or 'Different Fault'}' on {ai_result.affected_device or 'another device'}. "
                    f"Neither diagnosis has been artificially overridden."
                ),
                recommended_action=(
                    "Mandatory human operator review required. Inspect Cisco CLI evidence and Packet Tracer topology "
                    "to determine which diagnosis accurately represents the network defect."
                ),
                confidence_score=min(py_conf_pct, ai_conf_pct),
                human_review_required=True,
                python_summary=f"Python: {first_py.fault_type} on {first_py.device} ({first_py.description})",
                ai_summary=f"AI: {ai_result.fault_type or 'Fault'} on {ai_result.affected_device or 'Unknown'} ({ai_result.root_cause})",
                python_result=py_result,
                ai_result=ai_result
            )

comparator = DiagnosisComparator()
