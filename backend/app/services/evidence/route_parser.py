import re
from app.services.evidence.base import (
    BaseEvidenceParser,
    EvidenceParseResult,
    normalize_command_string,
    clean_cisco_output,
    normalize_interface_name,
    is_valid_ipv4,
)
from app.services.pkt.models import (
    AnalysisStatus,
    FactSource,
    RouteFact,
    GatewayFact,
    NormalizedNetworkFacts,
)

class RouteParser(BaseEvidenceParser):
    """
    Parses Cisco routing table commands:
    - show ip route
    - show ip route static
    - show ip route ospf / connected
    """

    def can_parse(self, command: str) -> bool:
        cmd = normalize_command_string(command)
        return bool(re.search(r"^(show|sh)\s+ip\s+ro(ute)?(\s+.*)?$", cmd))

    def parse(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        lines = clean_cisco_output(raw_output)
        routes: list[RouteFact] = []
        gateways: list[GatewayFact] = []
        warnings: list[str] = []
        unparsed_route_lines = 0

        # Protocol mapping
        proto_map = {
            "C": "Connected",
            "L": "Local",
            "S": "Static",
            "O": "OSPF",
            "R": "RIP",
            "D": "EIGRP",
            "B": "BGP",
            "i": "IS-IS",
        }

        # Track default gateway from "Gateway of last resort is 192.168.1.1 to network 0.0.0.0"
        default_gw_pattern = re.compile(
            r"Gateway of last resort is\s+([0-9\.]+)\s+to network\s+([0-9\.]+)",
            re.IGNORECASE,
        )

        route_line_pattern = re.compile(
            r"^([A-Z]\*?)\s+([0-9\./]+)(?:\s+\[(\d+)/(\d+)\])?(?:\s+is directly connected,|\s+via\s+([0-9\.]+),?)?(?:\s+[0-9:]+,)?(?:\s+([a-zA-Z0-9\/\.\-]+))?",
            re.IGNORECASE,
        )

        in_legend = True

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check for Gateway of last resort
            gw_match = default_gw_pattern.search(line_str)
            if gw_match:
                in_legend = False
                gw_ip = gw_match.group(1)
                if is_valid_ipv4(gw_ip) and gw_ip != "0.0.0.0":
                    gateways.append(
                        GatewayFact(
                            device=device,
                            gateway_ip=gw_ip,
                            source=FactSource.CISCO_EVIDENCE,
                        )
                    )
                continue

            # Skip legend lines containing codes e.g. "Codes:", "L - local, C - connected", "D - EIGRP"
            if in_legend:
                if (
                    "Codes:" in line_str
                    or " - " in line_str
                    or "OSPF inter area" in line_str
                    or "candidate default" in line_str
                    or "subnets" in line_str
                ):
                    continue
                else:
                    in_legend = False

            # Skip subnet grouping lines e.g. "10.0.0.0/8 is variably subnetted, 2 subnets, 2 masks"
            if "subnetted," in line_str or "subnets," in line_str:
                continue

            # Try parsing as route entry
            m = route_line_pattern.match(line_str)
            if m:
                code_raw = m.group(1).upper()
                dest_network = m.group(2)
                admin_dist_str = m.group(3)
                metric_str = m.group(4)
                next_hop_ip = m.group(5)
                interface_raw = m.group(6)

                # Determine protocol
                base_code = code_raw.replace("*", "")
                protocol_name = proto_map.get(base_code, base_code)
                is_default = "*" in code_raw or dest_network.startswith("0.0.0.0")

                # Parse network and mask/prefix
                net_parts = dest_network.split("/")
                mask_val = self._cidr_to_mask(int(net_parts[1])) if len(net_parts) > 1 else None

                # Clean interface
                out_if = normalize_interface_name(interface_raw) if interface_raw and not interface_raw.lower().startswith("via") and not interface_raw.lower().startswith("is") else None

                routes.append(
                    RouteFact(
                        device=device,
                        network=dest_network,
                        mask=mask_val,
                        next_hop=next_hop_ip if next_hop_ip and is_valid_ipv4(next_hop_ip) else None,
                        interface=out_if,
                        protocol=protocol_name,
                        admin_distance=int(admin_dist_str) if admin_dist_str else None,
                        metric=int(metric_str) if metric_str else None,
                        is_default=is_default,
                        source=FactSource.CISCO_EVIDENCE,
                    )
                )
            else:
                unparsed_route_lines += 1

        if len(routes) == 0 and len(gateways) == 0:
            status = AnalysisStatus.FAILED
            warnings.append("No routing entries or gateway could be parsed from output.")
        elif unparsed_route_lines > 0:
            status = AnalysisStatus.PARTIAL
        else:
            status = AnalysisStatus.SUCCESS

        facts = NormalizedNetworkFacts(
            routes=routes,
            gateways=gateways,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show ip route",
            facts=facts,
            warnings=warnings,
            extracted_count=len(routes) + len(gateways),
        )

    def _cidr_to_mask(self, cidr: int) -> str:
        mask_int = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF
        return f"{(mask_int >> 24) & 0xFF}.{(mask_int >> 16) & 0xFF}.{(mask_int >> 8) & 0xFF}.{mask_int & 0xFF}"
