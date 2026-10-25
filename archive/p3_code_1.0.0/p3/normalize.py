"""Trajectory normalization: raw run record -> canonical trajectory.

Two views of the same run:

* working record (normalize_run) - keeps text and argument values. It lives
  in memory only and feeds the non-primary features_extended.csv.
* structural record (structural_view) - the leakage-safe canonical trajectory
  that is written to disk and is the only input of the primary features.
  Raw text and raw argument values are replaced by structure
  (data_contract_v0.2 sections 5 and 11).

Both are built from a whitelist of fields, so provider-specific metadata,
model and scenario identity, labels and exposure markers cannot survive.
See docs/feature_schema_v1.0.md.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import tool_taxonomy as tx
from .parsers import ParsedRun, parse_record
from .tool_signatures import argument_mismatch

CANONICAL_SCHEMA_VERSION = "p3-canonical-0.3"

RECORD_KEYS = ("schema_version", "taxonomy_version", "run_id", "events")
_TOOL_FIELDS = ("tool", "action", "effect", "domain", "source_trust", "egress", "destructive", "tool_mapped")
_COMMON_KEYS = ("idx", "step", "type", "actor", "call_ref") + _TOOL_FIELDS + ("is_error", "t_rel")
EVENT_KEYS = _COMMON_KEYS + ("args", "text")  # working record
STRUCT_EVENT_KEYS = _COMMON_KEYS + (
    "arg_count", "arg_types", "n_missing_args", "n_extra_args", "args_ref", "result_type", "has_text")
_ACTOR = {
    "user_message": "user", "agent_message": "agent", "tool_call": "agent",
    "agent_final": "agent", "tool_result": "tool", "execution_error": "runtime",
}
# Raw record keys that are read here; every other record key is dropped.
_RECORD_CONSUMED = {"run_id", "events", "trajectory", "messages", "user_prompt"}


def _issue(issues: List[Dict[str, Any]], severity: str, code: str, detail: str = "",
           event_idx: Optional[int] = None) -> None:
    issues.append({"severity": severity, "code": code, "detail": detail, "event_idx": event_idx})


def _parse_args(raw_args: Any) -> Optional[Dict[str, Any]]:
    """Arguments as a dict regardless of provider encoding; None if unusable."""
    if raw_args is None or raw_args == "":
        return {}
    if isinstance(raw_args, str):
        try:
            raw_args = json.loads(raw_args)
        except ValueError:
            return None
    return raw_args if isinstance(raw_args, dict) else None


def _parse_time(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _blank_event(etype: str) -> Dict[str, Any]:
    ev = dict.fromkeys(EVENT_KEYS)
    ev.update(type=etype, actor=_ACTOR[etype], egress=False, destructive=False,
              tool_mapped=False, is_error=False)
    return ev


def _set_tool(ev: Dict[str, Any], name: str) -> None:
    spec = tx.lookup(name)
    ev.update(tool=name, action=spec.action, effect=spec.effect, domain=spec.domain,
              source_trust=spec.source_trust, egress=spec.egress,
              destructive=spec.destructive, tool_mapped=spec.mapped)


def _ordered(parsed: ParsedRun, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Events in chronological order; event_index wins over file order."""
    events = parsed.events
    indices = [e["raw_index"] for e in events]
    if not events or any(not isinstance(i, int) or isinstance(i, bool) for i in indices):
        if parsed.source_format == "events" and events:
            _issue(issues, "info", "missing_event_index", "file order used")
        return events
    if len(set(indices)) != len(indices):
        _issue(issues, "warning", "duplicate_event_index", "file order used")
        return events
    if indices != sorted(indices):
        _issue(issues, "warning", "event_order_violation", "re-sorted by event_index")
        return sorted(events, key=lambda e: e["raw_index"])
    return events


