"""Master data: device types (TA-editable, seeded with Cisco Packet Tracer types)."""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models_db import DeviceTypeModel
from app.schemas import DeviceType

_SEED_FILE = Path(__file__).resolve().parent.parent / "seed" / "device_types.json"

# Default seed: common Cisco Packet Tracer device types, stored as key/value
# (slug key -> display name).
_SEED_DEFAULT = [
    {"code": "pc", "label": "PC"},
    {"code": "laptop", "label": "Laptop"},
    {"code": "server", "label": "Server"},
    {"code": "printer", "label": "Printer"},
    {"code": "tablet", "label": "Tablet"},
    {"code": "smartphone", "label": "Smartphone"},
    {"code": "end_device", "label": "End Device"},
    {"code": "iot_gateway", "label": "IoT Gateway"},
    {"code": "sensor", "label": "Sensor"},
    {"code": "smart_device", "label": "Smart Device"},
    {"code": "home_speaker", "label": "Home Speaker"},
    {"code": "portable_music_player", "label": "Portable Music Player"},
    {"code": "coffee_machine", "label": "Coffee Machine"},
    {"code": "access_point", "label": "Access Point"},
    {"code": "switch", "label": "Switch"},
    {"code": "router", "label": "Router"},
    {"code": "wireless_router", "label": "Wireless Router"},
]


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def _seed() -> None:
    data = _SEED_DEFAULT
    if _SEED_FILE.exists():
        try:
            data = json.loads(_SEED_FILE.read_text())
        except Exception:  # noqa: BLE001
            data = _SEED_DEFAULT
    # Replace existing rows so stale entries (e.g. from the old 3-field schema) are cleared.
    with SessionLocal() as s:
        s.query(DeviceTypeModel).delete()
        for d in data:
            s.add(DeviceTypeModel(code=d["code"], label=d["label"]))
        s.commit()


def list_device_types() -> list[DeviceType]:
    with SessionLocal() as s:
        rows = s.scalars(select(DeviceTypeModel).order_by(DeviceTypeModel.label)).all()
        return [DeviceType(code=r.code, label=r.label) for r in rows]


def create_device_type(d: DeviceType) -> DeviceType:
    with SessionLocal() as s:
        if s.get(DeviceTypeModel, d.code):
            raise ValueError(f"Device type '{d.code}' already exists")
        s.add(DeviceTypeModel(code=d.code, label=d.label))
        s.commit()
    return d


def update_device_type(code: str, d: DeviceType) -> DeviceType:
    with SessionLocal() as s:
        row = s.get(DeviceTypeModel, code)
        if not row:
            raise KeyError(code)
        row.label = d.label
        s.commit()
    return d


def delete_device_type(code: str) -> None:
    with SessionLocal() as s:
        row = s.get(DeviceTypeModel, code)
        if not row:
            raise KeyError(code)
        s.delete(row)
        s.commit()
