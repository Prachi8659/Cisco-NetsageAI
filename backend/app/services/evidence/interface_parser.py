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
    InterfaceFact,
    NormalizedNetworkFacts,
)

class InterfaceParser(BaseEvidenceParser):
    """
    Parses Cisco interface commands:
    1. show ip interface brief
    2. show interfaces [name]
    """

    def can_parse(self, command: str) -> bool:
        cmd = normalize_command_string(command)
        # Matches "show ip interface brief", "sh ip int br", "show ip int brief"
        if re.search(r"^(show|sh)\s+ip\s+int(erface)?s?\s+br(ief)?", cmd):
            return True
        # Matches "show interfaces", "sh int", "show interface gigabitethernet0/0"
        if re.search(r"^(show|sh)\s+int(erface)?s?(\s+.*)?$", cmd) and not "trunk" in cmd:
            return True
        return False

    def parse(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        cmd = normalize_command_string(command)
        if re.search(r"^(show|sh)\s+ip\s+int(erface)?s?\s+br(ief)?", cmd):
            return self._parse_show_ip_interface_brief(device, raw_output)
        else:
            return self._parse_show_interfaces(device, raw_output)

    def _parse_show_ip_interface_brief(self, device: str, raw_output: str) -> EvidenceParseResult:
        lines = clean_cisco_output(raw_output)
        interfaces: list[InterfaceFact] = []
        warnings: list[str] = []
        unparsed_lines = 0

        for line in lines:
            line_str = line.strip()
            # Skip header line
            if re.match(r"^Interface\s+IP-Address", line_str, re.IGNORECASE):
                continue
            if line_str.startswith("----") or not line_str:
                continue

            # Standard line format: Interface IP-Address OK? Method Status Protocol
            # e.g.: GigabitEthernet0/0 192.168.1.1 YES manual up up
            # e.g.: GigabitEthernet0/1 unassigned YES unset administratively down down
            # e.g.: Vlan1 10.0.0.1 YES manual up up
            # Match columns allowing status to be multi-word like "administratively down"
            tokens = line_str.split()
            if len(tokens) >= 5:
                raw_if_name = tokens[0]
                ip_str = tokens[1]
                # Method might be manual, NVRAM, DHCP, unset, etc.
                # Status is before the last token (which is protocol)
                proto_val = tokens[-1].upper()
                status_tokens = tokens[3:-1] if tokens[2].upper() in ["YES", "NO"] else tokens[2:-1]
                # Remove "manual", "NVRAM", "DHCP", "unset" if present in status_tokens
                clean_status_tokens = [t for t in status_tokens if t.lower() not in ["manual", "nvram", "dhcp", "unset", "yes", "no", "tftp", "other"]]
                raw_status = " ".join(clean_status_tokens).upper()

                if "ADMIN" in raw_status:
                    status_val = "ADMINISTRATIVELY_DOWN"
                elif "UP" in raw_status:
                    status_val = "UP"
                elif "DOWN" in raw_status:
                    status_val = "DOWN"
                else:
                    status_val = "UNKNOWN"

                norm_name = normalize_interface_name(raw_if_name)
                clean_ip = ip_str if is_valid_ipv4(ip_str) else None

                interfaces.append(
                    InterfaceFact(
                        device=device,
                        name=norm_name,
                        ip=clean_ip,
                        mask=None,  # Not present in show ip int brief - never fabricate
                        status=status_val,
                        protocol=proto_val if proto_val in ["UP", "DOWN", "UNKNOWN"] else ("UP" if "UP" in proto_val else "DOWN"),
                        is_connected=(status_val == "UP" and proto_val == "UP"),
                        source=FactSource.CISCO_EVIDENCE,
                    )
                )
            else:
                unparsed_lines += 1
                warnings.append(f"Could not parse interface line: '{line_str}'")

        if len(interfaces) == 0:
            status = AnalysisStatus.FAILED
            warnings.append("No interface entries could be parsed from output.")
        elif unparsed_lines > 0:
            status = AnalysisStatus.PARTIAL
        else:
            status = AnalysisStatus.SUCCESS

        facts = NormalizedNetworkFacts(
            interfaces=interfaces,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show ip interface brief",
            facts=facts,
            warnings=warnings,
            extracted_count=len(interfaces),
        )

    def _parse_show_interfaces(self, device: str, raw_output: str) -> EvidenceParseResult:
        """Parses detailed output from 'show interfaces'."""
        lines = clean_cisco_output(raw_output)
        interfaces: list[InterfaceFact] = []
        warnings: list[str] = []

        current_if: dict = {}

        for line in lines:
            # New interface block starts with: "GigabitEthernet0/0 is up, line protocol is up"
            # or "FastEthernet0/1 is administratively down, line protocol is down"
            header_match = re.match(r"^([a-zA-Z0-9\/\.\-]+)\s+is\s+([^,]+),\s+line\s+protocol\s+is\s+([^\s]+)", line.strip(), re.IGNORECASE)
            if header_match:
                if current_if and current_if.get("name"):
                    interfaces.append(self._build_interface_fact(device, current_if))
                    current_if = {}

                raw_name, raw_status, raw_proto = header_match.groups()
                current_if["name"] = normalize_interface_name(raw_name)
                
                s_upper = raw_status.upper()
                if "ADMIN" in s_upper:
                    current_if["status"] = "ADMINISTRATIVELY_DOWN"
                elif "UP" in s_upper:
                    current_if["status"] = "UP"
                elif "DOWN" in s_upper:
                    current_if["status"] = "DOWN"
                else:
                    current_if["status"] = "UNKNOWN"

                p_upper = raw_proto.upper()
                current_if["protocol"] = "UP" if "UP" in p_upper else "DOWN"
                continue

            # Hardware is ..., address is 0001.42a1.b2c3 (bia 0001.42a1.b2c3)
            mac_match = re.search(r"address is\s+([0-9a-fA-F\.\-]{14,17})", line)
            if mac_match and current_if:
                current_if["mac_address"] = mac_match.group(1)

            # Internet address is 192.168.1.1/24 or Internet address is 192.168.1.1 255.255.255.0
            ip_match = re.search(r"Internet address is\s+([0-9\.]+)(?:/(\d+)|(?:\s+([0-9\.]+)))?", line, re.IGNORECASE)
            if ip_match and current_if:
                ip_addr, cidr, mask_str = ip_match.groups()
                if is_valid_ipv4(ip_addr):
                    current_if["ip"] = ip_addr
                    if cidr:
                        current_if["mask"] = self._cidr_to_mask(int(cidr))
                    elif mask_str and is_valid_ipv4(mask_str):
                        current_if["mask"] = mask_str

            # MTU 1500 bytes, BW 100000 Kbit/sec, DLY 100 usec
            mtu_bw_match = re.search(r"MTU\s+(\d+)\s+bytes,\s+BW\s+(\d+)\s+Kbit", line)
            if mtu_bw_match and current_if:
                current_if["mtu"] = int(mtu_bw_match.group(1))
                current_if["bandwidth_kbps"] = int(mtu_bw_match.group(2))

            # Full-duplex, 100Mb/s, media type is 100BaseTX
            duplex_match = re.search(r"([a-zA-Z\-]+-duplex),\s+([0-9a-zA-Z\/]+)", line, re.IGNORECASE)
            if duplex_match and current_if:
                current_if["duplex"] = duplex_match.group(1)
                current_if["speed"] = duplex_match.group(2)

        # Append last interface
        if current_if and current_if.get("name"):
            interfaces.append(self._build_interface_fact(device, current_if))

        if len(interfaces) == 0:
            status = AnalysisStatus.FAILED
            warnings.append("No interface entries could be parsed from 'show interfaces' output.")
        else:
            status = AnalysisStatus.SUCCESS

        facts = NormalizedNetworkFacts(
            interfaces=interfaces,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show interfaces",
            facts=facts,
            warnings=warnings,
            extracted_count=len(interfaces),
        )

    def _build_interface_fact(self, device: str, d: dict) -> InterfaceFact:
        status_val = d.get("status", "UNKNOWN")
        proto_val = d.get("protocol", "UNKNOWN")
        return InterfaceFact(
            device=device,
            name=d.get("name", "Unknown"),
            ip=d.get("ip"),
            mask=d.get("mask"),
            status=status_val,
            protocol=proto_val,
            is_connected=(status_val == "UP" and proto_val == "UP"),
            mac_address=d.get("mac_address"),
            duplex=d.get("duplex"),
            speed=d.get("speed"),
            mtu=d.get("mtu"),
            bandwidth_kbps=d.get("bandwidth_kbps"),
            source=FactSource.CISCO_EVIDENCE,
        )

    def _cidr_to_mask(self, cidr: int) -> str:
        mask_int = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF
        return f"{(mask_int >> 24) & 0xFF}.{(mask_int >> 16) & 0xFF}.{(mask_int >> 8) & 0xFF}.{mask_int & 0xFF}"
