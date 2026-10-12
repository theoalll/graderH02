"""
Pydantic schemas for the IP-addressing grader.

Two worlds are modelled:
  * CaseSchema        - what the teaching assistant authors (the scenario).
  * StudentJSON       - the normalized topology produced by the pkt decoder/adapter.
  * ExpectedSubnet    - the solver output (the "answer key") for one subnet.
  * GradeReport       - the grader output (per-check results + score).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Case definition (authored by the TA)
# --------------------------------------------------------------------------- #
class VarSource(str, Enum):
    npm_last2 = "npm_last2"
    npm_last3 = "npm_last3"
    const = "const"


class Variable(BaseModel):
    name: str
    source: Optional[VarSource] = None  # omitted when `expr` is used
    value: Optional[int] = None  # only for source == const
    expr: Optional[str] = None  # optional arithmetic expr over other vars (e.g. "NPM3 % 256")


class DeviceType(BaseModel):
    """Master data: a Cisco device type, stored as key/value (slug + display name)."""

    code: str  # slug key, e.g. "iot_gateway"
    label: str  # display name, e.g. "IoT Gateway"


class EndDeviceSpec(BaseModel):
    type: str = Field(
        default="",
        description="Device group / Cisco type, e.g. PC, Server, IoT Gateway.",
    )
    count: str = Field(
        default="0",
        description="Safe expression over the case variables (e.g. \"500 + (NPM3 % 35)\") "
        "for the number of devices of this type; drives subnet sizing only.",
    )
    name: str  # exact device name to verify in the submitted .pkt (graded 5 pts)
    dhcp: bool = True  # whether this end device should be DHCP-configured


class SubnetDef(BaseModel):
    name: str
    end_devices: List[EndDeviceSpec] = Field(
        default_factory=list,
        description="Expected end devices. Each row binds a device type (sizing), a count "
        "expression (subnet size), a device name (graded), and a DHCP flag. "
        "Graded 5 points each (name, DHCP, IP range, mask, gateway).",
    )
    wireless_to: Optional[str] = None  # name of the parent subnet the wireless devices attach to


class GradingConfig(BaseModel):
    auto: List[str] = Field(
        default_factory=lambda: [
            "dhcp_pool",
            "dhcp_mask",
            "dhcp_gateway",
            "gateway",
        ]
    )
    manual: List[str] = Field(
        default_factory=lambda: [
            "note_name_npm",
            "palette_boxes",
            "device_labels",
            "wireless_dots",
        ]
    )


class CaseSchema(BaseModel):
    case_id: str = ""
    title: str
    base_block: str  # e.g. "10.X.64.0/20"
    variables: List[Variable] = Field(default_factory=list)
    subnets: List[SubnetDef] = Field(default_factory=list)
    method: str = "VLSM"  # "VLSM" | "FLSM"
    gateway_is_first_host: bool = False  # True => gateway IS the first usable host
    order_tiebreak: str = "alpha"  # "alpha" | "reverse_alpha" (allocation order tie-break)
    grading: GradingConfig = Field(default_factory=GradingConfig)


# --------------------------------------------------------------------------- #
# Solver output (answer key)
# --------------------------------------------------------------------------- #
class ExpectedSubnet(BaseModel):
    name: str
    network_address: str
    broadcast_address: str
    subnet_mask: str
    prefix: int
    max_end_devices: int       # total addresses in the subnet (2^h)
    max_hosts: int             # usable host addresses (2^h - 2)
    host_first: str
    host_last: str
    gateway: str
    required_devices: Dict[str, int] = Field(default_factory=dict)


class SolveResult(BaseModel):
    case_id: str
    npm: str
    resolved_vars: Dict[str, int] = Field(default_factory=dict)
    subnets: List[ExpectedSubnet] = Field(default_factory=list)
    total_addresses_used: int = 0
    fits_base_block: bool = True


# --------------------------------------------------------------------------- #
# Student submission (normalized, decoder output)
# --------------------------------------------------------------------------- #
class StudentInterface(BaseModel):
    name: str
    ip: Optional[str] = None
    mask: Optional[str] = None
    gateway: Optional[str] = None
    status: str = "up"  # "up" | "down"
    is_wireless: bool = False
    ssid: Optional[str] = None
    dhcp_enabled: bool = False
    dhcp_server_ip: Optional[str] = None  # gateway offered by DHCP (for clients with no static IP)
    connected_device: Optional[str] = None
    connected_interface: Optional[str] = None


class StudentDevice(BaseModel):
    id: str
    name: str
    type: Optional[str] = None
    model: Optional[str] = None
    power: bool = True
    position: Optional[Dict[str, float]] = None
    interfaces: List[StudentInterface] = Field(default_factory=list)
    ip: Optional[str] = None          # convenience: first interface IP (end-devices)
    mask: Optional[str] = None
    gateway: Optional[str] = None
    dhcp_enabled: bool = False


class StudentLink(BaseModel):
    from_device: str
    from_interface: Optional[str] = None
    to_device: str
    to_interface: Optional[str] = None
    type: Optional[str] = None
    status: str = "up"


class StudentDhcpPool(BaseModel):
    router: str
    interface: Optional[str] = None
    name: Optional[str] = None
    network: Optional[str] = None
    mask: Optional[str] = None
    default_gateway: Optional[str] = None
    start_ip: Optional[str] = None
    end_ip: Optional[str] = None


class StudentNote(BaseModel):
    text: str
    position: Optional[Dict[str, float]] = None


class StudentJSON(BaseModel):
    source_file: Optional[str] = None
    devices: List[StudentDevice] = Field(default_factory=list)
    links: List[StudentLink] = Field(default_factory=list)
    dhcp_pools: List[StudentDhcpPool] = Field(default_factory=list)
    notes: List[StudentNote] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Grading output
# --------------------------------------------------------------------------- #
class CheckResult(BaseModel):
    key: str
    label: str
    passed: bool
    fraction: float = 0.0  # 0.0 .. 1.0, proportion of this check satisfied
    score: float
    max_score: float
    detail: str = ""
    expected: str = ""  # expected value (for two-column display)
    actual: str = ""  # value derived from the submitted .pkt


class DeviceGrade(BaseModel):
    name: str
    type: str = ""
    matched: bool = False
    checks: List[CheckResult] = Field(default_factory=list)
    score: float = 0.0
    max_score: float = 5.0


class SubnetGrade(BaseModel):
    name: str
    checks: List[CheckResult] = Field(default_factory=list)
    device_grades: List[DeviceGrade] = Field(default_factory=list)
    score: float = 0.0
    max_score: float = 0.0


class GradeReport(BaseModel):
    case_id: str
    npm: str
    auto_score: float = 0.0
    auto_max: float = 0.0
    manual_items: List[str] = Field(default_factory=list)
    subnet_grades: List[SubnetGrade] = Field(default_factory=list)
    summary: str = ""


class SolveRequest(BaseModel):
    case: CaseSchema
    npm: str


class GradeJsonRequest(BaseModel):
    case: CaseSchema
    npm: str
    student: StudentJSON
