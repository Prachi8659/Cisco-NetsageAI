from typing import List, Dict, Tuple
from backend.app.services.pkt.models import NormalizedNetworkFacts, InterfaceFact
from backend.app.services.rules.base import BaseRule
from backend.app.services.rules.models import RuleFinding, RuleSeverity, RuleStatus

class ConnectionInconsistencyRule(BaseRule):
    rule_id: str = "CONNECTION_FAULT"
    fault_type: str = "Connection / Interface Operational Inconsistency"

    def evaluate(self, facts: NormalizedNetworkFacts) -> List[RuleFinding]:
        findings: List[RuleFinding] = []

        # Map device:interface -> InterfaceFact
        intf_map: Dict[Tuple[str, str], InterfaceFact] = {
            (i.device.lower(), i.name.lower()): i for i in facts.interfaces
        }

        checked_links = set()

        for conn in facts.connections:
            key_a = (conn.device_a.lower(), conn.interface_a.lower())
            key_b = (conn.device_b.lower(), conn.interface_b.lower())

            link_id = tuple(sorted([f"{conn.device_a}:{conn.interface_a}", f"{conn.device_b}:{conn.interface_b}"]))
            if link_id in checked_links:
                continue
            checked_links.add(link_id)

            intf_a = intf_map.get(key_a)
            intf_b = intf_map.get(key_b)

            # Check 1: One endpoint is UP but peer endpoint is DOWN/ADMINISTRATIVELY_DOWN in Cisco evidence
            if intf_a and intf_b:
                status_a = intf_a.status.upper()
                status_b = intf_b.status.upper()
                proto_a = intf_a.protocol.upper()
                proto_b = intf_b.protocol.upper()

                if (status_a == "UP" and proto_a == "UP") and (status_b != "UP" or proto_b != "UP"):
                    findings.append(
                        RuleFinding(
                            rule_id=self.rule_id,
                            fault_type=self.fault_type,
                            severity=RuleSeverity.HIGH,
                            device=intf_b.device,
                            interface=intf_b.name,
                            description=f"Physical link exists between {intf_a.device} {intf_a.name} and {intf_b.device} {intf_b.name}, but {intf_b.device} {intf_b.name} is {intf_b.status}/{intf_b.protocol}.",
                            evidence=f"{intf_a.device} {intf_a.name} (UP/UP) <-> {intf_b.device} {intf_b.name} ({intf_b.status}/{intf_b.protocol}).",
                            suggested_correction=f"Check port status on {intf_b.device} ({intf_b.name}) and verify interface is enabled with 'no shutdown' in Cisco Packet Tracer.",
                            confidence=0.9,
                            source="MIXED",
                            status=RuleStatus.DETECTED,
                        )
                    )
                elif (status_b == "UP" and proto_b == "UP") and (status_a != "UP" or proto_a != "UP"):
                    findings.append(
                        RuleFinding(
                            rule_id=self.rule_id,
                            fault_type=self.fault_type,
                            severity=RuleSeverity.HIGH,
                            device=intf_a.device,
                            interface=intf_a.name,
                            description=f"Physical link exists between {intf_a.device} {intf_a.name} and {intf_b.device} {intf_b.name}, but {intf_a.device} {intf_a.name} is {intf_a.status}/{intf_a.protocol}.",
                            evidence=f"{intf_b.device} {intf_b.name} (UP/UP) <-> {intf_a.device} {intf_a.name} ({intf_a.status}/{intf_a.protocol}).",
                            suggested_correction=f"Check port status on {intf_a.device} ({intf_a.name}) and verify interface is enabled with 'no shutdown' in Cisco Packet Tracer.",
                            confidence=0.9,
                            source="MIXED",
                            status=RuleStatus.DETECTED,
                        )
                    )

                # Check 2: Duplex mismatch
                if intf_a.duplex and intf_b.duplex:
                    d_a = intf_a.duplex.lower()
                    d_b = intf_b.duplex.lower()
                    if ("full" in d_a and "half" in d_b) or ("half" in d_a and "full" in d_b):
                        findings.append(
                            RuleFinding(
                                rule_id=self.rule_id,
                                fault_type="Duplex Mismatch",
                                severity=RuleSeverity.MEDIUM,
                                device=f"{intf_a.device}, {intf_b.device}",
                                interface=f"{intf_a.name} <-> {intf_b.name}",
                                description=f"Duplex mismatch detected on link between {intf_a.device} {intf_a.name} ({intf_a.duplex}) and {intf_b.device} {intf_b.name} ({intf_b.duplex}).",
                                evidence=f"{intf_a.device} {intf_a.name}: {intf_a.duplex} <-> {intf_b.device} {intf_b.name}: {intf_b.duplex}.",
                                suggested_correction=f"Configure both link endpoints to matching duplex settings ('duplex full' or 'duplex auto') in Cisco Packet Tracer.",
                                confidence=0.95,
                                source="CISCO_EVIDENCE",
                                status=RuleStatus.DETECTED,
                            )
                        )

        return findings
