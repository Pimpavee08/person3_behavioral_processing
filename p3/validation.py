"""Record- and batch-level validation of input trajectories (data_contract_v0.2 sections 3 and 12)."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .common import find_key, has_key, short
from .normalize import is_blinded

Issue = Dict[str, Any]

# Required identity fields of a raw run, data_contract_v0.2 section 3.
IDENTITY_FIELDS = (
    "run_id", "scenario_group_id", "suite", "user_task_id", "condition", "source_llm", "model_id",
    "execution_status",
)
# Fields a blinded P2 trajectory carries (SCHEMA.json of the candidate package).
BLINDED_FIELDS = ("trajectory_id", "suite", "schema_version", "final_output_present", "events")
# v0.2 vocabulary plus the v0.1 spelling kept for archived logs.
EXECUTION_STATUSES = (
    "completed", "api_error", "timeout", "step_limit", "tool_error", "runner_error", "interrupted",
    "incomplete_log", "model_api_error",
)
EXPOSURE_FIELDS = ("ipi_present", "injection_inserted", "injection_encountered")
REPETITION_KEYS = ("repetition_index", "repetition_id")
ATTEMPT_KEYS = ("attempt_index", "attempt_id")
ACCEPTED_KEYS = ("accepted_for_analysis", "attempt_accepted", "accepted")


def _issue(severity: str, code: str, detail: str = "") -> Issue:
    return {"severity": severity, "code": code, "detail": detail, "event_idx": None}


def _plain(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def attempt_issues(pairs: Iterable[Tuple[str, Dict[str, Any]]]) -> Dict[str, List[Issue]]:
    """Several attempts of one intended run must name the accepted one (section 3).

    `pairs` are (trajectory id, raw record). Records without a scenario group and a
    source LLM (blinded trajectories, bare chat logs) carry no run identity and are
    skipped; that cheap check runs before the costlier scan for the blinded format.
    """
    groups: Dict[Any, List[Tuple[str, Dict[str, Any]]]] = defaultdict(list)
    for tid, raw in pairs:
        key = (raw.get("scenario_group_id"), raw.get("condition"), raw.get("source_llm"),
               find_key(raw, REPETITION_KEYS, depth=0))
        if key[0] is None or key[2] is None or not all(_plain(k) for k in key) or is_blinded(raw):
            continue
        groups[key].append((tid, raw))
    out: Dict[str, List[Issue]] = defaultdict(list)
    for key, runs in groups.items():
        if len(runs) < 2:
            continue
        accepted = [r for _, r in runs if find_key(r, ACCEPTED_KEYS, depth=0) in (True, 1, "true", "True")]
        if len(accepted) != 1:
            detail = "%d runs for %s, %d marked accepted" % (len(runs), "/".join(map(str, key)), len(accepted))
            for tid, _ in runs:
                out[tid].append(_issue("warning", "multiple_attempts_unresolved", detail))
    return out


def _validate_blinded(raw: Dict[str, Any]) -> List[Issue]:
    """Labels, model and run identity were removed upstream on purpose; only check the blinded fields."""
    missing = [k for k in BLINDED_FIELDS if raw.get(k) is None]
    return [_issue("warning", "missing_blinded_field", ", ".join(missing))] if missing else []


def _validate_raw(raw: Dict[str, Any], manifest: Optional[Dict[str, Dict[str, str]]]) -> List[Issue]:
    issues: List[Issue] = []
    missing = [k for k in IDENTITY_FIELDS if raw.get(k) is None]
    if missing:
        issues.append(_issue("warning", "missing_identity_field", ", ".join(missing)))
    condition = raw.get("condition")
    if condition == "ipi":  # section 12: three separate exposure concepts
        absent = [k for k in EXPOSURE_FIELDS if not has_key(raw, k)]
        if absent:
            issues.append(_issue("warning", "exposure_fields_missing", ", ".join(absent)))
    if condition not in ("benign", "ipi"):  # a label field: reported, but features never depend on it
        code = "missing_condition" if condition is None else "invalid_condition"
        issues.append(_issue("warning", code, short(condition)))
    status = raw.get("execution_status")
    if status is None:
        issues.append(_issue("warning", "missing_execution_status"))
    elif status not in EXECUTION_STATUSES:
        issues.append(_issue("warning", "unknown_execution_status", short(status)))
    elif status != "completed":
        issues.append(_issue("info", "non_completed_status", short(status)))
    if manifest is not None:
        row = manifest.get(raw.get("scenario_id"))
        if row is None:
            issues.append(_issue("error", "scenario_not_in_manifest", short(raw.get("scenario_id"))))
        elif condition == "ipi":
            logged = find_key(raw, ("payload_sha256", "attack_payload_sha256"))
            if logged is None:
                issues.append(_issue("warning", "missing_payload_hash"))
            elif logged != row.get("payload_sha256"):
                issues.append(_issue("error", "payload_hash_mismatch", short(logged)))
    return issues


def validate_record(raw: Dict[str, Any], manifest: Optional[Dict[str, Dict[str, str]]],
                    blinded: Optional[bool] = None) -> List[Issue]:
    """Issues about one record's identity and metadata. `blinded` may be passed if already known."""
    if blinded is None:
        blinded = is_blinded(raw)
    return _validate_blinded(raw) if blinded else _validate_raw(raw, manifest)
