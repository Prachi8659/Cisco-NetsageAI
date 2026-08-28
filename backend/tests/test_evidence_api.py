from fastapi import status

def create_test_case(client):
    res = client.post("/api/cases", json={
        "title": "Evidence Test Case",
        "category": "Routing",
        "severity": "HIGH",
        "symptom": "R1 cannot reach R2",
        "topology_notes": "R1 connected to R2"
    })
    assert res.status_code == status.HTTP_201_CREATED
    return res.json()["id"]

def test_create_and_get_evidence(client):
    case_id = create_test_case(client)

    raw_cli = """
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     192.168.1.1     YES manual up                    up
GigabitEthernet0/1     10.0.0.1        YES manual up                    up
    """

    # 1. Post Evidence
    post_res = client.post(f"/api/cases/{case_id}/evidence", json={
        "device": "R1",
        "command": "show ip interface brief",
        "raw_output": raw_cli
    })
    assert post_res.status_code == status.HTTP_201_CREATED
    data = post_res.json()

    assert data["case_id"] == case_id
    assert data["device"] == "R1"
    assert data["command"] == "show ip interface brief"
    assert data["parser_status"] == "SUCCESS"
    assert data["parsed_facts"] is not None
    assert len(data["parsed_facts"]["interfaces"]) == 2

    evidence_id = data["id"]

    # 2. Get Evidence List for Case
    list_res = client.get(f"/api/cases/{case_id}/evidence")
    assert list_res.status_code == status.HTTP_200_OK
    evidence_list = list_res.json()
    assert len(evidence_list) == 1
    assert evidence_list[0]["id"] == evidence_id

    # 3. Get Single Evidence
    single_res = client.get(f"/api/cases/{case_id}/evidence/{evidence_id}")
    assert single_res.status_code == status.HTTP_200_OK
    assert single_res.json()["raw_output"] == raw_cli

    # 4. Re-parse Single Evidence
    parse_res = client.post(f"/api/cases/{case_id}/evidence/{evidence_id}/parse")
    assert parse_res.status_code == status.HTTP_200_OK
    assert parse_res.json()["status"] == "SUCCESS"
    assert len(parse_res.json()["facts"]["interfaces"]) == 2

    # 5. Delete Evidence
    del_res = client.delete(f"/api/cases/{case_id}/evidence/{evidence_id}")
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # Verify 404 after deletion
    get_del_res = client.get(f"/api/cases/{case_id}/evidence/{evidence_id}")
    assert get_del_res.status_code == status.HTTP_404_NOT_FOUND

def test_evidence_on_nonexistent_case(client):
    res = client.post("/api/cases/99999/evidence", json={
        "device": "R1",
        "command": "show ip route",
        "raw_output": "some output"
    })
    assert res.status_code == status.HTTP_404_NOT_FOUND

def test_multiple_evidence_blocks(client):
    case_id = create_test_case(client)

    # Add evidence 1: R1 show ip int br
    client.post(f"/api/cases/{case_id}/evidence", json={
        "device": "R1",
        "command": "show ip interface brief",
        "raw_output": "GigabitEthernet0/0 192.168.1.1 YES manual up up"
    })

    # Add evidence 2: Switch0 show vlan brief
    client.post(f"/api/cases/{case_id}/evidence", json={
        "device": "Switch0",
        "command": "show vlan brief",
        "raw_output": "10 STUDENTS active Fa0/1, Fa0/2"
    })

    list_res = client.get(f"/api/cases/{case_id}/evidence")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 2
