import io
from pathlib import Path
from fastapi import status
from app.core.config import settings

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

def test_pkt_delete_valid_file(client):
    case_id = create_dummy_case(client)

    pkt_bytes = b"CISCO_PACKET_TRACER_FILE_TO_BE_DELETED"
    file_payload = ("delete_me.pkt", io.BytesIO(pkt_bytes), "application/octet-stream")

    upload_res = client.post(
        f"/api/cases/{case_id}/pkt",
        files={"file": file_payload}
    )
    assert upload_res.status_code == status.HTTP_201_CREATED
    data = upload_res.json()
    storage_path = Path(data["pkt_storage_path"])
    assert storage_path.exists()

    # Delete PKT file
    delete_res = client.delete(f"/api/cases/{case_id}/pkt")
    assert delete_res.status_code == status.HTTP_204_NO_CONTENT

    # Assert file on disk is removed
    assert not storage_path.exists()

    # Assert metadata & download return 404
    meta_res = client.get(f"/api/cases/{case_id}/pkt")
    assert meta_res.status_code == status.HTTP_404_NOT_FOUND

    dl_res = client.get(f"/api/cases/{case_id}/pkt/download")
    assert dl_res.status_code == status.HTTP_404_NOT_FOUND

def test_pkt_delete_outside_storage_path_blocked(client, db_session):
    from app.models.pkt import PktFile

    case_id = create_dummy_case(client)

    # Create a sensitive file outside PKT_STORAGE_DIR
    outside_file = settings.BACKEND_DIR / "sensitive_outside_file.txt"
    outside_file.write_text("SENSITIVE DATA")

    try:
        # Create a PktFile record pointing directly to the outside file
        malicious_pkt = PktFile(
            case_id=case_id,
            pkt_filename="malicious.pkt",
            pkt_storage_path=str(outside_file.resolve()),
            pkt_file_size=len("SENSITIVE DATA"),
            pkt_upload_status="STORED",
            sha256_hash="dummyhash"
        )
        db_session.add(malicious_pkt)
        db_session.commit()

        # Attempt to delete via API
        delete_res = client.delete(f"/api/cases/{case_id}/pkt")
        assert delete_res.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied" in delete_res.json()["detail"]

        # Ensure the outside file was NOT deleted
        assert outside_file.exists()
        assert outside_file.read_text() == "SENSITIVE DATA"
    finally:
        if outside_file.exists():
            outside_file.unlink()

