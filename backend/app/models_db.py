"""ORM models. Grading is ephemeral; cases and master data are persisted."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CaseModel(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    body: Mapped[dict] = mapped_column(JSON)  # full CaseSchema as dict


class DeviceTypeModel(Base):
    __tablename__ = "device_types"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String)

