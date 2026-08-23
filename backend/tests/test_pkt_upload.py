import io
from fastapi import status
from backend.app.core.config import settings

def create_dummy_case(client):
    res = client.post("/api/cases", json={
        "title": "Routing Issue Lab",
        "category": "Routing",
        "severity": "HIGH",
        "symptom": "R1 cannot reach subnet 10.0.2.0/24",
        "topology_notes": "R1 connected to R2 over serial link."
    })
    assert res.status_code == status.HTTP_201_CREATED
    return res.json()["id"]

def test_valid_pkt_upload(client):
    case_id = create_dummy_case(client)
    
    fake_pkt_content = b"PKT_HEADER_V8.0\x00\x01\x02\x03CiscoPacketTracerTopologyData"
    file_payload = ("lab_topology_fault.pkt", io.BytesIO(fake_pkt_content), "application/octet-stream")
    
    upload_res = client.post(
        f"/api/cases/{case_id}/pkt",
        files={"file": file_payload}
    )
    assert upload_res.status_code == status.HTTP_201_CREATED
    data = upload_res.json()
    
    assert data["case_id"] == case_id
    assert data["pkt_filename"] == "lab_topology_fault.pkt"
    assert data["pkt_file_size"] == len(fake_pkt_content)
    assert data["pkt_upload_status"] == "STORED"
    assert "pkt_uploaded_at" in data
    assert data["sha256_hash"] is not None

    # Check case detail reflects the attached pkt_file
    case_res = client.get(f"/api/cases/{case_id}")
    assert case_res.status_code == status.HTTP_200_OK
    case_data = case_res.json()
    assert case_data["pkt_file"] is not None
    assert case_data["pkt_file"]["pkt_filename"] == "lab_topology_fault.pkt"

def test_invalid_extension_rejection(client):
    case_id = create_dummy_case(client)
    
    invalid_extensions = ["script.exe", "notes.txt", "network.pkt.exe", "image.png"]
    for filename in invalid_extensions:
        file_payload = (filename, io.BytesIO(b"fake content"), "text/plain")
        res = client.post(
            f"/api/cases/{case_id}/pkt",
            files={"file": file_payload}
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid file type" in res.json()["detail"] or "Suspicious filename" in res.json()["detail"]

def test_empty_pkt_file_rejection(client):
    case_id = create_dummy_case(client)
    
    file_payload = ("empty.pkt", io.BytesIO(b""), "application/octet-stream")
    res = client.post(
        f"/api/cases/{case_id}/pkt",
        files={"file": file_payload}
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "empty" in res.json()["detail"].lower()

def test_upload_to_nonexistent_case(client):
    file_payload = ("network.pkt", io.BytesIO(b"valid pkt data"), "application/octet-stream")
    res = client.post(
        "/api/cases/88888/pkt",
        files={"file": file_payload}
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in res.json()["detail"].lower()

def test_pkt_download_and_integrity(client):
    case_id = create_dummy_case(client)
    
    pkt_bytes = b"CISCO_PACKET_TRACER_BINARY_DATA_TEST_12345"
    file_payload = ("final_topology.pkt", io.BytesIO(pkt_bytes), "application/octet-stream")
    
    upload_res = client.post(
        f"/api/cases/{case_id}/pkt",
        files={"file": file_payload}
    )
    assert upload_res.status_code == status.HTTP_201_CREATED

    # Download
    download_res = client.get(f"/api/cases/{case_id}/pkt/download")
    assert download_res.status_code == status.HTTP_200_OK
    assert download_res.content == pkt_bytes
    assert 'filename="final_topology.pkt"' in download_res.headers.get("content-disposition", "")
