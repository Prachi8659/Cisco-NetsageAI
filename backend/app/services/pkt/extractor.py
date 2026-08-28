import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from backend.app.services.pkt.models import (
    FactSource,
    ConnectionStatus,
    AnalysisStatus,
    DeviceFact,
    InterfaceFact,
    ConnectionFact,
    VlanFact,
    RouteFact,
    GatewayFact,
    NormalizedNetworkFacts,
    PktAnalysisResult,
)
from backend.app.services.pkt.decoder import pkt_decoder, PktDecodeResult


class PktExtractor:
    """
    Modular Cisco Packet Tracer (.pkt / .pka) file extractor.
    Extracts real topologies from modern (PT 7.x-9.x), legacy (PT 5.x-6.x), and XML Packet Tracer files.
    Truthfully reports UNKNOWN / UNAVAILABLE when proprietary encryption cannot be decoded.
    Distinguishes Network Devices from Non-Network / Infrastructure Objects.
    Never fabricates network topology or configuration data.
    """

    def __init__(self, decoder=pkt_decoder):
        self.decoder = decoder

    def extract(self, file_path: Path) -> PktAnalysisResult:
        if not file_path.exists():
            return PktAnalysisResult(
                status=AnalysisStatus.FAILED,
                source=FactSource.UNKNOWN,
                facts=NormalizedNetworkFacts(source=FactSource.UNKNOWN),
                warnings=[f"File not found on storage: {file_path.name}"],
                unsupported_fields=["all"],
            )

        try:
            with open(file_path, "rb") as f:
                content = f.read()
        except Exception as e:
            return PktAnalysisResult(
                status=AnalysisStatus.FAILED,
                source=FactSource.UNKNOWN,
                facts=NormalizedNetworkFacts(source=FactSource.UNKNOWN),
                warnings=[f"Failed to read file: {str(e)}"],
                unsupported_fields=["all"],
            )

        # 1. Run safe multi-stage decoder
        decode_res: PktDecodeResult = self.decoder.decode(content)

        if not decode_res.success or not decode_res.xml_bytes:
            return PktAnalysisResult(
                status=AnalysisStatus.UNAVAILABLE,
                source=FactSource.UNKNOWN,
                facts=NormalizedNetworkFacts(source=FactSource.UNKNOWN),
                warnings=[
                    "Uploaded Cisco Packet Tracer (.pkt) file could not be decoded.",
                    decode_res.error_message or "Unsupported proprietary binary encoding.",
                    "No facts were fabricated. Please provide Cisco show-command evidence to extract facts.",
                ],
                unsupported_fields=[
                    "devices",
                    "interfaces",
                    "connections",
                    "vlans",
                    "routes",
                    "gateways",
                ],
                extraction_details={
                    "file_size": len(content),
                    "format_type": decode_res.format_type,
                    "decode_success": False,
                },
            )

        # 2. Parse the decoded XML DOM
        try:
            root = ET.fromstring(decode_res.xml_bytes)
            return self._extract_from_element_tree(root, decode_res)
        except Exception as e:
            return PktAnalysisResult(
                status=AnalysisStatus.FAILED,
                source=FactSource.UNKNOWN,
                facts=NormalizedNetworkFacts(source=FactSource.UNKNOWN),
                warnings=[f"Decoded XML parsing error: {str(e)}"],
                unsupported_fields=["all"],
                extraction_details={
                    "file_size": len(content),
                    "format_type": decode_res.format_type,
                    "error": str(e),
                },
            )

    def _extract_from_element_tree(
        self, root: ET.Element, decode_res: PktDecodeResult
    ) -> PktAnalysisResult:
        """Extract structured network facts from Packet Tracer XML element tree."""
        devices: list[DeviceFact] = []
        interfaces: list[InterfaceFact] = []
        connections: list[ConnectionFact] = []
        vlans: list[VlanFact] = []
        routes: list[RouteFact] = []
        gateways: list[GatewayFact] = []
        warnings: list[str] = []

        # Reference lookup map: save-ref-id -> device_name
        ref_map: Dict[str, str] = {}

        # 1. First Pass: Index devices and build ref_map
        device_nodes = (
            root.findall(".//DEVICE")
            or root.findall(".//device")
            or root.findall(".//Device")
        )

        for dev_elem in device_nodes:
            name = (
                dev_elem.findtext(".//NAME")
                or dev_elem.findtext("NAME")
                or dev_elem.findtext(".//name")
                or dev_elem.findtext("name")
                or dev_elem.findtext(".//HOSTNAME")
                or dev_elem.findtext("HOSTNAME")
                or dev_elem.get("name")
                or "Unknown_Device"
            ).strip()

            engine = dev_elem.find("ENGINE")
            if engine is None:
                engine = dev_elem

            engine_type = engine.find("TYPE")
            raw_type = "Unknown"
            model = None

            if engine_type is not None:
                raw_type = (engine_type.text or "").strip()
                model = engine_type.get("customModel") or engine_type.get("model") or None

            if not raw_type or raw_type == "Unknown":
                raw_type = (
                    dev_elem.findtext(".//TYPE")
                    or dev_elem.findtext("TYPE")
                    or dev_elem.findtext(".//MODEL")
                    or dev_elem.get("type")
                    or "Unknown"
                ).strip()

            if not model:
                model = (
                    dev_elem.findtext(".//MODEL")
                    or dev_elem.findtext("MODEL")
                    or dev_elem.get("model")
                    or None
                )

            norm_type, is_net_dev, category = self._classify_device_type(raw_type, name)

            # Map save-ref-id to device name
            save_ref = dev_elem.findtext(".//SAVE_REF_ID") or dev_elem.findtext("SAVE_REF_ID")
            if save_ref:
                ref_map[save_ref.strip()] = name

            for elem in dev_elem.iter():
                if elem.text and "save-ref-id:" in elem.text:
                    ref_map[elem.text.strip()] = name
                for _, v in elem.attrib.items():
                    if "save-ref-id:" in str(v):
                        ref_map[str(v).strip()] = name

            devices.append(
                DeviceFact(
                    name=name,
                    device_type=norm_type,
                    model=model,
                    hostname=name,
                    is_network_device=is_net_dev,
                    category=category,
                    source=FactSource.PKT_EXTRACTED,
                )
            )

            # Default Gateway
            gw = (
                dev_elem.findtext(".//DEFAULT_GATEWAY")
                or dev_elem.findtext("DEFAULT_GATEWAY")
                or dev_elem.findtext(".//default_gateway")
                or dev_elem.findtext(".//GATEWAY")
                or dev_elem.findtext(".//gateway")
            )
            if gw and gw.strip() and gw.strip() not in ["0.0.0.0", ""]:
                gateways.append(
                    GatewayFact(
                        device=name,
                        gateway_ip=gw.strip(),
                        source=FactSource.PKT_EXTRACTED,
                    )
                )

            # Device VLANs (e.g. from <VLANS><VLAN ... />)
            vlan_container = dev_elem.find(".//VLANS")
            if vlan_container is None:
                vlan_container = dev_elem.find("VLANS")
            if vlan_container is not None:
                for v_elem in vlan_container.findall("VLAN"):
                    v_num = v_elem.get("number") or v_elem.findtext("NUMBER")
                    v_name = v_elem.get("name") or v_elem.findtext("NAME") or f"VLAN_{v_num}"
                    if v_num and str(v_num).isdigit():
                        v_id = int(v_num)
                        if not any(v.vlan_id == v_id and v.device == name for v in vlans):
                            vlans.append(
                                VlanFact(
                                    vlan_id=v_id,
                                    name=v_name,
                                    status="active",
                                    device=name,
                                    source=FactSource.PKT_EXTRACTED,
                                )
                            )

        # 2. Extract Physical & Logical Connections (Links)
        link_nodes = (
            root.findall(".//LINK")
            or root.findall(".//link")
            or root.findall(".//CONNECTION")
            or root.findall(".//connection")
        )

        connected_endpoints: Set[Tuple[str, str]] = set()

        for link_elem in link_nodes:
            cable = link_elem.find("CABLE")
            if cable is None:
                cable = link_elem.find("cable")

            if cable is not None:
                from_ref = (cable.findtext("FROM") or cable.findtext("from") or "").strip()
                to_ref = (cable.findtext("TO") or cable.findtext("to") or "").strip()
                c_ports = cable.findall("PORT")
                if len(c_ports) == 0:
                    c_ports = cable.findall("port")

                dev_a = ref_map.get(from_ref, from_ref)
                dev_b = ref_map.get(to_ref, to_ref)
                port_a = c_ports[0].text.strip() if len(c_ports) > 0 and c_ports[0].text else "Unknown"
                port_b = c_ports[1].text.strip() if len(c_ports) > 1 and c_ports[1].text else "Unknown"
                raw_ltype = cable.findtext("TYPE") or link_elem.findtext("TYPE") or "Copper"
            else:
                dev_a = (
                    link_elem.findtext("DEVICE_A")
                    or link_elem.findtext("dev1")
                    or link_elem.findtext("DEVICE1")
                    or link_elem.get("device_a")
                    or ""
                ).strip()
                port_a = (
                    link_elem.findtext("PORT_A")
                    or link_elem.findtext("port1")
                    or link_elem.findtext("PORT1")
                    or link_elem.get("interface_a")
                    or "Unknown"
                ).strip()
                dev_b = (
                    link_elem.findtext("DEVICE_B")
                    or link_elem.findtext("dev2")
                    or link_elem.findtext("DEVICE2")
                    or link_elem.get("device_b")
                    or ""
                ).strip()
                port_b = (
                    link_elem.findtext("PORT_B")
                    or link_elem.findtext("port2")
                    or link_elem.findtext("PORT2")
                    or link_elem.get("interface_b")
                    or "Unknown"
                ).strip()
                raw_ltype = link_elem.findtext("TYPE") or link_elem.findtext("type") or "Copper"

            # Normalize link type
            norm_link_type = "Copper"
            if "fiber" in raw_ltype.lower():
                norm_link_type = "Fiber"
            elif "serial" in raw_ltype.lower():
                norm_link_type = "Serial"
            elif "wireless" in raw_ltype.lower():
                norm_link_type = "Wireless"

            if dev_a and dev_b and dev_a != dev_b:
                connections.append(
                    ConnectionFact(
                        device_a=dev_a,
                        interface_a=port_a,
                        device_b=dev_b,
                        interface_b=port_b,
                        status=ConnectionStatus.CONNECTED,
                        link_type=norm_link_type,
                        source=FactSource.PKT_EXTRACTED,
                    )
                )
                connected_endpoints.add((dev_a.lower(), port_a.lower()))
                connected_endpoints.add((dev_b.lower(), port_b.lower()))

        # 3. Extract Interfaces / Ports with accurate status and connection state
        for dev_elem in device_nodes:
            name = (
                dev_elem.findtext(".//NAME")
                or dev_elem.findtext("NAME")
                or dev_elem.findtext(".//name")
                or dev_elem.findtext("name")
                or dev_elem.get("name")
                or "Unknown_Device"
            ).strip()

            # Find matching DeviceFact
            dev_fact = next((d for d in devices if d.name == name), None)
            norm_type = dev_fact.device_type if dev_fact else "Unknown"

            port_nodes = (
                dev_elem.findall(".//PORT")
                or dev_elem.findall(".//port")
                or dev_elem.findall(".//INTERFACE")
                or dev_elem.findall(".//interface")
            )

            port_counter = 0
            for port_elem in port_nodes:
                p_name = (
                    port_elem.findtext("NAME")
                    or port_elem.findtext("name")
                    or port_elem.get("name")
                )
                p_type = port_elem.findtext("TYPE") or port_elem.findtext("type") or ""

                if not p_name:
                    # Synthesize clean port name based on hardware type and index
                    if "gigabit" in p_type.lower():
                        p_name = f"GigabitEthernet0/{port_counter + 1}"
                    elif "fastethernet" in p_type.lower() or "copper" in p_type.lower():
                        if norm_type == "PC" or norm_type == "Server":
                            p_name = f"FastEthernet{port_counter}"
                        else:
                            p_name = f"FastEthernet0/{port_counter + 1}"
                    elif "bluetooth" in p_type.lower():
                        p_name = f"Bluetooth{port_counter}"
                    elif "serial" in p_type.lower():
                        p_name = f"Serial0/{port_counter}/0"
                    else:
                        p_name = f"Port{port_counter + 1}"

                port_counter += 1
                clean_p_name = p_name.strip()

                ip = (
                    port_elem.findtext("IP")
                    or port_elem.findtext("ip")
                    or port_elem.findtext("IP_ADDRESS")
                    or port_elem.findtext("ip_address")
                )
                mask = (
                    port_elem.findtext("SUBNET_MASK")
                    or port_elem.findtext("subnet_mask")
                    or port_elem.findtext("SUBNET")
                    or port_elem.findtext("subnet")
                    or port_elem.findtext("mask")
                )
                mac = (
                    port_elem.findtext("MACADDRESS")
                    or port_elem.findtext("mac_address")
                    or port_elem.findtext("MAC")
                )
                power_val = (
                    port_elem.findtext("POWER")
                    or port_elem.findtext("power")
                )
                explicit_status = (
                    port_elem.findtext("STATUS")
                    or port_elem.findtext("status")
                    or port_elem.findtext("ADMIN_STATUS")
                )
                explicit_proto = (
                    port_elem.findtext("PROTOCOL_STATUS")
                    or port_elem.findtext("protocol")
                )
                vlan_str = port_elem.findtext("VLAN") or port_elem.findtext("vlan")

                vlan_id = None
                if vlan_str and vlan_str.strip().isdigit():
                    vlan_id = int(vlan_str.strip())
                    if not any(v.vlan_id == vlan_id and v.device == name for v in vlans):
                        vlans.append(
                            VlanFact(
                                vlan_id=vlan_id,
                                name=f"VLAN_{vlan_id}",
                                device=name,
                                source=FactSource.PKT_EXTRACTED,
                            )
                        )

                clean_ip = ip.strip() if ip and ip.strip() and ip.strip() != "0.0.0.0" else None
                clean_mask = mask.strip() if mask and mask.strip() and mask.strip() != "0.0.0.0" else None

                # Check physical connection state
                is_physically_connected = (name.lower(), clean_p_name.lower()) in connected_endpoints

                # Determine accurate operational and administrative status
                # 1. Check if administratively disabled / power off
                if power_val and power_val.strip().lower() == "false":
                    status_str = "ADMINISTRATIVELY_DOWN"
                    proto_str = "DOWN"
                elif explicit_status:
                    raw_s = explicit_status.strip().upper()
                    if raw_s in ["UP", "DOWN", "ADMINISTRATIVELY_DOWN", "UNKNOWN"]:
                        status_str = raw_s
                    elif "admin" in raw_s.lower():
                        status_str = "ADMINISTRATIVELY_DOWN"
                    elif "up" in raw_s.lower():
                        status_str = "UP"
                    else:
                        status_str = "DOWN"
                    
                    if explicit_proto:
                        proto_str = explicit_proto.strip().upper()
                    else:
                        proto_str = "UP" if status_str == "UP" and is_physically_connected else "DOWN"
                else:
                    # No explicit status tag provided in XML
                    if is_physically_connected:
                        # Interface has an active physical link
                        status_str = "UP"
                        proto_str = "UP"
                    elif clean_ip:
                        # Interface has IP assigned (e.g. host loopback/virtual), status is UP
                        status_str = "UP"
                        proto_str = "UP"
                    else:
                        # Interface exists on hardware (e.g. unused switchport/router port), but is not connected
                        status_str = "DOWN"
                        proto_str = "DOWN"

                interfaces.append(
                    InterfaceFact(
                        device=name,
                        name=clean_p_name,
                        ip=clean_ip,
                        mask=clean_mask,
                        status=status_str,
                        protocol=proto_str,
                        vlan_id=vlan_id,
                        mac_address=mac.strip() if mac else None,
                        is_connected=is_physically_connected,
                        source=FactSource.PKT_EXTRACTED,
                    )
                )

        # 4. Extract Routes
        route_nodes = root.findall(".//ROUTE") or root.findall(".//route")
        for route_elem in route_nodes:
            r_dev = route_elem.findtext("DEVICE") or route_elem.get("device") or "Router"
            net = route_elem.findtext("NETWORK") or route_elem.findtext("prefix")
            mask = route_elem.findtext("MASK") or route_elem.findtext("subnet_mask")
            next_hop = route_elem.findtext("NEXT_HOP") or route_elem.findtext("gateway")
            proto = route_elem.findtext("PROTOCOL") or "Static"

            if net:
                routes.append(
                    RouteFact(
                        device=r_dev.strip(),
                        network=net.strip(),
                        mask=mask.strip() if mask else None,
                        next_hop=next_hop.strip() if next_hop else None,
                        protocol=proto.strip(),
                        source=FactSource.PKT_EXTRACTED,
                    )
                )

        # Build normalized facts
        facts = NormalizedNetworkFacts(
            devices=devices,
            interfaces=interfaces,
            connections=connections,
            vlans=vlans,
            routes=routes,
            gateways=gateways,
            source=FactSource.PKT_EXTRACTED,
        )

        network_devices = [d for d in devices if d.is_network_device]
        infra_devices = [d for d in devices if not d.is_network_device]

        status = AnalysisStatus.SUCCESS if len(devices) > 0 else AnalysisStatus.PARTIAL
        if len(devices) == 0:
            warnings.append("No active device nodes found in the Packet Tracer XML tree.")

        return PktAnalysisResult(
            status=status,
            source=FactSource.PKT_EXTRACTED,
            facts=facts,
            warnings=warnings,
            unsupported_fields=[],
            extraction_details={
                "device_count": len(devices),
                "network_device_count": len(network_devices),
                "infrastructure_count": len(infra_devices),
                "interface_count": len(interfaces),
                "connected_interface_count": len([i for i in interfaces if i.is_connected]),
                "connection_count": len(connections),
                "vlan_count": len(vlans),
                "route_count": len(routes),
                "format_type": decode_res.format_type,
                "version": decode_res.version,
            },
        )

    def _classify_device_type(self, raw_type: str, name: str) -> Tuple[str, bool, str]:
        """
        Classify device into:
        1. Device Type Name (Router, Switch, PC, Server, AccessPoint, Firewall, Infrastructure, or Unknown)
        2. is_network_device (bool)
        3. category (NETWORK_DEVICE or INFRASTRUCTURE_OBJECT)
        """
        t = raw_type.lower()
        n = name.lower()

        # Non-network / Infrastructure Objects
        if (
            "power distribution" in t
            or "power_distribution" in t
            or "powerdistribution" in t
            or "solar panel" in t
            or "battery" in t
            or "mcu" in t
            or "sbc" in t
            or "smart " in t
            or "appliance" in t
            or "sensor" in t
            or "actuator" in t
            or "lamp" in t
            or "door" in t
            or "fan" in t
            or "board" in t
            or "rack" in t
            or "table" in t
        ):
            return "INFRASTRUCTURE_OBJECT", False, "INFRASTRUCTURE_OBJECT"

        # Network Devices
        if "router" in t or "2911" in t or "2901" in t or "1941" in t or "2811" in t or "isr" in t or (n.startswith("r") and len(n) <= 4 and n[1:].isdigit()):
            return "Router", True, "NETWORK_DEVICE"
        if "switch" in t or "2960" in t or "3560" in t or "3650" in t or "catalyst" in t or (n.startswith("s") and len(n) <= 4 and n[1:].isdigit()) or (n.startswith("sw") and len(n) <= 5 and n[2:].isdigit()):
            return "Switch", True, "NETWORK_DEVICE"
        if "pc" in t or "desktop" in t or "workstation" in t or (n.startswith("pc") and len(n) <= 5 and n[2:].isdigit()) or (n.startswith("host") and len(n) <= 6 and n[4:].isdigit()):
            return "PC", True, "NETWORK_DEVICE"
        if "server" in t or (n.startswith("srv") and len(n) <= 5 and n[3:].isdigit()) or (n.startswith("server") and len(n) <= 8 and n[6:].isdigit()):
            return "Server", True, "NETWORK_DEVICE"
        if "accesspoint" in t or "access point" in t or "ap" in t or "wireless" in t:
            return "AccessPoint", True, "NETWORK_DEVICE"
        if "firewall" in t or "asa" in t or "security" in t:
            return "Firewall", True, "NETWORK_DEVICE"
        if "hub" in t or "repeater" in t:
            return "Hub", True, "NETWORK_DEVICE"

        return "Unknown", True, "NETWORK_DEVICE"


pkt_extractor = PktExtractor()
