"""
Streaming SAX XML Parser module for ptdecoder.
Utilizes Python standard library xml.parsers.expat to selectively parse network topology,
devices, configurations, PDU scenarios, and notes while skipping heavy Base64 image payloads.
"""

from __future__ import annotations
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import BinaryIO
import xml.parsers.expat

from ptdecoder.crypto import decrypt_pkt
from ptdecoder.models import (
    AclRule,
    Connection,
    Device,
    DhcpPool,
    Interface,
    NatPool,
    NatRule,
    OspfConfig,
    OspfNetwork,
    PduItem,
    PduScenario,
    PktDocument,
    PktMetadata,
    RouterConfig,
    StaticRoute,
    TopologyNote,
)


from ptdecoder.exceptions import PktXmlLimitError

HEAVY_UNKNOWN_TAGS = {
    "PIXMAPBANK",
    "PIXMAP",
    "MOVIEBANK",
    "BACKGROUND",
    "BACKGROUNDIMAGE",
    "BACKGROUND_IMAGE",
    "FILE_ENTRY",
    "IOS_IMAGE",
    "DISK_IMAGE",
    "CANVAS_GRAPHICS",
    "DRAWING_LAYER",
    "CUSTOM_ICONS",
    "ICON_BANK",
    "FSM_STATES",
    "SIMULATION_RECORDER",
    "EVENT_LIST",
    "ASSESSMENT",
}


