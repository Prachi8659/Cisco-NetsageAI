import pytest
from backend.app.services.pkt.models import (
    NormalizedNetworkFacts,
    FactSource,
    DeviceFact,
    InterfaceFact,
    ConnectionFact,
    VlanFact,
    RouteFact,
    GatewayFact,
)
from backend.app.services.rules.engine import rule_engine
from backend.app.services.rules.duplicate_ip import DuplicateIpRule
from backend.app.services.rules.subnet_mask import SubnetMaskRule
from backend.app.services.rules.gateway import GatewayMismatchRule
from backend.app.services.rules.interface import InterfaceDownRule
from backend.app.services.rules.vlan import MissingVlanRule
from backend.app.services.rules.route import MissingRouteRule
from backend.app.services.rules.connection import ConnectionInconsistencyRule
from backend.app.services.rules.models import RuleStatus

# 1. Duplicate IP tests
def test_duplicate_ip_detected():
    rule = DuplicateIpRule()
    facts = NormalizedNetworkFacts(
        interfaces=[
            InterfaceFact(device="PC0", name="FastEthernet0", ip="192.168.1.10", mask="255.255.255.0", source=FactSource.PKT_EXTRACTED),
            InterfaceFact(device="PC1", name="FastEthernet0", ip="192.168.1.10", mask="255.255.255.0", source=FactSource.CISCO_EVIDENCE),
            InterfaceFact(device="R1", name="GigabitEthernet0/0", ip="192.168.1.1", mask="255.255.255.0", source=FactSource.PKT_EXTRACTED),
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 1
    assert findings[0].rule_id == "DUPLICATE_IP"
    assert "192.168.1.10" in findings[0].description
    assert "PC0" in findings[0].device and "PC1" in findings[0].device
    assert findings[0].source == "MIXED"

def test_unique_ips_no_fault():
    rule = DuplicateIpRule()
    facts = NormalizedNetworkFacts(
        interfaces=[
            InterfaceFact(device="PC0", name="FastEthernet0", ip="192.168.1.10", mask="255.255.255.0"),
            InterfaceFact(device="PC1", name="FastEthernet0", ip="192.168.1.11", mask="255.255.255.0"),
            InterfaceFact(device="Switch0", name="Vlan1", ip=None),  # Unassigned IP
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 0

# 2. Subnet Mask tests
def test_wrong_subnet_mask_detected():
    rule = SubnetMaskRule()
    facts = NormalizedNetworkFacts(
        interfaces=[
            InterfaceFact(device="PC0", name="FastEthernet0", ip="192.168.1.10", mask="255.255.255.0"),
            InterfaceFact(device="R1", name="GigabitEthernet0/0", ip="192.168.1.1", mask="255.255.255.128"),
        ],
        connections=[
            ConnectionFact(device_a="PC0", interface_a="FastEthernet0", device_b="R1", interface_b="GigabitEthernet0/0")
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 1
    assert findings[0].rule_id == "WRONG_SUBNET_MASK"
    assert "conflicting subnet masks" in findings[0].description

def test_subnet_mask_network_or_broadcast_address():
    rule = SubnetMaskRule()
    facts = NormalizedNetworkFacts(
        interfaces=[
            InterfaceFact(device="PC0", name="FastEthernet0", ip="192.168.1.0", mask="255.255.255.0"),
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 1
    assert "network ID" in findings[0].description

# 3. Gateway Mismatch tests
def test_gateway_mismatch_detected():
    rule = GatewayMismatchRule()
    facts = NormalizedNetworkFacts(
        interfaces=[
            InterfaceFact(device="PC0", name="FastEthernet0", ip="192.168.1.50", mask="255.255.255.0"),
        ],
        gateways=[
            GatewayFact(device="PC0", gateway_ip="192.168.2.1", source=FactSource.PKT_EXTRACTED)
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 1
    assert findings[0].rule_id == "GATEWAY_MISMATCH"
    assert "outside the local network subnet" in findings[0].description

def test_correct_gateway_no_fault():
    rule = GatewayMismatchRule()
    facts = NormalizedNetworkFacts(
        interfaces=[
            InterfaceFact(device="PC0", name="FastEthernet0", ip="192.168.1.50", mask="255.255.255.0"),
        ],
        gateways=[
            GatewayFact(device="PC0", gateway_ip="192.168.1.1")
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 0

# 4. Interface Down & False Positive Prevention tests
def test_connected_fastethernet_admin_down_detected():
    """Regression Test 1: Connected FastEthernet administratively down -> DETECTED"""
    rule = InterfaceDownRule()
    facts = NormalizedNetworkFacts(
        devices=[
            DeviceFact(name="PC0", device_type="PC"),
            DeviceFact(name="Switch0", device_type="Switch"),
        ],
        interfaces=[
            InterfaceFact(device="PC0", name="FastEthernet0", status="ADMINISTRATIVELY_DOWN", protocol="DOWN", is_connected=True),
            InterfaceFact(device="Switch0", name="FastEthernet0/1", status="DOWN", protocol="DOWN", is_connected=True),
        ],
        connections=[
            ConnectionFact(device_a="PC0", interface_a="FastEthernet0", device_b="Switch0", interface_b="FastEthernet0/1")
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 1
    assert findings[0].rule_id == "INTERFACE_DOWN"
    assert findings[0].device == "PC0"
    assert findings[0].interface == "FastEthernet0"
    assert "administratively disabled" in findings[0].description

def test_connected_fastethernet_up_no_fault():
    """Regression Test 2: Connected FastEthernet up -> NO FAULT"""
    rule = InterfaceDownRule()
    facts = NormalizedNetworkFacts(
        devices=[
            DeviceFact(name="PC0", device_type="PC"),
            DeviceFact(name="Switch0", device_type="Switch"),
        ],
        interfaces=[
            InterfaceFact(device="PC0", name="FastEthernet0", status="UP", protocol="UP", is_connected=True),
            InterfaceFact(device="Switch0", name="FastEthernet0/1", status="UP", protocol="UP", is_connected=True),
        ],
        connections=[
            ConnectionFact(device_a="PC0", interface_a="FastEthernet0", device_b="Switch0", interface_b="FastEthernet0/1")
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 0

def test_unused_bluetooth_admin_down_not_detected():
    """Regression Test 3: Unused Bluetooth administratively down -> NOT DETECTED (NO FAULT)"""
    rule = InterfaceDownRule()
    facts = NormalizedNetworkFacts(
        devices=[
            DeviceFact(name="PC0", device_type="PC"),
            DeviceFact(name="PC1", device_type="PC"),
            DeviceFact(name="PC2", device_type="PC"),
        ],
        interfaces=[
            # Bluetooth interfaces with no IP and no connection
            InterfaceFact(device="PC0", name="Bluetooth1", status="ADMINISTRATIVELY_DOWN", protocol="DOWN", is_connected=False, ip=None),
            InterfaceFact(device="PC1", name="Bluetooth1", status="ADMINISTRATIVELY_DOWN", protocol="DOWN", is_connected=False, ip=None),
            InterfaceFact(device="PC2", name="Bluetooth1", status="ADMINISTRATIVELY_DOWN", protocol="DOWN", is_connected=False, ip=None),
            # Connected FastEthernet interfaces that are UP
            InterfaceFact(device="PC0", name="FastEthernet0", status="UP", protocol="UP", is_connected=True),
            InterfaceFact(device="PC1", name="FastEthernet0", status="UP", protocol="UP", is_connected=True),
            InterfaceFact(device="PC2", name="FastEthernet0", status="UP", protocol="UP", is_connected=True),
        ],
        connections=[
            ConnectionFact(device_a="PC0", interface_a="FastEthernet0", device_b="Switch0", interface_b="FastEthernet0/1"),
            ConnectionFact(device_a="PC1", interface_a="FastEthernet0", device_b="Switch0", interface_b="FastEthernet0/2"),
            ConnectionFact(device_a="PC2", interface_a="FastEthernet0", device_b="Switch0", interface_b="FastEthernet0/3"),
        ]
    )
    findings = rule.evaluate(facts)
    # ZERO findings - Bluetooth false positives MUST be eliminated
    assert len(findings) == 0

def test_unused_switchport_down_not_reported_as_fault():
    """Regression Test 4: Unused switchport down -> NOT DETECTED (NO FAULT)"""
    rule = InterfaceDownRule()
    facts = NormalizedNetworkFacts(
        devices=[
            DeviceFact(name="Switch0", device_type="Switch"),
        ],
        interfaces=[
            # Fa0/1 is connected and UP
            InterfaceFact(device="Switch0", name="FastEthernet0/1", status="UP", protocol="UP", is_connected=True),
            # Fa0/4 to Fa0/24 are unused switchports (down, not connected)
            InterfaceFact(device="Switch0", name="FastEthernet0/4", status="DOWN", protocol="DOWN", is_connected=False),
            InterfaceFact(device="Switch0", name="FastEthernet0/5", status="DOWN", protocol="DOWN", is_connected=False),
            InterfaceFact(device="Switch0", name="FastEthernet0/6", status="ADMINISTRATIVELY_DOWN", protocol="DOWN", is_connected=False),
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 0

# 5. Missing VLAN tests
def test_missing_vlan_detected():
    rule = MissingVlanRule()
    facts = NormalizedNetworkFacts(
        interfaces=[
            InterfaceFact(device="Switch0", name="FastEthernet0/2", vlan_id=20),
        ],
        vlans=[
            VlanFact(vlan_id=1, name="default", status="active", device="Switch0"),
            VlanFact(vlan_id=10, name="STUDENTS", status="active", device="Switch0"),
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 1
    assert findings[0].rule_id == "MISSING_VLAN"
    assert "VLAN 20" in findings[0].description

def test_existing_vlan_no_fault():
    rule = MissingVlanRule()
    facts = NormalizedNetworkFacts(
        interfaces=[
            InterfaceFact(device="Switch0", name="FastEthernet0/2", vlan_id=10),
        ],
        vlans=[
            VlanFact(vlan_id=1, name="default", status="active", device="Switch0"),
            VlanFact(vlan_id=10, name="STUDENTS", status="active", device="Switch0"),
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 0

# 6. Missing Route tests
def test_missing_route_detected():
    rule = MissingRouteRule()
    facts = NormalizedNetworkFacts(
        devices=[
            DeviceFact(name="R1", device_type="Router"),
        ],
        interfaces=[
            InterfaceFact(device="R1", name="GigabitEthernet0/0", ip="192.168.1.1", mask="255.255.255.0"),
            # Remote subnet in topology
            InterfaceFact(device="Server0", name="FastEthernet0", ip="10.0.0.50", mask="255.255.255.0"),
        ],
        routes=[
            RouteFact(device="R1", network="192.168.1.0/24", protocol="Connected"),
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 1
    assert findings[0].rule_id == "MISSING_ROUTE"
    assert "10.0.0.0/24" in findings[0].description

# 7. Connection Inconsistency tests
def test_connection_link_state_inconsistency():
    """Regression Test 5: Connected endpoint down + peer up -> connection inconsistency detected"""
    rule = ConnectionInconsistencyRule()
    facts = NormalizedNetworkFacts(
        interfaces=[
            InterfaceFact(device="Switch0", name="FastEthernet0/1", status="UP", protocol="UP"),
            InterfaceFact(device="PC0", name="FastEthernet0", status="DOWN", protocol="DOWN"),
        ],
        connections=[
            ConnectionFact(device_a="Switch0", interface_a="FastEthernet0/1", device_b="PC0", interface_b="FastEthernet0")
        ]
    )
    findings = rule.evaluate(facts)
    assert len(findings) == 1
    assert findings[0].rule_id == "CONNECTION_FAULT"
    assert "PC0" in findings[0].description

# 8. Full Rule Engine evaluation test with real PC0/PC1/PC2 + Switch0 topology
def test_rule_engine_full_evaluation_with_disabled_pc0_fastethernet():
    facts = NormalizedNetworkFacts(
        devices=[
            DeviceFact(name="PC0", device_type="PC"),
            DeviceFact(name="PC1", device_type="PC"),
            DeviceFact(name="PC2", device_type="PC"),
            DeviceFact(name="Switch0", device_type="Switch"),
        ],
        interfaces=[
            # PC0 FastEthernet0 is disabled
            InterfaceFact(device="PC0", name="FastEthernet0", ip="192.168.1.10", mask="255.255.255.0", status="ADMINISTRATIVELY_DOWN", protocol="DOWN", is_connected=True),
            InterfaceFact(device="PC0", name="Bluetooth1", status="ADMINISTRATIVELY_DOWN", protocol="DOWN", is_connected=False),
            # PC1 FastEthernet0 is UP
            InterfaceFact(device="PC1", name="FastEthernet0", ip="192.168.1.11", mask="255.255.255.0", status="UP", protocol="UP", is_connected=True),
            InterfaceFact(device="PC1", name="Bluetooth1", status="ADMINISTRATIVELY_DOWN", protocol="DOWN", is_connected=False),
            # PC2 FastEthernet0 is UP
            InterfaceFact(device="PC2", name="FastEthernet0", ip="192.168.1.12", mask="255.255.255.0", status="UP", protocol="UP", is_connected=True),
            InterfaceFact(device="PC2", name="Bluetooth1", status="ADMINISTRATIVELY_DOWN", protocol="DOWN", is_connected=False),
            # Switch0 ports
            InterfaceFact(device="Switch0", name="FastEthernet0/1", status="DOWN", protocol="DOWN", is_connected=True),
            InterfaceFact(device="Switch0", name="FastEthernet0/2", status="UP", protocol="UP", is_connected=True),
            InterfaceFact(device="Switch0", name="FastEthernet0/3", status="UP", protocol="UP", is_connected=True),
            InterfaceFact(device="Switch0", name="FastEthernet0/4", status="DOWN", protocol="DOWN", is_connected=False),
        ],
        connections=[
            ConnectionFact(device_a="PC0", interface_a="FastEthernet0", device_b="Switch0", interface_b="FastEthernet0/1"),
            ConnectionFact(device_a="PC1", interface_a="FastEthernet0", device_b="Switch0", interface_b="FastEthernet0/2"),
            ConnectionFact(device_a="PC2", interface_a="FastEthernet0", device_b="Switch0", interface_b="FastEthernet0/3"),
        ]
    )
    res = rule_engine.evaluate_facts(case_id=1, facts=facts)
    # MUST only detect PC0 FastEthernet0, NOT Bluetooth1 on PC0/PC1/PC2 or Fa0/4 on Switch0
    fault_intfs = [f.interface for f in res.faults_detected if f.rule_id == "INTERFACE_DOWN"]
    assert fault_intfs == ["FastEthernet0"]
    assert "Bluetooth1" not in str(res.faults_detected)

def test_rule_engine_empty_facts():
    facts = NormalizedNetworkFacts()
    res = rule_engine.evaluate_facts(case_id=99, facts=facts)
    assert len(res.faults_detected) == 0
    assert "No network facts available" in res.summary

# 9. API endpoint test
def test_rule_diagnosis_api_endpoint(client):
    # 1. Create a case
    create_res = client.post("/api/cases", json={
        "title": "Rule Engine Test Case",
        "category": "VLAN",
        "severity": "HIGH",
        "symptom": "Duplicate IP conflict on LAN"
    })
    case_id = create_res.json()["id"]

    # 2. Add Cisco Evidence with duplicate IP output
    cli_output = """
Interface              IP-Address      OK? Method Status Protocol
FastEthernet0          192.168.1.50    YES manual up     up
    """
    client.post(f"/api/cases/{case_id}/evidence", json={
        "device": "PC0",
        "command": "show ip interface brief",
        "raw_output": cli_output
    })
    client.post(f"/api/cases/{case_id}/evidence", json={
        "device": "PC1",
        "command": "show ip interface brief",
        "raw_output": cli_output
    })

    # 3. Call Rule Engine Diagnosis API
    diag_res = client.post(f"/api/cases/{case_id}/diagnose/rules")
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    assert diag_data["case_id"] == case_id
    assert diag_data["total_rules_evaluated"] == 7
    assert len(diag_data["faults_detected"]) == 1
    assert diag_data["faults_detected"][0]["rule_id"] == "DUPLICATE_IP"
