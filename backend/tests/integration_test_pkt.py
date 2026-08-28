import json
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def run_integration_test():
    print("=== 1. Testing Case #2 with Real Modern 45KB Encrypted .PKT File ===")
    res1 = client.post("/api/cases/2/pkt/analyze")
    print(f"Status Code: {res1.status_code}")
    data1 = res1.json()
    print(f"Analysis Status: {data1['status']}")
    print(f"Source: {data1['source']}")
    print(f"Detected Format: {data1['extraction_details'].get('format_type')}")
    print(f"Detected Version: {data1['extraction_details'].get('version')}")
    print(f"Devices Count: {len(data1['facts']['devices'])}")
    for d in data1['facts']['devices']:
        print(f"  - Device: {d['name']} ({d['device_type']}) Model={d['model']} Source={d['source']}")
    print(f"Connections Count: {len(data1['facts']['connections'])}")
    for c in data1['facts']['connections']:
        print(f"  - Link: {c['device_a']}:{c['interface_a']} <---> {c['device_b']}:{c['interface_b']} [{c['link_type']}]")
    print(f"Interfaces with IP:")
    for intf in data1['facts']['interfaces']:
        if intf['ip']:
            print(f"  - IP: {intf['device']}:{intf['name']} -> {intf['ip']} / {intf['mask']} MAC={intf['mac_address']}")
    
    assert data1['status'] == "SUCCESS"
    assert data1['source'] == "PKT_EXTRACTED"
    assert len(data1['facts']['devices']) == 5
    assert len(data1['facts']['connections']) == 3
    assert data1['extraction_details'].get('format_type') == "MODERN_TWOFISH_EAX"
    assert "9.0.1" in data1['extraction_details'].get('version', '')
    print("[PASS] Real Modern Encrypted .PKT test PASSED (Successfully Decoded, 100% Real Facts)\n")

    print("=== 2. Testing Case with Uncompressed/XML .PKT Topology File ===")
    case_res = client.post("/api/cases", json={
        "title": "VLAN 10 Subnet Topology Analysis",
        "category": "VLAN",
        "severity": "HIGH",
        "symptom": "PC1 cannot ping R1 gateway 192.168.10.1",
        "topology_notes": "PC1 -> S1 -> R1"
    })
    case_id = case_res.json()["id"]
    print(f"Created Case #{case_id}")

    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
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
</PACKETTRACER5_SAVED_NETWORK>"""

    import io
    files = {"file": ("vlan10_lab_topology.pkt", io.BytesIO(xml_content), "application/octet-stream")}
    up_res = client.post(f"/api/cases/{case_id}/pkt", files=files)
    print(f"Uploaded PKT Status: {up_res.status_code}")

    ana_res = client.post(f"/api/cases/{case_id}/pkt/analyze")
    print(f"Analyze Status Code: {ana_res.status_code}")
    data2 = ana_res.json()
    print(f"Analysis Status: {data2['status']}")
    print(f"Source: {data2['source']}")
    print(f"Extracted Devices: {[d['name'] for d in data2['facts']['devices']]}")
    print(f"Extracted Interfaces: {len(data2['facts']['interfaces'])}")
    print(f"Extracted Connections: {len(data2['facts']['connections'])}")
    print(f"Extracted Gateways: {data2['facts']['gateways']}")
    assert data2['status'] == "SUCCESS"
    assert data2['source'] == "PKT_EXTRACTED"
    assert len(data2['facts']['devices']) == 3
    assert len(data2['facts']['connections']) == 2
    print("[PASS] XML .PKT Topology Extraction test PASSED\n")

    print("=== All Integration Tests PASSED ===")

if __name__ == "__main__":
    run_integration_test()
