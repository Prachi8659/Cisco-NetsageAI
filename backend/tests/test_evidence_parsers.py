import pytest
from app.services.evidence.parser_service import evidence_parser_service
from app.services.pkt.models import AnalysisStatus, FactSource

def test_parse_show_ip_interface_brief():
    raw = """
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     192.168.1.1     YES manual up                    up
GigabitEthernet0/1     unassigned      YES unset  administratively down down
FastEthernet0/1        10.0.0.1        YES manual up                    up
Serial0/0/0            unassigned      YES unset  down                  down
    """
    res = evidence_parser_service.parse_evidence(
        device="R1",
        command="show ip interface brief",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS
    assert res.source == FactSource.CISCO_EVIDENCE
    assert res.extracted_count == 4

    intfs = res.facts.interfaces
    r1_g0 = next(i for i in intfs if i.name == "GigabitEthernet0/0")
    assert r1_g0.ip == "192.168.1.1"
    assert r1_g0.mask is None  # Never fabricated from brief output!
    assert r1_g0.status == "UP"
    assert r1_g0.protocol == "UP"
    assert r1_g0.is_connected is True
    assert r1_g0.source == FactSource.CISCO_EVIDENCE

    r1_g1 = next(i for i in intfs if i.name == "GigabitEthernet0/1")
    assert r1_g1.ip is None
    assert r1_g1.status == "ADMINISTRATIVELY_DOWN"
    assert r1_g1.protocol == "DOWN"
    assert r1_g1.is_connected is False

def test_parse_show_ip_interface_brief_abbreviation():
    raw = """
Interface              IP-Address      OK? Method Status Protocol
Fa0/1                  192.168.10.1    YES manual up     up
    """
    res = evidence_parser_service.parse_evidence(
        device="Switch1",
        command="sh ip int br",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS
    assert res.facts.interfaces[0].name == "FastEthernet0/1"
    assert res.facts.interfaces[0].ip == "192.168.10.1"

def test_parse_show_ip_route():
    raw = """
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 

Gateway of last resort is 192.168.10.1 to network 0.0.0.0

C    192.168.1.0/24 is directly connected, GigabitEthernet0/0
L    192.168.1.1/32 is directly connected, GigabitEthernet0/0
S    192.168.20.0/24 [1/0] via 192.168.10.2
S*   0.0.0.0/0 [1/0] via 192.168.10.1
O    172.16.1.0/24 [110/2] via 192.168.10.2, 00:04:12, GigabitEthernet0/1
    """
    res = evidence_parser_service.parse_evidence(
        device="R1",
        command="show ip route",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS
    assert len(res.facts.routes) == 5
    assert len(res.facts.gateways) == 1
    assert res.facts.gateways[0].gateway_ip == "192.168.10.1"

    # Verify OSPF route
    ospf_route = next(r for r in res.facts.routes if r.protocol == "OSPF")
    assert ospf_route.network == "172.16.1.0/24"
    assert ospf_route.mask == "255.255.255.0"
    assert ospf_route.next_hop == "192.168.10.2"
    assert ospf_route.interface == "GigabitEthernet0/1"
    assert ospf_route.admin_distance == 110
    assert ospf_route.metric == 2

    # Verify default route
    default_route = next(r for r in res.facts.routes if r.is_default)
    assert default_route.next_hop == "192.168.10.1"
    assert default_route.protocol == "Static"

def test_parse_show_vlan_brief():
    raw = """
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Fa0/1, Fa0/2, Fa0/3, Fa0/4
10   STUDENTS                         active    Fa0/5, Fa0/6
20   FACULTY                          active    Fa0/7, Fa0/8
99   MANAGEMENT                       active    
1002 fddi-default                     act/unsup 
    """
    res = evidence_parser_service.parse_evidence(
        device="Switch0",
        command="show vlan brief",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS
    vlans = res.facts.vlans
    assert len(vlans) == 5

    v10 = next(v for v in vlans if v.vlan_id == 10)
    assert v10.name == "STUDENTS"
    assert v10.status == "active"
    assert "FastEthernet0/5" in v10.ports
    assert "FastEthernet0/6" in v10.ports

def test_parse_show_interfaces_trunk():
    raw = """
Port        Mode         Encapsulation  Status        Native vlan
Fa0/1       on           802.1q         trunking      1
Gi0/1       auto         802.1q         trunking      99

Port        Vlans allowed on trunk
Fa0/1       1-4094
Gi0/1       1,10,20,99

Port        Vlans allowed and active in management domain
Fa0/1       1,10,20
Gi0/1       1,10,20,99
    """
    res = evidence_parser_service.parse_evidence(
        device="Switch0",
        command="show interfaces trunk",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS
    trunks = res.facts.trunks
    assert len(trunks) == 2

    t_fa1 = next(t for t in trunks if t.port == "FastEthernet0/1")
    assert t_fa1.mode == "on"
    assert t_fa1.encapsulation == "802.1q"
    assert t_fa1.native_vlan == 1
    assert t_fa1.allowed_vlans == "1-4094"

def test_parse_show_running_config():
    raw = """
Building configuration...

Current configuration : 1084 bytes
!
version 15.1
no service timestamps log datetime msec
hostname Router_Lab_1
!
ip dhcp pool LAN_POOL
 network 192.168.1.0 255.255.255.0
 default-router 192.168.1.1
 dns-server 8.8.8.8
!
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
 duplex auto
 speed auto
!
interface GigabitEthernet0/1
 ip address 10.0.0.1 255.255.255.252
 shutdown
!
ip route 192.168.2.0 255.255.255.0 10.0.0.2
ip default-gateway 192.168.1.254
!
access-list 10 permit 192.168.1.0 0.0.0.255
access-list 10 deny any
!
end
    """
    res = evidence_parser_service.parse_evidence(
        device="Router_Lab_1",
        command="show running-config",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS

    # Verify device
    assert res.facts.devices[0].name == "Router_Lab_1"

    # Verify interfaces
    intfs = res.facts.interfaces
    assert len(intfs) == 2
    g0 = next(i for i in intfs if i.name == "GigabitEthernet0/0")
    assert g0.ip == "192.168.1.1"
    assert g0.mask == "255.255.255.0"
    assert g0.status == "UP"

    g1 = next(i for i in intfs if i.name == "GigabitEthernet0/1")
    assert g1.status == "ADMINISTRATIVELY_DOWN"

    # Verify static route
    assert len(res.facts.routes) == 1
    assert res.facts.routes[0].network == "192.168.2.0/24"
    assert res.facts.routes[0].next_hop == "10.0.0.2"

    # Verify default gateway
    assert len(res.facts.gateways) == 1
    assert res.facts.gateways[0].gateway_ip == "192.168.1.254"

    # Verify DHCP pool
    assert len(res.facts.dhcp_pools) == 1
    assert res.facts.dhcp_pools[0].pool_name == "LAN_POOL"
    assert res.facts.dhcp_pools[0].default_router == "192.168.1.1"

    # Verify ACL
    assert len(res.facts.acls) == 1
    assert res.facts.acls[0].acl_name_or_number == "10"
    assert len(res.facts.acls[0].rules) == 2

def test_parse_show_access_lists():
    raw = """
Standard IP access list 10
    10 permit 192.168.1.0, wildcard bits 0.0.0.255 (24 matches)
    20 deny any (5 matches)
Extended IP access list BLOCK_TELNET
    10 deny tcp any any eq 23 (10 matches)
    20 permit ip any any
    """
    res = evidence_parser_service.parse_evidence(
        device="R1",
        command="show access-lists",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS
    assert len(res.facts.acls) == 2

    std_acl = next(a for a in res.facts.acls if a.acl_name_or_number == "10")
    assert std_acl.acl_type == "Standard"
    assert len(std_acl.rules) == 2
    assert std_acl.rules[0].action == "permit"
    assert std_acl.rules[0].matches == 24

def test_parse_show_ip_dhcp_binding():
    raw = """
Bindings from all pools :
IP address          Client-ID/              Lease expiration        Type
                    Hardware address/
                    User name
192.168.1.50        0100.5079.6668.01       Infinite                Automatic
192.168.1.51        0100.0216.4351.89       Feb 27 2026 05:30 PM    Automatic
    """
    res = evidence_parser_service.parse_evidence(
        device="R1",
        command="show ip dhcp binding",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS
    assert len(res.facts.dhcp_bindings) == 2
    assert res.facts.dhcp_bindings[0].ip_address == "192.168.1.50"
    assert res.facts.dhcp_bindings[0].mac_address == "0100.5079.6668.01"

def test_parse_show_interfaces_detailed():
    raw = """
GigabitEthernet0/0 is up, line protocol is up
  Hardware is CN Giga, address is 0001.42a1.b2c3 (bia 0001.42a1.b2c3)
  Internet address is 192.168.10.1/24
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, loopback not set
  Full-duplex, 1000Mb/s, media type is RJ45
    """
    res = evidence_parser_service.parse_evidence(
        device="R1",
        command="show interfaces GigabitEthernet0/0",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS
    assert len(res.facts.interfaces) == 1
    intf = res.facts.interfaces[0]
    assert intf.name == "GigabitEthernet0/0"
    assert intf.ip == "192.168.10.1"
    assert intf.mask == "255.255.255.0"
    assert intf.mac_address == "0001.42a1.b2c3"
    assert intf.mtu == 1500
    assert intf.bandwidth_kbps == 1000000
    assert intf.duplex == "Full-duplex"
    assert intf.speed == "1000Mb/s"

def test_parse_show_mac_address_table():
    raw = """
          Mac Address Table
-------------------------------------------

Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
   1    0001.42a1.b2c3    DYNAMIC     Fa0/1
   1    0002.1643.5189    DYNAMIC     Fa0/2
  10    0050.7966.6801    STATIC      Fa0/3
Total Mac Addresses for this criterion: 3
    """
    res = evidence_parser_service.parse_evidence(
        device="Switch0",
        command="show mac address-table",
        raw_output=raw,
    )
    assert res.status == AnalysisStatus.SUCCESS
    assert len(res.facts.mac_entries) == 3
    entry1 = res.facts.mac_entries[0]
    assert entry1.vlan_id == 1
    assert entry1.mac_address == "0001.42a1.b2c3"
    assert entry1.entry_type == "DYNAMIC"
    assert entry1.port == "FastEthernet0/1"

def test_parse_empty_or_unsupported_command():
    # Empty output
    res1 = evidence_parser_service.parse_evidence("R1", "show ip int br", "")
    assert res1.status == AnalysisStatus.FAILED

    # Unsupported command
    res2 = evidence_parser_service.parse_evidence("R1", "show crypto isakmp sa", "some vpn output")
    assert res2.status == AnalysisStatus.UNKNOWN
    assert "unsupported" in res2.warnings[0].lower()
