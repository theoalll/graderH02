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


def _normalize_allocation_order(order: str | None, tiebreak: str | None = None) -> str:
    """Map legacy tiebreak values and validate the per-upload allocation order.

    Valid orders:
      * "host_desc" - same-mask ties broken by host requirement, descending,
        then subnet code ascending (A..Z) for determinism.
      * "code_desc" - same-mask ties broken by subnet code, descending (Z..A).
    Legacy aliases: "alpha" -> "host_desc", "reverse_alpha" -> "code_desc".
    """
    if order is None:
        order = tiebreak if tiebreak in ("host_desc", "code_desc") else None
    if order is None:
        if tiebreak == "reverse_alpha":
            return "code_desc"
        # "alpha" and anything else fall back to the default behavior.
        return "host_desc"
    if order == "alpha":
        return "host_desc"
    if order == "reverse_alpha":
        return "code_desc"
    if order not in ("host_desc", "code_desc"):
        raise ValueError(f"Invalid allocation_order '{order}': expected 'host_desc' or 'code_desc'")
    return order


def allocate(
    base_block: str,
    requirements: List[tuple[str, int]],
    method: str = "VLSM",
    tiebreak: str = "alpha",
    allocation_order: Optional[str] = None,
) -> List[Allocation]:
    # Use the LITERAL base address as the allocation start. Packet Tracer VLSM starts
    # allocating from the given network address (e.g. 10.148.124.0/21 begins at
    # .124.0, NOT the /21 network boundary .120.0). Do NOT snap to the prefix boundary.
    addr_str, prefix_str = base_block.split("/", 1)
    base_int = int(ipaddress.ip_address(addr_str))
    prefix = int(prefix_str)
    base_size = 2 ** (32 - prefix)
    base_broadcast_int = base_int + base_size - 1

    order = _normalize_allocation_order(allocation_order, tiebreak)
    # Primary: allocated block size, largest first (standard VLSM).
    # Same-mask ties are user-selectable per upload:
    #   host_desc -> host requirement descending, then code ascending (A..Z).
    #   code_desc -> subnet code descending (Z..A).
    if order == "code_desc":
        # Stable two-pass sort: code Z..A first, then size largest-first.
        # Python sort is stable, so equal sizes keep the Z..A code order.
        requirements = sorted(requirements, key=lambda r: r[0].upper(), reverse=True)
        requirements = sorted(requirements, key=lambda r: -_size_for_hosts(r[1]))
    else:  # host_desc (default, backward compatible)
        requirements = sorted(
            requirements, key=lambda r: (-_size_for_hosts(r[1]), -r[1], r[0].upper())
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
