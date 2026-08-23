# Python script to generate a sample .pkt file and upload it to case 1
import io
import httpx

API_URL = "http://localhost:8000/api"

# 1. Create realistic sample .pkt binary content
pkt_content = b"PKT7.3\x00\x00\x00\x01PacketTracer_VLAN10_Trunk_Fault_Topology_Simulation_Data_01020304"

# 2. Upload to Case 1
with httpx.Client() as client:
    files = {"file": ("vlan10_trunk_fault.pkt", io.BytesIO(pkt_content), "application/octet-stream")}
    res = client.post(f"{API_URL}/cases/1/pkt", files=files)
    print("Upload response:", res.status_code, res.json())
