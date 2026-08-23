from fastapi import status

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["project"] == "NetSage AI"
    assert "safety_notice" in data
    assert "manual" in data["safety_notice"].lower()

def test_create_and_get_case(client):
    case_payload = {
        "title": "VLAN 10 Workstation Isolated",
        "category": "VLAN",
        "severity": "HIGH",
        "symptom": "PC-1 cannot ping default gateway 192.168.10.1",
        "topology_notes": "Switch S1 connected to Router R1 via Gi0/1 trunk, PC-1 on Fa0/2."
    }
    create_res = client.post("/api/cases", json=case_payload)
    assert create_res.status_code == status.HTTP_201_CREATED
    data = create_res.json()
    assert data["title"] == case_payload["title"]
    assert data["case_number"].startswith("CASE-")
    assert data["status"] == "OPEN"
    assert data["pkt_file"] is None
    case_id = data["id"]

    # Get case details
    get_res = client.get(f"/api/cases/{case_id}")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["id"] == case_id

def test_list_cases(client):
    res = client.get("/api/cases")
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 1

def test_get_nonexistent_case(client):
    res = client.get("/api/cases/99999")
    assert res.status_code == status.HTTP_404_NOT_FOUND
