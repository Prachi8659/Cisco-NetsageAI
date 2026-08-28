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
    MacEntryFact,
    NormalizedNetworkFacts,
)

class MacParser(BaseEvidenceParser):
    """
    Parses Cisco MAC Address Table commands:
    - show mac address-table
    - show mac-address-table
    - show mac address-table dynamic
    """

    def can_parse(self, command: str) -> bool:
        cmd = normalize_command_string(command)
        return bool(re.search(r"^(show|sh)\s+mac(\s+|\-)address-table(\s+.*)?$", cmd))

    def parse(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        lines = clean_cisco_output(raw_output)
        mac_entries: list[MacEntryFact] = []
        warnings: list[str] = []

        in_table = False

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("----") or "Mac Address Table" in stripped or "Total Mac Addresses" in stripped:
                continue

            if "Vlan" in stripped and "Mac Address" in stripped:
                in_table = True
                continue

            # Row format: Vlan  Mac Address  Type  Ports
            # e.g.: "   1    0001.42a1.b2c3    DYNAMIC     Fa0/1"
            # e.g.: "  10    0050.7966.6801    STATIC      Gi0/1"
            # e.g.: "   *    0002.1643.5189    DYNAMIC     Fa0/2"
            # e.g.: " All    0100.0ccc.cccc    STATIC      CPU"
            parts = stripped.split()
            if len(parts) >= 4:
                vlan_str = parts[0]
                mac_str = parts[1]
                type_str = parts[2].upper()
                port_str = parts[3]

                # Verify MAC address structure
                if re.match(r"^[0-9a-fA-F\.\-]{14,17}$", mac_str):
                    v_id = int(vlan_str) if vlan_str.isdigit() else None
                    mac_entries.append(
                        MacEntryFact(
                            device=device,
                            vlan_id=v_id,
                            mac_address=mac_str,
                            entry_type=type_str if type_str in ["DYNAMIC", "STATIC"] else "DYNAMIC",
                            port=normalize_interface_name(port_str),
                            source=FactSource.CISCO_EVIDENCE,
                        )
                    )

        if len(mac_entries) == 0:
            if "none" in raw_output.lower() or len(lines) <= 3:
                status = AnalysisStatus.SUCCESS
                warnings.append("No active entries in MAC address table.")
            else:
                status = AnalysisStatus.FAILED
                warnings.append("Could not parse MAC address table entries from output.")
        else:
            status = AnalysisStatus.SUCCESS

        facts = NormalizedNetworkFacts(
            mac_entries=mac_entries,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show mac address-table",
            facts=facts,
            warnings=warnings,
            extracted_count=len(mac_entries),
        )
