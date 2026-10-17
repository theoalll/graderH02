"""Postgres-backed case storage (replaces the file-based store)."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models_db import CaseModel
from app.schemas import CaseSchema

_SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def _seed_if_empty() -> None:
    """Refresh every case in the seed directory from its JSON file.

    Cases are matched by case_id and overwritten with the file contents, so
    editing a seed file and restarting the server always reflects the change.
    Cases created via the UI (different case_ids) are never touched."""
    if not _SEED_DIR.exists():
        return
    for path in sorted(_SEED_DIR.glob("*_case.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(data, dict):
            continue
        case_id = data.get("case_id")
        if not case_id:
            continue
        try:
            save_case(CaseSchema.model_validate(data))
        except Exception:  # noqa: BLE001
            pass


def list_cases() -> list[dict]:
    with SessionLocal() as s:
        rows = s.scalars(select(CaseModel).order_by(CaseModel.case_id)).all()
        summaries = []
        for r in rows:
            body = r.body if isinstance(r.body, dict) else {}
            subnets = body.get("subnets")
            summaries.append(
                {
                    "case_id": r.case_id,
                    "title": r.title,
                    "base_block": body.get("base_block"),
                    "method": body.get("method"),
                    "subnet_count": len(subnets) if isinstance(subnets, list) else 0,
                }
            )
        return summaries


def get_case(case_id: str) -> CaseSchema | None:
    with SessionLocal() as s:
        row = s.scalars(select(CaseModel).where(CaseModel.case_id == case_id)).first()
        if not row:
            return None
        return CaseSchema.model_validate(row.body)


def save_case(case: CaseSchema) -> CaseSchema:
    # Auto-generate a UUID when the caller did not supply a case_id (e.g. a new
    # case created from the UI). Existing cases keep their id.
    if not case.case_id:
        case = case.model_copy(update={"case_id": str(uuid.uuid4())})
    with SessionLocal() as s:
        row = s.scalars(select(CaseModel).where(CaseModel.case_id == case.case_id)).first()
        if row:
            row.title = case.title
            row.body = case.model_dump()
        else:
            row = CaseModel(
                case_id=case.case_id, title=case.title, body=case.model_dump()
            )
            s.add(row)
        s.commit()
    return case


def delete_case(case_id: str) -> bool:
    with SessionLocal() as s:
        row = s.scalars(select(CaseModel).where(CaseModel.case_id == case_id)).first()
        if not row:
            return False
        s.delete(row)
        s.commit()
        return True
