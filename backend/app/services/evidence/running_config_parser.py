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
    DeviceFact,
    InterfaceFact,
    RouteFact,
    VlanFact,
    GatewayFact,
    AclFact,
    AclRule,
    DhcpPoolFact,
    NormalizedNetworkFacts,
)

class RunningConfigParser(BaseEvidenceParser):
    """
    Parses Cisco running/startup configuration commands:
    - show running-config
    - show startup-config
    """

    def can_parse(self, command: str) -> bool:
        cmd = normalize_command_string(command)
        return bool(re.search(r"^(show|sh)\s+(run(ning-config)?|start(up-config)?)$", cmd))

    def parse(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        lines = clean_cisco_output(raw_output)
        devices: list[DeviceFact] = []
        interfaces: list[InterfaceFact] = []
        routes: list[RouteFact] = []
        vlans: list[VlanFact] = []
        gateways: list[GatewayFact] = []
        acls: list[AclFact] = []
        dhcp_pools: list[DhcpPoolFact] = []
        warnings: list[str] = []

        current_block = None
        current_data: dict = {}
        standard_acls_map: dict[str, list[AclRule]] = {}

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("!") or stripped.startswith("Building configuration"):
                # End of a block (like interface, vlan, or dhcp pool)
                if current_block == "INTERFACE" and current_data:
                    interfaces.append(self._build_interface(device, current_data))
                    current_data = {}
                    current_block = None
                elif current_block == "VLAN" and current_data:
                    vlans.append(self._build_vlan(device, current_data))
                    current_data = {}
                    current_block = None
                elif current_block == "DHCP_POOL" and current_data:
                    dhcp_pools.append(self._build_dhcp_pool(device, current_data))
                    current_data = {}
                    current_block = None
                elif current_block == "NAMED_ACL" and current_data:
                    acls.append(self._build_acl(device, current_data))
                    current_data = {}
                    current_block = None
                continue

            # Hostname
            host_match = re.match(r"^hostname\s+([a-zA-Z0-9_\-]+)", stripped, re.IGNORECASE)
            if host_match:
                hostname_val = host_match.group(1)
                devices.append(
                    DeviceFact(
                        name=hostname_val,
                        device_type="Unknown",
                        hostname=hostname_val,
                        source=FactSource.CISCO_EVIDENCE,
                    )
                )
                continue

            # Default Gateway (e.g. ip default-gateway 192.168.1.1)
            gw_match = re.match(r"^ip\s+default-gateway\s+([0-9\.]+)", stripped, re.IGNORECASE)
            if gw_match:
                gw_ip = gw_match.group(1)
                if is_valid_ipv4(gw_ip):
                    gateways.append(
                        GatewayFact(
                            device=device,
                            gateway_ip=gw_ip,
                            source=FactSource.CISCO_EVIDENCE,
                        )
                    )
                continue

            # Static Route (e.g. ip route 192.168.2.0 255.255.255.0 192.168.1.2)
            route_match = re.match(r"^ip\s+route\s+([0-9\.]+)\s+([0-9\.]+)\s+([a-zA-Z0-9\/\.\-]+)", stripped, re.IGNORECASE)
            if route_match:
                net_ip, mask_ip, next_hop_or_if = route_match.groups()
                is_nh_ip = is_valid_ipv4(next_hop_or_if)
                routes.append(
                    RouteFact(
                        device=device,
                        network=f"{net_ip}/{self._mask_to_cidr(mask_ip)}",
                        mask=mask_ip,
                        next_hop=next_hop_or_if if is_nh_ip else None,
                        interface=normalize_interface_name(next_hop_or_if) if not is_nh_ip else None,
                        protocol="Static",
                        is_default=(net_ip == "0.0.0.0" and mask_ip == "0.0.0.0"),
                        source=FactSource.CISCO_EVIDENCE,
                    )
                )
                continue

            # Numbered Access List (e.g. access-list 10 permit 192.168.1.0 0.0.0.255)
            std_acl_match = re.match(r"^access-list\s+(\d+)\s+(permit|deny|remark)\s+(.*)", stripped, re.IGNORECASE)
            if std_acl_match:
                acl_num, action, rule_body = std_acl_match.groups()
                rule = AclRule(
                    action=action.lower(),
                    source=rule_body,
                    raw_rule=stripped,
                )
                if acl_num not in standard_acls_map:
                    standard_acls_map[acl_num] = []
                standard_acls_map[acl_num].append(rule)
                continue

            # Start of Named Access List (e.g. ip access-list extended BLOCK_HTTP)
            named_acl_match = re.match(r"^ip\s+access-list\s+(standard|extended)\s+([a-zA-Z0-9_\-]+)", stripped, re.IGNORECASE)
            if named_acl_match:
                acl_type_str, acl_name = named_acl_match.groups()
                current_block = "NAMED_ACL"
                current_data = {
                    "name": acl_name,
                    "type": f"Named {acl_type_str.capitalize()}",
                    "rules": [],
                }
                continue

            # Inside Named Access List
            if current_block == "NAMED_ACL":
                rule_match = re.match(r"^(permit|deny|remark)\s+(.*)", stripped, re.IGNORECASE)
                if rule_match:
                    act, body = rule_match.groups()
                    current_data["rules"].append(
                        AclRule(
                            action=act.lower(),
                            source=body,
                            raw_rule=stripped,
                        )
                    )
                continue

            # Start of DHCP Pool (e.g. ip dhcp pool POOL1)
            dhcp_pool_match = re.match(r"^ip\s+dhcp\s+pool\s+([a-zA-Z0-9_\-]+)", stripped, re.IGNORECASE)
            if dhcp_pool_match:
                current_block = "DHCP_POOL"
                current_data = {"pool_name": dhcp_pool_match.group(1)}
                continue

            # Inside DHCP Pool
            if current_block == "DHCP_POOL":
                net_m = re.match(r"^network\s+([0-9\.]+)\s+([0-9\.]+)", stripped, re.IGNORECASE)
                if net_m:
                    current_data["network"] = net_m.group(1)
                    current_data["mask"] = net_m.group(2)
                router_m = re.match(r"^default-router\s+([0-9\.]+)", stripped, re.IGNORECASE)
                if router_m:
                    current_data["default_router"] = router_m.group(1)
                dns_m = re.match(r"^dns-server\s+([0-9\.]+)", stripped, re.IGNORECASE)
                if dns_m:
                    current_data["dns_server"] = dns_m.group(1)
                domain_m = re.match(r"^domain-name\s+([a-zA-Z0-9_\-\.]+)", stripped, re.IGNORECASE)
                if domain_m:
                    current_data["domain_name"] = domain_m.group(1)
                continue

            # Start of VLAN (e.g. vlan 10)
            vlan_match = re.match(r"^vlan\s+(\d+)", stripped, re.IGNORECASE)
            if vlan_match:
                current_block = "VLAN"
                current_data = {"vlan_id": int(vlan_match.group(1))}
                continue

            # Inside VLAN
            if current_block == "VLAN":
                name_m = re.match(r"^name\s+([a-zA-Z0-9_\-]+)", stripped, re.IGNORECASE)
                if name_m:
                    current_data["name"] = name_m.group(1)
                continue

            # Start of Interface (e.g. interface GigabitEthernet0/0)
            if_match = re.match(r"^interface\s+([a-zA-Z0-9\/\.\-]+)", stripped, re.IGNORECASE)
            if if_match:
                current_block = "INTERFACE"
                current_data = {
                    "name": normalize_interface_name(if_match.group(1)),
                    "status": "UP",
                    "protocol": "UP",
                }
                continue

            # Inside Interface
            if current_block == "INTERFACE":
                if "shutdown" in stripped.lower() and not "no shutdown" in stripped.lower():
                    current_data["status"] = "ADMINISTRATIVELY_DOWN"
                    current_data["protocol"] = "DOWN"
                ip_m = re.match(r"^ip\s+address\s+([0-9\.]+)\s+([0-9\.]+)", stripped, re.IGNORECASE)
                if ip_m:
                    current_data["ip"] = ip_m.group(1)
                    current_data["mask"] = ip_m.group(2)
                vlan_m = re.match(r"^switchport\s+access\s+vlan\s+(\d+)", stripped, re.IGNORECASE)
                if vlan_m:
                    current_data["vlan_id"] = int(vlan_m.group(1))
                continue

        # Commit standard ACLs
        for acl_num, rules in standard_acls_map.items():
            acl_type = "Standard" if int(acl_num) < 100 or 1300 <= int(acl_num) <= 1999 else "Extended"
            acls.append(
                AclFact(
                    device=device,
                    acl_name_or_number=acl_num,
                    acl_type=acl_type,
                    rules=rules,
                    source=FactSource.CISCO_EVIDENCE,
                )
            )

        total_extracted = len(interfaces) + len(routes) + len(vlans) + len(gateways) + len(acls) + len(dhcp_pools)
        status = AnalysisStatus.SUCCESS if total_extracted > 0 else AnalysisStatus.FAILED

        facts = NormalizedNetworkFacts(
            devices=devices,
            interfaces=interfaces,
            routes=routes,
            vlans=vlans,
            gateways=gateways,
            acls=acls,
            dhcp_pools=dhcp_pools,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show running-config",
            facts=facts,
            warnings=warnings,
            extracted_count=total_extracted,
        )

    def _build_interface(self, device: str, d: dict) -> InterfaceFact:
        return InterfaceFact(
            device=device,
            name=d["name"],
            ip=d.get("ip"),
            mask=d.get("mask"),
            status=d.get("status", "UP"),
            protocol=d.get("protocol", "UP"),
            vlan_id=d.get("vlan_id"),
            source=FactSource.CISCO_EVIDENCE,
        )

    def _build_vlan(self, device: str, d: dict) -> VlanFact:
        return VlanFact(
            vlan_id=d["vlan_id"],
            name=d.get("name", f"VLAN_{d['vlan_id']}"),
            status="active",
            device=device,
            source=FactSource.CISCO_EVIDENCE,
        )

    def _build_dhcp_pool(self, device: str, d: dict) -> DhcpPoolFact:
        return DhcpPoolFact(
            device=device,
            pool_name=d["pool_name"],
            network=d.get("network"),
            mask=d.get("mask"),
            default_router=d.get("default_router"),
            dns_server=d.get("dns_server"),
            domain_name=d.get("domain_name"),
            source=FactSource.CISCO_EVIDENCE,
        )

    def _build_acl(self, device: str, d: dict) -> AclFact:
        return AclFact(
            device=device,
            acl_name_or_number=d["name"],
            acl_type=d["type"],
            rules=d.get("rules", []),
            source=FactSource.CISCO_EVIDENCE,
        )

    def _mask_to_cidr(self, mask_str: str) -> int:
        try:
            return sum(bin(int(x)).count("1") for x in mask_str.split("."))
        except Exception:
            return 24
