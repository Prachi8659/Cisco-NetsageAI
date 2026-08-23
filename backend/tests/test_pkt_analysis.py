import io
import zlib
from pathlib import Path
from fastapi import status
from backend.app.services.pkt.models import (
    FactSource,
    ConnectionStatus,
    AnalysisStatus,
    NormalizedNetworkFacts,
    PktAnalysisResult
)

def create_case_with_pkt(client, filename: str, content: bytes):
    # 1. Create Case
    case_res = client.post("/api/cases", json={
        "title": "Analysis Test Case",
        "category": "VLAN",
        "severity": "HIGH",
        "symptom": "VLAN 10 isolated",
        "topology_notes": "S1 Fa0/1 -> PC1, S1 Gi0/1 -> R1 Gi0/1"
    })
    assert case_res.status_code == status.HTTP_201_CREATED
    case_id = case_res.json()["id"]

    # 2. Upload PKT file
    file_payload = (filename, io.BytesIO(content), "application/octet-stream")
    upload_res = client.post(f"/api/cases/{case_id}/pkt", files={"file": file_payload})
    assert upload_res.status_code == status.HTTP_201_CREATED
    return case_id

def test_analyze_modern_encrypted_twofish_eax_pkt(client):
    # Load actual 45KB Packet Tracer 9.x encrypted .pkt file
    pkt_file = Path("data/pkt_uploads/case_2_cc2f75d7447c.pkt")
    if not pkt_file.exists():
        return

    content = pkt_file.read_bytes()
    case_id = create_case_with_pkt(client, "modern_lab_pt9.pkt", content)

    res = client.post(f"/api/cases/{case_id}/pkt/analyze")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    # Verify modern Twofish-EAX decode success
    assert data["status"] == "SUCCESS"
    assert data["source"] == "PKT_EXTRACTED"
    assert data["extraction_details"]["format_type"] == "MODERN_TWOFISH_EAX"
    assert "9.0.1" in data["extraction_details"].get("version", "")

    # Verify extracted devices
    facts = data["facts"]
    dev_names = [d["name"] for d in facts["devices"]]
    assert "PC0" in dev_names
    assert "PC1" in dev_names
    assert "PC2" in dev_names
    assert "Switch0" in dev_names

    for dev in facts["devices"]:
        assert dev["source"] == "PKT_EXTRACTED"

    # Verify extracted connections
    connections = facts["connections"]
    assert len(connections) == 3
    for conn in connections:
        assert conn["source"] == "PKT_EXTRACTED"
        assert conn["status"] == "CONNECTED"
        assert conn["link_type"] == "Copper"

    # Verify extracted IP addresses
    pc0_int = next(i for i in facts["interfaces"] if i["device"] == "PC0" and i["ip"])
    assert pc0_int["ip"] == "192.168.1.1"
    assert pc0_int["mask"] == "255.255.255.0"
    assert pc0_int["source"] == "PKT_EXTRACTED"

def test_analyze_xml_pkt_topology(client):
    xml_topology = b"""<?xml version="1.0" encoding="UTF-8"?>
    <PACKETTRACER5_SAVED_NETWORK>
        <DEVICES>
            <DEVICE>
                <NAME>R1</NAME>
                <TYPE>Router</TYPE>
                <MODEL>2911</MODEL>
                <PORTS>
                    <PORT>
                        <NAME>GigabitEthernet0/1</NAME>
                        <IP>192.168.10.1</IP>
                        <SUBNET_MASK>255.255.255.0</SUBNET_MASK>
                        <STATUS>up</STATUS>
                        <PROTOCOL_STATUS>up</PROTOCOL_STATUS>
                    </PORT>
                </PORTS>
            </DEVICE>
            <DEVICE>
                <NAME>S1</NAME>
                <TYPE>Switch</TYPE>
                <MODEL>2960</MODEL>
                <PORTS>
                    <PORT>
                        <NAME>FastEthernet0/1</NAME>
                        <STATUS>up</STATUS>
                        <VLAN>10</VLAN>
                    </PORT>
                    <PORT>
                        <NAME>GigabitEthernet0/1</NAME>
                        <STATUS>up</STATUS>
                    </PORT>
                </PORTS>
            </DEVICE>
            <DEVICE>
                <NAME>PC1</NAME>
                <TYPE>PC</TYPE>
                <DEFAULT_GATEWAY>192.168.10.1</DEFAULT_GATEWAY>
                <PORTS>
                    <PORT>
                        <NAME>FastEthernet0</NAME>
                        <IP>192.168.10.50</IP>
                        <SUBNET_MASK>255.255.255.0</SUBNET_MASK>
                        <STATUS>up</STATUS>
                    </PORT>
                </PORTS>
            </DEVICE>
        </DEVICES>
        <LINKS>
            <LINK>
                <DEVICE_A>PC1</DEVICE_A>
                <PORT_A>FastEthernet0</PORT_A>
                <DEVICE_B>S1</DEVICE_B>
                <PORT_B>FastEthernet0/1</PORT_B>
                <TYPE>Copper</TYPE>
            </LINK>
            <LINK>
                <DEVICE_A>S1</DEVICE_A>
                <PORT_A>GigabitEthernet0/1</PORT_A>
                <DEVICE_B>R1</DEVICE_B>
                <PORT_B>GigabitEthernet0/1</PORT_B>
                <TYPE>Copper</TYPE>
            </LINK>
        </LINKS>
    </PACKETTRACER5_SAVED_NETWORK>
    """

    case_id = create_case_with_pkt(client, "test_vlan10.pkt", xml_topology)

    # Trigger analysis API
    res = client.post(f"/api/cases/{case_id}/pkt/analyze")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    # Verify status and source
    assert data["status"] == "SUCCESS"
    assert data["source"] == "PKT_EXTRACTED"
    facts = data["facts"]

    # Verify extracted devices
    dev_names = [d["name"] for d in facts["devices"]]
    assert "R1" in dev_names
    assert "S1" in dev_names
    assert "PC1" in dev_names
    for dev in facts["devices"]:
        assert dev["source"] == "PKT_EXTRACTED"

    # Verify extracted interfaces
    interfaces = facts["interfaces"]
    r1_int = next(i for i in interfaces if i["device"] == "R1" and i["name"] == "GigabitEthernet0/1")
    assert r1_int["ip"] == "192.168.10.1"
    assert r1_int["mask"] == "255.255.255.0"
    assert r1_int["source"] == "PKT_EXTRACTED"

    # Verify topology connections
    connections = facts["connections"]
    assert len(connections) == 2
    conn1 = connections[0]
    assert conn1["device_a"] == "PC1"
    assert conn1["interface_a"] == "FastEthernet0"
    assert conn1["device_b"] == "S1"
    assert conn1["interface_b"] == "FastEthernet0/1"
    assert conn1["status"] == "CONNECTED"
    assert conn1["source"] == "PKT_EXTRACTED"

    # Verify Gateway extraction
    assert len(facts["gateways"]) == 1
    assert facts["gateways"][0]["device"] == "PC1"
    assert facts["gateways"][0]["gateway_ip"] == "192.168.10.1"

