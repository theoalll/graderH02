"""Aggregate checks into a GradeReport.

Scoring model:
  * Each graded end device is worth 5 points, one per check: Name, DHCP,
    IP Range, Subnet Mask, Default Gateway. Devices with
    `exclude_from_grading` (IP assigned by a home gateway) still count toward
    subnet sizing but earn no device points.
  * Each subnet also earns up to 3 network points: DHCP Pool, Gateway on
    router, Links Up (1 point each).
Manual items are surfaced for the TA to verify by eye (not auto-scored).
"""
from __future__ import annotations

from app.grader.checks import (
    check_dhcp_gateway,
    check_dhcp_mask,
    check_dhcp_pool,
    check_gateway,
    grade_end_device,
)
from app.schemas import CaseSchema, CheckResult, GradeReport, SolveResult, StudentJSON, SubnetGrade

# Network-level checks run per subnet: (key, label, callable, weight).
_NETWORK_CHECKS = [
    ("dhcp_pool", "DHCP Pool", check_dhcp_pool, 1.0),
    ("dhcp_mask", "Subnet Mask", check_dhcp_mask, 1.0),
    ("dhcp_gateway", "Default Gateway", check_dhcp_gateway, 1.0),
    ("gateway", "Gateway", check_gateway, 1.0),
]


def grade(case: CaseSchema, student: StudentJSON, solve: SolveResult) -> GradeReport:
    expected_by_name = {s.name: s.end_devices for s in case.subnets}

    subnet_grades: list[SubnetGrade] = []
    total_score = 0.0
    total_max = 0.0

    for sub in solve.subnets:
        checks: list[CheckResult] = []
        sub_score = 0.0
        sub_max = 0.0

        # Network-level checks
        for key, label, fn, weight in _NETWORK_CHECKS:
            frac, detail, expected, actual = fn(sub, student)
            frac = max(0.0, min(1.0, float(frac)))
            cr = CheckResult(
                key=key,
                label=label,
                passed=frac >= 0.999,
                fraction=round(frac, 3),
                score=round(frac * weight, 2),
                max_score=weight,
                detail=detail,
                expected=expected,
                actual=actual,
            )
            checks.append(cr)
            sub_score += cr.score
            sub_max += weight

        # Per-end-device (5-point) grades. Devices behind a home gateway get
        # their IP from that gateway's own pool, so they are not graded.
        device_grades = []
        for ed in expected_by_name.get(sub.name, []):
            if ed.exclude_from_grading:
                continue
            dg = grade_end_device(ed, sub, student)
            device_grades.append(dg)
            sub_score += dg.score
            sub_max += dg.max_score

        subnet_grades.append(
            SubnetGrade(
                name=sub.name,
                checks=checks,
                device_grades=device_grades,
                score=round(sub_score, 2),
                max_score=round(sub_max, 2),
            )
        )
        total_score += sub_score
        total_max += sub_max

    manual = list(case.grading.manual)
    summary = f"Auto-graded {total_score:.1f}/{total_max:.1f}."
    return GradeReport(
        case_id=case.case_id,
        npm=solve.npm,
        auto_score=round(total_score, 2),
        auto_max=round(total_max, 2),
        manual_items=manual,
        subnet_grades=subnet_grades,
        summary=summary,
        allocation_order=getattr(solve, "allocation_order", "host_desc"),
    )
