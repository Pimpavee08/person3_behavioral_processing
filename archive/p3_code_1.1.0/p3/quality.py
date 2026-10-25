"""Record- and batch-level validation (data_contract_v0.2 section 12) and the quality report."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .features import CORE_FEATURE_NAMES
from .normalize import is_blinded, record_id

KEY = "trajectory_id"
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


def _find_key(obj: Any, keys: Tuple[str, ...], depth: int = 2) -> Any:
    """Value of the first of `keys` at the top level or inside a nested metadata object."""
    if not isinstance(obj, dict):
        return None
    for key in keys:
        if obj.get(key) is not None:
            return obj[key]
    if depth:
        for value in obj.values():
            found = _find_key(value, keys, depth - 1)
            if found is not None:
                return found
    return None


def _has_key(obj: Any, key: str, depth: int = 2) -> bool:
    if not isinstance(obj, dict):
        return False
    return key in obj or (depth > 0 and any(_has_key(v, key, depth - 1) for v in obj.values()))


def attempt_issues(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Several attempts of one intended run must name the accepted one (section 3).

    Blinded trajectories carry no run identity, so they cannot be grouped and are skipped.
    """
    groups: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for raw in records:
        if is_blinded(raw):
            continue
        key = (raw.get("scenario_group_id"), raw.get("condition"), raw.get("source_llm"),
               _find_key(raw, REPETITION_KEYS, depth=0))
        groups[key].append(raw)
    out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for key, runs in groups.items():
        if len(runs) < 2:
            continue
        accepted = [r for r in runs if _find_key(r, ACCEPTED_KEYS, depth=0) in (True, 1, "true", "True")]
        if len(accepted) != 1:
            for r in runs:
                out[record_id(r)].append({
                    "severity": "warning", "code": "multiple_attempts_unresolved", "event_idx": None,
                    "detail": "%d runs for %s, %d marked accepted" % (len(runs), "/".join(map(str, key)),
                                                                     len(accepted))})
    return out