class PacketTracerSaxParser:
    """SAX event handler for streaming Packet Tracer XML parsing with security guards."""

    def __init__(
        self,
        file_name: str | None = None,
        file_size: int | None = None,
        file_mtime: datetime | None = None,
        max_xml_elements: int | None = 500_000,
        max_xml_depth: int | None = 100,
        max_text_length: int | None = 10_000_000,
    ):
        self.file_name = file_name
        self.file_size = file_size
        self.file_mtime = file_mtime
        self.max_xml_elements = max_xml_elements
        self.max_xml_depth = max_xml_depth
        self.max_text_length = max_text_length

        # Parser state & security counters
        self.element_count = 0
        self.skip_depth = 0
        self.current_path: list[str] = []
        self.char_buffer: list[str] = []
        self.current_text_len = 0

        # Document attributes
        self.version = "Unknown"
        self.save_time_unix_ms: int | None = None
        self.save_time: datetime | None = None

        self.devices: list[Device] = []
        self.raw_connections: list[dict[str, str]] = []
        self.notes: list[TopologyNote] = []
        self.scenarios: list[PduScenario] = []

        # Temporary object builder states
        self.cur_device: dict[str, Any] | None = None
        self.cur_port: dict[str, Any] | None = None
        self.cur_cli_lines: list[str] = []
        self.cur_note: dict[str, Any] | None = None
        self.cur_scenario: dict[str, Any] | None = None
        self.cur_pdu: dict[str, Any] | None = None
        self.cur_cable: dict[str, str] | None = None

    def start_element(self, name: str, attrs: dict[str, str]) -> None:
        self.element_count += 1
        if self.max_xml_elements is not None and self.element_count > self.max_xml_elements:
            raise PktXmlLimitError(
                f"XML element count ({self.element_count:,}) exceeded safety limit ({self.max_xml_elements:,})."
            )

        self.current_path.append(name)
        if self.max_xml_depth is not None and len(self.current_path) > self.max_xml_depth:
            raise PktXmlLimitError(
                f"XML nesting depth ({len(self.current_path)}) exceeded safety limit ({self.max_xml_depth})."
            )

        self.char_buffer = []
        self.current_text_len = 0

        # Selective skipping of heavy media, binary images, and non-topology workspace payloads
        if name in HEAVY_UNKNOWN_TAGS:
            self.skip_depth += 1
            return

        if self.skip_depth > 0:
            self.skip_depth += 1
            return

        # Start object builders
        if name == "DEVICE":
            self.cur_device = {
                "name": "",
                "power": True,
                "ref_id": attrs.get("save-ref-id"),
                "model": "",
                "type": "",
                "x": 0.0,
                "y": 0.0,
                "interfaces": [],
                "cli_lines": [],
            }
        elif name == "TYPE" and self.cur_device is not None and self.current_path[-2:] == ["ENGINE", "TYPE"]:
            # Packet Tracer >= 8.x stores the device model as an attribute on ENGINE/TYPE
            self.cur_device["model"] = attrs.get("model", "")
        elif name == "PORT" and self.cur_device is not None:
            self.cur_port = {
                "name": "",
                "power": True,
                "dhcp_enabled": False,
                "ip": None,
                "subnet_mask": None,
                "default_gateway": None,
                "dns_server": None,
                "dhcp_server_ip": None,
                "mac": None,
                "vlan": None,
                "nat_role": None,
                "is_wireless": False,
                "ssid": None,
                "wifi_channel": None,
                "radio_band": None,
                "wifi_authentication": None,
                "wifi_encryption": None,
            }
        elif name == "CABLE" or name == "CONNECTION":
            self.cur_cable = {"from": "", "from_port": "", "to": "", "to_port": "", "type": ""}
        elif name == "NOTE":
            self.cur_note = {"text": "", "x": 0.0, "y": 0.0, "uuid": attrs.get("uuid")}
        elif name == "SCENARIO":
            self.cur_scenario = {"name": attrs.get("name", "Scenario"), "pdus": []}
        elif name == "PDU" and self.cur_scenario is not None:
            self.cur_pdu = {"source": "", "destination": "", "type": "ICMP", "last_status": None}
        elif name == "DESTINATION" and self.cur_pdu is not None:
            if "device" in attrs:
                self.cur_pdu["destination"] = attrs["device"]

    def end_element(self, name: str) -> None:
        if self.skip_depth > 0:
            self.skip_depth -= 1
            if len(self.current_path) > 0:
                self.current_path.pop()
            return

        text = "".join(self.char_buffer).strip()

        # Parse Metadata Timestamps
        if name == "VERSION" and len(self.current_path) == 2:
            self.version = text
        elif name in ("STARTTIME", "DATE_TIME") and text.isdigit() and self.save_time is None:
            val = int(text)
            if val > 1000000000:
                self.save_time_unix_ms = val if val > 100000000000 else val * 1000
                self.save_time = datetime.fromtimestamp(self.save_time_unix_ms / 1000.0, tz=timezone.utc)

        # Device builder populator
        if self.cur_device is not None:
            if name == "NAME" and self.current_path[-2:] == ["ENGINE", "NAME"]:
                self.cur_device["name"] = text
            elif name == "TYPE" and self.current_path[-2:] == ["ENGINE", "TYPE"]:
                self.cur_device["type"] = text
                if "model" in self.current_path:
                    pass
            elif name == "POWER" and self.current_path[-2:] == ["ENGINE", "POWER"]:
                self.cur_device["power"] = text.lower() == "true"
            elif name == "SAVE_REF_ID":
                # Packet Tracer >= 8.x stores the reference id as a child element, not a DEVICE attribute
                self.cur_device["ref_id"] = text
            elif name == "X_COORD" or (name == "X" and "COORD_SETTINGS" in self.current_path):
                try: self.cur_device["x"] = float(text)
                except ValueError: pass
            elif name == "Y_COORD" or (name == "Y" and "COORD_SETTINGS" in self.current_path):
                try: self.cur_device["y"] = float(text)
                except ValueError: pass
            elif name == "LINE":
                self.cur_device["cli_lines"].append(text)

            # Port builder populator
            if self.cur_port is not None:
                if name == "POWER" and "PORT" in self.current_path:
                    self.cur_port["power"] = text.lower() == "true"
                elif name == "IP" and "PORT" in self.current_path:
                    if text: self.cur_port["ip"] = text
                elif name == "SUBNET" and "PORT" in self.current_path:
                    if text: self.cur_port["subnet_mask"] = text
                elif name == "PORT_GATEWAY" and "PORT" in self.current_path:
                    if text: self.cur_port["default_gateway"] = text
                elif name == "PORT_DNS" and "PORT" in self.current_path:
                    if text: self.cur_port["dns_server"] = text
                elif name == "PORT_DHCP_ENABLE" and "PORT" in self.current_path:
                    self.cur_port["dhcp_enabled"] = text.lower() == "true"
                elif name == "DHCP_SERVER_IP" and "PORT" in self.current_path:
                    if text: self.cur_port["dhcp_server_ip"] = text
                elif name == "MACADDRESS" and "PORT" in self.current_path:
                    if text: self.cur_port["mac"] = text
                elif name == "VLAN" and "PORT" in self.current_path:
                    if text: self.cur_port["vlan"] = text
                elif name == "SSID":
                    self.cur_port["ssid"] = text
                    self.cur_port["is_wireless"] = True
                elif name == "CHANNEL":
                    try: self.cur_port["wifi_channel"] = int(text)
                    except ValueError: pass
                elif name == "RADIO_BAND":
                    self.cur_port["radio_band"] = "5GHz" if text == "1" else "2.4GHz"
                elif name == "AUTHEN_TYPE":
                    auth_map = {"0": "Open", "1": "WEP", "2": "WPA-PSK", "3": "WPA2-PSK", "4": "WPA-Enterprise"}
                    self.cur_port["wifi_authentication"] = auth_map.get(text, text)
                elif name == "ENCRYPT_TYPE":
                    enc_map = {"0": "None", "1": "AES", "2": "TKIP"}
                    self.cur_port["wifi_encryption"] = enc_map.get(text, text)
                elif name == "WEP_KEY" or name == "WPA_EAP_PASSWORD":
                    if text: self.cur_port["wifi_key"] = text

                if name == "PORT":
                    port_name = self.cur_port.get("name") or text
                    if not port_name or port_name == text:
                        # Estimate port name from TYPE / MODEL if name tag absent
                        type_tag = self.current_path[-1]
                        port_name = f"Port_{len(self.cur_device['interfaces'])}"
                    self.cur_port["name"] = port_name
                    self.cur_device["interfaces"].append(self.cur_port)
                    self.cur_port = None

            if name == "DEVICE":
                dev_obj = self._build_device(self.cur_device)
                self.devices.append(dev_obj)
                self.cur_device = None

        # Cable / Connection builder populator
        if self.cur_cable is not None:
            if name in ("FROM", "DEV1", "FROM_DEVICE"):
                self.cur_cable["from"] = text
            elif name in ("PORT", "PORT1", "FROM_PORT") and not self.cur_cable["from_port"]:
                self.cur_cable["from_port"] = text
            elif name in ("TO", "DEV2", "TO_DEVICE"):
                self.cur_cable["to"] = text
            elif name in ("PORT", "PORT2", "TO_PORT") and self.cur_cable["from_port"]:
                self.cur_cable["to_port"] = text
            elif name == "TYPE":
                self.cur_cable["type"] = text

            if name in ("CABLE", "CONNECTION"):
                if self.cur_cable["from"] and self.cur_cable["to"]:
                    self.raw_connections.append(self.cur_cable)
                self.cur_cable = None

        # Note builder populator
        if self.cur_note is not None:
            if name == "TEXT": self.cur_note["text"] = text
            elif name == "X":
                try: self.cur_note["x"] = float(text)
                except ValueError: pass
            elif name == "Y":
                try: self.cur_note["y"] = float(text)
                except ValueError: pass
            elif name == "NOTE":
                if self.cur_note["text"]:
                    self.notes.append(TopologyNote(
                        text=self.cur_note["text"],
                        position={"x": self.cur_note["x"], "y": self.cur_note["y"]},
                        uuid=self.cur_note["uuid"]
                    ))
                self.cur_note = None

        # Scenario / PDU builder populator
        if self.cur_scenario is not None:
            if name == "NAME" and self.current_path[-2:] == ["SCENARIO", "NAME"]:
                self.cur_scenario["name"] = text
            elif name == "DESCRIPTION" and self.current_path[-2:] == ["SCENARIO", "DESCRIPTION"]:
                self.cur_scenario["description"] = text

            if self.cur_pdu is not None:
                if name == "SOURCE": self.cur_pdu["source"] = text
                elif name == "TYPE": self.cur_pdu["type"] = text or "ICMP"
                elif name in ("LAST_STATUS", "STATUS"): self.cur_pdu["last_status"] = text
                elif name == "PDU":
                    if self.cur_pdu["source"] and self.cur_pdu["destination"]:
                        self.cur_scenario["pdus"].append(self.cur_pdu)
                    self.cur_pdu = None

            if name == "SCENARIO":
                sc_obj = PduScenario(
                    name=self.cur_scenario["name"],
                    description=self.cur_scenario.get("description"),
                    pdus=[]
                )
                # Store raw PDU list to resolve after device building
                sc_obj._raw_pdus = self.cur_scenario["pdus"]  # type: ignore
                self.scenarios.append(sc_obj)
                self.cur_scenario = None

        if len(self.current_path) > 0:
            self.current_path.pop()

    def character_data(self, data: str) -> None:
        if self.skip_depth == 0:
            self.char_buffer.append(data)

    def _build_device(self, raw_dev: dict[str, Any]) -> Device:
        interfaces: list[Interface] = []
        for p in raw_dev["interfaces"]:
            iface = Interface(
                name=p["name"],
                power=p["power"],
                dhcp_enabled=p["dhcp_enabled"],
                ip=p["ip"],
                subnet_mask=p["subnet_mask"],
                default_gateway=p["default_gateway"],
                dns_server=p["dns_server"],
                dhcp_server_ip=p["dhcp_server_ip"],
                mac=p["mac"],
                vlan=p["vlan"],
                nat_role=p["nat_role"],
                is_wireless=p["is_wireless"],
                ssid=p["ssid"],
                wifi_channel=p["wifi_channel"],
                radio_band=p["radio_band"],
                wifi_authentication=p["wifi_authentication"],
                wifi_encryption=p["wifi_encryption"],
            )
            interfaces.append(iface)

        # Parse Router CLI Config lines if present
        router_config = self._parse_router_cli(raw_dev["cli_lines"]) if raw_dev["cli_lines"] else None

        dev = Device(
            name=raw_dev["name"],
            power=raw_dev["power"],
            ref_id=raw_dev["ref_id"],
            model=raw_dev["model"],
            type=raw_dev["type"],
            position={"x": raw_dev["x"], "y": raw_dev["y"]},
            interfaces=interfaces,
            router_config=router_config,
        )

        # Back-reference pointer
        for iface in interfaces:
            iface.device = dev

        return dev

    def _parse_router_cli(self, cli_lines: list[str]) -> RouterConfig:
        hostname = None
        dhcp_pools: list[DhcpPool] = []
        ospf_configs: list[OspfConfig] = []
        static_routes: list[StaticRoute] = []
        acls: list[AclRule] = []
        nat_pools: list[NatPool] = []
        nat_rules: list[NatRule] = []

        cur_pool: DhcpPool | None = None
        cur_ospf: OspfConfig | None = None

        for line in cli_lines:
            s_line = line.strip()
            if not s_line:
                continue

            if s_line.startswith("hostname "):
                hostname = s_line.split()[1]
            elif s_line.startswith("ip dhcp pool "):
                pool_name = s_line.split()[3]
                cur_pool = DhcpPool(name=pool_name)
                dhcp_pools.append(cur_pool)
            elif cur_pool and s_line.startswith("network "):
                parts = s_line.split()
                if len(parts) >= 3:
                    cur_pool.network = parts[1]
                    cur_pool.mask = parts[2]
            elif cur_pool and s_line.startswith("default-router "):
                cur_pool.default_router = s_line.split()[1]
            elif cur_pool and s_line.startswith("dns-server "):
                cur_pool.dns_server = s_line.split()[1]
            elif s_line.startswith("router ospf "):
                pid = s_line.split()[2]
                cur_ospf = OspfConfig(process_id=pid)
                ospf_configs.append(cur_ospf)
            elif cur_ospf and s_line.startswith("router-id "):
                cur_ospf.router_id = s_line.split()[1]
            elif cur_ospf and s_line.startswith("network "):
                parts = s_line.split()
                if len(parts) >= 5 and parts[3] == "area":
                    cur_ospf.networks.append(OspfNetwork(network=parts[1], wildcard_mask=parts[2], area=parts[4]))
            elif s_line.startswith("ip route "):
                parts = s_line.split()
                if len(parts) >= 5:
                    static_routes.append(StaticRoute(destination_prefix=parts[2], subnet_mask=parts[3], next_hop=parts[4]))
            elif s_line.startswith("access-list "):
                parts = s_line.split()
                if len(parts) >= 4:
                    acls.append(AclRule(name_or_number=parts[1], action=parts[2], source=parts[3]))
            elif s_line.startswith("ip nat pool "):
                parts = s_line.split()
                if len(parts) >= 6:
                    nat_pools.append(NatPool(name=parts[3], start_ip=parts[4], end_ip=parts[5], netmask=parts[-1]))
            elif s_line.startswith("ip nat inside source static "):
                parts = s_line.split()
                if len(parts) >= 6:
                    nat_rules.append(NatRule(nat_type="static", inside_local=parts[4], inside_global=parts[5]))

        return RouterConfig(
            hostname=hostname,
            running_config_raw="\n".join(cli_lines),
            cli_lines=cli_lines,
            dhcp_pools=dhcp_pools,
            ospf_configs=ospf_configs,
            static_routes=static_routes,
            acls=acls,
            nat_pools=nat_pools,
            nat_rules=nat_rules,
        )


