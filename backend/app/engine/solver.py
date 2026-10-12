"""Case solver: case + student NPM -> the expected IP-addressing answer key."""
from __future__ import annotations

import ipaddress
from typing import Dict, List

from app.engine.formulas import eval_quantity
from app.engine.vars import resolve_var_values
from app.engine.vlsm import allocate
from app.schemas import CaseSchema, ExpectedSubnet, SolveResult, SubnetDef


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


def solve_case(case: CaseSchema, npm: str) -> SolveResult:
    variables = resolve_var_values(npm, case.variables)
    base_block = _substitute_vars(case.base_block, variables)

    requirements: List[tuple[str, int]] = []
    meta: Dict[str, Dict[str, int]] = {}
    for subnet in case.subnets:
        hosts, by_type = _subnet_hosts(subnet, variables)
        requirements.append((subnet.name, hosts))
        meta[subnet.name] = by_type

    allocs = allocate(base_block, requirements, case.method, case.order_tiebreak)

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
            )
        )
        total_used += a.size

    addr_str, prefix_str = base_block.split("/", 1)
    base_broadcast_int = int(ipaddress.ip_address(addr_str)) + (2 ** (32 - int(prefix_str))) - 1
    fits = base_broadcast_int >= (allocs[-1].network_int + allocs[-1].size - 1) if allocs else True

    return SolveResult(
        case_id=case.case_id,
        npm=npm,
        resolved_vars=variables,
        subnets=expected,
        total_addresses_used=total_used,
        fits_base_block=fits,
    )
