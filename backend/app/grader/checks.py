"""Per-subnet network checks + per-end-device (5-point) grading."""
from __future__ import annotations

import ipaddress
from typing import Dict, List, Optional, Tuple

from app.schemas import (
    CheckResult,
    DeviceGrade,
    EndDeviceSpec,
    ExpectedSubnet,
    StudentDevice,
    StudentDhcpPool,
    StudentJSON,
)

# Human-friendly labels for the report.
LABELS = {
    "device_name": "Device Names",
    "ip_in_subnet": "IP in Subnet",
    "gateway": "Gateway",
    "dhcp_pool": "DHCP Pool",
    "links_up": "Links Up",
}

_ROUTER_TYPES = {"router", "switch", "l3switch", "l3 switch"}


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _find_device(student: StudentJSON, name: str) -> Optional[StudentDevice]:
    n = _norm(name)
    for d in student.devices:
        if _norm(d.name) == n:
            return d
    return None


def _pool_for_subnet(student: StudentJSON, subnet: ExpectedSubnet) -> Optional[StudentDhcpPool]:
    expected_net = ipaddress.ip_network(f"{subnet.network_address}/{subnet.prefix}")
    # Prefer an exact network/mask match, then fall back to the gateway match.
    for p in student.dhcp_pools:
        if p.network and p.mask:
            try:
                if ipaddress.ip_network(f"{p.network}/{p.mask}", strict=False) == expected_net:
                    return p
            except ValueError:
                pass
    for p in student.dhcp_pools:
        if p.default_gateway == subnet.gateway:
            return p
    return None


def check_dhcp_pool(subnet: ExpectedSubnet, student: StudentJSON) -> Tuple[float, str, str, str]:
    pool = _pool_for_subnet(student, subnet)
    expected_net = ipaddress.ip_network(f"{subnet.network_address}/{subnet.prefix}")
    expected = str(expected_net)
    if not pool:
        return 0.0, "no matching DHCP pool for this subnet", expected, "no pool"
    try:
        pool_net = ipaddress.ip_network(f"{pool.network}/{pool.mask}", strict=False)
    except ValueError:
        return 0.0, f"invalid pool network {pool.network}/{pool.mask}", expected, f"{pool.network}/{pool.mask}"
    if pool_net == expected_net:
        return 1.0, "pool network matches expected", expected, str(pool_net)
    return 0.0, f"pool network {pool_net} != expected", expected, str(pool_net)


def check_dhcp_mask(subnet: ExpectedSubnet, student: StudentJSON) -> Tuple[float, str, str, str]:
    pool = _pool_for_subnet(student, subnet)
    expected = subnet.subnet_mask
    if not pool:
        return 0.0, "no matching DHCP pool for this subnet", expected, "no pool"
    if pool.mask == expected:
        return 1.0, "pool mask matches expected", expected, pool.mask
    return 0.0, f"pool mask {pool.mask} != expected", expected, pool.mask


def check_dhcp_gateway(subnet: ExpectedSubnet, student: StudentJSON) -> Tuple[float, str, str, str]:
    pool = _pool_for_subnet(student, subnet)
    expected = subnet.gateway
    if not pool:
        return 0.0, "no matching DHCP pool for this subnet", expected, "no pool"
    if pool.default_gateway == expected:
        return 1.0, "pool gateway matches expected", expected, pool.default_gateway
    return 0.0, f"pool gateway {pool.default_gateway} != expected", expected, pool.default_gateway


def check_gateway(subnet: ExpectedSubnet, student: StudentJSON) -> Tuple[float, str, str, str]:
    expected = subnet.gateway
    holders = [d for d in student.devices for i in d.interfaces if i.ip == subnet.gateway]
    if not holders:
        return 0.0, f"no device holds gateway IP {subnet.gateway}", expected, "no device"
    dev = holders[0]
    iface = next(i for i in dev.interfaces if i.ip == subnet.gateway)
    if _norm(dev.type) not in _ROUTER_TYPES:
        return (
            0.0,
            f"gateway {subnet.gateway} on non-router device '{dev.name}' ({dev.type})",
            expected,
            f"{dev.name} ({dev.type})",
        )
    return 1.0, f"gateway {subnet.gateway} on {dev.name}", expected, f"{dev.name} ({iface.ip})"


