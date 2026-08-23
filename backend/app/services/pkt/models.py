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

class DeviceFact(BaseModel):
    name: str
    device_type: str = Field(..., description="Router, Switch, PC, Server, AccessPoint, or Unknown")
    model: str | None = None
    hostname: str | None = None
    source: FactSource = FactSource.PKT_EXTRACTED

class InterfaceFact(BaseModel):
    device: str
    name: str
    ip: str | None = None
    mask: str | None = None
    status: str = "UNKNOWN"  # up, down, administratively down, UNKNOWN
    protocol: str = "UNKNOWN"  # up, down, UNKNOWN
    vlan_id: int | None = None
    mac_address: str | None = None
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
    source: FactSource = FactSource.PKT_EXTRACTED

class RouteFact(BaseModel):
    device: str
    network: str
    mask: str | None = None
    next_hop: str | None = None
    interface: str | None = None
    protocol: str | None = None  # C (Connected), S (Static), O (OSPF), etc.
    metric: int | None = None
    source: FactSource = FactSource.PKT_EXTRACTED

class GatewayFact(BaseModel):
    device: str
    gateway_ip: str | None = None
    source: FactSource = FactSource.PKT_EXTRACTED

class NormalizedNetworkFacts(BaseModel):
    devices: list[DeviceFact] = Field(default_factory=list)
    interfaces: list[InterfaceFact] = Field(default_factory=list)
    connections: list[ConnectionFact] = Field(default_factory=list)
    vlans: list[VlanFact] = Field(default_factory=list)
    routes: list[RouteFact] = Field(default_factory=list)
    gateways: list[GatewayFact] = Field(default_factory=list)
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
