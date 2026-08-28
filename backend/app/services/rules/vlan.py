from typing import List, Set, Dict
from backend.app.services.pkt.models import NormalizedNetworkFacts
from backend.app.services.rules.base import BaseRule
from backend.app.services.rules.models import RuleFinding, RuleSeverity, RuleStatus

class MissingVlanRule(BaseRule):
    rule_id: str = "MISSING_VLAN"
    fault_type: str = "Missing VLAN Definition"

    def evaluate(self, facts: NormalizedNetworkFacts) -> List[RuleFinding]:
        findings: List[RuleFinding] = []

        if not facts.vlans:
            # If no VLAN evidence exists, we cannot determine missing VLANs without guessing
            return findings

        # Group defined VLAN IDs by device (or global if device is None)
        device_vlans: Dict[str, Set[int]] = {}
        all_defined_vlans: Set[int] = set()

        for v in facts.vlans:
            all_defined_vlans.add(v.vlan_id)
            if v.device:
                device_vlans.setdefault(v.device.lower(), set()).add(v.vlan_id)

        # Check interface VLAN assignments
        for intf in facts.interfaces:
            if intf.vlan_id is None:
                continue

            v_id = intf.vlan_id
            # VLAN 1 is default on all Cisco switches
            if v_id == 1:
                continue

            dev_key = intf.device.lower()
            defined_for_dev = device_vlans.get(dev_key, all_defined_vlans)

            if defined_for_dev and v_id not in defined_for_dev:
                defined_str = ", ".join(str(x) for x in sorted(list(defined_for_dev)))
                source_val = intf.source.value if hasattr(intf.source, "value") else str(intf.source)

                findings.append(
                    RuleFinding(
                        rule_id=self.rule_id,
                        fault_type=self.fault_type,
                        severity=RuleSeverity.HIGH,
                        device=intf.device,
                        interface=intf.name,
                        description=f"Interface {intf.name} on {intf.device} is assigned to VLAN {v_id}, but VLAN {v_id} does not exist in the active VLAN database.",
                        evidence=f"Interface configured with VLAN {v_id}. Active VLANs on device: [{defined_str}].",
                        suggested_correction=f"Define the missing VLAN in Cisco Packet Tracer: enter global configuration mode on {intf.device} and execute 'vlan {v_id}'.",
                        confidence=1.0,
                        source=source_val,
                        status=RuleStatus.DETECTED,
                    )
                )

        return findings
