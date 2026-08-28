from abc import ABC, abstractmethod
import ipaddress
from typing import List, Optional, Tuple
from backend.app.services.pkt.models import NormalizedNetworkFacts
from backend.app.services.rules.models import RuleFinding

def ip_in_network(ip_str: str, network_str: str, mask_str: Optional[str] = None) -> bool:
    """Check if an IP address belongs to a specific network/mask."""
    try:
        if "/" in network_str:
            net = ipaddress.IPv4Network(network_str, strict=False)
        elif mask_str:
            net = ipaddress.IPv4Network(f"{network_str}/{mask_str}", strict=False)
        else:
            return False
        ip = ipaddress.IPv4Address(ip_str)
        return ip in net
    except Exception:
        return False

def same_subnet(ip1_str: str, ip2_str: str, mask_str: str) -> bool:
    """Check if two IP addresses reside within the same subnet under a given mask."""
    try:
        ip1 = ipaddress.IPv4Address(ip1_str)
        ip2 = ipaddress.IPv4Address(ip2_str)
        mask = ipaddress.IPv4Address(mask_str)
        return (int(ip1) & int(mask)) == (int(ip2) & int(mask))
    except Exception:
        return False

def get_network_address(ip_str: str, mask_str: str) -> Optional[str]:
    """Calculate network CIDR notation string from IP and mask."""
    try:
        net = ipaddress.IPv4Network(f"{ip_str}/{mask_str}", strict=False)
        return str(net)
    except Exception:
        return None

class BaseRule(ABC):
    rule_id: str = "BASE_RULE"
    fault_type: str = "Base Fault"

    @abstractmethod
    def evaluate(self, facts: NormalizedNetworkFacts) -> List[RuleFinding]:
        """
        Evaluate normalized facts and return a list of findings.
        If no fault is found, returns an empty list.
        If facts are insufficient to verify, may return finding with status=INSUFFICIENT_EVIDENCE.
        """
        pass