def normalize_run(raw: Dict[str, Any], fallback_prompt: Optional[str] = None
                  ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    """Return (canonical record, issues, normalization stats) for one raw run."""
    issues: List[Dict[str, Any]] = []
    parsed = parse_record(raw)
    if parsed.source_format is None:
        _issue(issues, "error", "no_trajectory", "record has neither 'events' nor 'messages'")
    for t in parsed.unknown_event_types:
        _issue(issues, "warning", "unknown_event_type", str(t))
    if parsed.malformed_events:
        _issue(issues, "warning", "malformed_event", "%d non-object entries" % parsed.malformed_events)

    out: List[Dict[str, Any]] = []
    times: List[Optional[float]] = []
    by_raw_id: Dict[Any, Dict[str, Any]] = {}
    open_calls: List[Dict[str, Any]] = []   # calls still waiting for a result
    n_calls = 0

    prompt = raw.get("user_prompt")
    raw_events = _ordered(parsed, issues)
    if not any(e["type"] == "user_message" for e in raw_events):
        if not prompt and fallback_prompt:
            prompt = fallback_prompt
            _issue(issues, "info", "user_prompt_from_manifest")
        if prompt:
            ev = _blank_event("user_message")
            ev["text"] = str(prompt)
            out.append(ev)
            times.append(None)
        else:
            _issue(issues, "warning", "missing_user_prompt", "provenance features will be empty")

    for src in raw_events:
        ev = _blank_event(src["type"])
        if src["type"] == "tool_call":
            ev["call_ref"] = "c%d" % n_calls
            n_calls += 1
            name = tx.canonical_tool_name(src["tool"])
            _set_tool(ev, name)
            if not name:
                _issue(issues, "error", "missing_tool_name", ev["call_ref"])
            elif not ev["tool_mapped"]:
                _issue(issues, "warning", "unmapped_tool", name)
            ev["args"] = _parse_args(src["args"])
            if ev["args"] is None:
                _issue(issues, "warning", "unparseable_tool_arguments", ev["call_ref"])
            elif tx.adds_recipients(name, ev["args"]):
                ev["egress"] = True
            if src["call_id"] is not None:
                if src["call_id"] in by_raw_id:
                    _issue(issues, "warning", "duplicate_tool_call_id", ev["call_ref"])
                by_raw_id[src["call_id"]] = ev
            open_calls.append(ev)
        elif src["type"] == "tool_result":
            ev["text"] = src["text"] if src["error"] is None else str(src["error"])
            ev["is_error"] = src["error"] is not None
            name = tx.canonical_tool_name(src["tool"])
            if src["call_id"] is not None:
                call = by_raw_id.get(src["call_id"])
                call = call if any(call is c for c in open_calls) else None
            else:  # no ids in the log: oldest pending call of the same tool
                call = next((c for c in open_calls if not name or c["tool"] == name), None)
                if call is not None:
                    _issue(issues, "info", "result_linked_by_position", call["call_ref"])
            if call is None:
                _issue(issues, "warning", "orphan_tool_result", name)
                if name:
                    _set_tool(ev, name)
            else:
                open_calls[:] = [c for c in open_calls if c is not call]
                ev["call_ref"] = call["call_ref"]
                ev.update({k: call[k] for k in _TOOL_FIELDS})
        elif src["type"] == "execution_error":
            ev["text"] = str(src["error"]) if src["error"] is not None else None
            ev["is_error"] = True
        else:
            ev["text"] = src["text"]
        out.append(ev)
        times.append(_parse_time(src["timestamp"]))

    for call in open_calls:
        _issue(issues, "warning", "tool_call_without_result", "%s %s" % (call["call_ref"], call["tool"]))

    # Some runners log the closing answer twice: agent_message, then agent_final with the same text.
    keep = [not (ev["type"] == "agent_message" and i + 1 < len(out) and out[i + 1]["type"] == "agent_final"
                 and out[i + 1]["text"] == ev["text"]) for i, ev in enumerate(out)]
    if not all(keep):
        _issue(issues, "info", "duplicate_final_merged")
        out = [ev for ev, k in zip(out, keep) if k]
        times = [t for t, k in zip(times, keep) if k]

    # Steps = model turns, recomputed so that provider step numbering is irrelevant.
    step, prev_actor, step_of_call = -1, None, {}
    for ev in out:
        if ev["actor"] == "agent":
            if prev_actor != "agent":
                step += 1
            ev["step"] = step
            if ev["type"] == "tool_call":
                step_of_call[ev["call_ref"]] = step
        elif ev["actor"] == "tool":
            ev["step"] = step_of_call.get(ev["call_ref"], max(step, 0))
        elif ev["actor"] == "runtime":
            ev["step"] = max(step, 0)
        prev_actor = ev["actor"]

    # The closing text turn is the final answer, whatever the logger called it.
    if out and out[-1]["type"] == "agent_message":
        out[-1]["type"] = "agent_final"
    if not any(e["type"] == "agent_final" for e in out):
        _issue(issues, "info", "no_final_message")
    if not any(e["actor"] == "agent" for e in out):
        _issue(issues, "error", "no_agent_events")

    known = [t for t in times if t is not None]
    if len(known) < len([e for e in out if e["actor"] != "user"]):
        _issue(issues, "info", "missing_timestamps")
    t0 = min(known) if known else None
    for i, (ev, t) in enumerate(zip(out, times)):
        ev["idx"] = i
        ev["t_rel"] = round(t - t0, 3) if t is not None else None

    if parsed.reasoning_removed:
        _issue(issues, "info", "reasoning_removed", str(parsed.reasoning_removed))
    if parsed.exposure_markers_removed:
        _issue(issues, "info", "exposure_marker_removed", str(parsed.exposure_markers_removed))

    canonical = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "taxonomy_version": tx.TAXONOMY_VERSION,
        "run_id": raw.get("run_id"),
        "events": out,
    }
    n_results = sum(1 for e in out if e["type"] == "tool_result" and e["call_ref"])
    stats = {
        "source_format": parsed.source_format,
        "n_events": len(out),
        "n_tool_calls": n_calls,
        "n_linked_results": n_results,
        "stripped_keys": sorted(parsed.stripped_keys | {"record." + k for k in raw if k not in _RECORD_CONSUMED}),
    }
    return canonical, issues, stats


