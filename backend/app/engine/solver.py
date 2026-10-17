"""Case solver: case + student NPM -> the expected IP-addressing answer key."""
from __future__ import annotations

import ipaddress
from typing import Dict, List

from app.engine.formulas import eval_quantity
from app.engine.vars import resolve_var_values
from app.engine.vlsm import _normalize_allocation_order, allocate
from app.schemas import CaseSchema, ExpectedDevice, ExpectedSubnet, SolveResult, SubnetDef


def _substitute_vars(block: str, variables: Dict[str, int]) -> str:
    for name, val in variables.items():
        block = block.replace(name, str(val))
    return block


def _subnet_hosts(subnet: SubnetDef, variables: Dict[str, int]) -> tuple[int, Dict[str, int]]:
    total = 0
    by_type: Dict[str, int] = {}
    for ed in subnet.end_devices:
        qty = int(eval_quantity(ed.count or "0", variables))
        by_type[ed.type] = by_type.get(ed.type, 0) + qty
        total += qty
    return total, by_type


def _min_prefix(total_used: int) -> int | None:
    """Smallest prefix whose block size can hold `total_used` addresses."""
    if total_used <= 0:
        return None
    size = 1 << (total_used - 1).bit_length()  # next power of two >= total_used
    return 32 - (size.bit_length() - 1)


def solve_case(
    case: CaseSchema, npm: str, allocation_order: str | None = None
) -> SolveResult:
    variables = resolve_var_values(npm, case.variables)
    base_block = _substitute_vars(case.base_block, variables)

    # Per-upload order wins; when omitted, fall back to the case default
    # ("reverse_alpha" -> "code_desc", anything else -> "host_desc").
    effective_order = _normalize_allocation_order(allocation_order, case.order_tiebreak)

    requirements: List[tuple[str, int]] = []
    meta: Dict[str, Dict[str, int]] = {}
    expected_devices: Dict[str, List[ExpectedDevice]] = {}
    for subnet in case.subnets:
        hosts, by_type = _subnet_hosts(subnet, variables)
        requirements.append((subnet.name, hosts))
        meta[subnet.name] = by_type
        expected_devices[subnet.name] = [
            ExpectedDevice(
                name=ed.name,
                type=ed.type,
                count=int(eval_quantity(ed.count or "0", variables)),
                graded=not ed.exclude_from_grading,
            )
            for ed in subnet.end_devices
        ]

    allocs = allocate(
        base_block, requirements, case.method, case.order_tiebreak, effective_order
    )

    # map allocation name -> SubnetDef for metadata
    defs = {s.name: s for s in case.subnets}

    expected: List[ExpectedSubnet] = []
    total_used = 0
    for a in allocs:
        net = ipaddress.ip_network((a.network_int, a.prefix))
        gateway = str(ipaddress.ip_address(a.network_int + 1))
        if case.gateway_is_first_host:
            host_first = gateway  # gateway IS the first usable host
        else:
            host_first = str(ipaddress.ip_address(a.network_int + 2))
        host_last = str(ipaddress.ip_address(a.network_int + a.size - 2))
        broadcast = str(net.broadcast_address)
        expected.append(
            ExpectedSubnet(
                name=a.name,
                network_address=str(net.network_address),
                broadcast_address=broadcast,
                subnet_mask=str(net.netmask),
                prefix=a.prefix,
                max_end_devices=a.size,
                max_hosts=a.size - 2,
                host_first=host_first,
                host_last=host_last,
                gateway=gateway,
                required_devices=meta[a.name],
                devices=expected_devices.get(a.name, []),
            )
        )
        total_used += a.size

    addr_str, prefix_str = base_block.split("/", 1)
    base_broadcast_int = int(ipaddress.ip_address(addr_str)) + (2 ** (32 - int(prefix_str))) - 1
    fits = base_broadcast_int >= (allocs[-1].network_int + allocs[-1].size - 1) if allocs else True

    # Smallest single block that can hold every address this VLSM plan allocates.
    recommended_prefix = _min_prefix(total_used)
    recommended_block_size = (1 << (32 - recommended_prefix)) if recommended_prefix else 0

    return SolveResult(
        case_id=case.case_id,
        npm=npm,
        resolved_vars=variables,
        subnets=expected,
        total_addresses_used=total_used,
        fits_base_block=fits,
        recommended_prefix=recommended_prefix,
        recommended_block_size=recommended_block_size,
        allocation_order=effective_order,
    )
