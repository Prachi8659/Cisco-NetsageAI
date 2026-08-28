import re
from backend.app.services.evidence.base import (
    BaseEvidenceParser,
    EvidenceParseResult,
    normalize_command_string,
    clean_cisco_output,
    is_valid_ipv4,
)
from backend.app.services.pkt.models import (
    AnalysisStatus,
    FactSource,
    DhcpBindingFact,
    DhcpPoolFact,
    NormalizedNetworkFacts,
)

class DhcpParser(BaseEvidenceParser):
    """
    Parses Cisco DHCP commands:
    - show ip dhcp binding
    - show ip dhcp pool
    """

    def can_parse(self, command: str) -> bool:
        cmd = normalize_command_string(command)
        return bool(re.search(r"^(show|sh)\s+ip\s+dhcp\s+(binding|bind|pool(\s+.*)?)$", cmd))

    def parse(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        cmd = normalize_command_string(command)
        if "pool" in cmd:
            return self._parse_dhcp_pool(device, raw_output)
        else:
            return self._parse_dhcp_binding(device, raw_output)

    def _parse_dhcp_binding(self, device: str, raw_output: str) -> EvidenceParseResult:
        lines = clean_cisco_output(raw_output)
        bindings: list[DhcpBindingFact] = []
        warnings: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("IP address") or stripped.startswith("----") or "Bindings from" in stripped:
                continue

            # e.g.: "192.168.1.100    0100.5079.6668.01       Infinite                Automatic"
            # e.g.: "10.0.0.50        0001.42a1.b2c3          Feb 25 2026 12:00 PM    Automatic"
            parts = stripped.split()
            if len(parts) >= 3 and is_valid_ipv4(parts[0]):
                ip_val = parts[0]
                mac_val = parts[1]
                b_type = parts[-1] if parts[-1].lower() in ["automatic", "manual"] else "Automatic"
                lease_val = " ".join(parts[2:-1]) if len(parts) > 3 else parts[2]

                bindings.append(
                    DhcpBindingFact(
                        device=device,
                        ip_address=ip_val,
                        mac_address=mac_val,
                        lease_expiration=lease_val if lease_val else None,
                        binding_type=b_type,
                        source=FactSource.CISCO_EVIDENCE,
                    )
                )

        if len(bindings) == 0:
            if "none" in raw_output.lower() or len(lines) <= 2:
                status = AnalysisStatus.SUCCESS
                warnings.append("No active DHCP bindings found in table.")
            else:
                status = AnalysisStatus.FAILED
                warnings.append("Could not parse DHCP binding entries from output.")
        else:
            status = AnalysisStatus.SUCCESS

        facts = NormalizedNetworkFacts(
            dhcp_bindings=bindings,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show ip dhcp binding",
            facts=facts,
            warnings=warnings,
            extracted_count=len(bindings),
        )

    def _parse_dhcp_pool(self, device: str, raw_output: str) -> EvidenceParseResult:
        lines = clean_cisco_output(raw_output)
        pools: list[DhcpPoolFact] = []
        warnings: list[str] = []

        current_pool: dict = {}

        for line in lines:
            stripped = line.strip()

            # Pool POOL1 :
            pool_m = re.match(r"^Pool\s+([a-zA-Z0-9_\-]+)\s*:", stripped, re.IGNORECASE)
            if pool_m:
                if current_pool:
                    pools.append(DhcpPoolFact(device=device, **current_pool, source=FactSource.CISCO_EVIDENCE))
                current_pool = {"pool_name": pool_m.group(1)}
                continue

            # Total addresses : 254
            total_m = re.search(r"Total addresses\s*:\s*(\d+)", stripped, re.IGNORECASE)
            if total_m and current_pool:
                current_pool["total_addresses"] = int(total_m.group(1))

        if current_pool:
            pools.append(DhcpPoolFact(device=device, **current_pool, source=FactSource.CISCO_EVIDENCE))

        if len(pools) == 0:
            status = AnalysisStatus.FAILED
            warnings.append("No DHCP pool information could be parsed from output.")
        else:
            status = AnalysisStatus.SUCCESS

        facts = NormalizedNetworkFacts(
            dhcp_pools=pools,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show ip dhcp pool",
            facts=facts,
            warnings=warnings,
            extracted_count=len(pools),
        )