def validate_record(raw: Dict[str, Any], manifest: Optional[Dict[str, Dict[str, str]]]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    def add(severity: str, code: str, detail: str = "") -> None:
        issues.append({"severity": severity, "code": code, "detail": detail, "event_idx": None})

    if is_blinded(raw):  # labels, model and run identity were removed upstream on purpose
        missing = [k for k in BLINDED_FIELDS if raw.get(k) is None]
        if missing:
            add("warning", "missing_blinded_field", ", ".join(missing))
        return issues

    missing = [k for k in IDENTITY_FIELDS if raw.get(k) is None]
    if missing:
        add("warning", "missing_identity_field", ", ".join(missing))
    if raw.get("condition") == "ipi":  # section 12: three separate exposure concepts
        absent = [k for k in EXPOSURE_FIELDS if not _has_key(raw, k)]
        if absent:
            add("warning", "exposure_fields_missing", ", ".join(absent))
    condition = raw.get("condition")
    if condition not in ("benign", "ipi"):
        add("error", "invalid_condition", str(condition))
    status = raw.get("execution_status")
    if status is None:
        add("warning", "missing_execution_status")
    elif status not in EXECUTION_STATUSES:
        add("warning", "unknown_execution_status", str(status))
    elif status != "completed":
        add("info", "non_completed_status", str(status))
    if manifest is not None:
        row = manifest.get(raw.get("scenario_id"))
        if row is None:
            add("error", "scenario_not_in_manifest", str(raw.get("scenario_id")))
        elif condition == "ipi":
            logged = _find_key(raw, ("payload_sha256", "attack_payload_sha256"))
            if logged is None:
                add("warning", "missing_payload_hash")
            elif logged != row.get("payload_sha256"):
                add("error", "payload_hash_mismatch", str(logged))
    return issues


def _table(header: List[str], rows: List[List[Any]]) -> List[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(" --- " for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return lines + [""]


def _group_column(index: List[Dict[str, Any]]) -> str:
    """Report grouping: source LLM when the input has it, else suite (blinded data)."""
    return "source_llm" if any(r.get("source_llm") is not None for r in index) else "suite"


def build_report(raw_path: str, versions: Dict[str, str], index: List[Dict[str, Any]],
                 issues: List[Dict[str, Any]], stats: Dict[str, Dict[str, Any]],
                 features: List[Dict[str, Any]], feature_names: List[str], n_lines: int) -> str:
    col = _group_column(index)
    group_of = {r[KEY]: str(r.get(col) or "?") for r in index}
    groups = sorted(set(group_of.values()))
    out = ["# Person 3 Quality Report", "", "Input: `%s`" % raw_path, ""]
    out += ["%s: %s  " % kv for kv in versions.items()] + [""]

    valid = sum(r["structurally_valid"] for r in index)
    out += ["## 1. Summary", ""]
    out += _table(["Item", "Count"], [
        ["Lines read", n_lines],
        ["Trajectories indexed", len(index)],
        ["Structurally valid (features written)", valid],
        ["Excluded from features", len(index) - valid],
        ["Issues: error / warning / info", " / ".join(
            str(sum(1 for i in issues if i["severity"] == s)) for s in ("error", "warning", "info"))],
    ])

    out += ["## 2. Trajectories by %s and execution status" % col, ""]
    statuses = sorted({str(r.get("execution_status") or "n/a") for r in index})
    by = Counter((group_of[r[KEY]], str(r.get("execution_status") or "n/a")) for r in index)
    out += _table([col] + statuses, [[g] + [by[(g, s)] for s in statuses] for g in groups])

    out += ["## 3. Issues", ""]
    if issues:
        grouped: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
        for i in issues:
            grouped[(i["severity"], i["code"])].append(i)
        order = {"error": 0, "warning": 1, "info": 2}
        rows = []
        for (sev, code), items in sorted(grouped.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
            per = Counter(group_of.get(i[KEY], "?") for i in items)
            rows.append([sev, code, len(items), len({i[KEY] for i in items})] + [per[g] for g in groups])
        out += _table(["severity", "code", "issues", "trajectories"] + groups, rows)
    else:
        out += ["No issues.", ""]

    out += ["## 4. Tool call / result pairing", ""]
    agg = defaultdict(lambda: [0, 0])
    for tid, s in stats.items():
        agg[group_of.get(tid, "?")][0] += s["n_tool_calls"]
        agg[group_of.get(tid, "?")][1] += s["n_linked_results"]
    out += _table([col, "tool calls", "linked results", "paired"], [
        [g, c, r, "%.1f%%" % (100.0 * r / c) if c else "n/a"] for g, (c, r) in sorted(agg.items())])

    out += ["## 5. Unmapped tools", "",
            "Tool names outside the 69 AgentDojo v1 tools (e.g. names the model invented). They stay in the "
            "trajectory and are counted by `n_unmapped_tool_calls`.", ""]
    unmapped = Counter(i["detail"] for i in issues if i["code"] == "unmapped_tool")
    out += _table(["tool", "calls"], sorted(unmapped.items())) if unmapped else ["None.", ""]

    out += ["## 6. Raw fields removed during normalization", "",
            "Everything outside the canonical schema is dropped. Keys seen in this input:", ""]
    keys = defaultdict(set)
    for tid, s in stats.items():
        for k in s["stripped_keys"]:
            keys[k].add(group_of.get(tid, "?"))
    out += _table(["raw key", "seen for"], [[k, ", ".join(sorted(v))] for k, v in sorted(keys.items())])

    out += ["## 7. Feature matrix", ""]
    missing = {n: sum(1 for f in features if f[n] is None) for n in feature_names}
    core_missing = {n: v for n, v in missing.items() if n in CORE_FEATURE_NAMES and v}
    constant = [n for n in CORE_FEATURE_NAMES if len({f[n] for f in features}) <= 1]
    out += _table(["Item", "Value"], [
        ["Rows", len(features)],
        ["Primary features (features.csv)", len(CORE_FEATURE_NAMES)],
        ["Primary features with missing values", len(core_missing)],
        ["Constant primary features", len(constant)],
        ["Secondary features fully empty (no text/time in input)",
         sum(1 for n in feature_names if n not in CORE_FEATURE_NAMES and missing[n] == len(features))],
    ])
    if core_missing:
        out += _table(["primary feature", "missing rows"], sorted(core_missing.items()))
    if constant:
        out += ["Constant in this input (no information here): " + ", ".join("`%s`" % n for n in constant), ""]
    return "\n".join(out)


def build_summary(features: List[Dict[str, Any]], index: List[Dict[str, Any]], names: List[str]) -> str:
    """Descriptive statistics of the primary features. Never uses labels or conditions."""
    varying = [n for n in names if len({f[n] for f in features}) > 1]
    lines = ["# Primary feature summary", "",
             "%d trajectories. Descriptive only; nothing here is fitted or used to transform features." % len(features),
             "", "Constant across all trajectories: %s" % (
                 ", ".join("`%s`" % n for n in names if n not in varying) or "none"), ""]

    def values(rows: List[Dict[str, Any]], name: str) -> List[float]:
        return [r[name] for r in rows if r[name] is not None]

    if any(r.get("source_llm") is not None for r in index):  # raw runs: compare models
        meta = {r[KEY]: r for r in index}
        groups: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
        for row in features:
            groups[str(meta[row[KEY]].get("source_llm"))].append(row)
        keys = sorted(groups)
        lines += ["Mean per source LLM. Large differences point to features that identify the model.", "",
                  "| feature | " + " | ".join("%s (n=%d)" % (m, len(groups[m])) for m in keys) + " |",
                  "|---|" + "---:|" * len(keys)]
        for n in varying:
            cells = []
            for k in keys:
                v = values(groups[k], n)
                cells.append("%.2f" % (sum(v) / len(v)) if v else "")
            lines.append("| `%s` | " % n + " | ".join(cells) + " |")
        return "\n".join(lines)

    lines += ["| feature | mean | min | max | share non-zero | missing |", "|---|---:|---:|---:|---:|---:|"]
    for n in varying:
        v = values(features, n)
        if not v:
            continue
        lines.append("| `%s` | %.3f | %g | %g | %.3f | %d |" % (
            n, sum(v) / len(v), min(v), max(v), sum(1 for x in v if x) / len(v), len(features) - len(v)))
    return "\n".join(lines)
