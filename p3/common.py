"""Small helpers shared by the pipeline, validation and reports."""
from __future__ import annotations

from typing import Any, Tuple

KEY = "trajectory_id"  # the only key of every table; raw logs use run_id as their trajectory_id
DETAIL_LIMIT = 200     # longest issue detail written to quality_issues.csv


def short(value: Any, limit: int = DETAIL_LIMIT) -> str:
    """One-line, length-capped text for reports (input-controlled text never spans lines)."""
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[:limit] + "..."


def find_key(obj: Any, keys: Tuple[str, ...], depth: int = 2) -> Any:
    """Value of the first of `keys` at the top level or inside a nested metadata object."""
    if not isinstance(obj, dict):
        return None
    for key in keys:
        if obj.get(key) is not None:
            return obj[key]
    if depth:
        for value in obj.values():
            found = find_key(value, keys, depth - 1)
            if found is not None:
                return found
    return None


def has_key(obj: Any, key: str, depth: int = 2) -> bool:
    """True if `key` exists at the top level or inside a nested metadata object."""
    if not isinstance(obj, dict):
        return False
    return key in obj or (depth > 0 and any(has_key(v, key, depth - 1) for v in obj.values()))