def value_type(value: Any) -> str:
    """Type label of one argument value; the value itself is never kept."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "str" if value.strip() else "empty_str"
    if isinstance(value, (list, tuple)):
        return "list" if value else "empty_list"
    if isinstance(value, dict):
        return "object" if value else "empty_object"
    return "other"


def structural_view(working: Dict[str, Any]) -> Dict[str, Any]:
    """Leakage-safe canonical record: structure only, no raw text or argument values."""
    events, signatures = [], {}
    for ev in working["events"]:
        out = {k: ev[k] for k in _COMMON_KEYS}
        out.update(dict.fromkeys(STRUCT_EVENT_KEYS[len(_COMMON_KEYS):]))
        if ev["type"] == "tool_call":
            args = ev["args"]
            if args is not None:
                out["arg_count"] = len(args)
                out["arg_types"] = {k: value_type(v) for k, v in sorted(args.items())}
                out["n_missing_args"], out["n_extra_args"] = argument_mismatch(ev["tool"], args)
            # same args_ref <=> same tool and identical arguments within this run
            key = (ev["tool"], json.dumps(args, sort_keys=True, default=str))
            out["args_ref"] = signatures.setdefault(key, "a%d" % len(signatures))
        elif ev["type"] == "tool_result":
            out["result_type"] = "error" if ev["is_error"] else ("value" if (ev["text"] or "").strip() else "empty")
        elif ev["type"] in ("user_message", "agent_message", "agent_final"):
            out["has_text"] = bool(ev["text"])
        events.append(out)
    return dict(working, events=events)
