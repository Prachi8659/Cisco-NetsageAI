import re
from backend.app.services.evidence.base import (
    BaseEvidenceParser,
    EvidenceParseResult,
    normalize_command_string,
    clean_cisco_output,
    normalize_interface_name,
)
from backend.app.services.pkt.models import (
    AnalysisStatus,
    FactSource,
    VlanFact,
    NormalizedNetworkFacts,
)

class VlanParser(BaseEvidenceParser):
    """
    Parses Cisco VLAN commands:
    - show vlan brief
    - show vlan
    """

    def can_parse(self, command: str) -> bool:
        cmd = normalize_command_string(command)
        return bool(re.search(r"^(show|sh)\s+vlan(\s+brief|\s+br)?$", cmd))

    def parse(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        lines = clean_cisco_output(raw_output)
        vlans: list[VlanFact] = []
        warnings: list[str] = []
        unparsed_lines = 0

        # Match VLAN line:
        # e.g.: 10   STUDENTS                         active    Fa0/1, Fa0/2, Fa0/3
        # e.g.: 20   FACULTY                          active    
        # e.g.: 1002 fddi-default                     act/unsup 
        vlan_line_regex = re.compile(
            r"^(\d+)\s+([a-zA-Z0-9_\-\.]+)\s+([a-zA-Z\/]+)(?:\s+(.*))?$"
        )

        in_vlan_table = False
        current_vlan: dict = {}

        for line in lines:
            line_str = line.strip()

            if re.match(r"^VLAN\s+Name\s+Status", line_str, re.IGNORECASE):
                in_vlan_table = True
                continue
            if line_str.startswith("----") or not line_str:
                continue

            # Check if line continues ports list from previous VLAN line
            if in_vlan_table and current_vlan and not re.match(r"^\d+\s+", line_str):
                # Continuation line of ports (e.g. "                     Fa0/10, Fa0/11")
                extra_ports = [p.strip() for p in line_str.split(",") if p.strip()]
                for p in extra_ports:
                    current_vlan["ports"].append(normalize_interface_name(p))
                continue

            # New VLAN row
            m = vlan_line_regex.match(line_str)
            if m:
                if current_vlan:
                    vlans.append(self._build_vlan_fact(device, current_vlan))
                    current_vlan = {}

                v_id_str, v_name, v_status, raw_ports_str = m.groups()
                ports_list = []
                if raw_ports_str:
                    for p in raw_ports_str.split(","):
                        if p.strip():
                            ports_list.append(normalize_interface_name(p.strip()))

                current_vlan = {
                    "vlan_id": int(v_id_str),
                    "name": v_name,
                    "status": "active" if "act" in v_status.lower() else v_status,
                    "ports": ports_list,
                }
            elif in_vlan_table and not line_str.startswith("VLAN Type"):
                unparsed_lines += 1

        if current_vlan:
            vlans.append(self._build_vlan_fact(device, current_vlan))

        if len(vlans) == 0:
            status = AnalysisStatus.FAILED
            warnings.append("No VLAN entries could be parsed from 'show vlan brief' output.")
        elif unparsed_lines > 0:
            status = AnalysisStatus.PARTIAL
        else:
            status = AnalysisStatus.SUCCESS

        facts = NormalizedNetworkFacts(
            vlans=vlans,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show vlan brief",
            facts=facts,
            warnings=warnings,
            extracted_count=len(vlans),
        )

    def _build_vlan_fact(self, device: str, d: dict) -> VlanFact:
        return VlanFact(
            vlan_id=d["vlan_id"],
            name=d["name"],
            status=d["status"],
            device=device,
            ports=d.get("ports", []),
            source=FactSource.CISCO_EVIDENCE,
        )
