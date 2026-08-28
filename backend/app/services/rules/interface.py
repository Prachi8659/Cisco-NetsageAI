from typing import List, Set, Tuple
from app.services.pkt.models import NormalizedNetworkFacts
from app.services.rules.base import BaseRule
from app.services.rules.models import RuleFinding, RuleSeverity, RuleStatus

AUXILIARY_PORT_PREFIXES = (
    "bluetooth",
    "rs232",
    "console",
    "aux",
    "null",
    "async",
    "modem",
    "coaxial",
)

class InterfaceDownRule(BaseRule):
    rule_id: str = "INTERFACE_DOWN"
    fault_type: str = "Interface Administratively Down / Down"

    def evaluate(self, facts: NormalizedNetworkFacts) -> List[RuleFinding]:
        findings: List[RuleFinding] = []

        # 1. Identify all interfaces that are physically connected according to topology connections
        connected_interfaces: Set[Tuple[str, str]] = set()
        for conn in facts.connections:
            connected_interfaces.add((conn.device_a.lower(), conn.interface_a.lower()))
            connected_interfaces.add((conn.device_b.lower(), conn.interface_b.lower()))

        # 2. Build device type lookup
        device_types = {d.name.lower(): d.device_type.lower() for d in facts.devices}

        for intf in facts.interfaces:
            dev_key = intf.device.lower()
            intf_key = intf.name.lower()
            dev_type = device_types.get(dev_key, "")

            is_connected_link = (dev_key, intf_key) in connected_interfaces or bool(intf.is_connected)
            has_ip_configured = bool(intf.ip and intf.ip.lower() not in ["unassigned", "none", "0.0.0.0", ""])
            is_auxiliary_port = any(intf_key.startswith(p) for p in AUXILIARY_PORT_PREFIXES)
            is_switch = "switch" in dev_type or "bridge" in dev_type

            # Strict false-positive guard:
            # 1. Ignore non-network / auxiliary ports (e.g. Bluetooth, RS232) unless they have a configured IP.
            # 2. Ignore unused/unconnected interfaces (e.g. unused switchports, unused PC NICs)
            #    that have NO physical link connection and NO configured IP.
            if is_auxiliary_port and not has_ip_configured:
                continue

            if not is_connected_link and not has_ip_configured:
                continue

            status_upper = intf.status.upper()
            proto_upper = intf.protocol.upper()
            source_val = intf.source.value if hasattr(intf.source, "value") else str(intf.source)

            # Case A: Administratively Down (explicitly disabled with 'shutdown')
            if "ADMIN" in status_upper or "SHUTDOWN" in status_upper:
                findings.append(
                    RuleFinding(
                        rule_id=self.rule_id,
                        fault_type="Interface Administratively Down",
                        severity=RuleSeverity.HIGH,
                        device=intf.device,
                        interface=intf.name,
                        description=f"Interface {intf.name} on {intf.device} is administratively disabled ('shutdown') and not passing traffic.",
                        evidence=f"Status: {intf.status}, Protocol: {intf.protocol}, Configured IP: {intf.ip or 'unassigned'}.",
                        suggested_correction=f"Enter interface configuration mode on {intf.device} ('interface {intf.name}') and execute 'no shutdown' in Cisco Packet Tracer.",
                        confidence=1.0,
                        source=source_val,
                        status=RuleStatus.DETECTED,
                    )
                )
            # Case B: Configured host/router IP interface or non-switch interface whose line protocol is DOWN
            elif (has_ip_configured or (is_connected_link and not is_switch)) and (status_upper == "DOWN" or proto_upper == "DOWN"):
                findings.append(
                    RuleFinding(
                        rule_id=self.rule_id,
                        fault_type="Interface Line Protocol Down",
                        severity=RuleSeverity.HIGH,
                        device=intf.device,
                        interface=intf.name,
                        description=f"Interface {intf.name} on {intf.device} is connected or configured, but its operational status or line protocol is DOWN.",
                        evidence=f"Physical Connection: Detected in topology, Status: {intf.status}, Protocol: {intf.protocol}.",
                        suggested_correction=f"Check the remote connected interface and verify both endpoints are enabled with matching speed/duplex settings in Cisco Packet Tracer.",
                        confidence=0.9,
                        source=source_val,
                        status=RuleStatus.DETECTED,
                    )
                )

        return findings
