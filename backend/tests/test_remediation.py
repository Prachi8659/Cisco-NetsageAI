import uuid
import pytest
from backend.app.models.case import Case
from backend.app.models.evidence import CiscoEvidence
from backend.app.models.review import HumanReview
from backend.app.schemas.remediation import HumanReviewCreate, RemediationConfirmInput, ReviewDecision, VerificationStatus
from backend.app.services.remediation.service import remediation_service

@pytest.fixture
def sample_case(db_session):
    uid = uuid.uuid4().hex[:8]
    case = Case(
        title=f"Remediation Test Case {uid}",
        case_number=f"CASE-REM-{uid}",
        category="Interface",
        severity="HIGH",
        symptom="PC0 interface down",
        status="OPEN"
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case

# 1. Test ACCEPT Review
def test_submit_review_accept(db_session, sample_case):
    review_in = HumanReviewCreate(
        decision=ReviewDecision.ACCEPT,
        reviewer_name="Senior Engineer",
        reviewer_notes="Confirmed interface shutdown matches symptoms.",
        previous_fault_type="Interface Down",
        previous_fault_device="PC0"
    )
    review = remediation_service.submit_review(sample_case.id, review_in, db_session)
    assert review.case_id == sample_case.id
    assert review.decision == "ACCEPT"
    assert review.reviewer_name == "Senior Engineer"
    assert review.verification_status == "PENDING"
    assert sample_case.status == "VERIFIED"

# 2. Test REJECT Review
def test_submit_review_reject(db_session, sample_case):
    review_in = HumanReviewCreate(
        decision=ReviewDecision.REJECT,
        reviewer_name="Operator B",
        reviewer_notes="Topology indicates port was intended to be disabled."
    )
    review = remediation_service.submit_review(sample_case.id, review_in, db_session)
    assert review.decision == "REJECT"
    assert sample_case.status == "OPEN"

# 3. Test NEEDS_REVIEW
def test_submit_review_needs_review(db_session, sample_case):
    review_in = HumanReviewCreate(
        decision=ReviewDecision.NEEDS_REVIEW,
        reviewer_name="Operator C",
        reviewer_notes="Awaiting additional show ip route output."
    )
    review = remediation_service.submit_review(sample_case.id, review_in, db_session)
    assert review.decision == "NEEDS_REVIEW"
    assert sample_case.status == "REVIEW_REQUIRED"

# 4. Test Confirm Remediation (Manual PT Fix Confirmed)
def test_confirm_remediation(db_session, sample_case):
    review_in = HumanReviewCreate(
        decision=ReviewDecision.ACCEPT,
        reviewer_name="Operator D"
    )
    review = remediation_service.submit_review(sample_case.id, review_in, db_session)
    assert review.remediation_confirmed is False

    confirm_in = RemediationConfirmInput(
        remediation_notes="Executed 'no shutdown' on PC0 FastEthernet0 in Packet Tracer."
    )
    updated_review = remediation_service.confirm_remediation(sample_case.id, review.id, confirm_in, db_session)
    assert updated_review.remediation_confirmed is True
    assert updated_review.remediation_applied_at is not None
    assert "no shutdown" in updated_review.remediation_notes

# 5. Test Verify Remediation: Fault Still Present
def test_verify_remediation_still_present(db_session, sample_case):
    # Add evidence showing FastEthernet0 is still administratively down
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

    review_in = HumanReviewCreate(
        decision=ReviewDecision.ACCEPT,
        reviewer_name="Operator E",
        previous_fault_type="Interface Down",
        previous_fault_device="PC0"
    )
    review = remediation_service.submit_review(sample_case.id, review_in, db_session)

    res = remediation_service.verify_remediation(sample_case.id, review.id, db_session)
    assert res["verification_status"] == VerificationStatus.STILL_PRESENT
    assert res["after_findings_count"] >= 1
    assert "Fault Still Present" in res["verdict_message"]
    assert sample_case.status == "INVESTIGATING"

# 6. Test Verify Remediation: Resolved
def test_verify_remediation_resolved(db_session, sample_case):
    # Add evidence showing FastEthernet0 is up/up
    ev = CiscoEvidence(
        case_id=sample_case.id,
        device="PC0",
        command="show ip interface brief",
        raw_output="FastEthernet0 192.168.10.10 YES manual up up",
        parser_status="SUCCESS",
        parsed_facts={"interfaces": [{"device": "PC0", "name": "FastEthernet0", "status": "UP", "protocol": "UP", "ip": "192.168.10.10"}]}
    )
    db_session.add(ev)
    db_session.commit()

    review_in = HumanReviewCreate(
        decision=ReviewDecision.ACCEPT,
        reviewer_name="Operator F",
        previous_fault_type="Interface Down",
        previous_fault_device="PC0"
    )
    review = remediation_service.submit_review(sample_case.id, review_in, db_session)

    res = remediation_service.verify_remediation(sample_case.id, review.id, db_session)
    assert res["verification_status"] == VerificationStatus.RESOLVED
    assert res["after_findings_count"] == 0
    assert "Successfully Verified" in res["verdict_message"]
    assert sample_case.status == "VERIFIED"

# 7. Test Verify Remediation: Insufficient Evidence
def test_verify_remediation_insufficient_evidence(db_session, sample_case):
    sample_case.pkt_file = None
    db_session.commit()

    review_in = HumanReviewCreate(
        decision=ReviewDecision.NEEDS_REVIEW,
        reviewer_name="Operator G"
    )
    review = remediation_service.submit_review(sample_case.id, review_in, db_session)

    res = remediation_service.verify_remediation(sample_case.id, review.id, db_session)
    assert res["verification_status"] == VerificationStatus.INSUFFICIENT_EVIDENCE
    assert "Inconclusive" in res["verdict_message"]

# 8. Test Audit Trail Retrieval
def test_audit_trail_history(db_session, sample_case):
    rev1 = remediation_service.submit_review(
        sample_case.id,
        HumanReviewCreate(decision=ReviewDecision.NEEDS_REVIEW, reviewer_name="Auditor 1"),
        db_session
    )
    rev2 = remediation_service.submit_review(
        sample_case.id,
        HumanReviewCreate(decision=ReviewDecision.ACCEPT, reviewer_name="Auditor 2"),
        db_session
    )

    history = remediation_service.get_case_reviews(sample_case.id, db_session)
    assert len(history) >= 2
    assert history[0].id == rev2.id  # Latest first
    assert history[1].id == rev1.id

# 9. Test Remediation API Endpoints
def test_remediation_api_endpoints(client):
    # 1. Create a case
    create_res = client.post("/api/cases", json={
        "title": "API Remediation Test Case",
        "category": "Interface",
        "severity": "HIGH",
        "symptom": "PC0 cannot connect"
    })
    case_id = create_res.json()["id"]

    # 2. Submit Human Review
    review_res = client.post(f"/api/cases/{case_id}/reviews", json={
        "decision": "ACCEPT",
        "reviewer_name": "QA Lead",
        "reviewer_notes": "Approved for Packet Tracer remediation.",
        "previous_fault_type": "Interface Down",
        "previous_fault_device": "PC0"
    })
    assert review_res.status_code == 201
    review_data = review_res.json()
    review_id = review_data["id"]
    assert review_data["decision"] == "ACCEPT"
    assert review_data["reviewer_name"] == "QA Lead"

    # 3. Confirm Manual Remediation
    confirm_res = client.post(f"/api/cases/{case_id}/reviews/{review_id}/confirm-remediation", json={
        "remediation_notes": "Applied 'no shutdown' in Packet Tracer CLI."
    })
    assert confirm_res.status_code == 200
    assert confirm_res.json()["remediation_confirmed"] is True

    # 4. Add Resolved Evidence
    client.post(f"/api/cases/{case_id}/evidence", json={
        "device": "PC0",
        "command": "show ip interface brief",
        "raw_output": "FastEthernet0 192.168.1.10 YES manual up up"
    })

    # 5. Verify After Fix
    verify_res = client.post(f"/api/cases/{case_id}/reviews/{review_id}/verify")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["verification_status"] == "RESOLVED"
    assert v_data["after_findings_count"] == 0

    # 6. Retrieve Audit History
    list_res = client.get(f"/api/cases/{case_id}/reviews")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert list_res.json()[0]["id"] == review_id
