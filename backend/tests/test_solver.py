import json
import os

import pytest

from app.engine.solver import solve_case
from app.engine.vars import is_valid_npm
from app.schemas import CaseSchema

HERE = os.path.dirname(__file__)
CASE = CaseSchema.model_validate_json(open(os.path.join(HERE, "bgn_case.json")).read())


def test_solver_bgn_example():
    # NPM 2406123456 -> X=56, NPM3=456
    res = solve_case(CASE, "2406123456")
    assert res.resolved_vars == {"X": 56, "NPM3": 456}
    by_name = {s.name: s for s in res.subnets}

    # Order must be largest -> smallest requirement
    assert [s.name for s in res.subnets] == ["CC-MON", "GIB-RAN", "SEKRE", "MEET", "WO2"]

    assert by_name["CC-MON"].required_devices["PC"] == 501
    assert by_name["GIB-RAN"].required_devices["Sensor"] == 135
    assert by_name["SEKRE"].required_devices["IoT Gateway"] == 3
    assert by_name["WO2"].required_devices["Server Application Worker"] == 0
    assert by_name["MEET"].required_devices["Tablet Presensi"] == 6

    # VLSM allocations
    assert by_name["CC-MON"].network_address == "10.56.64.0"
    assert by_name["CC-MON"].prefix == 23
    assert by_name["CC-MON"].gateway == "10.56.64.1"
    assert by_name["GIB-RAN"].network_address == "10.56.66.0"
    assert by_name["GIB-RAN"].prefix == 23
    assert by_name["SEKRE"].network_address == "10.56.68.0"
    assert by_name["SEKRE"].prefix == 26
    assert by_name["MEET"].network_address == "10.56.68.64"
    assert by_name["MEET"].prefix == 26
    assert by_name["WO2"].network_address == "10.56.68.128"
    assert by_name["WO2"].prefix == 28
    assert res.fits_base_block is True


def _tiny_case(subnets: list[tuple[str, int]]):
    return CaseSchema(
        case_id="tiny",
        title="tiny",
        base_block="10.0.0.0/22",
        variables=[],
        subnets=[
            {
                "name": name,
                "end_devices": [
                    {"type": "PC", "count": str(hosts), "name": f"PC {name}", "dhcp": True}
                ],
            }
            for name, hosts in subnets
        ],
        method="VLSM",
    )


def test_solver_other_npm_changes_block():
    res = solve_case(CASE, "2306165660")  # X=60, NPM3=660
    assert res.resolved_vars == {"X": 60, "NPM3": 660}
    assert res.subnets[0].network_address == "10.60.64.0"
    # CC-MON = 500 + (660%35)=500+30=530
    assert res.subnets[0].required_devices["PC"] == 530


def test_allocation_order_host_desc_is_default():
    # AAA (50 hosts) and ZZZ (36 hosts) share the same mask (/26, 64 addr).
    # Default must be host needs descending, so AAA comes first.
    case = _tiny_case([("ZZZ", 36), ("AAA", 50), ("MID", 10)])
    res = solve_case(case, "0")
    assert res.allocation_order == "host_desc"
    assert [s.name for s in res.subnets] == ["AAA", "ZZZ", "MID"]
    # Larger-host block keeps the lower address.
    by_name = {s.name: s for s in res.subnets}
    assert by_name["AAA"].network_address == "10.0.0.0"
    assert by_name["ZZZ"].network_address == "10.0.0.64"


def test_allocation_order_code_desc():
    # Same inputs, but subnet code descending (Z..A) puts ZZZ first,
    # even though AAA needs more hosts. MID (smaller mask) stays last.
    case = _tiny_case([("ZZZ", 36), ("AAA", 50), ("MID", 10)])
    res = solve_case(case, "0", "code_desc")
    assert res.allocation_order == "code_desc"
    assert [s.name for s in res.subnets] == ["ZZZ", "AAA", "MID"]
    by_name = {s.name: s for s in res.subnets}
    assert by_name["ZZZ"].network_address == "10.0.0.0"
    assert by_name["AAA"].network_address == "10.0.0.64"


def test_allocation_order_exact_tie():
    # Identical host counts: host_desc falls back to code ascending (A..Z),
    # code_desc uses code descending (Z..A).
    case = _tiny_case([("ZZZ", 40), ("AAA", 40)])
    assert [s.name for s in solve_case(case, "0", "host_desc").subnets] == ["AAA", "ZZZ"]
    assert [s.name for s in solve_case(case, "0", "code_desc").subnets] == ["ZZZ", "AAA"]


def test_npm_must_be_exactly_ten_digits():
    assert is_valid_npm("2406123456") is True
    assert is_valid_npm(" 2406123456 ") is True
    assert is_valid_npm("240612345") is False      # 9 digits
    assert is_valid_npm("24061234567") is False    # 11 digits
    assert is_valid_npm("240612345a") is False     # letter
    assert is_valid_npm("2406-123-45") is False    # punctuation
    assert is_valid_npm("") is False
    assert is_valid_npm(None) is False
