from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.case import Case
from app.models.pkt import PktFile
from app.models.evidence import CiscoEvidence
from app.services.pkt.analyzer import pkt_analyzer_service
from app.services.pkt.models import (
    NormalizedNetworkFacts,
    FactSource,
    DeviceFact,
    InterfaceFact,
    ConnectionFact,
    VlanFact,
    RouteFact,
    GatewayFact,
    TrunkFact,
    AclFact,
    DhcpBindingFact,
    DhcpPoolFact,
    MacEntryFact,
)
from app.services.rules.base import BaseRule
from app.services.rules.models import RuleFinding, RuleEngineResult, RuleStatus
from app.services.rules.duplicate_ip import DuplicateIpRule
from app.services.rules.subnet_mask import SubnetMaskRule
from app.services.rules.gateway import GatewayMismatchRule
from app.services.rules.interface import InterfaceDownRule
from app.services.rules.vlan import MissingVlanRule
from app.services.rules.route import MissingRouteRule
from app.services.rules.connection import ConnectionInconsistencyRule

class RuleEngine:
    """
    Deterministic Python Fault Detection Rule Engine for NetSage AI.
    Runs 7 independent, verifiable networking rules over combined normalized facts.
    """

    def __init__(self):
        self.rules: List[BaseRule] = [
            DuplicateIpRule(),
            SubnetMaskRule(),
            GatewayMismatchRule(),
            InterfaceDownRule(),
            MissingVlanRule(),
            MissingRouteRule(),
            ConnectionInconsistencyRule(),
        ]

    def aggregate_case_facts(self, case_id: int, db: Session) -> NormalizedNetworkFacts:
        """
        Aggregate normalized facts from both:
        1. .pkt topology analysis (PKT_EXTRACTED)
        2. Stored Cisco show-command evidence (CISCO_EVIDENCE)
        """
        combined_devices: Dict[str, DeviceFact] = {}
        combined_interfaces: Dict[tuple, InterfaceFact] = {}
        combined_connections: List[ConnectionFact] = []
        combined_vlans: Dict[int, VlanFact] = {}
        combined_routes: List[RouteFact] = []
        combined_gateways: Dict[str, GatewayFact] = {}
        combined_trunks: List[TrunkFact] = []
        combined_acls: List[AclFact] = []
        combined_dhcp_bindings: List[DhcpBindingFact] = []
        combined_dhcp_pools: List[DhcpPoolFact] = []
        combined_mac_entries: List[MacEntryFact] = []

        # 1. Load .pkt analysis facts if PKT file exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if case and case.pkt_file:
            try:
                pkt_analysis = pkt_analyzer_service.analyze_case_pkt(case_id=case_id, db=db)
                if pkt_analysis and pkt_analysis.facts:
                    for d in pkt_analysis.facts.devices:
                        combined_devices[d.name.lower()] = d
                    for i in pkt_analysis.facts.interfaces:
                        combined_interfaces[(i.device.lower(), i.name.lower())] = i
                    for c in pkt_analysis.facts.connections:
                        combined_connections.append(c)
                    for v in pkt_analysis.facts.vlans:
                        combined_vlans[v.vlan_id] = v
                    for r in pkt_analysis.facts.routes:
                        combined_routes.append(r)
                    for g in pkt_analysis.facts.gateways:
                        combined_gateways[g.device.lower()] = g
            except Exception:
                pass  # Continue if PKT analysis fails or is unavailable

        # 2. Load Cisco show-command evidence facts
        evidence_list = db.query(CiscoEvidence).filter(CiscoEvidence.case_id == case_id).all()
        for ev in evidence_list:
            if not ev.parsed_facts or not isinstance(ev.parsed_facts, dict):
                continue
            p = ev.parsed_facts

            # Devices
            for d_data in p.get("devices", []):
                try:
                    df = DeviceFact(**d_data)
                    combined_devices[df.name.lower()] = df
                except Exception:
                    pass

            # Interfaces (Cisco evidence can supplement or update operational status)
            for i_data in p.get("interfaces", []):
                try:
                    intf_fact = InterfaceFact(**i_data)
                    key = (intf_fact.device.lower(), intf_fact.name.lower())
                    if key in combined_interfaces:
                        # Merge: Preserve connection info from PKT while updating IP/status/duplex from Cisco CLI
                        existing = combined_interfaces[key]
                        merged_ip = intf_fact.ip or existing.ip
                        merged_mask = intf_fact.mask or existing.mask
                        merged_vlan = intf_fact.vlan_id if intf_fact.vlan_id is not None else existing.vlan_id
                        merged_status = intf_fact.status if intf_fact.status != "UNKNOWN" else existing.status
                        merged_proto = intf_fact.protocol if intf_fact.protocol != "UNKNOWN" else existing.protocol
                        merged_conn = existing.is_connected or intf_fact.is_connected
                        combined_interfaces[key] = InterfaceFact(
                            device=intf_fact.device,
                            name=intf_fact.name,
                            ip=merged_ip,
                            mask=merged_mask,
                            status=merged_status,
                            protocol=merged_proto,
                            vlan_id=merged_vlan,
                            mac_address=intf_fact.mac_address or existing.mac_address,
                            is_connected=merged_conn,
                            duplex=intf_fact.duplex or existing.duplex,
                            speed=intf_fact.speed or existing.speed,
                            mtu=intf_fact.mtu or existing.mtu,
                            bandwidth_kbps=intf_fact.bandwidth_kbps or existing.bandwidth_kbps,
                            source=FactSource.CISCO_EVIDENCE,
                        )
                    else:
                        combined_interfaces[key] = intf_fact
                except Exception:
                    pass

            # VLANs
            for v_data in p.get("vlans", []):
                try:
                    vf = VlanFact(**v_data)
                    combined_vlans[vf.vlan_id] = vf
                except Exception:
                    pass

            # Routes
            for r_data in p.get("routes", []):
                try:
                    rf = RouteFact(**r_data)
                    combined_routes.append(rf)
                except Exception:
                    pass

            # Gateways
            for g_data in p.get("gateways", []):
                try:
                    gf = GatewayFact(**g_data)
                    combined_gateways[gf.device.lower()] = gf
                except Exception:
                    pass

            # Trunks
            for t_data in p.get("trunks", []):
                try:
                    combined_trunks.append(TrunkFact(**t_data))
                except Exception:
                    pass

            # ACLs
            for a_data in p.get("acls", []):
                try:
                    combined_acls.append(AclFact(**a_data))
                except Exception:
                    pass

            # DHCP Bindings
            for db_data in p.get("dhcp_bindings", []):
                try:
                    combined_dhcp_bindings.append(DhcpBindingFact(**db_data))
                except Exception:
                    pass

            # DHCP Pools
            for dp_data in p.get("dhcp_pools", []):
                try:
                    combined_dhcp_pools.append(DhcpPoolFact(**dp_data))
                except Exception:
                    pass

            # MAC entries
            for m_data in p.get("mac_entries", []):
                try:
                    combined_mac_entries.append(MacEntryFact(**m_data))
                except Exception:
                    pass

        return NormalizedNetworkFacts(
            devices=list(combined_devices.values()),
            interfaces=list(combined_interfaces.values()),
            connections=combined_connections,
            vlans=list(combined_vlans.values()),
            routes=combined_routes,
            gateways=list(combined_gateways.values()),
            trunks=combined_trunks,
            acls=combined_acls,
            dhcp_bindings=combined_dhcp_bindings,
            dhcp_pools=combined_dhcp_pools,
            mac_entries=combined_mac_entries,
            source=FactSource.PYTHON_RULE,
        )

    def evaluate_facts(self, case_id: int, facts: NormalizedNetworkFacts) -> RuleEngineResult:
        """Evaluate all 7 deterministic rules against normalized network facts."""
        faults_detected: List[RuleFinding] = []
        insufficient_evidence: List[RuleFinding] = []
        no_fault_rules: List[str] = []

        for rule in self.rules:
            findings = rule.evaluate(facts)
            rule_has_fault = False

            for f in findings:
                if f.status == RuleStatus.DETECTED:
                    faults_detected.append(f)
                    rule_has_fault = True
                elif f.status == RuleStatus.INSUFFICIENT_EVIDENCE:
                    insufficient_evidence.append(f)

            if not rule_has_fault and not any(f.rule_id == rule.rule_id for f in insufficient_evidence):
                no_fault_rules.append(rule.rule_id)

        # Build human-friendly summary
        if faults_detected:
            summary = f"Detected {len(faults_detected)} networking fault{'s' if len(faults_detected) != 1 else ''} across {len(self.rules)} evaluated rules."
        elif not facts.devices and not facts.interfaces:
            summary = "No network facts available for analysis. Please upload a .pkt file or add Cisco show-command evidence."
        else:
            summary = "No faults detected from the available network facts."

        return RuleEngineResult(
            case_id=case_id,
            total_rules_evaluated=len(self.rules),
            faults_detected=faults_detected,
            insufficient_evidence=insufficient_evidence,
            no_fault_rules=no_fault_rules,
            summary=summary,
        )

    def diagnose_case(self, case_id: int, db: Session) -> RuleEngineResult:
        """Load, aggregate facts, and run the complete rule engine for a case."""
        facts = self.aggregate_case_facts(case_id=case_id, db=db)
        return self.evaluate_facts(case_id=case_id, facts=facts)


rule_engine = RuleEngine()
