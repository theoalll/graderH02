"""Grading: devices behind a home gateway are sized but not graded."""
import os

from app.engine.solver import solve_case
from app.grader.score import grade
from app.schemas import CaseSchema, StudentJSON

HERE = os.path.dirname(__file__)
SEED_CASE = CaseSchema.model_validate_json(
    open(os.path.join(HERE, "..", "seed", "bgn_case.json")).read()
)

EXCLUDED = {
    ("GIB-RAN", "Sensor IoT Smart Cold Chain"),
    ("SEKRE", "Mesin Kopi"),
    ("SEKRE", "Speaker Karaoke"),
    ("SEKRE", "Music Player Karaoke"),
    ("MEET", "Gateway MEET"),
}


def test_excluded_devices_are_emitted_and_ungraded():
    solve = solve_case(SEED_CASE, "2406123456")
    flagged = {(s.name, d.name) for s in solve.subnets for d in s.devices if not d.graded}
    assert flagged == EXCLUDED
    # every spec still appears in the expected devices list, with a count
    names = {d.name for s in solve.subnets for d in s.devices}
    assert "Music Player Karaoke" in names
    assert all(d.count >= 0 for s in solve.subnets for d in s.devices)


def test_excluded_devices_still_size_their_subnet():
    solve = solve_case(SEED_CASE, "2406123456")
    by_name = {s.name: s for s in solve.subnets}
    # the home-gateway devices keep contributing to subnet sizing metadata
    assert by_name["GIB-RAN"].required_devices["Sensor"] == 135
    assert by_name["SEKRE"].required_devices["Coffee Machine"] == 3
    assert by_name["SEKRE"].required_devices["Home Speaker"] == 6
    # the layer 2 access point has no IP but still sizes the subnet
    assert by_name["MEET"].required_devices["Access Point"] == 5
    # masks are unchanged by the exclusion
    assert by_name["GIB-RAN"].prefix == 23
    assert by_name["SEKRE"].prefix == 26


def test_grade_hides_excluded_devices():
    solve = solve_case(SEED_CASE, "2406123456")
    report = grade(SEED_CASE, StudentJSON(), solve)
    graded = {dg.name for sg in report.subnet_grades for dg in sg.device_grades}
    assert graded.isdisjoint(n for _, n in EXCLUDED)
    # 5 subnets x 4 network checks = 20, plus 11 graded specs x 5 = 55
    assert report.auto_max == 75.0
    assert report.auto_score == 0.0


def test_recommended_prefix_covers_the_whole_plan():
    solve = solve_case(SEED_CASE, "2406123456")
    # 512 + 512 + 64 + 64 + 16 = 1168 addresses, so the smallest single block is /21
    assert solve.total_addresses_used == 1168
    assert solve.recommended_prefix == 21
    assert solve.recommended_block_size == 2048
    assert solve.recommended_block_size >= solve.total_addresses_used


def test_modulo_counts_never_zero():
    for npm in ("2406123456", "2306165660", "2406000000", "2406999999"):
        solve = solve_case(SEED_CASE, npm)
        for sub in solve.subnets:
            for dev in sub.devices:
                assert dev.count > 0, f"{npm} {sub.name} {dev.name} count is {dev.count}"
