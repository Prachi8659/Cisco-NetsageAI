import ipaddress
from typing import List, Set, Dict
from app.services.pkt.models import NormalizedNetworkFacts, RouteFact
from app.services.rules.base import BaseRule
from app.services.rules.models import RuleFinding, RuleSeverity, RuleStatus

class MissingRouteRule(BaseRule):
    rule_id: str = "MISSING_ROUTE"
    fault_type: str = "Missing Route / Unreachable Network"

    def evaluate(self, facts: NormalizedNetworkFacts) -> List[RuleFinding]:
        findings: List[RuleFinding] = []

        # Gather all distinct IP subnets present across the entire network topology
        all_known_subnets: Set[ipaddress.IPv4Network] = set()
        for intf in facts.interfaces:
            if intf.ip and intf.mask:
                try:
                    net = ipaddress.IPv4Network(f"{intf.ip}/{intf.mask}", strict=False)
                    all_known_subnets.add(net)
                except Exception:
                    pass

        # If only 1 or 0 subnets exist in total, inter-subnet routing is not required
        if len(all_known_subnets) <= 1:
            return findings

        # Group routes by device
        device_routes: Dict[str, List[RouteFact]] = {}
        for r in facts.routes:
            device_routes.setdefault(r.device.lower(), []).append(r)

        # Check routers that have routing tables
        router_devices = [
            d for d in facts.devices
            if "router" in d.device_type.lower()
        ]

        for router in router_devices:
            dev_key = router.name.lower()
            routes = device_routes.get(dev_key, [])
            if not routes:
                # No routing evidence was captured for this router
                continue

            # Check if router has a default route (0.0.0.0/0)
            has_default_route = any(
                r.is_default or r.network.startswith("0.0.0.0")
                for r in routes
            )
            if has_default_route:
                # Default route covers all unlisted subnets
                continue

            # Identify networks directly connected or reachable via routes
            covered_subnets: Set[ipaddress.IPv4Network] = set()
            for r in routes:
                try:
                    r_net = ipaddress.IPv4Network(r.network, strict=False)
                    covered_subnets.add(r_net)
                except Exception:
                    pass

            # Check local interface subnets of the router
            for intf in facts.interfaces:
                if intf.device.lower() == dev_key and intf.ip and intf.mask:
                    try:
                        i_net = ipaddress.IPv4Network(f"{intf.ip}/{intf.mask}", strict=False)
                        covered_subnets.add(i_net)
                    except Exception:
                        pass

            # Find any known topology network not covered by router's routing table
            for target_subnet in all_known_subnets:
                is_covered = any(
                    target_subnet == cs or target_subnet.subnet_of(cs) or cs.subnet_of(target_subnet)
                    for cs in covered_subnets
                )
                if not is_covered:
                    source_val = router.source.value if hasattr(router.source, "value") else str(router.source)
                    findings.append(
                        RuleFinding(
                            rule_id=self.rule_id,
                            fault_type=self.fault_type,
                            severity=RuleSeverity.HIGH,
                            device=router.name,
                            description=f"Router {router.name} has no route or default gateway for destination subnet {target_subnet}.",
                            evidence=f"Active routes on {router.name}: {[r.network for r in routes]}. Missing entry for known topology subnet {target_subnet}.",
                            suggested_correction=f"Configure a static route ('ip route {target_subnet.network_address} {target_subnet.netmask} <NEXT_HOP>') or enable a dynamic routing protocol on {router.name} in Cisco Packet Tracer.",
                            confidence=0.85,
                            source=source_val,
                            status=RuleStatus.DETECTED,
                        )
                    )

        return findings
