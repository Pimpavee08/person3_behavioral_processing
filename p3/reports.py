"""Human-readable reports of a pipeline run: quality report and descriptive feature summary."""
from __future__ import annotations

import os
from collections import Counter, defaultdict
from typing import Any, Dict, List

from .common import KEY, short
from .features import CORE_FEATURE_NAMES

MD_CELL_LIMIT = 120  # longest input-controlled text shown in a Markdown table cell


def _md(value: Any) -> str:
    """Input-controlled text as an inert Markdown code span inside a table cell."""
    text = short(value, MD_CELL_LIMIT).replace("`", "'").replace("|", "\\|")
    return "`%s`" % text


def _table(header: List[str], rows: List[List[Any]]) -> List[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(" --- " for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return lines + [""]


def _group_column(index: List[Dict[str, Any]]) -> str:
    """Report grouping: source LLM when the input has it, else suite (blinded data)."""
    return "source_llm" if any(r.get("source_llm") is not None for r in index) else "suite"


def _summary_section(index, issues, n_lines) -> List[str]:
    valid = sum(r["structurally_valid"] for r in index)
    return ["## 1. Summary", ""] + _table(["Item", "Count"], [
        ["Lines read", n_lines],
        ["Trajectories indexed", len(index)],
        ["Structurally valid (features written)", valid],
        ["Excluded from features", len(index) - valid],
        ["Issues: error / warning / info", " / ".join(
            str(sum(1 for i in issues if i["severity"] == s)) for s in ("error", "warning", "info"))],
    ])


def _status_section(index, col, group_of, groups) -> List[str]:
    statuses = sorted({str(r.get("execution_status") or "n/a") for r in index})
    by = Counter((group_of[r[KEY]], str(r.get("execution_status") or "n/a")) for r in index)
    return (["## 2. Trajectories by %s and execution status" % col, ""]
            + _table([col] + [_md(s) for s in statuses], [[_md(g)] + [by[(g, s)] for s in statuses] for g in groups]))


def _issue_section(issues, group_of, groups) -> List[str]:
    out = ["## 3. Issues", ""]
    if not issues:
        return out + ["No issues.", ""]
    grouped: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for i in issues:
        grouped[(i["severity"], i["code"])].append(i)
    order = {"error": 0, "warning": 1, "info": 2}
    rows = []
    for (sev, code), items in sorted(grouped.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        per = Counter(group_of.get(i[KEY], "?") for i in items)
        rows.append([sev, code, len(items), len({i[KEY] for i in items})] + [per[g] for g in groups])
    return out + _table(["severity", "code", "issues", "trajectories"] + [_md(g) for g in groups], rows)


def _pairing_section(stats, col, group_of) -> List[str]:
    agg = defaultdict(lambda: [0, 0])
    for tid, s in stats.items():
        agg[group_of.get(tid, "?")][0] += s["n_tool_calls"]
        agg[group_of.get(tid, "?")][1] += s["n_linked_results"]
    return ["## 4. Tool call / result pairing", ""] + _table([col, "tool calls", "linked results", "paired"], [
        [_md(g), c, r, "%.1f%%" % (100.0 * r / c) if c else "n/a"] for g, (c, r) in sorted(agg.items())])


def _unmapped_section(issues) -> List[str]:
    out = ["## 5. Unmapped tools", "",
           "Tool names outside the 69 AgentDojo v1 tools (e.g. names the model invented). They stay in the "
           "trajectory and are counted by `n_unmapped_tool_calls`.", ""]
    unmapped = Counter(i["detail"] for i in issues if i["code"] == "unmapped_tool")
    return out + (_table(["tool", "calls"], [[_md(t), n] for t, n in sorted(unmapped.items())])
                  if unmapped else ["None.", ""])


def _stripped_section(stats, group_of) -> List[str]:
    keys = defaultdict(set)
    for tid, s in stats.items():
        for k in s["stripped_keys"]:
            keys[k].add(group_of.get(tid, "?"))
    return (["## 6. Raw fields removed during normalization", "",
             "Everything outside the canonical schema is dropped. Keys seen in this input:", ""]
            + _table(["raw key", "seen for"], [[_md(k), ", ".join(_md(g) for g in sorted(v))]
                                               for k, v in sorted(keys.items())]))


def _feature_section(features, feature_names) -> List[str]:
    missing = {n: sum(1 for f in features if f[n] is None) for n in feature_names}
    core_missing = {n: v for n, v in missing.items() if n in CORE_FEATURE_NAMES and v}
    constant = [n for n in CORE_FEATURE_NAMES if len({f[n] for f in features}) <= 1]
    out = ["## 7. Feature matrix", ""] + _table(["Item", "Value"], [
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
    return out


def build_report(raw_path: str, versions: Dict[str, str], index: List[Dict[str, Any]],
                 issues: List[Dict[str, Any]], stats: Dict[str, Dict[str, Any]],
                 features: List[Dict[str, Any]], feature_names: List[str], n_lines: int) -> str:
    col = _group_column(index)
    group_of = {r[KEY]: str(r.get(col) or "?") for r in index}
    groups = sorted(set(group_of.values()))
    out = ["# Person 3 Quality Report", "", "Input: %s" % _md(os.path.basename(raw_path)), ""]
    out += ["%s: %s  " % kv for kv in versions.items()] + [""]
    out += _summary_section(index, issues, n_lines)
    out += _status_section(index, col, group_of, groups)
    out += _issue_section(issues, group_of, groups)
    out += _pairing_section(stats, col, group_of)
    out += _unmapped_section(issues)
    out += _stripped_section(stats, group_of)
    out += _feature_section(features, feature_names)
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
