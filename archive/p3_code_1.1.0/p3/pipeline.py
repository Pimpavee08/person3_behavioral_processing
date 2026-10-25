"""End-to-end run: raw or blinded trajectories (JSONL) -> P3 package (canonical trajectories, features, reports)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import __version__
from .features import (CORE_FEATURE_NAMES, EXTENDED_ONLY_NAMES, FEATURE_NAMES, FEATURE_SET_VERSION,
                       extract_features, feature_dictionary)
from .leakage import check_canonical_record, check_feature_columns
from .normalize import CANONICAL_SCHEMA_VERSION, normalize_run, record_id, structural_view
from .quality import (ATTEMPT_KEYS, REPETITION_KEYS, _find_key, attempt_issues, build_report, build_summary,
                      validate_record)
from .schema import ROOT, load_frozen
from .tool_taxonomy import TAXONOMY_VERSION

DATA_CONTRACT = "data_contract_v0.2"
KEY = "trajectory_id"  # the only key of every table; raw logs use run_id as their trajectory_id
# Metadata kept next to the features for partitioning only. NOT detector input. A column is
# written only if the input has it, so blinded data never gains model, label or split columns.
INDEX_META = ("source_llm", "suite", "scenario_group_id", "user_task_id", "repetition_index",
              "attempt_index", "split", "execution_status", "input_schema_version")
INDEX_STATS = ("source_format", "n_events", "n_tool_calls", "n_errors", "n_warnings", "structurally_valid")
ISSUE_COLUMNS = (KEY, "line", "severity", "code", "detail", "event_idx")
# Documentation shipped inside every package.
PACKAGE_DOCS = ("docs/feature_schema_v1.1.md", "docs/preprocessing_notes_v1.1.md")
PREPROCESSING_RULES = [
    "One deterministic rule set for every trajectory; no rule depends on the source model or the label.",
    "Runner events (injected_content_delivered), system messages and hidden reasoning are removed.",
    "Events are ordered by event_index; steps are recomputed as model turns.",
    "Raw call ids are replaced by c0, c1, ...; results inherit the tool fields of their call.",
    "A closing answer logged as agent_message + agent_final in the same step is kept once.",
    "Tools are mapped to action/effect/domain/source_trust/egress/destructive (taxonomy).",
    "Argument values become type descriptors (STR, INT, FLOAT, BOOL, NULL, LIST[n]:T, OBJECT{k:T}); "
    "blinded logs already arrive that way.",
    "create_calendar_event with a non-empty participants list counts as egress.",
    "Missing/extra arguments compare argument keys with the tool signatures at the frozen AgentDojo commit.",
    "The written canonical trajectory holds no text, no tool-result content, no argument values and "
    "no user message.",
    "features.csv (primary) is computed per trajectory from that structural trajectory only. Nothing is "
    "fitted on the data set: no scaling, imputation, feature selection or PCA (P4 fits those on training data).",
    "features_extended.csv (text-derived and timing) is written only when the input has text and timestamps.",
]


def load_manifest(path: str) -> Dict[str, Dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {row["scenario_id"]: row for row in csv.DictReader(fh)}


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    return round(value, 6) if isinstance(value, float) else value


def _write_csv(path: str, columns: List[str], rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _cell(row.get(k)) for k in columns})


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")


def _read_records(raw_path: str, issues: List[Dict[str, Any]]) -> List[Any]:
    """(line number, record) for every JSON object line; bad lines become issues."""
    records = []
    with open(raw_path, encoding="utf-8-sig") as fh:
        for line_no, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("not a JSON object")
            except ValueError as exc:
                issues.append({KEY: "<line %d>" % line_no, "line": line_no, "severity": "error",
                               "code": "invalid_json", "detail": str(exc), "event_idx": None})
                continue
            records.append((line_no, raw))
    return records


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


def id_validation(records: List[Any], n_invalid: int, feature_rows: List[Dict[str, Any]],
                  expected: Optional[int]) -> Dict[str, Any]:
    ids = [record_id(raw) for _, raw in records]
    counts = Counter(i for i in ids if i)
    feature_ids = [r[KEY] for r in feature_rows]
    result = {
        "records_read": len(records),
        "invalid_json_lines": n_invalid,
        "records_without_id": sum(1 for i in ids if not i),
        "unique_ids": len(counts),
        "duplicate_ids": sorted(k for k, v in counts.items() if v > 1),
        "expected_ids": expected,
        "feature_rows": len(feature_rows),
        "feature_ids_unique": len(set(feature_ids)) == len(feature_ids),
        "feature_ids_equal_input_ids": set(feature_ids) == set(counts),
        "ids_without_feature_row": sorted(set(counts) - set(feature_ids)),
    }
    result["PASS"] = (n_invalid == 0 and not result["records_without_id"] and not result["duplicate_ids"]
                      and result["feature_ids_unique"] and result["feature_ids_equal_input_ids"]
                      and (expected is None or result["unique_ids"] == expected == len(feature_rows)))
    return result


def run_pipeline(raw_path: str, out_dir: str, manifest_path: Optional[str] = None,
                 run_metadata_path: Optional[str] = None, expected: Optional[int] = None) -> Dict[str, Any]:
    frozen = load_frozen()  # refuse to produce features that differ from the frozen schema
    manifest = load_manifest(manifest_path) if manifest_path else None
    os.makedirs(out_dir, exist_ok=True)
    issues: List[Dict[str, Any]] = []
    records = _read_records(raw_path, issues)
    n_invalid = len(issues)
    n_lines = len(records) + n_invalid

    accepted, seen = [], set()
    for line_no, raw in records:
        tid = record_id(raw)
        if not tid or tid in seen:  # unusable as a join key: recorded, not emitted
            issues.append({KEY: tid or "<line %d>" % line_no, "line": line_no, "severity": "error",
                           "code": "duplicate_id" if tid else "missing_id",
                           "detail": "record excluded", "event_idx": None})
            continue
        seen.add(tid)
        accepted.append((line_no, raw))
    batch_issues = attempt_issues([raw for _, raw in accepted])

    structural_rows, feature_rows, index = [], [], []
    stats: Dict[str, Dict[str, Any]] = {}
    for line_no, raw in accepted:
        tid = record_id(raw)
        row = (manifest or {}).get(raw.get("scenario_id")) or {}
        working, run_issues, run_stats = normalize_run(raw, fallback_prompt=row.get("user_prompt"))
        run_issues = validate_record(raw, manifest) + batch_issues.get(tid, []) + run_issues
        structural = structural_view(working)
        check_canonical_record(structural)
        issues += [dict(i, **{KEY: tid, "line": line_no}) for i in run_issues]
        n_err = sum(1 for i in run_issues if i["severity"] == "error")
        stats[tid] = run_stats
        meta = {k: raw.get(k) for k in INDEX_META}
        meta.update(repetition_index=_find_key(raw, REPETITION_KEYS, depth=0),
                    attempt_index=_find_key(raw, ATTEMPT_KEYS, depth=0),
                    input_schema_version=raw.get("schema_version"))
        index.append({KEY: tid, **meta, "source_format": run_stats["source_format"],
                      "n_events": len(structural["events"]), "n_tool_calls": run_stats["n_tool_calls"],
                      "n_errors": n_err, "n_warnings": sum(1 for i in run_issues if i["severity"] == "warning"),
                      "structurally_valid": int(n_err == 0)})
        structural_rows.append(structural)
        if n_err == 0:
            feature_rows.append({KEY: tid, **extract_features(working)})

    check_feature_columns(FEATURE_NAMES)  # covers the core subset too
    with open(os.path.join(out_dir, "canonical_trajectories.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for rec in structural_rows:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    _write_csv(os.path.join(out_dir, "features.csv"), [KEY] + CORE_FEATURE_NAMES, feature_rows)
    if any(r[n] is not None for r in feature_rows for n in EXTENDED_ONLY_NAMES):
        _write_csv(os.path.join(out_dir, "features_extended.csv"), [KEY] + FEATURE_NAMES, feature_rows)
    meta_cols = [k for k in INDEX_META if any(r.get(k) is not None for r in index)]
    _write_csv(os.path.join(out_dir, "trajectory_index.csv"), [KEY] + meta_cols + list(INDEX_STATS), index)
    _write_csv(os.path.join(out_dir, "quality_issues.csv"), list(ISSUE_COLUMNS), issues)
    _write_csv(os.path.join(out_dir, "feature_dictionary.csv"),
               ["feature", "group", "caution", "description"], feature_dictionary())
    _write_text(os.path.join(out_dir, "feature_readme.md"), feature_readme())
    versions = {"p3 version": __version__, "data contract": DATA_CONTRACT,
                "canonical schema": CANONICAL_SCHEMA_VERSION, "taxonomy": TAXONOMY_VERSION,
                "feature set": FEATURE_SET_VERSION, "frozen schema sha256": frozen["schema_sha256"]}
    _write_text(os.path.join(out_dir, "feature_schema.json"), json.dumps(frozen, indent=2, ensure_ascii=False))
    for doc in PACKAGE_DOCS:
        if os.path.exists(os.path.join(ROOT, doc)):
            shutil.copyfile(os.path.join(ROOT, doc), os.path.join(out_dir, os.path.basename(doc)))
    _write_text(os.path.join(out_dir, "quality_report.md"),
                build_report(raw_path, versions, index, issues, stats, feature_rows, FEATURE_NAMES, n_lines))
    if feature_rows:
        _write_text(os.path.join(out_dir, "feature_summary.md"),
                    build_summary(feature_rows, index, CORE_FEATURE_NAMES))
    validation = id_validation(records, n_invalid, feature_rows, expected)
    _write_text(os.path.join(out_dir, "id_validation.json"), json.dumps(validation, indent=2))

    summary = {"lines": n_lines, "runs": len(index), "feature_rows": len(feature_rows),
               "issues": len(issues), "errors": sum(1 for i in issues if i["severity"] == "error"),
               "id_check": "PASS" if validation["PASS"] else "FAIL"}
    inputs = {"trajectories": {"file": os.path.basename(raw_path), "sha256": _sha256(raw_path)}}
    for key, path in (("manifest", manifest_path), ("run_metadata", run_metadata_path)):
        if path:
            inputs[key] = {"file": os.path.basename(path), "sha256": _sha256(path)}
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versions": versions, "python": sys.version.split()[0], "inputs": inputs, "counts": summary,
        "n_primary_features": len(CORE_FEATURE_NAMES), "n_all_features": len(FEATURE_NAMES),
        "not_received": ["approved labels", "eval_evidence.jsonl", "pre/post snapshots", "evaluator outputs",
                         "adjudication notes", "trajectory_id mapping"],
        "rules": PREPROCESSING_RULES,
    }
    _write_text(os.path.join(out_dir, "preprocessing_metadata.json"), json.dumps(metadata, indent=2))
    # Package checksum: only files actually in this directory (section 12, package validation).
    names = sorted(n for n in os.listdir(out_dir)
                   if n != "checksums.sha256" and os.path.isfile(os.path.join(out_dir, n)))
    _write_text(os.path.join(out_dir, "checksums.sha256"),
                "".join("%s  %s\n" % (_sha256(os.path.join(out_dir, n)), n) for n in names))
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m p3", description=__doc__)
    parser.add_argument("--raw", required=True, help="trajectories JSONL from Person 2 (raw or blinded)")
    parser.add_argument("--out", required=True, help="output directory (use a new one per input)")
    parser.add_argument("--manifest", help="pilot manifest CSV (validation and user-prompt fallback only)")
    parser.add_argument("--run-metadata", help="run_metadata.txt from Person 2 (hash recorded only)")
    parser.add_argument("--expected", type=int, help="expected number of unique trajectory ids")
    args = parser.parse_args(argv)
    summary = run_pipeline(args.raw, args.out, args.manifest, args.run_metadata, args.expected)
    print("lines=%(lines)d runs=%(runs)d feature_rows=%(feature_rows)d issues=%(issues)d errors=%(errors)d "
          "id_check=%(id_check)s" % summary)
    print("outputs written to %s" % args.out)
    return 0 if summary["id_check"] == "PASS" else 1