def test_analyze_decompressed_zlib_pkt(client):
    xml_data = b"<PACKETTRACER5_SAVED_NETWORK><DEVICES><DEVICE><NAME>R2</NAME><TYPE>Router</TYPE></DEVICE></DEVICES></PACKETTRACER5_SAVED_NETWORK>"
    compressed = zlib.compress(xml_data)

    case_id = create_case_with_pkt(client, "compressed_lab.pkt", compressed)

    res = client.post(f"/api/cases/{case_id}/pkt/analyze")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["facts"]["devices"][0]["name"] == "R2"

def test_analyze_legacy_xor_pkt(client):
    xml_data = b"<PACKETTRACER5_SAVED_NETWORK><DEVICES><DEVICE><NAME>Switch_Legacy</NAME><TYPE>Switch</TYPE></DEVICE></DEVICES></PACKETTRACER5_SAVED_NETWORK>"
    zlib_payload = len(xml_data).to_bytes(4, "big") + zlib.compress(xml_data)
    length = len(zlib_payload)
    xor_bytes = bytearray(length)
    for i in range(length):
        xor_bytes[i] = zlib_payload[i] ^ ((length - i) & 0xFF)

    case_id = create_case_with_pkt(client, "legacy_lab.pkt", bytes(xor_bytes))

    res = client.post(f"/api/cases/{case_id}/pkt/analyze")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["facts"]["devices"][0]["name"] == "Switch_Legacy"
    assert data["extraction_details"]["format_type"] == "LEGACY_XOR"

def test_analyze_unsupported_corrupt_pkt_truthful_unavailability(client):
    # Corrupt / unrecognized binary payload
    raw_corrupt_pkt = b"RANDOM_CORRUPT_BYTES\x00\x01\xfe\xdc\xba\x98" + (b"\x13\x37\x42" * 20)

    case_id = create_case_with_pkt(client, "corrupt_lab.pkt", raw_corrupt_pkt)

    res = client.post(f"/api/cases/{case_id}/pkt/analyze")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    # Must truthfully report UNAVAILABLE and not fabricate fake devices
    assert data["status"] == "UNAVAILABLE"
    assert data["source"] == "UNKNOWN"
    assert len(data["facts"]["devices"]) == 0
    assert len(data["facts"]["connections"]) == 0
    assert len(data["warnings"]) > 0

def test_no_fabricated_facts_policy(client):
    # An unrecognized binary must NEVER produce hallucinated IP addresses or devices
    raw_dummy = b"\x01\x02\x03\x04\x05\x06\x07\x08" * 8
    case_id = create_case_with_pkt(client, "dummy.pkt", raw_dummy)

    res = client.post(f"/api/cases/{case_id}/pkt/analyze")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "UNAVAILABLE"
    assert data["facts"]["devices"] == []
    assert data["facts"]["interfaces"] == []
    assert data["facts"]["connections"] == []
    assert data["facts"]["vlans"] == []
    assert data["facts"]["routes"] == []

def test_analyze_missing_pkt_file(client):
    case_res = client.post("/api/cases", json={
        "title": "Case with No PKT",
        "category": "Routing",
        "severity": "LOW",
        "symptom": "No file uploaded yet"
    })
    case_id = case_res.json()["id"]

    res = client.post(f"/api/cases/{case_id}/pkt/analyze")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert "upload a .pkt file" in res.json()["detail"].lower()

def test_analyze_nonexistent_case(client):
    res = client.post("/api/cases/99999/pkt/analyze")
    assert res.status_code == status.HTTP_404_NOT_FOUND
