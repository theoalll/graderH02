import json
import os

import pytest

from app.engine.solver import solve_case
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


def test_solver_other_npm_changes_block():
    res = solve_case(CASE, "2306165660")  # X=60, NPM3=660
    assert res.resolved_vars == {"X": 60, "NPM3": 660}
    assert res.subnets[0].network_address == "10.60.64.0"
    # CC-MON = 500 + (660%35)=500+30=530
    assert res.subnets[0].required_devices["PC"] == 530
