import re
from app.services.evidence.base import (
    BaseEvidenceParser,
    EvidenceParseResult,
    normalize_command_string,
    clean_cisco_output,
)
from app.services.pkt.models import (
    AnalysisStatus,
    FactSource,
    AclFact,
    AclRule,
    NormalizedNetworkFacts,
)

class AclParser(BaseEvidenceParser):
    """
    Parses Cisco Access Control List commands:
    - show access-lists
    - show ip access-lists
    """

    def can_parse(self, command: str) -> bool:
        cmd = normalize_command_string(command)
        return bool(re.search(r"^(show|sh)\s+(ip\s+)?access-lists?(\s+.*)?$", cmd))

    def parse(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        lines = clean_cisco_output(raw_output)
        acls: list[AclFact] = []
        warnings: list[str] = []

        current_acl: dict = {}

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check header: e.g. "Standard IP access list 10" or "Extended IP access list 100"
            # or "Extended IP access list BLOCK_HTTP"
            header_m = re.match(
                r"^(Standard|Extended)\s+IP\s+access\s+list\s+([a-zA-Z0-9_\-]+)",
                stripped,
                re.IGNORECASE,
            )
            if header_m:
                if current_acl:
                    acls.append(self._build_acl_fact(device, current_acl))
                acl_kind, acl_id = header_m.groups()
                current_acl = {
                    "name": acl_id,
                    "type": f"{acl_kind.capitalize()}",
                    "rules": [],
                }
                continue

            # Rule lines:
            # e.g.: "    10 permit 192.168.1.0, wildcard bits 0.0.0.255 (15 matches)"
            # e.g.: "    20 deny any (3 matches)"
            # e.g.: "    permit tcp 192.168.1.0 0.0.0.255 any eq www"
            rule_m = re.match(
                r"^(?:\d+\s+)?(permit|deny|remark)\s+(.*)",
                stripped,
                re.IGNORECASE,
            )
            if rule_m and current_acl:
                act, body = rule_m.groups()
                # Check for match count
                matches = None
                match_m = re.search(r"\((\d+)\s+matches?\)", body)
                if match_m:
                    matches = int(match_m.group(1))
                    body = re.sub(r"\(\d+\s+matches?\)", "", body).strip()

                current_acl["rules"].append(
                    AclRule(
                        action=act.lower(),
                        source=body,
                        matches=matches,
                        raw_rule=stripped,
                    )
                )

        if current_acl:
            acls.append(self._build_acl_fact(device, current_acl))

        if len(acls) == 0:
            status = AnalysisStatus.FAILED
            warnings.append("No Access Lists could be parsed from output.")
        else:
            status = AnalysisStatus.SUCCESS

        facts = NormalizedNetworkFacts(
            acls=acls,
            source=FactSource.CISCO_EVIDENCE,
        )

        return EvidenceParseResult(
            status=status,
            source=FactSource.CISCO_EVIDENCE,
            command_type="show access-lists",
            facts=facts,
            warnings=warnings,
            extracted_count=len(acls),
        )

    def _build_acl_fact(self, device: str, d: dict) -> AclFact:
        return AclFact(
            device=device,
            acl_name_or_number=d["name"],
            acl_type=d["type"],
            rules=d.get("rules", []),
            source=FactSource.CISCO_EVIDENCE,
        )
