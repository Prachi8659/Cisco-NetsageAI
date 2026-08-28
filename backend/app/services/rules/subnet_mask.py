import ipaddress
from typing import List, Dict, Tuple
from collections import defaultdict
from backend.app.services.pkt.models import NormalizedNetworkFacts, InterfaceFact
from backend.app.services.rules.base import BaseRule, get_network_address
from backend.app.services.rules.models import RuleFinding, RuleSeverity, RuleStatus

class SubnetMaskRule(BaseRule):
    rule_id: str = "WRONG_SUBNET_MASK"
    fault_type: str = "Subnet Mask Mismatch"

    def evaluate(self, facts: NormalizedNetworkFacts) -> List[RuleFinding]:
        findings: List[RuleFinding] = []

        # 1. Check for network/broadcast address assigned as host IP
        for intf in facts.interfaces:
            if intf.ip and intf.mask:
                try:
                    net = ipaddress.IPv4Network(f"{intf.ip}/{intf.mask}", strict=False)
                    ip_obj = ipaddress.IPv4Address(intf.ip)
                    if net.prefixlen < 31:
                        if ip_obj == net.network_address:
                            findings.append(
                                RuleFinding(
                                    rule_id=self.rule_id,
                                    fault_type=self.fault_type,
                                    severity=RuleSeverity.HIGH,
                                    device=intf.device,
                                    interface=intf.name,
                                    description=f"Interface {intf.name} on {intf.device} is assigned the subnet network ID ({intf.ip}) rather than a valid host address.",
                                    evidence=f"Configured IP: {intf.ip}, Subnet Mask: {intf.mask}, Network Address: {net.network_address}.",
                                    suggested_correction=f"Change {intf.device} {intf.name} IP to a valid host address within {net} (e.g. {list(net.hosts())[0]}).",
                                    confidence=1.0,
                                    source=intf.source.value if hasattr(intf.source, "value") else str(intf.source),
                                    status=RuleStatus.DETECTED,
                                )
                            )
                        elif ip_obj == net.broadcast_address:
                            findings.append(
                                RuleFinding(
                                    rule_id=self.rule_id,
                                    fault_type=self.fault_type,
                                    severity=RuleSeverity.HIGH,
                                    device=intf.device,
                                    interface=intf.name,
                                    description=f"Interface {intf.name} on {intf.device} is assigned the subnet broadcast address ({intf.ip}) rather than a valid host address.",
                                    evidence=f"Configured IP: {intf.ip}, Subnet Mask: {intf.mask}, Broadcast Address: {net.broadcast_address}.",
                                    suggested_correction=f"Change {intf.device} {intf.name} IP to a valid host address within {net}.",
                                    confidence=1.0,
                                    source=intf.source.value if hasattr(intf.source, "value") else str(intf.source),
                                    status=RuleStatus.DETECTED,
                                )
                            )
                except Exception:
                    pass

        # 2. Check directly connected peers for conflicting subnet masks
        # Map device:interface to InterfaceFact
        intf_lookup: Dict[Tuple[str, str], InterfaceFact] = {
            (i.device.lower(), i.name.lower()): i for i in facts.interfaces if i.ip and i.mask
        }

        checked_pairs = set()
        for conn in facts.connections:
            key_a = (conn.device_a.lower(), conn.interface_a.lower())
            key_b = (conn.device_b.lower(), conn.interface_b.lower())
            pair_id = tuple(sorted([f"{conn.device_a}:{conn.interface_a}", f"{conn.device_b}:{conn.interface_b}"]))
            if pair_id in checked_pairs:
                continue
            checked_pairs.add(pair_id)

            intf_a = intf_lookup.get(key_a)
            intf_b = intf_lookup.get(key_b)

            if intf_a and intf_b and intf_a.ip and intf_b.ip and intf_a.mask and intf_b.mask:
                if intf_a.mask != intf_b.mask:
                    sources = set([
                        intf_a.source.value if hasattr(intf_a.source, "value") else str(intf_a.source),
                        intf_b.source.value if hasattr(intf_b.source, "value") else str(intf_b.source),
                    ])
                    source_str = "MIXED" if len(sources) > 1 else list(sources)[0]

                    findings.append(
                        RuleFinding(
                            rule_id=self.rule_id,
                            fault_type=self.fault_type,
                            severity=RuleSeverity.HIGH,
                            device=f"{intf_a.device}, {intf_b.device}",
                            interface=f"{intf_a.name} <-> {intf_b.name}",
                            description=f"Directly connected interfaces {intf_a.device} {intf_a.name} and {intf_b.device} {intf_b.name} have conflicting subnet masks ({intf_a.mask} vs {intf_b.mask}).",
                            evidence=f"{intf_a.device} {intf_a.name}: {intf_a.ip}/{intf_a.mask} connected to {intf_b.device} {intf_b.name}: {intf_b.ip}/{intf_b.mask}.",
                            suggested_correction=f"Configure matching subnet masks on both link endpoints ({intf_a.device} {intf_a.name} and {intf_b.device} {intf_b.name}) in Cisco Packet Tracer.",
                            confidence=0.95,
                            source=source_str,
                            status=RuleStatus.DETECTED,
                        )
                    )

        return findings
