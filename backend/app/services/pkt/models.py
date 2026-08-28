from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class FactSource(str, Enum):
    PKT_EXTRACTED = "PKT_EXTRACTED"
    CISCO_EVIDENCE = "CISCO_EVIDENCE"
    USER_INPUT = "USER_INPUT"
    PYTHON_RULE = "PYTHON_RULE"
    AI_DIAGNOSIS = "AI_DIAGNOSIS"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    UNKNOWN = "UNKNOWN"

class AnalysisStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

class DeviceFact(BaseModel):
    name: str
    device_type: str = Field(..., description="Router, Switch, PC, Server, AccessPoint, Firewall, Infrastructure, or Unknown")
    model: str | None = None
    hostname: str | None = None
    is_network_device: bool = True
    category: str = "NETWORK_DEVICE"  # NETWORK_DEVICE or INFRASTRUCTURE_OBJECT
    source: FactSource = FactSource.PKT_EXTRACTED

class InterfaceFact(BaseModel):
    device: str
    name: str
    ip: str | None = None
    mask: str | None = None
    status: str = "UNKNOWN"  # UP, DOWN, ADMINISTRATIVELY_DOWN, UNKNOWN
    protocol: str = "UNKNOWN"  # UP, DOWN, UNKNOWN
    vlan_id: int | None = None
    mac_address: str | None = None
    is_connected: bool = False
    duplex: str | None = None
    speed: str | None = None
    mtu: int | None = None
    bandwidth_kbps: int | None = None
    source: FactSource = FactSource.PKT_EXTRACTED

class ConnectionFact(BaseModel):
    device_a: str
    interface_a: str
    device_b: str
    interface_b: str
    status: ConnectionStatus = ConnectionStatus.CONNECTED
    link_type: str | None = None  # Copper, Fiber, Serial, etc.
    source: FactSource = FactSource.PKT_EXTRACTED

class VlanFact(BaseModel):
    vlan_id: int
    name: str | None = None
    status: str = "active"
    device: str | None = None
    ports: list[str] = Field(default_factory=list)
    source: FactSource = FactSource.PKT_EXTRACTED

class RouteFact(BaseModel):
    device: str
    network: str
    mask: str | None = None
    next_hop: str | None = None
    interface: str | None = None
    protocol: str | None = None  # C (Connected), S (Static), O (OSPF), R (RIP), D (EIGRP), etc.
    admin_distance: int | None = None
    metric: int | None = None
    is_default: bool = False
    source: FactSource = FactSource.PKT_EXTRACTED

class GatewayFact(BaseModel):
    device: str
    gateway_ip: str | None = None
    source: FactSource = FactSource.PKT_EXTRACTED

class TrunkFact(BaseModel):
    device: str
    port: str
    mode: str | None = None  # on, auto, desirable, etc.
    encapsulation: str | None = None  # 802.1q, isl
    status: str | None = None  # trunking, not-trunking
    native_vlan: int | None = None
    allowed_vlans: str | None = None
    active_vlans: str | None = None
    source: FactSource = FactSource.CISCO_EVIDENCE

class AclRule(BaseModel):
    action: str  # permit, deny, remark
    protocol: str | None = None  # ip, tcp, udp, icmp
    source: str
    source_wildcard: str | None = None
    destination: str | None = None
    destination_wildcard: str | None = None
    port: str | None = None
    matches: int | None = None
    raw_rule: str

class AclFact(BaseModel):
    device: str
    acl_name_or_number: str
    acl_type: str = "Standard"  # Standard, Extended, Named Standard, Named Extended
    rules: list[AclRule] = Field(default_factory=list)
    source: FactSource = FactSource.CISCO_EVIDENCE

class DhcpBindingFact(BaseModel):
    device: str
    ip_address: str
    mac_address: str
    lease_expiration: str | None = None
    binding_type: str = "Automatic"  # Automatic, Manual
    source: FactSource = FactSource.CISCO_EVIDENCE

class DhcpPoolFact(BaseModel):
    device: str
    pool_name: str
    network: str | None = None
    mask: str | None = None
    default_router: str | None = None
    dns_server: str | None = None
    domain_name: str | None = None
    lease_time: str | None = None
    source: FactSource = FactSource.CISCO_EVIDENCE

class MacEntryFact(BaseModel):
    device: str
    vlan_id: int | None = None
    mac_address: str
    entry_type: str = "DYNAMIC"  # DYNAMIC, STATIC
    port: str
    source: FactSource = FactSource.CISCO_EVIDENCE

class NormalizedNetworkFacts(BaseModel):
    devices: list[DeviceFact] = Field(default_factory=list)
    interfaces: list[InterfaceFact] = Field(default_factory=list)
    connections: list[ConnectionFact] = Field(default_factory=list)
    vlans: list[VlanFact] = Field(default_factory=list)
    routes: list[RouteFact] = Field(default_factory=list)
    gateways: list[GatewayFact] = Field(default_factory=list)
    trunks: list[TrunkFact] = Field(default_factory=list)
    acls: list[AclFact] = Field(default_factory=list)
    dhcp_bindings: list[DhcpBindingFact] = Field(default_factory=list)
    dhcp_pools: list[DhcpPoolFact] = Field(default_factory=list)
    mac_entries: list[MacEntryFact] = Field(default_factory=list)
    networks: list[str] = Field(default_factory=list)
    source: FactSource = FactSource.PKT_EXTRACTED

class PktAnalysisResult(BaseModel):
    status: AnalysisStatus
    source: FactSource
    facts: NormalizedNetworkFacts
    unsupported_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    extraction_details: dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
