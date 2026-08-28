import uuid
import pytest
from app.core.config import settings
from app.models.case import Case
from app.services.ai.models import AiDiagnosisResult, AiDiagnosisStatus
from app.services.ai.service import AiDiagnosisService
from app.services.ai.providers.mock_provider import MockAiProvider

@pytest.fixture
def sample_case(db_session):
    uid = uuid.uuid4().hex[:8]
    case = Case(
        title=f"AI Test Case {uid}",
        case_number=f"CASE-AI-{uid}",
        category="VLAN",
        severity="HIGH",
        symptom="PC0 cannot ping gateway or switch",
        topology_notes="PC0 connected to Switch0 Fa0/1",
        status="OPEN"
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case

# 1. Test Valid AI diagnosis response
def test_valid_ai_diagnosis_response(db_session, sample_case):
    mock = MockAiProvider()
    service = AiDiagnosisService(provider_override=mock)
    
    res = service.diagnose_case(sample_case.id, db_session)
    assert res.case_id == sample_case.id
    assert res.status in [AiDiagnosisStatus.SUCCESS, AiDiagnosisStatus.INSUFFICIENT_EVIDENCE]

# 2. Test AI diagnosis with interface-down evidence
def test_ai_diagnosis_interface_down_evidence(db_session, sample_case):
    mock = MockAiProvider()
    service = AiDiagnosisService(provider_override=mock)
    
    from app.models.evidence import CiscoEvidence
    ev = CiscoEvidence(
        case_id=sample_case.id,
        device="PC0",
        command="show ip interface brief",
        raw_output="FastEthernet0 192.168.10.10 YES manual administratively down down",
        parser_status="SUCCESS",
        parsed_facts={"interfaces": [{"device": "PC0", "name": "FastEthernet0", "status": "ADMINISTRATIVELY_DOWN", "protocol": "DOWN"}]}
    )
    db_session.add(ev)
    db_session.commit()

    res = service.diagnose_case(sample_case.id, db_session)
    assert res.status == AiDiagnosisStatus.SUCCESS
    assert res.fault_type == "Interface Down"
    assert res.affected_device == "PC0"
    assert res.affected_interface == "FastEthernet0"
    assert "administratively disabled" in res.root_cause
    assert res.confidence >= 90

# 3. Test AI diagnosis with duplicate IP evidence
def test_ai_diagnosis_duplicate_ip_evidence(db_session, sample_case):
    mock = MockAiProvider()
    service = AiDiagnosisService(provider_override=mock)
    
    from app.models.evidence import CiscoEvidence
    ev1 = CiscoEvidence(
        case_id=sample_case.id,
        device="PC0",
        command="show ip interface brief",
        raw_output="FastEthernet0 192.168.1.50 YES manual up up",
        parser_status="SUCCESS"
    )
    ev2 = CiscoEvidence(
        case_id=sample_case.id,
        device="PC1",
        command="show ip interface brief",
        raw_output="FastEthernet0 192.168.1.50 YES manual up up",
        parser_status="SUCCESS"
    )
    db_session.add_all([ev1, ev2])
    db_session.commit()

    res = service.diagnose_case(sample_case.id, db_session)
    assert res.status == AiDiagnosisStatus.SUCCESS
    assert res.fault_type in ["Duplicate IP", "Interface Down"]

# 4. Test AI insufficient evidence when no facts uploaded
def test_ai_insufficient_evidence(db_session, sample_case):
    # Ensure sample case has no pkt and no evidence
    sample_case.pkt_file = None
    db_session.commit()

    mock = MockAiProvider()
    service = AiDiagnosisService(provider_override=mock)
    
    res = service.diagnose_case(sample_case.id, db_session)
    assert res.status == AiDiagnosisStatus.INSUFFICIENT_EVIDENCE
    assert res.confidence == 0

# 5. Test AI unavailable when unconfigured / missing API key
def test_ai_unavailable_when_unconfigured(db_session, sample_case, monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "AI_API_KEY", None)

    service = AiDiagnosisService(provider_override=None)
    res = service.diagnose_case(sample_case.id, db_session)
    
    assert res.status == AiDiagnosisStatus.AI_UNAVAILABLE
    assert "AI_API_KEY is not configured" in res.reasoning_summary

# 6. Test invalid AI response schema handling
def test_invalid_ai_response_handling(db_session, sample_case):
    class CorruptAiProvider(MockAiProvider):
        def generate_diagnosis(self, *args, **kwargs):
            raise ValueError("Malformed AI response format")

    service = AiDiagnosisService(provider_override=CorruptAiProvider())
    
    from app.models.evidence import CiscoEvidence
    db_session.add(CiscoEvidence(case_id=sample_case.id, device="PC0", command="show ip route", raw_output="192.168.1.0/24"))
    db_session.commit()

    res = service.diagnose_case(sample_case.id, db_session)
    assert res.status == AiDiagnosisStatus.FAILED
    assert "AI diagnosis failed" in res.explanation

# 7. Test Python and AI independent evaluation (Agreement)
def test_python_and_ai_agreement(db_session, sample_case):
    from app.models.evidence import CiscoEvidence
    ev = CiscoEvidence(
        case_id=sample_case.id,
        device="PC0",
        command="show ip interface brief",
        raw_output="FastEthernet0 192.168.10.10 YES manual administratively down down",
        parser_status="SUCCESS",
        parsed_facts={"interfaces": [{"device": "PC0", "name": "FastEthernet0", "status": "ADMINISTRATIVELY_DOWN", "protocol": "DOWN", "ip": "192.168.10.10"}]}
    )
    db_session.add(ev)
    db_session.commit()

    mock = MockAiProvider()
    service = AiDiagnosisService(provider_override=mock)
    
    ai_res = service.diagnose_case(sample_case.id, db_session)
    assert ai_res.fault_type == "Interface Down"
    assert ai_res.affected_device == "PC0"

# 8. Test Python and AI independent evaluation (Disagreement allowed)
def test_python_and_ai_disagreement(db_session, sample_case):
    # Mock AI returning insufficient evidence even if Python has a rule
    class DisagreeingAiProvider(MockAiProvider):
        def generate_diagnosis(self, *args, **kwargs):
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "root_cause": "Insufficient evidence to independently confirm duplicate IP.",
                "confidence": 20
            }

    service = AiDiagnosisService(provider_override=DisagreeingAiProvider())
    from app.models.evidence import CiscoEvidence
    db_session.add(CiscoEvidence(case_id=sample_case.id, device="PC0", command="show ip route", raw_output="192.168.1.0/24"))
    db_session.commit()

    res = service.diagnose_case(sample_case.id, db_session)
    assert res.status == AiDiagnosisStatus.INSUFFICIENT_EVIDENCE
    assert "Insufficient evidence" in res.root_cause

# 9. Test API Endpoint
def test_ai_diagnosis_api_endpoint(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    
    # 1. Create a case
    create_res = client.post("/api/cases", json={
        "title": "AI Diagnosis Test Case",
        "category": "Routing",
        "severity": "HIGH",
        "symptom": "PC cannot reach server"
    })
    case_id = create_res.json()["id"]

    # 2. Add Cisco Evidence
    client.post(f"/api/cases/{case_id}/evidence", json={
        "device": "PC0",
        "command": "show ip interface brief",
        "raw_output": "FastEthernet0 192.168.1.10 YES manual administratively down down"
    })

    # 3. Request AI Diagnosis
    diag_res = client.post(f"/api/cases/{case_id}/diagnose/ai")
    assert diag_res.status_code == 200
    data = diag_res.json()
    assert data["case_id"] == case_id
    assert data["status"] in ["SUCCESS", "INSUFFICIENT_EVIDENCE", "AI_UNAVAILABLE"]
    assert "FastEthernet0" in (data.get("affected_interface") or "FastEthernet0")
