"""Argument type descriptors (the P2 blinded format: STR, INT, FLOAT, BOOL, NULL, LIST[n]:T, OBJECT{k:T}).

Raw argument values are converted to the same descriptors, so blinded and raw
logs are reduced to identical structure. A descriptor never carries a value.
"""
from __future__ import annotations

import re
from typing import Any

_LIST_RE = re.compile(r"^LIST\[(\d+)\]")
_DESCRIPTOR_RE = re.compile(r"(STR|INT|FLOAT|BOOL|NULL|OTHER|LIST\[\d+\](:.+)?|OBJECT\{.*\})\Z")


_MAX_DEPTH = 32  # deeper structures are summarised as OTHER instead of recursing further


def describe(value: Any, _depth: int = 0) -> str:
    """Descriptor of a raw argument value."""
    if _depth > _MAX_DEPTH:
        return "OTHER"
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT"
    if isinstance(value, float):
        return "FLOAT"
    if isinstance(value, str):
        return "STR"
    if isinstance(value, (list, tuple)):
        inner = sorted({describe(v, _depth + 1) for v in value})
        return "LIST[%d]" % len(value) + (":" + "|".join(inner) if inner else "")
    if isinstance(value, dict):
        return "OBJECT{%s}" % ",".join("%s:%s" % (k, describe(v, _depth + 1))
                                       for k, v in sorted(value.items(), key=lambda kv: str(kv[0])))
    return "OTHER"


def is_descriptor(value: Any) -> bool:
    return isinstance(value, str) and _DESCRIPTOR_RE.match(value) is not None


def type_label(descriptor: str) -> str:
    """Coarse type class used by features."""
    if descriptor == "STR":
        return "str"
    if descriptor in ("INT", "FLOAT"):
        return "number"
    if descriptor == "BOOL":
        return "bool"
    if descriptor == "NULL":
        return "null"
    match = _LIST_RE.match(descriptor)
    if match:
        return "list" if int(match.group(1)) else "empty_list"
    if descriptor.startswith("OBJECT{"):
        return "empty_object" if descriptor == "OBJECT{}" else "object"
    return "other"


def is_nonempty(descriptor: str) -> bool:
    """False for NULL, LIST[0] and OBJECT{}; strings count as non-empty (their length is not kept)."""
    return type_label(descriptor) not in ("null", "empty_list", "empty_object")
