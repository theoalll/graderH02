"""
Adapter: raw ptdecoder document -> normalized StudentJSON.

The grader only ever sees StudentJSON, so it stays decoupled from the
internal ptdecoder object graph.
"""
from __future__ import annotations

import ipaddress
from typing import Any, Dict, List

from app.schemas import (
    StudentDevice,
    StudentDhcpPool,
    StudentInterface,
    StudentJSON,
    StudentLink,
    StudentNote,
)


def _status_from_power(powered: bool) -> str:
    return "up" if powered else "down"


def adapt(doc_dict: Dict[str, Any]) -> StudentJSON:
    devices: List[StudentDevice] = []
    device_by_name: Dict[str, Dict[str, Any]] = {}

    for raw in doc_dict.get("devices", []):
        ifaces: List[StudentInterface] = []
        first_ip = first_mask = first_gw = None
        for ifc in raw.get("interfaces", []):
            si = StudentInterface(
                name=ifc.get("name") or "",
                ip=ifc.get("ip"),
                mask=ifc.get("subnet_mask"),
                gateway=ifc.get("default_gateway"),
                status=_status_from_power(ifc.get("power", True)),
                is_wireless=bool(ifc.get("is_wireless")),
                ssid=ifc.get("ssid"),
                dhcp_enabled=bool(ifc.get("dhcp_enabled")),
                dhcp_server_ip=ifc.get("dhcp_server_ip"),
                connected_device=ifc.get("connected_device"),
                connected_interface=ifc.get("connected_interface"),
            )
            ifaces.append(si)
            if first_ip is None and si.ip:
                first_ip, first_mask, first_gw = si.ip, si.mask, si.gateway
        dev = StudentDevice(
            id=raw.get("ref_id") or raw.get("name") or "",
            name=raw.get("name") or "",
            type=raw.get("type"),
            model=raw.get("model"),
            power=raw.get("power", True),
            position=raw.get("position"),
            interfaces=ifaces,
            ip=first_ip,
            mask=first_mask,
            gateway=first_gw,
            dhcp_enabled=any(i.dhcp_enabled for i in ifaces),
        )
        devices.append(dev)
        device_by_name[dev.name] = raw

    links: List[StudentLink] = []
    for c in doc_dict.get("connections", []):
        from_if = _find_iface(device_by_name.get(c.get("from_device", ""), {}), c.get("from_interface"))
        to_if = _find_iface(device_by_name.get(c.get("to_device", ""), {}), c.get("to_interface"))
        up = (from_if.get("power", True) if from_if else True) and (to_if.get("power", True) if to_if else True)
        links.append(
            StudentLink(
                from_device=c.get("from_device"),
                from_interface=c.get("from_interface"),
                to_device=c.get("to_device"),
                to_interface=c.get("to_interface"),
                type=c.get("cable_type"),
                status=_status_from_power(up),
            )
        )

    pools: List[StudentDhcpPool] = []
    for raw in doc_dict.get("devices", []):
        rc = raw.get("router_config")
        if not rc:
            continue
        # build a quick lookup of this router's interfaces by subnet
        iface_subnets = {}
        for ifc in raw.get("interfaces", []):
            if ifc.get("ip") and ifc.get("subnet_mask"):
                try:
                    net = ipaddress.ip_interface(f"{ifc['ip']}/{ifc['subnet_mask']}").network
                    iface_subnets[str(net)] = ifc.get("name")
                except ValueError:
                    pass
        for p in rc.get("dhcp_pools", []):
            net = p.get("network")
            pools.append(
                StudentDhcpPool(
                    router=raw.get("name"),
                    interface=iface_subnets.get(net),
                    name=p.get("name"),
                    network=net,
                    mask=p.get("mask"),
                    default_gateway=p.get("default_router"),
                    start_ip=p.get("start_ip"),
                    end_ip=p.get("end_ip"),
                )
            )

    notes: List[StudentNote] = [
        StudentNote(text=n.get("text", ""), position=n.get("position"))
        for n in doc_dict.get("notes", [])
        if n.get("text")
    ]

    return StudentJSON(
        source_file=doc_dict.get("metadata", {}).get("file_name"),
        devices=devices,
        links=links,
        dhcp_pools=pools,
        notes=notes,
    )


def _find_iface(raw_dev: Dict[str, Any], name: str | None) -> Dict[str, Any] | None:
    if not raw_dev:
        return None
    for ifc in raw_dev.get("interfaces", []):
        if ifc.get("name") == name:
            return ifc
    return None
