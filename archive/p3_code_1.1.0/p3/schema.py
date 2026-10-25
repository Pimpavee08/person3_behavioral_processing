"""Frozen feature schema.

P3 declares the schema frozen before P1 labels reach P4. The frozen copy lives
in schema/feature_schema_<version>.json. The pipeline refuses to run when the
code no longer matches it, so a change forces a new feature_set_version.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict

from . import tool_taxonomy as tx
from .features import FEATURE_SET_VERSION, feature_dictionary
from .normalize import CANONICAL_SCHEMA_VERSION, STRUCT_EVENT_KEYS
from .tool_signatures import SIGNATURE_SOURCE, SIGNATURES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FROZEN_PATH = os.path.join(ROOT, "schema", "feature_schema_%s.json" % FEATURE_SET_VERSION)
_FLOAT_PREFIXES = ("frac_", "mean_", "trans_")
_FLOAT_NAMES = {"action_entropy", "first_write_pos", "duration_s"}


class SchemaChangedError(RuntimeError):
    pass


def dtype(name: str) -> str:
    return "float" if name.startswith(_FLOAT_PREFIXES) or name in _FLOAT_NAMES else "int"


def schema_body() -> Dict[str, Any]:
    """Everything that decides a feature value. Descriptions are left out of the hash."""
    specs = feature_dictionary()
    return {
        "feature_set_version": FEATURE_SET_VERSION,
        "canonical_schema_version": CANONICAL_SCHEMA_VERSION,
        "taxonomy_version": tx.TAXONOMY_VERSION,
        "tool_signature_source": SIGNATURE_SOURCE,
        "primary_features": [{"feature": s["feature"], "group": s["group"], "dtype": dtype(s["feature"])}
                             for s in specs if not s["caution"]],
        "secondary_features": [{"feature": s["feature"], "group": s["group"], "caution": s["caution"],
                                "dtype": dtype(s["feature"])} for s in specs if s["caution"]],
        "structural_event_keys": list(STRUCT_EVENT_KEYS),
        "taxonomy": {name: spec._asdict() for name, spec in sorted(tx.TOOLS.items())},
        "recipient_rules": dict(tx._RECIPIENT_ARGS),
        "tool_signatures": {name: {"required": sorted(req), "optional": sorted(opt)}
                            for name, (req, opt) in sorted(SIGNATURES.items())},
    }


def schema_sha256() -> str:
    blob = json.dumps(schema_body(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_frozen() -> Dict[str, Any]:
    """The frozen schema for this feature set version; raise if the code drifted from it."""
    if not os.path.exists(FROZEN_PATH):
        raise SchemaChangedError("no frozen schema at %s" % FROZEN_PATH)
    with open(FROZEN_PATH, encoding="utf-8") as fh:
        frozen = json.load(fh)
    if frozen.get("schema_sha256") != schema_sha256():
        raise SchemaChangedError(
            "feature code differs from frozen %s; bump FEATURE_SET_VERSION and freeze again" % FEATURE_SET_VERSION)
    return frozen
