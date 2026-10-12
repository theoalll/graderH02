"""Link helpers for network-level checks."""
from __future__ import annotations

from app.schemas import StudentJSON


def subnet_links(student: StudentJSON, device_names: set) -> list:
    return [
        link
        for link in student.links
        if link.from_device in device_names or link.to_device in device_names
    ]
