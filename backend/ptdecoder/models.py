"""
Data models for ptdecoder.
Defines Python 3.11+ dataclasses with first-class object graph linking,
safe native ipaddress properties, and JSON serializable dictionary conversion.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
import ipaddress
from typing import Any
import networkx as nx
from networkx.algorithms.isomorphism import GraphMatcher


@dataclass
class PktMetadata:
    version: str
    file_name: str | None = None
    file_size: int | None = None
    save_time: datetime | None = None  # 100% Stable internal payload save time (UTC)
    save_time_unix_ms: int | None = None
    file_mtime: datetime | None = None


@dataclass
class WirelessConfig:
    ssid: str | None = None
    channel: int | None = None
    radio_band: str | None = None  # "2.4GHz" | "5GHz"
    authentication_type: str | None = None  # "Open" | "WEP" | "WPA-PSK" | "WPA2-PSK" | "WPA-Enterprise"
    encryption_type: str | None = None  # "AES" | "TKIP" | "None"
    key_passphrase: str | None = None


@dataclass
class Interface:
    name: str
    power: bool = True  # True = ON / no shutdown, False = OFF / shutdown
    
    # Unified IP & Network Configuration
    dhcp_enabled: bool = False
    ip: str | None = None
    subnet_mask: str | None = None
    default_gateway: str | None = None
    dns_server: str | None = None
    dhcp_server_ip: str | None = None
    mac: str | None = None
    vlan: str | None = None
    nat_role: str | None = None  # "inside" | "outside" | None
    
    # Wireless / Wi-Fi Configuration
    is_wireless: bool = False
    ssid: str | None = None
    wifi_channel: int | None = None
    radio_band: str | None = None  # "2.4GHz" | "5GHz"
    wifi_authentication: str | None = None
    wifi_encryption: str | None = None
    wifi_key: str | None = None
    
    # First-class Object Graph Pointers
    device: Device = field(default=None, repr=False)
    connected_device: Device | None = field(default=None, repr=False)
    connected_interface: Interface | None = field(default=None, repr=False)

    @property
    def last_dhcp_lease_successful(self) -> bool:
        """Returns True if DHCP is enabled and a valid IP lease was acquired."""
        return (
            self.dhcp_enabled
            and bool(self.ip)
            and self.ip != "0.0.0.0"
            and not self.ip.startswith("169.254.")
        )

    @property
    def ip_obj(self) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        """Returns native ipaddress object if valid IP is set, else None (safe against student typos)."""
        if not self.ip or self.ip == "0.0.0.0":
            return None
        try:
            return ipaddress.ip_address(self.ip)
        except ValueError:
            return None

    @property
    def ip_interface(self) -> ipaddress.IPv4Interface | ipaddress.IPv6Interface | None:
        """Returns native ipaddress interface (IP + Subnet Mask) for subnet math."""
        if not self.ip or not self.subnet_mask or self.ip == "0.0.0.0":
            return None
        try:
            return ipaddress.ip_interface(f"{self.ip}/{self.subnet_mask}")
        except ValueError:
            return None


@dataclass
class Connection:
    from_device: Device
    from_interface: Interface
    to_device: Device
    to_interface: Interface
    cable_type: str | None = None


@dataclass
class AclRule:
    name_or_number: str
    action: str  # "permit" | "deny"
    protocol: str | None = None
    source: str | None = None
    destination: str | None = None


@dataclass
class NatPool:
    name: str
    start_ip: str
    end_ip: str
    netmask: str


@dataclass
class NatRule:
    nat_type: str  # "static" | "dynamic_pat" | "dynamic_pool"
    inside_local: str | None = None
    inside_global: str | None = None
    acl: AclRule | None = None  # First-class AclRule instance
    pool: NatPool | None = None  # First-class NatPool instance
    overload: bool = False


@dataclass
class DhcpPool:
    name: str
    network: str | None = None
    mask: str | None = None
    default_router: str | None = None
    dns_server: str | None = None
    start_ip: str | None = None
    end_ip: str | None = None


@dataclass
class OspfNetwork:
    network: str
    wildcard_mask: str
    area: str


@dataclass
class OspfConfig:
    process_id: str
    router_id: str | None = None
    networks: list[OspfNetwork] = field(default_factory=list)


@dataclass
class StaticRoute:
    destination_prefix: str
    subnet_mask: str
    next_hop: str


@dataclass
class RouterConfig:
    hostname: str | None = None
    running_config_raw: str | None = None
    cli_lines: list[str] = field(default_factory=list)
    dhcp_pools: list[DhcpPool] = field(default_factory=list)
    ospf_configs: list[OspfConfig] = field(default_factory=list)
    static_routes: list[StaticRoute] = field(default_factory=list)
    acls: list[AclRule] = field(default_factory=list)
    nat_pools: list[NatPool] = field(default_factory=list)
    nat_rules: list[NatRule] = field(default_factory=list)


@dataclass
class Device:
    name: str
    power: bool = True  # True = Device powered ON, False = Device powered OFF
    ref_id: str | None = None
    model: str | None = None
    type: str | None = None  # "PC" | "Server" | "Router" | "Switch" | etc.
    position: dict[str, float] | None = None
    interfaces: list[Interface] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list, repr=False)
    router_config: RouterConfig | None = None

    def get_interface(self, name: str) -> Interface | None:
        """Lookup interface by port name (e.g. 'FastEthernet0/0', 'GigabitEthernet0/1')."""
        return next((i for i in self.interfaces if i.name == name), None)


@dataclass
class TopologyNote:
    text: str
    position: dict[str, float] | None = None
    uuid: str | None = None


@dataclass
class PduItem:
    source_device: Device
    destination_device: Device
    pdu_type: str  # "ICMP (Ping)", "HTTP", "DNS", etc.
    last_status: str | None = None  # "Successful" | "Failed" | "Untested"


@dataclass
class PduScenario:
    name: str
    description: str | None = None
    pdus: list[PduItem] = field(default_factory=list)


@dataclass
class PktDocument:
    metadata: PktMetadata
    devices: list[Device]
    connections: list[Connection]
    notes: list[TopologyNote]
    scenarios: list[PduScenario]
    _graph: nx.Graph | None = field(init=False, default=None, repr=False)

    @property
    def graph(self) -> nx.Graph:
        """
        Pre-built NetworkX Graph representing the network topology (available from onset).
        Nodes contain 'name' and 'type' attributes.
        """
        if self._graph is None:
            self._graph = self.to_networkx_graph(node_key="name", multigraph=False)
        return self._graph

    def get_device(self, name_or_id: str) -> Device | None:
        """Lookup device by hostname or reference ID."""
        return next((d for d in self.devices if d.name == name_or_id or d.ref_id == name_or_id), None)

    def to_dict(self) -> dict[str, Any]:
        """Converts the document and object graph to a clean, JSON-serializable dictionary."""
        def serialize_val(val: Any) -> Any:
            if isinstance(val, datetime):
                return val.isoformat()
            if isinstance(val, Device):
                return {"name": val.name, "type": val.type, "model": val.model}
            if isinstance(val, Interface):
                return {"name": val.name, "device": val.device.name if val.device else None, "ip": val.ip}
            if isinstance(val, AclRule):
                return {"name_or_number": val.name_or_number, "action": val.action}
            if isinstance(val, NatPool):
                return {"name": val.name, "start_ip": val.start_ip, "end_ip": val.end_ip}
            if isinstance(val, list):
                return [serialize_val(v) for v in val]
            if isinstance(val, dict):
                return {k: serialize_val(v) for k, v in val.items()}
            return val

        res: dict[str, Any] = {
            "metadata": {
                "version": self.metadata.version,
                "file_name": self.metadata.file_name,
                "file_size": self.metadata.file_size,
                "save_time": self.metadata.save_time.isoformat() if self.metadata.save_time else None,
                "save_time_unix_ms": self.metadata.save_time_unix_ms,
                "file_mtime": self.metadata.file_mtime.isoformat() if self.metadata.file_mtime else None,
            },
            "devices": [],
            "connections": [],
            "notes": [asdict(n) for n in self.notes],
            "scenarios": [],
        }

        for dev in self.devices:
            dev_dict: dict[str, Any] = {
                "name": dev.name,
                "power": dev.power,
                "ref_id": dev.ref_id,
                "model": dev.model,
                "type": dev.type,
                "position": dev.position,
                "interfaces": [],
            }
            for iface in dev.interfaces:
                dev_dict["interfaces"].append({
                    "name": iface.name,
                    "power": iface.power,
                    "dhcp_enabled": iface.dhcp_enabled,
                    "ip": iface.ip,
                    "subnet_mask": iface.subnet_mask,
                    "default_gateway": iface.default_gateway,
                    "dns_server": iface.dns_server,
                    "dhcp_server_ip": iface.dhcp_server_ip,
                    "mac": iface.mac,
                    "vlan": iface.vlan,
                    "nat_role": iface.nat_role,
                    "is_wireless": iface.is_wireless,
                    "ssid": iface.ssid,
                    "wifi_channel": iface.wifi_channel,
                    "radio_band": iface.radio_band,
                    "wifi_authentication": iface.wifi_authentication,
                    "wifi_encryption": iface.wifi_encryption,
                    "connected_device": iface.connected_device.name if iface.connected_device else None,
                    "connected_interface": iface.connected_interface.name if iface.connected_interface else None,
                })
            if dev.router_config:
                dev_dict["router_config"] = {
                    "hostname": dev.router_config.hostname,
                    "running_config_raw": dev.router_config.running_config_raw,
                    "cli_lines": dev.router_config.cli_lines,
                    "dhcp_pools": [asdict(p) for p in dev.router_config.dhcp_pools],
                    "ospf_configs": [asdict(o) for o in dev.router_config.ospf_configs],
                    "static_routes": [asdict(r) for r in dev.router_config.static_routes],
                    "acls": [asdict(a) for a in dev.router_config.acls],
                    "nat_pools": [asdict(np) for np in dev.router_config.nat_pools],
                    "nat_rules": [
                        {
                            "nat_type": nr.nat_type,
                            "inside_local": nr.inside_local,
                            "inside_global": nr.inside_global,
                            "acl": nr.acl.name_or_number if nr.acl else None,
                            "pool": nr.pool.name if nr.pool else None,
                            "overload": nr.overload,
                        }
                        for nr in dev.router_config.nat_rules
                    ],
                }
            res["devices"].append(dev_dict)

        for conn in self.connections:
            res["connections"].append({
                "from_device": conn.from_device.name,
                "from_interface": conn.from_interface.name,
                "to_device": conn.to_device.name,
                "to_interface": conn.to_interface.name,
                "cable_type": conn.cable_type,
            })

        for sc in self.scenarios:
            res["scenarios"].append({
                "name": sc.name,
                "description": sc.description,
                "pdus": [
                    {
                        "source_device": p.source_device.name if p.source_device else None,
                        "destination_device": p.destination_device.name if p.destination_device else None,
                        "pdu_type": p.pdu_type,
                        "last_status": p.last_status,
                    }
                    for p in sc.pdus
                ],
            })

        return res

    def to_networkx_graph(self, node_key: str = "name", multigraph: bool = False) -> nx.Graph | nx.MultiGraph:
        """
        Converts the document network topology into a NetworkX Graph or MultiGraph.
        Nodes contain 'name' and 'type' attributes.

        Args:
            node_key: Field on Device to use as graph node identifier.
                      Options: 'name' (default), 'ref_id', 'model', 'type'.
            multigraph: If True, returns networkx.MultiGraph (preserving multiple parallel links).
                        If False (default), returns networkx.Graph.

        Returns:
            networkx.Graph or networkx.MultiGraph
        """
        G = nx.MultiGraph() if multigraph else nx.Graph()

        for dev in self.devices:
            key = getattr(dev, node_key, dev.name)
            G.add_node(
                key,
                name=dev.name,
                type=dev.type,
                model=dev.model,
                ref_id=dev.ref_id,
                power=dev.power,
                device_obj=dev,
            )

        for conn in self.connections:
            u = getattr(conn.from_device, node_key, conn.from_device.name)
            v = getattr(conn.to_device, node_key, conn.to_device.name)
            G.add_edge(
                u,
                v,
                from_interface=conn.from_interface.name,
                to_interface=conn.to_interface.name,
                cable_type=conn.cable_type,
            )

        return G

    def is_topology_isomorphic(
        self,
        other: PktDocument | nx.Graph | nx.MultiGraph,
        node_match_by: str = "type",
        match_interfaces: bool = False,
    ) -> bool:
        """
        Checks if this topology graph is isomorphic to another document's topology or external NetworkX Graph.

        Args:
            other: Another PktDocument instance or a NetworkX Graph / MultiGraph instance.
            node_match_by: Attribute used to match corresponding nodes ('type', 'name', 'ref_id').
            match_interfaces: If True, requires connected interface names to match as well.

        Returns:
            bool: True if topologies are isomorphic, False otherwise.
        """
        g1 = self.graph if node_match_by == "name" else self.to_networkx_graph(node_key="ref_id" if node_match_by == "ref_id" else "name")

        if isinstance(other, PktDocument):
            g2 = other.graph if node_match_by == "name" else other.to_networkx_graph(node_key="ref_id" if node_match_by == "ref_id" else "name")
        elif isinstance(other, (nx.Graph, nx.MultiGraph)):
            g2 = other
        else:
            raise TypeError("Expected 'other' to be a PktDocument or NetworkX Graph instance.")

        def node_match(n1: dict[str, Any], n2: dict[str, Any]) -> bool:
            val1 = n1.get(node_match_by) or n1.get("type") or n1.get("name")
            val2 = n2.get(node_match_by) if isinstance(n2, dict) and node_match_by in n2 else (n2.get("type") or n2.get("name") if isinstance(n2, dict) else None)
            if val1 is not None and val2 is not None:
                return val1 == val2
            return True

        def edge_match(e1: dict[str, Any], e2: dict[str, Any]) -> bool:
            if not match_interfaces:
                return True
            i1 = (e1.get("from_interface"), e1.get("to_interface"))
            i2 = (e2.get("from_interface"), e2.get("to_interface"))
            if i1 == (None, None) or i2 == (None, None):
                return True
            return i1 == i2 or i1 == (i2[1], i2[0])

        matcher = GraphMatcher(g1, g2, node_match=node_match, edge_match=edge_match if match_interfaces else None)
        return matcher.is_isomorphic()

