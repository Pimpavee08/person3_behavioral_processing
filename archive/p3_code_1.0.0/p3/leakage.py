"""Guards for data_contract_v0.2 sections 11-12 (detector input restrictions)."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .normalize import RECORD_KEYS, STRUCT_EVENT_KEYS

# Column names that must never appear in the feature matrix.
FORBIDDEN_FEATURE_COLUMNS = {
    # ground truth and evaluator output
    "ipi_present", "injection_inserted", "injection_encountered", "ipi_affected",
    "benchmark_security", "benchmark_utility", "strict_attack_succeeded", "user_task_succeeded",
    "adjudicated_user_task_succeeded", "adjudication_status", "annotation_status", "annotation_note",
    "annotation_notes", "evidence_event_indices", "utility", "security", "label", "target",
    # attacker side
    "attacker_goal", "payload", "payload_sha256", "attack_payload_sha256", "attack_template",
    "attack_template_id", "injection_task_id", "injection_vector_id", "selected_injection_vector",
    "expected_actions",
    # scenario, model and runtime identity
    "scenario_id", "scenario_group_id", "suite", "user_task_id", "condition", "split",
    "source_llm", "model_id", "model_digest", "provider", "execution_status", "usage_total",
}

# Event keys that would carry raw text or raw argument values.
RAW_CONTENT_KEYS = {"text", "args", "content", "content_text", "tool_result", "tool_arguments"}


class LeakageError(ValueError):
    pass


def check_feature_columns(columns: Iterable[str]) -> None:
    """Raise if a feature column is a label, an identity field or an attack field."""
    bad = sorted(c for c in columns if c.lower() in FORBIDDEN_FEATURE_COLUMNS)
    if bad:
        raise LeakageError("forbidden columns in feature matrix: %s" % ", ".join(bad))


def check_canonical_record(record: Dict[str, Any]) -> None:
    """Raise unless a structural record has exactly the whitelisted, text-free keys."""
    extra: List[str] = sorted(set(record) - set(RECORD_KEYS))
    for ev in record.get("events", []):
        extra += sorted(set(ev) ^ set(STRUCT_EVENT_KEYS))
        extra += sorted(RAW_CONTENT_KEYS & set(ev))
    if extra:
        raise LeakageError("non-canonical keys: %s" % ", ".join(sorted(set(extra))))
