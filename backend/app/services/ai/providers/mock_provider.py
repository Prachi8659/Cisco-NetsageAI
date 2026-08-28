import json
import re
from typing import Any, Dict
from backend.app.services.ai.base import BaseAiProvider

class MockAiProvider(BaseAiProvider):
    """
    Deterministic Mock AI Provider for offline testing and development.
    Produces valid evidence-first JSON responses based on input facts.
    """

    def __init__(self, override_response: Dict[str, Any] | None = None):
        self.override_response = override_response

    def generate_diagnosis(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "mock-model",
        timeout: int = 30
    ) -> Dict[str, Any]:
        if self.override_response:
            return self.override_response

        # Parse user prompt to extract facts if JSON is embedded
        try:
            json_match = re.search(r'(\{[\s\S]*\})', user_prompt)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = {}
        except Exception:
            data = {}

        # Heuristic mock logic based on evidence in input
        py_findings = data.get("python_rule_engine_findings", [])
        cisco_evidence = data.get("cisco_show_evidence", [])
        pkt_facts = data.get("pkt_topology_facts", {})

        # Check for Interface Down in evidence
        has_admin_down = False
        target_dev = "PC0"
        target_intf = "FastEthernet0"

        for ev in cisco_evidence:
            raw = str(ev.get("raw_output", "")).upper()
            if "ADMIN" in raw and "DOWN" in raw:
                has_admin_down = True
                target_dev = ev.get("device", "PC0")
                break

        if not has_admin_down:
            for intf in pkt_facts.get("interfaces", []):
                st = str(intf.get("status", "")).upper()
                if "ADMIN" in st or "DOWN" in st:
                    has_admin_down = True
                    target_dev = intf.get("device", "PC0")
                    target_intf = intf.get("name", "FastEthernet0")
                    break

        if has_admin_down:
            return {
                "status": "SUCCESS",
                "root_cause": f"Interface {target_intf} on {target_dev} is administratively disabled ('shutdown'), preventing network frame transmission.",
                "fault_type": "Interface Down",
                "affected_device": target_dev,
                "affected_interface": target_intf,
                "evidence": [
                    f"Device {target_dev} interface {target_intf} status is ADMINISTRATIVELY_DOWN in show-command evidence.",
                    f"Line protocol is DOWN on physical connection segment."
                ],
                "explanation": f"When {target_dev} {target_intf} is administratively down, the physical and data link layers cannot establish carrier signal, isolating the device from the LAN.",
                "recommended_correction": f"Enter configuration mode on {target_dev}: 'interface {target_intf}' followed by 'no shutdown' in Cisco Packet Tracer.",
                "confidence": 95,
                "reasoning_summary": f"Direct observation of {target_dev} {target_intf} show ip interface brief demonstrates administrative shutdown state."
            }

        # Check for Duplicate IP across cisco_evidence, parsed_facts, pkt_facts, and python_findings
        ip_counts: Dict[str, list] = {}
        for intf in pkt_facts.get("interfaces", []):
            ip = intf.get("ip")
            if ip and ip.lower() not in ["none", "unassigned", "0.0.0.0"]:
                ip_counts.setdefault(ip, []).append(intf.get("device", "Host"))

        for ev in cisco_evidence:
            raw = str(ev.get("raw_output", ""))
            ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', raw)
            dev = ev.get("device", "Host")
            for ip in ips:
                if ip not in ["255.255.255.0", "0.0.0.0", "255.255.255.255"]:
                    ip_counts.setdefault(ip, []).append(dev)

        for f in py_findings:
            if f.get("rule_id") == "DUPLICATE_IP":
                ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', f.get("description", ""))
                if ip_match:
                    ip_counts.setdefault(ip_match.group(0), ["PC0", "PC1"])

        for ip, devs in ip_counts.items():
            if len(devs) > 1:
                devs_unique = sorted(list(set(devs)))
                devs_str = ", ".join(devs_unique) if devs_unique else "Multiple Hosts"
                return {
                    "status": "SUCCESS",
                    "root_cause": f"Duplicate IP address conflict detected on {ip} across {devs_str}.",
                    "fault_type": "Duplicate IP",
                    "affected_device": devs_str,
                    "affected_interface": "FastEthernet0",
                    "evidence": [
                        f"IPv4 address {ip} is concurrently assigned to multiple interfaces ({devs_str}) in collected evidence."
                    ],
                    "explanation": "Duplicate IP assignments cause ARP cache poisoning and intermittent packet drops on the local broadcast domain.",
                    "recommended_correction": f"Assign a unique, unused IPv4 address in the local subnet to one of the conflicting devices ({devs_str}) in Cisco Packet Tracer.",
                    "confidence": 98,
                    "reasoning_summary": f"Evidence verifies IP {ip} collision across multiple endpoint nodes ({devs_str})."
                }

        # Check for Gateway Mismatch
        for gw in pkt_facts.get("gateways", []):
            gw_ip = gw.get("gateway_ip")
            if gw_ip and gw_ip == "192.168.2.1":
                return {
                    "status": "SUCCESS",
                    "root_cause": f"Default gateway {gw_ip} is configured outside the local host subnet (192.168.1.0/24).",
                    "fault_type": "Gateway Mismatch",
                    "affected_device": gw.get("device", "PC0"),
                    "affected_interface": "FastEthernet0",
                    "evidence": [
                        f"Configured IP is 192.168.1.50/24 while configured default gateway is {gw_ip}."
                    ],
                    "explanation": "A host cannot route off-subnet traffic if its default gateway address does not share the same local subnet prefix.",
                    "recommended_correction": f"Change the default gateway on {gw.get('device', 'PC0')} to a valid router interface IP within the 192.168.1.0/24 subnet.",
                    "confidence": 96,
                    "reasoning_summary": "Subnet prefix comparison shows numerical mismatch between local interface subnet mask and default gateway IP."
                }

        if not pkt_facts.get("devices") and not cisco_evidence:
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "root_cause": None,
                "fault_type": None,
                "affected_device": None,
                "affected_interface": None,
                "evidence": [],
                "explanation": "No network facts or Cisco show-command evidence have been uploaded for this case.",
                "recommended_correction": "Please attach a .pkt file or paste Cisco CLI show command output to provide necessary troubleshooting context.",
                "confidence": 0,
                "reasoning_summary": "Missing network topology facts and CLI diagnostic outputs."
            }

        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "root_cause": "Unable to definitively isolate root cause from available facts.",
            "fault_type": "Other",
            "affected_device": None,
            "affected_interface": None,
            "evidence": ["No explicit fault markers detected in available evidence."],
            "explanation": "The available evidence does not reveal an obvious IP configuration or interface status error.",
            "recommended_correction": "Collect additional show commands such as 'show ip route' or 'show running-config' from the devices.",
            "confidence": 30,
            "reasoning_summary": "Available evidence shows normal operational status for captured interfaces."
        }
