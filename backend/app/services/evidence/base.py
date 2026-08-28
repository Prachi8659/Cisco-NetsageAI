import re
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field

from app.services.pkt.models import (
    AnalysisStatus,
    FactSource,
    NormalizedNetworkFacts,
)

class EvidenceParseResult(BaseModel):
    status: AnalysisStatus = AnalysisStatus.UNKNOWN
    source: FactSource = FactSource.CISCO_EVIDENCE
    command_type: str = "UNKNOWN"
    facts: NormalizedNetworkFacts = Field(default_factory=lambda: NormalizedNetworkFacts(source=FactSource.CISCO_EVIDENCE))
    warnings: list[str] = Field(default_factory=list)
    extracted_count: int = 0

def normalize_command_string(command: str) -> str:
    """Normalize whitespace and lowercase command string for flexible matching."""
    cleaned = re.sub(r"\s+", " ", command.strip().lower())
    # Remove leading prompt characters if user included prompt (e.g. "R1# show ip int br" -> "show ip int br")
    cleaned = re.sub(r"^[a-zA-Z0-9_\-\.\(\)]+[#>]\s*", "", cleaned)
    return cleaned

def clean_cisco_output(raw_output: str) -> list[str]:
    """Clean raw terminal output into usable non-empty lines without prompt artifacts."""
    lines: list[str] = []
    for line in raw_output.splitlines():
        # Strip trailing carriage returns and whitespace
        stripped = line.rstrip()
        if not stripped:
            continue
        # Skip terminal pager prompts like "--More--"
        if "--more--" in stripped.lower():
            continue
        lines.append(stripped)
    return lines

def normalize_interface_name(name: str) -> str:
    """Expand abbreviated Cisco interface names (e.g. Fa0/1 -> FastEthernet0/1, Gi0/0 -> GigabitEthernet0/0)."""
    n = name.strip()
    match = re.match(r"^([a-zA-Z]+)\s*(\d.*)$", n)
    if not match:
        return n
    prefix, num = match.groups()
    prefix_lower = prefix.lower()

    if prefix_lower in ["fa", "fas", "fast", "fastethernet"]:
        return f"FastEthernet{num}"
    if prefix_lower in ["gi", "gig", "gige", "gigabitethernet"]:
        return f"GigabitEthernet{num}"
    if prefix_lower in ["te", "tengig", "tengigabitethernet"]:
        return f"TenGigabitEthernet{num}"
    if prefix_lower in ["se", "ser", "serial"]:
        return f"Serial{num}"
    if prefix_lower in ["vl", "vlan"]:
        return f"Vlan{num}"
    if prefix_lower in ["lo", "loop", "loopback"]:
        return f"Loopback{num}"
    if prefix_lower in ["po", "port-channel"]:
        return f"Port-channel{num}"
    if prefix_lower in ["eth", "ethernet"]:
        return f"Ethernet{num}"
    return n

def is_valid_ipv4(ip: str) -> bool:
    """Check if string is a valid non-unassigned IPv4 address."""
    if not ip or ip.lower() in ["unassigned", "none", "0.0.0.0", "undefined"]:
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit() or not (0 <= int(p) <= 255):
            return False
    return True

class BaseEvidenceParser(ABC):
    @abstractmethod
    def can_parse(self, command: str) -> bool:
        """Return True if this parser supports the given Cisco command."""
        pass

    @abstractmethod
    def parse(self, device: str, command: str, raw_output: str) -> EvidenceParseResult:
        """Parse raw Cisco CLI output into normalized network facts."""
        pass
