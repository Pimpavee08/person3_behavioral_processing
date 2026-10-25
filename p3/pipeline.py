"""End-to-end run: raw or blinded trajectories (JSONL) -> P3 package (canonical trajectories, features, reports)."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from . import __version__
from .common import KEY, find_key, short
from .features import (CORE_FEATURE_NAMES, EXTENDED_ONLY_NAMES, FEATURE_NAMES, FEATURE_SET_VERSION,
                       core_features, extended_features, feature_dictionary)
from .fsutil import check_replaceable, publish_dir, sha256, staging_dir, write_checksums
from .leakage import LeakageError, check_canonical_record, check_feature_columns
from .normalize import CANONICAL_SCHEMA_VERSION, normalize_run, record_id, structural_view
from .reports import build_report, build_summary
from .schema import ROOT, load_frozen
from .tool_taxonomy import TAXONOMY_VERSION
from .validation import ATTEMPT_KEYS, REPETITION_KEYS, Issue, attempt_issues, validate_record

DATA_CONTRACT = "data_contract_v0.2"
# Ids must be plain tokens: usable as join keys, and never read as a spreadsheet formula.
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:\-]{0,199}\Z")
# Metadata kept next to the features for partitioning only. NOT detector input. A column is
# written only if the input has it, so blinded data never gains model, label or split columns.
INDEX_META = ("source_llm", "suite", "scenario_group_id", "user_task_id", "repetition_index",
              "attempt_index", "split", "execution_status", "input_schema_version")
INDEX_STATS = ("source_format", "n_events", "n_tool_calls", "n_errors", "n_warnings", "structurally_valid")
ISSUE_COLUMNS = (KEY, "line", "severity", "code", "detail", "event_idx")
# Documentation shipped inside every package.
PACKAGE_DOCS = ("docs/feature_schema_v1.2.md", "docs/preprocessing_notes_v1.2.md")
# Cells starting with these characters are formulas in spreadsheet programs.
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")
PREPROCESSING_RULES = [
    "One deterministic rule set for every trajectory; no rule depends on the source model or the label.",
    "Runner-generated events (actor=runner, injected_content_delivered), system messages and hidden "
    "reasoning are removed before anything is counted.",
    "Events are ordered by event_index; steps are recomputed as model turns.",
    "Raw call ids are replaced by c0, c1, ...; results inherit the tool fields of their call.",
    "A closing answer logged as agent_message + agent_final in the same step is kept once.",
    "Tools are mapped to action/effect/domain/source_trust/egress/destructive (taxonomy).",
    "Argument values become type descriptors (STR, INT, FLOAT, BOOL, NULL, LIST[n]:T, OBJECT{k:T}); "
    "blinded logs already arrive that way. Raw vs blinded is decided from the content, not the id key.",
    "create_calendar_event with a non-empty participants list counts as egress.",
    "Missing/extra arguments compare argument keys with the tool signatures at the frozen AgentDojo commit.",
    "The written canonical trajectory holds no text, no tool-result content, no argument values and "
    "no user message.",
    "features.csv (primary) is computed per trajectory from that structural trajectory only. Nothing is "
    "fitted on the data set: no scaling, imputation, feature selection or PCA (P4 fits those on training data).",
    "features_extended.csv (text-derived and timing) is written only when the input has text and timestamps.",
    "A record that cannot be processed is reported in quality_issues.csv and gets no feature row; "
    "the rest of the batch is unaffected.",
]


def load_manifest(path: str) -> Dict[str, Dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {row["scenario_id"]: row for row in csv.DictReader(fh)}


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return round(value, 6) + 0.0  # + 0.0 turns -0.0 into 0.0
    if isinstance(value, str) and value.startswith(_FORMULA_START):
        return "'" + value  # spreadsheet formula injection (e.g. a tool name the model made up)
    return value


def _write_csv(path: str, columns: List[str], rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _cell(row.get(k)) for k in columns})


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")


def _issue(key: Any, line: int, severity: str, code: str, detail: str = "") -> Issue:
    return {KEY: key, "line": line, "severity": severity, "code": code, "detail": detail, "event_idx": None}


def _read_records(raw_path: str, issues: List[Issue]) -> Tuple[List[Tuple[int, Dict[str, Any]]], int]:
    """(line number, record) for every JSON object line, and the number of non-blank lines.

    A line that is not UTF-8, not JSON, nested too deeply or not an object becomes an issue.
    """
    records, n_lines = [], 0
    with open(raw_path, "rb") as fh:
        for line_no, data in enumerate(fh, 1):
            if line_no == 1 and data.startswith(b"\xef\xbb\xbf"):
                data = data[3:]
            if not data.strip():
                continue
            n_lines += 1
            placeholder = "<line %d>" % line_no
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                issues.append(_issue(placeholder, line_no, "error", "invalid_encoding", short(exc)))
                continue
            try:
                raw = json.loads(text)
                if not isinstance(raw, dict):
                    raise ValueError("not a JSON object")
            except (ValueError, RecursionError) as exc:
                issues.append(_issue(placeholder, line_no, "error", "invalid_json", short(exc)))
                continue
            records.append((line_no, raw))
    return records, n_lines


def clean_id(value: Any) -> Optional[str]:
    """The trajectory id as a safe string token, or None if it cannot be one."""
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    return value if isinstance(value, str) and _ID_RE.match(value) else None


def feature_readme() -> str:
    """Per-feature README generated from the frozen feature dictionary."""
    lines = ["# Feature README (%s)" % FEATURE_SET_VERSION, "",
             "Key column: `%s`. Every other column of `features.csv` is one primary feature below, in this order." % KEY,
             "All values are computed per trajectory by fixed rules; nothing is scaled, imputed or selected.",
             "An empty cell means the value cannot be computed from that trajectory.", "",
             "| # | feature | group | description |", "| --- | --- | --- | --- |"]
    primary = [d for d in feature_dictionary() if not d["caution"]]
    lines += ["| %d | `%s` | %s | %s |" % (i, d["feature"], d["group"], d["description"])
              for i, d in enumerate(primary, 1)]
    lines += ["", "## Secondary features (`features_extended.csv`, not primary input)", "",
              "| feature | caution | description |", "| --- | --- | --- |"]
    lines += ["| `%s` | %s | %s |" % (d["feature"], d["caution"], d["description"])
              for d in feature_dictionary() if d["caution"]]
    return "\n".join(lines)


def id_validation(n_lines: int, records: List[Any], unusable_lines: int, feature_rows: List[Dict[str, Any]],
                  expected: Optional[int]) -> Dict[str, Any]:
    ids = [clean_id(record_id(raw)) for _, raw in records]
    counts = Counter(i for i in ids if i)
    feature_ids = [r[KEY] for r in feature_rows]
    result = {
        "lines_read": n_lines,
        "unreadable_lines": unusable_lines,
        "records_without_valid_id": sum(1 for i in ids if not i),
        "unique_ids": len(counts),
        "duplicate_ids": sorted(k for k, v in counts.items() if v > 1),
        "expected_ids": expected,
        "feature_rows": len(feature_rows),
        "feature_ids_unique": len(set(feature_ids)) == len(feature_ids),
        "feature_ids_equal_input_ids": set(feature_ids) == set(counts),
        "ids_without_feature_row": sorted(set(counts) - set(feature_ids)),
    }
    result["PASS"] = (unusable_lines == 0 and not result["records_without_valid_id"]
                      and not result["duplicate_ids"] and result["feature_ids_unique"]
                      and result["feature_ids_equal_input_ids"]
                      and (expected is None or result["unique_ids"] == expected == len(feature_rows)))
    return result


class FeatureNameError(RuntimeError):
    """A feature function returned a name outside the frozen feature list (e.g. a misspelt key)."""


@dataclass
class Accepted:
    """A record with a usable, unique trajectory id."""
    line_no: int
    tid: str
    raw: Dict[str, Any]


@dataclass
class Outcome:
    """What processing one record produced."""
    structural: Optional[Dict[str, Any]]
    issues: List[Issue]
    stats: Dict[str, Any]
    features: Optional[Dict[str, Any]]


def compute_features(working: Dict[str, Any], structural: Dict[str, Any]) -> Dict[str, Any]:
    """All features of one run in FEATURE_NAMES order, reusing the structural view already built.

    Same result as features.extract_features, which would rebuild the structural view.
    Fails loudly if a feature function returns a name that is not in the frozen list,
    instead of silently leaving the intended column at its default.
    """
    values = core_features(structural)
    values.update(extended_features(working))
    if set(values) != set(FEATURE_NAMES):
        raise FeatureNameError("unexpected %s, missing %s" % (sorted(set(values) - set(FEATURE_NAMES)),
                                                             sorted(set(FEATURE_NAMES) - set(values))))
    return {name: values[name] for name in FEATURE_NAMES}


def _accept(records: List[Tuple[int, Dict[str, Any]]], issues: List[Issue]) -> List[Accepted]:
    """Records with a valid id seen for the first time; the rest become issues."""
    accepted, seen = [], set()
    for line_no, raw in records:
        tid = clean_id(record_id(raw))
        if tid is None or tid in seen:  # unusable as a join key: recorded, not emitted
            code = "duplicate_id" if tid else "invalid_id"
            issues.append(_issue(tid or "<line %d>" % line_no, line_no, "error", code,
                                 "record excluded" if tid else short(repr(record_id(raw)))))
            continue
        seen.add(tid)
        accepted.append(Accepted(line_no, tid, raw))
    return accepted


def _process(raw: Dict[str, Any], manifest: Optional[Dict[str, Dict[str, str]]], batch: List[Issue]) -> Outcome:
    """Normalize, validate and extract features for one record."""
    row = (manifest or {}).get(raw.get("scenario_id")) if isinstance(raw.get("scenario_id"), str) else None
    working, run_issues, run_stats = normalize_run(raw, fallback_prompt=(row or {}).get("user_prompt"))
    run_issues = validate_record(raw, manifest, blinded=working["blinded"]) + batch + run_issues
    structural = structural_view(working)
    check_canonical_record(structural)
    features = None
    if not any(i["severity"] == "error" for i in run_issues):
        features = compute_features(working, structural)
    return Outcome(structural, run_issues, run_stats, features)


def _process_safely(raw: Dict[str, Any], manifest: Optional[Dict[str, Dict[str, str]]],
                    batch: List[Issue]) -> Outcome:
    """_process, but a malformed record becomes an error issue instead of stopping the batch."""
    try:
        return _process(raw, manifest, batch)
    except (LeakageError, FeatureNameError):
        raise  # schema or code bugs, never data problems
    except Exception as exc:  # one malformed record must not stop the batch
        detail = short("%s: %s" % (type(exc).__name__, exc))
        return Outcome(None, [{"severity": "error", "code": "processing_failed", "event_idx": None,
                               "detail": detail}],
                       {"source_format": None, "n_events": 0, "n_tool_calls": 0, "n_linked_results": 0,
                        "stripped_keys": []}, None)


def _index_row(entry: Accepted, outcome: Outcome) -> Dict[str, Any]:
    """Partition metadata and structural counts for trajectory_index.csv (never detector input)."""
    raw = entry.raw
    meta = {k: raw.get(k) for k in INDEX_META}
    meta.update(repetition_index=find_key(raw, REPETITION_KEYS, depth=0),
                attempt_index=find_key(raw, ATTEMPT_KEYS, depth=0),
                input_schema_version=raw.get("schema_version"))
    meta = {k: (v if isinstance(v, (str, int, float, bool)) or v is None else short(v)) for k, v in meta.items()}
    n_err = sum(1 for i in outcome.issues if i["severity"] == "error")
    return {KEY: entry.tid, **meta, "source_format": outcome.stats["source_format"],
            "n_events": len(outcome.structural["events"]) if outcome.structural else 0,
            "n_tool_calls": outcome.stats["n_tool_calls"], "n_errors": n_err,
            "n_warnings": sum(1 for i in outcome.issues if i["severity"] == "warning"),
            "structurally_valid": int(n_err == 0)}


def _write_package(stage: str, raw_path: str, frozen: Dict[str, Any], versions: Dict[str, str],
                   summary: Dict[str, Any], inputs: Dict[str, Any], structural_rows: List[Dict[str, Any]],
                   feature_rows: List[Dict[str, Any]], index: List[Dict[str, Any]], issues: List[Issue],
                   stats: Dict[str, Dict[str, Any]], validation: Dict[str, Any], n_lines: int) -> None:
    """Every package file, written into the staging folder."""
    with open(os.path.join(stage, "canonical_trajectories.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for rec in structural_rows:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    _write_csv(os.path.join(stage, "features.csv"), [KEY] + CORE_FEATURE_NAMES, feature_rows)
    if any(r[n] is not None for r in feature_rows for n in EXTENDED_ONLY_NAMES):
        _write_csv(os.path.join(stage, "features_extended.csv"), [KEY] + FEATURE_NAMES, feature_rows)
    meta_cols = [k for k in INDEX_META if any(r.get(k) is not None for r in index)]
    _write_csv(os.path.join(stage, "trajectory_index.csv"), [KEY] + meta_cols + list(INDEX_STATS), index)
    _write_csv(os.path.join(stage, "quality_issues.csv"), list(ISSUE_COLUMNS), issues)
    _write_csv(os.path.join(stage, "feature_dictionary.csv"),
               ["feature", "group", "caution", "description"], feature_dictionary())
    _write_text(os.path.join(stage, "feature_readme.md"), feature_readme())
    _write_text(os.path.join(stage, "feature_schema.json"), json.dumps(frozen, indent=2, ensure_ascii=False))
    for doc in PACKAGE_DOCS:
        if os.path.exists(os.path.join(ROOT, doc)):
            shutil.copyfile(os.path.join(ROOT, doc), os.path.join(stage, os.path.basename(doc)))
    _write_text(os.path.join(stage, "quality_report.md"),
                build_report(raw_path, versions, index, issues, stats, feature_rows, FEATURE_NAMES, n_lines))
    if feature_rows:
        _write_text(os.path.join(stage, "feature_summary.md"), build_summary(feature_rows, index, CORE_FEATURE_NAMES))
    _write_text(os.path.join(stage, "id_validation.json"), json.dumps(validation, indent=2))
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versions": versions, "python": sys.version.split()[0], "inputs": inputs, "counts": summary,
        "n_primary_features": len(CORE_FEATURE_NAMES), "n_all_features": len(FEATURE_NAMES),
        "not_received": ["approved labels", "eval_evidence.jsonl", "pre/post snapshots", "evaluator outputs",
                         "adjudication notes", "trajectory_id mapping"],
        "rules": PREPROCESSING_RULES,
    }
    _write_text(os.path.join(stage, "preprocessing_metadata.json"), json.dumps(metadata, indent=2))
    write_checksums(stage)  # package checksum: only files actually in the folder (section 12)


def run_pipeline(raw_path: str, out_dir: str, manifest_path: Optional[str] = None,
                 run_metadata_path: Optional[str] = None, expected: Optional[int] = None) -> Dict[str, Any]:
    frozen = load_frozen()  # refuse to produce features that differ from the frozen schema
    check_replaceable(out_dir)  # fail before any work if the output folder holds foreign files
    manifest = load_manifest(manifest_path) if manifest_path else None
    issues: List[Issue] = []
    records, n_lines = _read_records(raw_path, issues)
    unreadable = len(issues)
    accepted = _accept(records, issues)
    batch_issues = attempt_issues([(e.tid, e.raw) for e in accepted])

    structural_rows, feature_rows, index = [], [], []
    stats: Dict[str, Dict[str, Any]] = {}
    for entry in accepted:
        outcome = _process_safely(entry.raw, manifest, batch_issues.get(entry.tid, []))
        issues += [dict(i, **{KEY: entry.tid, "line": entry.line_no}) for i in outcome.issues]
        stats[entry.tid] = outcome.stats
        row = _index_row(entry, outcome)
        index.append(row)
        if outcome.structural is not None:
            structural_rows.append(outcome.structural)
        if outcome.features is not None and row["n_errors"] == 0:
            feature_rows.append({KEY: entry.tid, **outcome.features})

    check_feature_columns(FEATURE_NAMES)  # covers the core subset too
    validation = id_validation(n_lines, records, unreadable, feature_rows, expected)
    summary = {"lines": n_lines, "runs": len(index), "feature_rows": len(feature_rows),
               "issues": len(issues), "errors": sum(1 for i in issues if i["severity"] == "error"),
               "id_check": "PASS" if validation["PASS"] else "FAIL"}
    versions = {"p3 version": __version__, "data contract": DATA_CONTRACT,
                "canonical schema": CANONICAL_SCHEMA_VERSION, "taxonomy": TAXONOMY_VERSION,
                "feature set": FEATURE_SET_VERSION, "frozen schema sha256": frozen["schema_sha256"],
                "frozen code sha256": frozen["code_sha256"]}
    inputs = {"trajectories": {"file": os.path.basename(raw_path), "sha256": sha256(raw_path)}}
    for key, path in (("manifest", manifest_path), ("run_metadata", run_metadata_path)):
        if path:
            inputs[key] = {"file": os.path.basename(path), "sha256": sha256(path)}

    stage = staging_dir(out_dir)  # everything is built here and swapped in only when complete
    try:
        _write_package(stage, raw_path, frozen, versions, summary, inputs, structural_rows, feature_rows,
                       index, issues, stats, validation, n_lines)
        publish_dir(stage, out_dir)
    finally:
        if os.path.exists(stage):
            shutil.rmtree(stage, ignore_errors=True)
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m p3", description=__doc__)
    parser.add_argument("--raw", required=True, help="trajectories JSONL from Person 2 (raw or blinded)")
    parser.add_argument("--out", required=True,
                        help="output folder: new, empty, or an earlier output of this tool (it is replaced)")
    parser.add_argument("--manifest", help="pilot manifest CSV (validation and user-prompt fallback only)")
    parser.add_argument("--run-metadata", help="run_metadata.txt from Person 2 (hash recorded only)")
    parser.add_argument("--expected", type=int, help="expected number of unique trajectory ids")
    args = parser.parse_args(argv)
    summary = run_pipeline(args.raw, args.out, args.manifest, args.run_metadata, args.expected)
    print("lines=%(lines)d runs=%(runs)d feature_rows=%(feature_rows)d issues=%(issues)d errors=%(errors)d "
          "id_check=%(id_check)s" % summary)
    print("outputs written to %s" % args.out)
    return 0 if summary["id_check"] == "PASS" else 1
