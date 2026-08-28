import uuid
import pytest
from backend.app.core.config import settings
from backend.app.models.case import Case
from backend.app.models.evidence import CiscoEvidence
from backend.app.services.rules.models import RuleEngineResult, RuleFinding, RuleSeverity, RuleStatus
from backend.app.services.ai.models import AiDiagnosisResult, AiDiagnosisStatus
from backend.app.services.comparison.models import ComparisonStatus
from backend.app.services.comparison.comparator import comparator
from backend.app.services.comparison.service import ComparisonService

@pytest.fixture
def sample_case(db_session):
    uid = uuid.uuid4().hex[:8]
    case = Case(
        title=f"Comparison Test Case {uid}",
        case_number=f"CASE-COMP-{uid}",
        category="VLAN",
        severity="HIGH",
        symptom="PC0 cannot ping switch or gateway",
        status="OPEN"
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case

# 1. Test Agreement: Both Python and AI agree on interface down
def test_comparison_agreement():
    py_result = RuleEngineResult(
        case_id=1,
        total_rules_evaluated=7,
        faults_detected=[
            RuleFinding(
                rule_id="INTERFACE_DOWN",
                fault_type="Interface Down",
                severity=RuleSeverity.HIGH,
                device="PC0",
                interface="FastEthernet0",
                description="Interface FastEthernet0 on PC0 is administratively down.",
                evidence="FastEthernet0 is ADMINISTRATIVELY_DOWN in show ip interface brief.",
                suggested_correction="Issue 'no shutdown' on PC0 FastEthernet0.",
                confidence=0.95,
                source="CISCO_SHOW",
                status=RuleStatus.DETECTED
            )
        ],
        insufficient_evidence=[],
        no_fault_rules=["DUPLICATE_IP", "WRONG_SUBNET_MASK"],
        summary="1 fault detected by Python Rule Engine."
    )

    ai_result = AiDiagnosisResult(
        case_id=1,
        status=AiDiagnosisStatus.SUCCESS,
        root_cause="FastEthernet0 on PC0 is administratively shut down.",
        fault_type="Interface Down",
        affected_device="PC0",
        affected_interface="FastEthernet0",
        evidence=["FastEthernet0 status is administratively down."],
        explanation="Physical link carrier is disabled.",
        recommended_correction="Issue 'no shutdown' on PC0 FastEthernet0.",
        confidence=98,
        model_name="mock-model"
    )

    res = comparator.compare(case_id=1, py_result=py_result, ai_result=ai_result)
    assert res.status == ComparisonStatus.AGREEMENT
    assert "Consensus Achieved" in res.verdict_title
    assert res.aligned_fault_type == "Interface Down"
    assert res.aligned_device == "PC0"
    assert res.confidence_score >= 95
    assert res.human_review_required is True

# 2. Test Disagreement: Python detects Duplicate IP, AI diagnoses Missing Route on Router
def test_comparison_disagreement():
    py_result = RuleEngineResult(
        case_id=2,
        total_rules_evaluated=7,
        faults_detected=[
            RuleFinding(
                rule_id="DUPLICATE_IP",
                fault_type="Duplicate IP",
                severity=RuleSeverity.CRITICAL,
                device="PC0, PC1",
                interface="FastEthernet0",
                description="Duplicate IP address 192.168.1.50 assigned to PC0 and PC1.",
                evidence="Both PC0 and PC1 have IP 192.168.1.50.",
                suggested_correction="Change PC1 IP to an unused address.",
                confidence=1.0,
                source="CISCO_SHOW",
                status=RuleStatus.DETECTED
            )
        ],
        insufficient_evidence=[],
        no_fault_rules=[],
        summary="Duplicate IP fault detected."
    )

    ai_result = AiDiagnosisResult(
        case_id=2,
        status=AiDiagnosisStatus.SUCCESS,
        root_cause="Missing default route on Router R1 causes upstream packet drops.",
        fault_type="Missing Route",
        affected_device="R1",
        affected_interface="GigabitEthernet0/0",
        evidence=["ip route 0.0.0.0 0.0.0.0 is missing from show ip route."],
        explanation="Router R1 cannot forward packets to external destinations.",
        recommended_correction="Configure 'ip route 0.0.0.0 0.0.0.0 10.0.0.1' on R1.",
        confidence=85,
        model_name="mock-model"
    )

    res = comparator.compare(case_id=2, py_result=py_result, ai_result=ai_result)
    assert res.status == ComparisonStatus.DISAGREEMENT
    assert "Divergent Diagnoses" in res.verdict_title
    assert "Duplicate IP" in res.python_summary
    assert "Missing Route" in res.ai_summary
    assert res.human_review_required is True

# 3. Test AI_ONLY: PC4 has no IP address assigned (Python evaluates 7 rules with 0 faults)
def test_comparison_ai_only_unassigned_ip():
    py_result = RuleEngineResult(
        case_id=3,
        total_rules_evaluated=7,
        faults_detected=[],
        insufficient_evidence=[],
        no_fault_rules=["DUPLICATE_IP", "WRONG_SUBNET_MASK", "GATEWAY_MISMATCH", "INTERFACE_DOWN", "MISSING_VLAN", "MISSING_ROUTE", "CONNECTION_FAULT"],
        summary="All 7 deterministic fault rules passed with 0 violations."
    )

    ai_result = AiDiagnosisResult(
        case_id=3,
        status=AiDiagnosisStatus.SUCCESS,
        root_cause="PC4 has no IPv4 address configured on FastEthernet0 (unassigned/0.0.0.0), preventing local subnet ARP and ping.",
        fault_type="Missing IP Configuration",
        affected_device="PC4",
        affected_interface="FastEthernet0",
        evidence=["FastEthernet0 IP address is unassigned in show ip interface brief."],
        explanation="Without an IP address and subnet mask, host PC4 cannot create IP datagrams.",
        recommended_correction="Assign a static IPv4 address (e.g. 192.168.1.14/24) to PC4 in Cisco Packet Tracer.",
        confidence=95,
        model_name="mock-model"
    )

    res = comparator.compare(case_id=3, py_result=py_result, ai_result=ai_result)
    assert res.status == ComparisonStatus.AI_ONLY
    assert "Novel Fault Detected" in res.verdict_title
    assert "PC4" in res.explanation
    assert "outside the hardcoded rule set" in res.explanation
    assert res.aligned_fault_type == "Missing IP Configuration"
    assert res.aligned_device == "PC4"

# 4. Test PYTHON_ONLY: Python flags fault, but AI reports insufficient evidence
def test_comparison_python_only():
    py_result = RuleEngineResult(
        case_id=4,
        total_rules_evaluated=7,
        faults_detected=[
            RuleFinding(
                rule_id="GATEWAY_MISMATCH",
                fault_type="Gateway Mismatch",
                severity=RuleSeverity.HIGH,
                device="PC0",
                interface="FastEthernet0",
                description="Default gateway 192.168.2.1 is outside local subnet 192.168.1.0/24.",
                evidence="Configured IP: 192.168.1.50/24, Gateway: 192.168.2.1",
                suggested_correction="Change default gateway on PC0 to 192.168.1.1.",
                confidence=0.96,
                source="PKT_EXTRACTED",
                status=RuleStatus.DETECTED
            )
        ],
        insufficient_evidence=[],
        no_fault_rules=[],
        summary="Gateway mismatch detected."
    )

    ai_result = AiDiagnosisResult(
        case_id=4,
        status=AiDiagnosisStatus.INSUFFICIENT_EVIDENCE,
        explanation="Insufficient evidence to evaluate routing topology.",
        confidence=0,
        model_name="mock-model"
    )

    res = comparator.compare(case_id=4, py_result=py_result, ai_result=ai_result)
    assert res.status == ComparisonStatus.PYTHON_ONLY
    assert "Gateway Mismatch" in res.verdict_title
    assert res.aligned_device == "PC0"
    assert res.confidence_score == 96

# 5. Test Insufficient Evidence on both sides
def test_comparison_insufficient_evidence():
    py_result = RuleEngineResult(
        case_id=5,
        total_rules_evaluated=7,
        faults_detected=[],
        insufficient_evidence=[],
        no_fault_rules=["DUPLICATE_IP", "WRONG_SUBNET_MASK"],
        summary="0 faults detected."
    )

    ai_result = AiDiagnosisResult(
        case_id=5,
        status=AiDiagnosisStatus.INSUFFICIENT_EVIDENCE,
        explanation="No Packet Tracer facts or Cisco show commands uploaded.",
        confidence=0,
        model_name="mock-model"
    )

    res = comparator.compare(case_id=5, py_result=py_result, ai_result=ai_result)
    assert res.status == ComparisonStatus.INSUFFICIENT_EVIDENCE
    assert "Insufficient Evidence" in res.verdict_title
    assert res.confidence_score == 0

# 6. Test Comparison API Endpoint
def test_comparison_api_endpoint(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")

    # 1. Create a case
    create_res = client.post("/api/cases", json={
        "title": "Comparison API Test Case",
        "category": "Interface",
        "severity": "HIGH",
        "symptom": "PC0 interface is down"
    })
    case_id = create_res.json()["id"]

    # 2. Add Cisco Evidence (PC0 FastEthernet0 administratively down)
    client.post(f"/api/cases/{case_id}/evidence", json={
        "device": "PC0",
        "command": "show ip interface brief",
        "raw_output": "FastEthernet0 192.168.10.10 YES manual administratively down down"
    })

    # 3. Request Diagnosis Comparison
    comp_res = client.post(f"/api/cases/{case_id}/diagnose/compare")
    assert comp_res.status_code == 200
    data = comp_res.json()
    assert data["case_id"] == case_id
    assert data["status"] in ["AGREEMENT", "PYTHON_ONLY", "AI_ONLY", "DISAGREEMENT", "INSUFFICIENT_EVIDENCE"]
    assert data["human_review_required"] is True
    assert "python_summary" in data
    assert "ai_summary" in data
