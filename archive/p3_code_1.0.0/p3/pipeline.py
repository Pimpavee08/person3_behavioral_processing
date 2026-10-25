"""End-to-end run: raw_runs.jsonl -> P3 package (canonical trajectories, features, reports)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import __version__
from .features import (CORE_FEATURE_NAMES, FEATURE_NAMES, FEATURE_SET_VERSION, extract_features,
                       feature_dictionary)
from .leakage import check_canonical_record, check_feature_columns
from .normalize import CANONICAL_SCHEMA_VERSION, normalize_run, structural_view
from .schema import ROOT, load_frozen
from .quality import (ATTEMPT_KEYS, REPETITION_KEYS, _find_key, attempt_issues, build_report, build_summary,
                      validate_record)
from .tool_taxonomy import TAXONOMY_VERSION

DATA_CONTRACT = "data_contract_v0.2"
# Partition/split metadata for Person 4. NOT detector input. Labels (condition,
# ipi_present, injection_encountered, ...) come only from P1's approved label file.
INDEX_COLUMNS = (
    "run_id", "source_llm", "suite", "scenario_group_id", "user_task_id",
    "repetition_index", "attempt_index", "split", "execution_status",
    "source_format", "n_events", "n_tool_calls", "n_errors", "n_warnings", "structurally_valid",
)
# Documentation shipped inside every package.
PACKAGE_DOCS = ("docs/feature_schema_v1.0.md", "docs/preprocessing_notes.md")
ISSUE_COLUMNS = ("run_id", "line", "severity", "code", "detail", "event_idx")
PREPROCESSING_RULES = [
    "Runner events (injected_content_delivered), system messages and hidden reasoning are removed.",
    "Events are ordered by event_index; steps are recomputed as model turns.",
    "Raw call ids are replaced by c0, c1, ...; results inherit the tool fields of their call.",
    "A closing answer logged as agent_message + agent_final with the same text is kept once.",
    "Tools are mapped to action/effect/domain/source_trust/egress/destructive (taxonomy).",
    "create_calendar_event with non-empty participants counts as egress (emptiness only, values unread).",
    "The written canonical trajectory holds no raw text and no argument values: arguments become "
    "arg_count/arg_types/n_missing_args/n_extra_args/args_ref, results become result_type, "
    "messages become has_text.",
    "Missing/extra arguments compare argument keys with the tool signatures at the frozen AgentDojo commit.",
    "features.csv (primary) is computed from that structural trajectory only.",
    "features_extended.csv adds text-derived and timing features; not primary detector input.",
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
                issues.append({"run_id": "<line %d>" % line_no, "line": line_no, "severity": "error",
                               "code": "invalid_json", "detail": str(exc), "event_idx": None})
                continue
            records.append((line_no, raw))
    return records


def run_pipeline(raw_path: str, out_dir: str, manifest_path: Optional[str] = None,
                 run_metadata_path: Optional[str] = None) -> Dict[str, Any]:
    frozen = load_frozen()  # refuse to produce features that differ from the frozen schema
    manifest = load_manifest(manifest_path) if manifest_path else None
    os.makedirs(out_dir, exist_ok=True)
    issues: List[Dict[str, Any]] = []
    records = _read_records(raw_path, issues)
    n_lines = len(records) + len(issues)

    accepted, seen = [], set()
    for line_no, raw in records:
        run_id = raw.get("run_id")
        if not run_id or run_id in seen:  # unusable as a join key: recorded, not emitted
            issues.append({"run_id": run_id or "<line %d>" % line_no, "line": line_no, "severity": "error",
                           "code": "duplicate_run_id" if run_id else "missing_run_id",
                           "detail": "record excluded", "event_idx": None})
            continue
        seen.add(run_id)
        accepted.append((line_no, raw))
    batch_issues = attempt_issues([raw for _, raw in accepted])

    structural_rows, feature_rows, index = [], [], []
    stats: Dict[str, Dict[str, Any]] = {}
    for line_no, raw in accepted:
        run_id = raw["run_id"]
        row = (manifest or {}).get(raw.get("scenario_id")) or {}
        working, run_issues, run_stats = normalize_run(raw, fallback_prompt=row.get("user_prompt"))
        run_issues = validate_record(raw, manifest) + batch_issues.get(run_id, []) + run_issues
        structural = structural_view(working)
        check_canonical_record(structural)
        issues += [dict(i, run_id=run_id, line=line_no) for i in run_issues]
        n_err = sum(1 for i in run_issues if i["severity"] == "error")
        stats[run_id] = run_stats
        index.append({
            "run_id": run_id,
            **{k: raw.get(k) for k in ("source_llm", "suite", "scenario_group_id", "user_task_id",
                                       "split", "execution_status")},
            "repetition_index": _find_key(raw, REPETITION_KEYS, depth=0),
            "attempt_index": _find_key(raw, ATTEMPT_KEYS, depth=0),
            "source_format": run_stats["source_format"],
            "n_events": run_stats["n_events"],
            "n_tool_calls": run_stats["n_tool_calls"],
            "n_errors": n_err,
            "n_warnings": sum(1 for i in run_issues if i["severity"] == "warning"),
            "structurally_valid": int(n_err == 0),
        })
        structural_rows.append(structural)
        if n_err == 0:
            feature_rows.append({"run_id": run_id, **extract_features(working)})

    check_feature_columns(FEATURE_NAMES)  # covers the core subset too
    with open(os.path.join(out_dir, "canonical_trajectories.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for rec in structural_rows:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    _write_csv(os.path.join(out_dir, "features.csv"), ["run_id"] + CORE_FEATURE_NAMES, feature_rows)
    _write_csv(os.path.join(out_dir, "features_extended.csv"), ["run_id"] + FEATURE_NAMES, feature_rows)
    _write_csv(os.path.join(out_dir, "run_index.csv"), list(INDEX_COLUMNS), index)
    _write_csv(os.path.join(out_dir, "quality_issues.csv"), list(ISSUE_COLUMNS), issues)
    _write_csv(os.path.join(out_dir, "feature_dictionary.csv"),
               ["feature", "group", "caution", "description"], feature_dictionary())
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

    summary = {"lines": n_lines, "runs": len(index), "feature_rows": len(feature_rows),
               "issues": len(issues), "errors": sum(1 for i in issues if i["severity"] == "error")}
    inputs = {"raw_runs": {"file": os.path.basename(raw_path), "sha256": _sha256(raw_path)}}
    for key, path in (("manifest", manifest_path), ("run_metadata", run_metadata_path)):
        if path:
            inputs[key] = {"file": os.path.basename(path), "sha256": _sha256(path)}
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versions": versions, "python": sys.version.split()[0], "inputs": inputs, "counts": summary,
        "n_primary_features": len(CORE_FEATURE_NAMES), "n_all_features": len(FEATURE_NAMES),
        "received_from_p1": ["data_contract_v0.2.md", "experiment_protocol_v0.2.md",
                             "pilot_manifest_v0.1.csv (user_prompt fallback and scenario check only)"],
        "not_received": ["approved labels", "eval_evidence.jsonl", "pre/post snapshots", "evaluator outputs",
                         "adjudication notes"],
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
    parser.add_argument("--raw", required=True, help="raw_runs.jsonl from Person 2")
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--manifest", help="pilot manifest CSV (validation and user-prompt fallback only)")
    parser.add_argument("--run-metadata", help="run_metadata.txt from Person 2 (hash recorded only)")
    args = parser.parse_args(argv)
    summary = run_pipeline(args.raw, args.out, args.manifest, args.run_metadata)
    print("lines=%(lines)d runs=%(runs)d feature_rows=%(feature_rows)d issues=%(issues)d errors=%(errors)d"
          % summary)
    print("outputs written to %s" % args.out)
    return 0
