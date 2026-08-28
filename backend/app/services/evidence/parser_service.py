import re
from typing import List

from backend.app.services.evidence.base import (
    BaseEvidenceParser,
    EvidenceParseResult,
    normalize_command_string,
)
from backend.app.services.evidence.interface_parser import InterfaceParser
from backend.app.services.evidence.route_parser import RouteParser
from backend.app.services.evidence.vlan_parser import VlanParser
from backend.app.services.evidence.trunk_parser import TrunkParser
from backend.app.services.evidence.running_config_parser import RunningConfigParser
from backend.app.services.evidence.acl_parser import AclParser
from backend.app.services.evidence.dhcp_parser import DhcpParser
from backend.app.services.evidence.mac_parser import MacParser
from backend.app.services.pkt.models import (
    AnalysisStatus,
    FactSource,
    NormalizedNetworkFacts,
)

class EvidenceParserService:
    """
    Modular Evidence Parser Service for Cisco Show-Commands.
    Routes commands to specialized parsers and returns normalized network facts with zero fabrication.
    """

    def __init__(self):
        self.parsers: List[BaseEvidenceParser] = [
            InterfaceParser(),
            RouteParser(),
            VlanParser(),
            TrunkParser(),
            RunningConfigParser(),
            AclParser(),
            DhcpParser(),
            MacParser(),
        ]

    def parse_evidence(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        if not device or not device.strip():
            return EvidenceParseResult(
                status=AnalysisStatus.FAILED,
                source=FactSource.CISCO_EVIDENCE,
                command_type=command,
                warnings=["Device name is required to associate evidence."],
            )

        if not command or not command.strip():
            return EvidenceParseResult(
                status=AnalysisStatus.FAILED,
                source=FactSource.CISCO_EVIDENCE,
                command_type="UNKNOWN",
                warnings=["Cisco command string cannot be empty."],
            )

        if not raw_output or not raw_output.strip():
            return EvidenceParseResult(
                status=AnalysisStatus.FAILED,
                source=FactSource.CISCO_EVIDENCE,
                command_type=command,
                warnings=["Raw Cisco command output is empty."],
            )

        clean_cmd = normalize_command_string(command)

        # Dispatch to matching parser
        for parser in self.parsers:
            if parser.can_parse(clean_cmd):
                try:
                    return parser.parse(device=device.strip(), command=clean_cmd, raw_output=raw_output)
                except Exception as e:
                    return EvidenceParseResult(
                        status=AnalysisStatus.FAILED,
                        source=FactSource.CISCO_EVIDENCE,
                        command_type=clean_cmd,
                        warnings=[f"Parser internal error during execution: {str(e)}"],
                    )

        # No matching parser found
        return EvidenceParseResult(
            status=AnalysisStatus.UNKNOWN,
            source=FactSource.CISCO_EVIDENCE,
            command_type=clean_cmd,
            warnings=[
                f"Command '{command}' is currently unsupported by the deterministic evidence parser.",
                "Raw output has been preserved for manual inspection.",
            ],
        )


evidence_parser_service = EvidenceParserService()
