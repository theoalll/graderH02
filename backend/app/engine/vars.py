"""Resolve NPM-derived variables (X, NPM3, ...) from a student NPM string."""
from __future__ import annotations

import re
from typing import Dict, List

from app.schemas import Variable
from app.engine.formulas import eval_quantity

# A student NPM is exactly 10 digits. Anything else resolves to wrong values
# without raising, so it is rejected up front.
NPM_PATTERN = re.compile(r"^\d{10}$")


def is_valid_npm(npm: str) -> bool:
    return bool(NPM_PATTERN.match((npm or "").strip()))


def _digits(npm: str) -> str:
    return re.sub(r"\D", "", npm)


def resolve_var_values(npm: str, variables: List[Variable]) -> Dict[str, int]:
    """Returns a mapping name -> integer value for every case variable.

    Supports two kinds of variables:
      * source-based  -> npm_last2 / npm_last3 / const
      * expr-based     -> arithmetic over already-resolved variables
    """
    digits = _digits(npm)
    n = len(digits)
    out: Dict[str, int] = {}
    for v in variables:
        if v.source is None:
            continue  # resolved later via expr
        if v.source.value == "npm_last2":
            out[v.name] = int(digits[-2:]) if n >= 2 else 0
        elif v.source.value == "npm_last3":
            out[v.name] = int(digits[-3:]) if n >= 3 else 0
        elif v.source.value == "const":
            out[v.name] = int(v.value or 0)

    # Resolve expr-based vars (fixpoint: a var may reference another expr var)
    for _ in range(len(variables) + 2):
        progress = False
        for v in variables:
            if v.expr and v.name not in out:
                try:
                    out[v.name] = int(eval_quantity(v.expr, out))
                    progress = True
                except Exception:
                    pass  # depends on a not-yet-resolved var; retry next pass
        if not progress:
            break

    return out
