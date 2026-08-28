import re
from app.services.evidence.base import (
    BaseEvidenceParser,
    EvidenceParseResult,
    normalize_command_string,
    clean_cisco_output,
    normalize_interface_name,
)
from app.services.pkt.models import (
    AnalysisStatus,
    FactSource,
    TrunkFact,
    NormalizedNetworkFacts,
)

class TrunkParser(BaseEvidenceParser):
    """
    Parses Cisco trunking commands:
    - show interfaces trunk
    - show interface [name] trunk
    """

    def can_parse(self, command: str) -> bool:
        cmd = normalize_command_string(command)
        return bool(re.search(r"^(show|sh)\s+int(erface)?s?(\s+[a-zA-Z0-9\/\.\-]+)?\s+trunk$", cmd))

    def parse(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        lines = clean_cisco_output(raw_output)
        trunks_map: dict[str, dict] = {}
        warnings: list[str] = []

        current_section = None

        for line in lines:
            line_str = line.strip()

            if "Port" in line_str and "Encapsulation" in line_str:
                current_section = "STATUS"
                continue
            elif "Port" in line_str and "Vlans allowed on trunk" in line_str:
                current_section = "ALLOWED"
                continue
            elif "Port" in line_str and "Vlans allowed and active in management domain" in line_str:
                current_section = "ACTIVE"
                continue
            elif "Port" in line_str and "spanning tree" in line_str:
                current_section = "STP"
                continue

            if not line_str or line_str.startswith("----"):
                continue

            # Section 1: Port Mode Encapsulation Status Native vlan
            # e.g.: Fa0/1 on 802.1q trunking 1
            if current_section == "STATUS":
                parts = line_str.split()
                if len(parts) >= 5:
                    port_name = normalize_interface_name(parts[0])
                    mode = parts[1]
                    encap = parts[2]
                    status_str = parts[3]
                    native_vlan = int(parts[4]) if parts[4].isdigit() else 1

                    if port_name not in trunks_map:
                        trunks_map[port_name] = {}

                    trunks_map[port_name].update({
                        "port": port_name,
                        "mode": mode,
                        "encapsulation": encap,
                        "status": status_str,
                        "native_vlan": native_vlan,
                    })

            # Section 2: Port Vlans allowed on trunk
            # e.g.: Fa0/1 1-4094
            elif current_section == "ALLOWED":
                parts = line_str.split(None, 1)
                if len(parts) >= 2:
                    port_name = normalize_interface_name(parts[0])
                    allowed_vlans = parts[1].strip()
                    if port_name in trunks_map:
                        trunks_map[port_name]["allowed_vlans"] = allowed_vlans

            # Section 3: Port Vlans allowed and active
            # e.g.: Fa0/1 1,10,20
            elif current_section == "ACTIVE":
                parts = line_str.split(None, 1)
                if len(parts) >= 2:
                    port_name = normalize_interface_name(parts[0])
                    active_vlans = parts[1].strip()
                    if port_name in trunks_map:
                        trunks_map[port_name]["active_vlans"] = active_vlans

        trunks: list[TrunkFact] = [
            TrunkFact(
                device=device,
                port=t["port"],
                mode=t.get("mode"),
                encapsulation=t.get("encapsulation"),
                status=t.get("status"),
                native_vlan=t.get("native_vlan"),
                allowed_vlans=t.get("allowed_vlans"),
                active_vlans=t.get("active_vlans"),
                source=FactSource.CISCO_EVIDENCE,
            )
            for t in trunks_map.values()
        ]

        if len(trunks) == 0:
            # Maybe no ports are trunking
            if "none" in raw_output.lower() or len(lines) <= 2:
                status = AnalysisStatus.SUCCESS
                warnings.append("No active trunk ports found on device.")
            else:
                status = AnalysisStatus.FAILED
                warnings.append("Could not parse trunking information from output.")
        else:
            status = AnalysisStatus.SUCCESS

        facts = NormalizedNetworkFacts(
            trunks=trunks,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show interfaces trunk",
            facts=facts,
            warnings=warnings,
            extracted_count=len(trunks),
        )