def _port_index_from_name(port_name: str | None) -> int | None:
    """Extracts a port index from a Packet Tracer port name (e.g. 'FastEthernet0/1' -> 1)."""
    if not port_name:
        return None
    last = port_name.split("/")[-1]
    if last.isdigit():
        return int(last)
    return None


def _resolve_iface(device: Device, port_name: str | None) -> Interface | None:
    """Resolves an interface by name, then by trailing index parsed from the cable port name."""
    iface = device.get_interface(port_name) if port_name else None
    if iface:
        return iface
    idx = _port_index_from_name(port_name)
    if idx is not None and 0 <= idx < len(device.interfaces):
        return device.interfaces[idx]
    if device.interfaces:
        return device.interfaces[0]
    return None


def _resolve_object_graph(handler: PacketTracerSaxParser, metadata: PktMetadata) -> PktDocument:
    """Post-processing step resolving first-class object pointers across devices, connections, and scenarios."""
    device_map: dict[str, Device] = {}
    for dev in handler.devices:
        device_map[dev.name] = dev
        if dev.ref_id:
            device_map[dev.ref_id] = dev

    connections: list[Connection] = []

    # Resolve Connection object graph pointers
    for rc in handler.raw_connections:
        from_dev = device_map.get(rc["from"])
        to_dev = device_map.get(rc["to"])
        if from_dev and to_dev:
            from_iface = _resolve_iface(from_dev, rc["from_port"])
            to_iface = _resolve_iface(to_dev, rc["to_port"])
            if from_iface and to_iface:
                conn = Connection(
                    from_device=from_dev,
                    from_interface=from_iface,
                    to_device=to_dev,
                    to_interface=to_iface,
                    cable_type=rc.get("type"),
                )
                connections.append(conn)
                from_dev.connections.append(conn)
                to_dev.connections.append(conn)

                # Link symmetric interface cable pointers
                from_iface.connected_device = to_dev
                from_iface.connected_interface = to_iface
                to_iface.connected_device = from_dev
                to_iface.connected_interface = from_iface

    # Resolve PDU scenario object pointers
    for sc in handler.scenarios:
        raw_pdus = getattr(sc, "_raw_pdus", [])
        for rp in raw_pdus:
            src_dev = device_map.get(rp["source"])
            dst_dev = device_map.get(rp["destination"])
            if src_dev and dst_dev:
                sc.pdus.append(PduItem(
                    source_device=src_dev,
                    destination_device=dst_dev,
                    pdu_type=rp.get("type", "ICMP"),
                    last_status=rp.get("last_status")
                ))

    return PktDocument(
        metadata=metadata,
        devices=handler.devices,
        connections=connections,
        notes=handler.notes,
        scenarios=handler.scenarios,
    )


