"""Minimal shared-credential auth (single TA). Token stored in memory."""
from __future__ import annotations

import os
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Header

_VALID_TOKENS: set[str] = set()

EXPECTED_USERNAME = os.getenv("APP_USERNAME", "admin")
EXPECTED_PASSWORD = os.getenv("APP_PASSWORD", "admin")


def login(username: str, password: str) -> Optional[str]:
    if username == EXPECTED_USERNAME and password == EXPECTED_PASSWORD:
        token = secrets.token_hex(16)
        _VALID_TOKENS.add(token)
        return token
    return None


def logout(token: str) -> None:
    _VALID_TOKENS.discard(token)


def _extract_token(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return authorization


def require_auth(authorization: Optional[str] = Header(default=None)) -> str:
    token = _extract_token(authorization)
    if not token or token not in _VALID_TOKENS:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token