def grade_end_device(
    ed: EndDeviceSpec, subnet: ExpectedSubnet, student: StudentJSON
) -> DeviceGrade:
    expected_net = f"{subnet.network_address}/{subnet.prefix}"
    sd = _find_device(student, ed.name)

    if sd is None:
        checks = [
            CheckResult(key="name", label="Name", passed=False, score=0, max_score=1, expected=ed.name, actual="device not found"),
            CheckResult(key="dhcp", label="DHCP", passed=False, score=0, max_score=1, expected="DHCP client" if ed.dhcp else "static", actual="device not found"),
            CheckResult(key="ip", label="IP Address", passed=False, score=0, max_score=1, expected=expected_net, actual="device not found"),
            CheckResult(key="mask", label="Subnet Mask", passed=False, score=0, max_score=1, expected=subnet.subnet_mask, actual="device not found"),
            CheckResult(key="gw", label="Default Gateway", passed=False, score=0, max_score=1, expected=subnet.gateway, actual="device not found"),
        ]
        return DeviceGrade(name=ed.name, type=ed.type, matched=False, checks=checks, score=0.0, max_score=5.0)

    # 1) Name
    name_ok = _norm(sd.name) == _norm(ed.name)

    # 2) DHCP configuration. A device is a DHCP client when it has DHCP enabled
    # and no static IP. We intentionally do NOT require dhcp_server_ip to equal
    # the subnet gateway: IoT/multi-homed devices report the IoT registration
    # server (e.g. 192.168.25.1) as their "server", and the router's DHCP
    # server correctness is already validated by the subnet-level DHCP checks.
    has_static = any(i.ip for i in sd.interfaces)
    if ed.dhcp:
        dhcp_ok = sd.dhcp_enabled and not has_static
        if sd.dhcp_enabled and has_static:
            dhcp_actual = "DHCP + static IP"
        else:
            dhcp_actual = "DHCP client" if sd.dhcp_enabled else "static"
    else:
        dhcp_ok = has_static
        dhcp_actual = "static" if has_static else "DHCP client"

    # 3-5) IP range / mask / gateway. For DHCP end devices the actual values come
    # from the subnet's DHCP pool (the client has no stored IP in the .pkt); for
    # static devices we read the device's own interface.
    if ed.dhcp:
        pool = _pool_for_subnet(student, subnet)
        if pool and pool.network and pool.mask:
            try:
                pnet = ipaddress.ip_network(f"{pool.network}/{pool.mask}", strict=False)
                src_ip = str(pnet.network_address + 1)
            except ValueError:
                src_ip = pool.network.split("/")[0]
        else:
            src_ip = None
        src_mask = pool.mask if pool else None
        src_gw = pool.default_gateway if pool else None
    else:
        ifc = next((i for i in sd.interfaces if i.ip), None)
        src_ip = ifc.ip if ifc else None
        src_mask = ifc.mask if ifc else None
        src_gw = ifc.gateway if ifc else None

    ip_ok = False
    ip_actual = src_ip or "none"
    if src_ip:
        try:
            ip_ok = ipaddress.ip_address(src_ip) in ipaddress.ip_network(expected_net)
        except ValueError:
            ip_ok = False

    mask_ok = src_mask == subnet.subnet_mask
    gw_ok = src_gw == subnet.gateway

    checks = [
        CheckResult(key="name", label="Name", passed=name_ok, score=1 if name_ok else 0, max_score=1, expected=ed.name, actual=sd.name),
        CheckResult(key="dhcp", label="DHCP", passed=dhcp_ok, score=1 if dhcp_ok else 0, max_score=1, expected="DHCP client" if ed.dhcp else "static", actual=dhcp_actual),
        CheckResult(key="ip", label="IP Address", passed=ip_ok, score=1 if ip_ok else 0, max_score=1, expected=expected_net, actual=ip_actual),
        CheckResult(key="mask", label="Subnet Mask", passed=mask_ok, score=1 if mask_ok else 0, max_score=1, expected=subnet.subnet_mask, actual=src_mask or "none"),
        CheckResult(key="gw", label="Default Gateway", passed=gw_ok, score=1 if gw_ok else 0, max_score=1, expected=subnet.gateway, actual=src_gw or "none"),
    ]
    return DeviceGrade(
        name=ed.name,
        type=ed.type,
        matched=True,
        checks=checks,
        score=sum(c.score for c in checks),
        max_score=5.0,
    )