def parse_pkt_stream(
    stream_or_path: str | Path | bytes | BinaryIO,
    file_name: str | None = None,
    max_file_size: int | None = 50_000_000,
    max_uncompressed_bytes: int | None = 100_000_000,
    max_xml_elements: int | None = 500_000,
    max_xml_depth: int | None = 100,
    max_text_length: int | None = 10_000_000,
) -> PktDocument:
    """
    Synchronously decodes and parses a Packet Tracer (.pkt/.pka/.xml) file into a structured PktDocument object.

    Args:
        stream_or_path: Path, bytes, or open BinaryIO stream.
        file_name: Optional file name override.
        max_file_size: Maximum allowed raw input file size in bytes (default: 50MB). Pass None to disable.
        max_uncompressed_bytes: Maximum allowed uncompressed XML size in bytes (default: 100MB). Pass None to disable.
        max_xml_elements: Maximum allowed XML elements (default: 500k). Pass None to disable.
        max_xml_depth: Maximum allowed XML nesting depth (default: 100). Pass None to disable.
        max_text_length: Maximum allowed character data length per node (default: 10MB). Pass None to disable.

    Returns:
        PktDocument instance.
    """
    file_size = None
    file_mtime = None

    if isinstance(stream_or_path, (str, Path)):
        p = Path(stream_or_path)
        file_name = file_name or p.name
        file_size = p.stat().st_size
        file_mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)

    xml_bytes = decrypt_pkt(
        stream_or_path,
        max_file_size=max_file_size,
        max_uncompressed_bytes=max_uncompressed_bytes,
    )

    metadata = PktMetadata(
        version="Unknown",
        file_name=file_name,
        file_size=file_size or len(xml_bytes),
        file_mtime=file_mtime,
    )

    handler = PacketTracerSaxParser(
        file_name=file_name,
        file_size=file_size,
        file_mtime=file_mtime,
        max_xml_elements=max_xml_elements,
        max_xml_depth=max_xml_depth,
        max_text_length=max_text_length,
    )
    p = xml.parsers.expat.ParserCreate(encoding="utf-8")
    p.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
    p.StartElementHandler = handler.start_element
    p.EndElementHandler = handler.end_element
    p.CharacterDataHandler = handler.character_data

    p.Parse(xml_bytes)

    metadata.version = handler.version
    metadata.save_time = handler.save_time
    metadata.save_time_unix_ms = handler.save_time_unix_ms

    return _resolve_object_graph(handler, metadata)
