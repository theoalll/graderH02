"""
VLSM / FLSM subnet allocator.

Given a base block and a list of (name, needed_hosts) requirements, it returns
contiguous allocations in descending size order (the standard VLSM approach).
Also supports FLSM (every subnet gets the size of the largest requirement).
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Allocation:
    name: str
    network_int: int
    prefix: int
    size: int  # number of addresses (power of two)


def _size_for_hosts(hosts: int) -> int:
    """Smallest power-of-two address block that fits `hosts` end-devices plus the
    default gateway. Usable = size - 2, so we need size - 2 >= hosts + 1,
    i.e. size >= hosts + 3."""
    need = hosts + 3
    size = 1
    while size < need:
        size <<= 1
    # a /32 or /31 are pathological for host ranges; enforce at least /30 (4 addr)
    return max(size, 4)


def _prefix_for_size(size: int) -> int:
    return 32 - (size.bit_length() - 1)


def _tie_key(name: str, reverse: bool):
    """Tie-break by subnet name. reverse=True -> reverse-alphabetical (Z..A)."""
    return tuple(-ord(c) for c in name.upper()) if reverse else name.upper()


def allocate(
    base_block: str,
    requirements: List[tuple[str, int]],
    method: str = "VLSM",
    tiebreak: str = "alpha",
) -> List[Allocation]:
    # Use the LITERAL base address as the allocation start. Packet Tracer VLSM starts
    # allocating from the given network address (e.g. 10.148.124.0/21 begins at
    # .124.0, NOT the /21 network boundary .120.0). Do NOT snap to the prefix boundary.
    addr_str, prefix_str = base_block.split("/", 1)
    base_int = int(ipaddress.ip_address(addr_str))
    prefix = int(prefix_str)
    base_size = 2 ** (32 - prefix)
    base_broadcast_int = base_int + base_size - 1

    reverse = tiebreak == "reverse_alpha"
    # Order by allocated block size (largest first); equal sizes broken by name.
    requirements = sorted(
        requirements, key=lambda r: (-_size_for_hosts(r[1]), _tie_key(r[0], reverse))
    )

    if method.upper() == "FLSM":
        max_size = max(_size_for_hosts(h) for _, h in requirements)
        allocs = [
            Allocation(name=name, network_int=0, prefix=_prefix_for_size(max_size), size=max_size)
            for name, _ in requirements
        ]
    else:  # VLSM: largest block first
        allocs = [
            Allocation(
                name=name,
                network_int=0,
                prefix=_prefix_for_size(_size_for_hosts(h)),
                size=_size_for_hosts(h),
            )
            for name, h in requirements
        ]

    current = base_int
    out: List[Allocation] = []
    for a in allocs:
        aligned = (current // a.size) * a.size  # keep power-of-two alignment
        if aligned + a.size - 1 > base_broadcast_int:
            raise ValueError(
                f"Subnet '{a.name}' ({a.size} addr) does not fit inside base block {base_block}"
            )
        out.append(Allocation(name=a.name, network_int=aligned, prefix=a.prefix, size=a.size))
        current = aligned + a.size
    return out
