import ipaddress
from typing import List, Dict
from app.services.pkt.models import NormalizedNetworkFacts
from app.services.rules.base import BaseRule, same_subnet
from app.services.rules.models import RuleFinding, RuleSeverity, RuleStatus

class GatewayMismatchRule(BaseRule):
    rule_id: str = "GATEWAY_MISMATCH"
    fault_type: str = "Default Gateway Inconsistency"

    def evaluate(self, facts: NormalizedNetworkFacts) -> List[RuleFinding]:
        findings: List[RuleFinding] = []

        # Build mapping of device -> list of InterfaceFacts with valid IP & mask
        device_interfaces: Dict[str, list] = {}
        for intf in facts.interfaces:
            if intf.ip and intf.mask:
                device_interfaces.setdefault(intf.device.lower(), []).append(intf)

        for gw in facts.gateways:
            if not gw.gateway_ip:
                continue
            gw_ip = gw.gateway_ip.strip()
            if gw_ip.lower() in ["unassigned", "none", "0.0.0.0", ""]:
                continue

            dev_key = gw.device.lower()
            intfs = device_interfaces.get(dev_key, [])

            if not intfs:
                # Device has a gateway configured but no interface IP/mask in facts
                continue

            # Check if gateway matches ANY of the device's configured subnets
            matches_any_subnet = False
            matching_intf = None
            own_ip_conflict = False

            for intf in intfs:
                if intf.ip == gw_ip:
                    own_ip_conflict = True
                    matching_intf = intf
                    break
                try:
                    net = ipaddress.IPv4Network(f"{intf.ip}/{intf.mask}", strict=False)
                    gw_obj = ipaddress.IPv4Address(gw_ip)
                    if gw_obj in net:
                        matches_any_subnet = True
                        matching_intf = intf
                        break
                except Exception:
                    pass

            if own_ip_conflict and matching_intf:
                findings.append(
                    RuleFinding(
                        rule_id=self.rule_id,
                        fault_type=self.fault_type,
                        severity=RuleSeverity.HIGH,
                        device=gw.device,
                        interface=matching_intf.name,
                        description=f"Device {gw.device} has configured its default gateway to its own local IP address ({gw_ip}).",
                        evidence=f"Configured IP: {matching_intf.ip}, Configured Gateway: {gw_ip}.",
                        suggested_correction=f"Change the default gateway on {gw.device} to the LAN interface IP of the local router/gateway in Cisco Packet Tracer.",
                        confidence=1.0,
                        source=gw.source.value if hasattr(gw.source, "value") else str(gw.source),
                        status=RuleStatus.DETECTED,
                    )
                )
            elif not matches_any_subnet:
                intf_ref = intfs[0]
                source_val = gw.source.value if hasattr(gw.source, "value") else str(gw.source)
                try:
                    local_net = ipaddress.IPv4Network(f"{intf_ref.ip}/{intf_ref.mask}", strict=False)
                    local_net_str = str(local_net)
                except Exception:
                    local_net_str = f"{intf_ref.ip}/{intf_ref.mask}"

                findings.append(
                    RuleFinding(
                        rule_id=self.rule_id,
                        fault_type=self.fault_type,
                        severity=RuleSeverity.CRITICAL,
                        device=gw.device,
                        interface=intf_ref.name,
                        description=f"Default gateway {gw_ip} on {gw.device} is outside the local network subnet ({local_net_str}), preventing off-subnet communication.",
                        evidence=f"Device {gw.device} IP is {intf_ref.ip} (Subnet: {intf_ref.mask}), but Default Gateway is set to {gw_ip}.",
                        suggested_correction=f"Update the default gateway on {gw.device} to a valid router/gateway IP within {local_net_str} in Cisco Packet Tracer.",
                        confidence=1.0,
                        source=source_val,
                        status=RuleStatus.DETECTED,
                    )
                )

        return findings
