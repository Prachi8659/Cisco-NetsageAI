from collections import defaultdict
from typing import List
from backend.app.services.pkt.models import NormalizedNetworkFacts
from backend.app.services.rules.base import BaseRule
from backend.app.services.rules.models import RuleFinding, RuleSeverity, RuleStatus

class DuplicateIpRule(BaseRule):
    rule_id: str = "DUPLICATE_IP"
    fault_type: str = "Duplicate IP Address"

    def evaluate(self, facts: NormalizedNetworkFacts) -> List[RuleFinding]:
        findings: List[RuleFinding] = []
        # Group interfaces by valid IPv4
        ip_map = defaultdict(list)

        for intf in facts.interfaces:
            if not intf.ip:
                continue
            ip_str = intf.ip.strip()
            if ip_str.lower() in ["unassigned", "none", "0.0.0.0", "127.0.0.1", ""]:
                continue
            ip_map[ip_str].append(intf)

        for ip_addr, intf_list in ip_map.items():
            # Check if assigned to multiple distinct devices or multiple interfaces
            if len(intf_list) > 1:
                devices = sorted(list(set(i.device for i in intf_list)))
                devices_str = ", ".join(devices)
                interfaces_str = ", ".join(f"{i.device} ({i.name})" for i in intf_list)
                
                # Determine source origin
                sources = set(i.source.value if hasattr(i.source, "value") else str(i.source) for i in intf_list)
                source_str = "MIXED" if len(sources) > 1 else list(sources)[0]

                findings.append(
                    RuleFinding(
                        rule_id=self.rule_id,
                        fault_type=self.fault_type,
                        severity=RuleSeverity.CRITICAL,
                        device=devices_str,
                        interface=", ".join(i.name for i in intf_list),
                        description=f"The IPv4 address {ip_addr} is assigned to multiple interfaces ({interfaces_str}), creating an IP address conflict on the local segment.",
                        evidence=f"Duplicate assignment found for IP {ip_addr}: configured on {interfaces_str}.",
                        suggested_correction=f"Assign a unique, unused IPv4 address in the local subnet to one of the conflicting interfaces ({interfaces_str}) in Cisco Packet Tracer.",
                        confidence=1.0,
                        source=source_str,
                        status=RuleStatus.DETECTED,
                    )
                )

        return findings
