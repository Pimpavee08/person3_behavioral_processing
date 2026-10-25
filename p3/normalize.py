"""Trajectory normalization: raw or blinded run record -> canonical trajectory.

Two views of the same run:

* working record (normalize_run) - keeps text and argument values when the
  input has them. It lives in memory only and feeds the secondary features.
* structural record (structural_view) - the leakage-safe canonical trajectory
  that is written to disk and is the only input of the primary features.
  Arguments are reduced to type descriptors, there is no text, no result
  content and no user message (data_contract_v0.2 sections 5 and 11).

Raw logs (run_id, values, text) and P2's blinded logs (trajectory_id, type
descriptors, no text) are reduced to the same structural record, so one rule
set serves both. See docs/feature_schema_v1.1.md.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import tool_taxonomy as tx
from .descriptors import describe, is_descriptor
from .parsers import ParsedRun, parse_record
from .tool_signatures import argument_mismatch

CANONICAL_SCHEMA_VERSION = "p3-canonical-0.5"

RECORD_KEYS = ("schema_version", "taxonomy_version", "trajectory_id", "final_output_present", "events")
_TOOL_FIELDS = ("tool", "action", "effect", "domain", "source_trust", "egress", "destructive", "tool_mapped")
_COMMON_KEYS = ("idx", "step", "type", "actor", "call_ref") + _TOOL_FIELDS + ("is_error", "error_class", "t_rel")
EVENT_KEYS = _COMMON_KEYS + ("arg_shape", "args", "text")  # working record
STRUCT_EVENT_KEYS = _COMMON_KEYS + ("arg_count", "arg_shape", "n_missing_args", "n_extra_args", "args_ref")
_ACTOR = {
    "user_message": "user", "agent_message": "agent", "tool_call": "agent",
    "agent_final": "agent", "tool_result": "tool", "execution_error": "runtime",
}
# Raw record keys that are read here; every other record key is dropped.
_RECORD_CONSUMED = {"run_id", "trajectory_id", "events", "trajectory", "messages", "user_prompt",
                    "final_output_present"}


# Event fields that only a raw (not blinded) log carries a value in.
_RAW_ONLY_FIELDS = ("content", "content_text", "text", "message", "tool_result", "result", "output",
                    "timestamp", "time", "ts")


def _has_value(value: Any) -> bool:
    return value not in (None, "", [], {})


def is_blinded(raw: Dict[str, Any]) -> bool:
    """P2's sanitized format: no text, no tool-result content, no timestamps.

    Decided from the content, not from which id key is present, so a renamed id
    field cannot flip the interpretation of argument values.
    """
    if _has_value(raw.get("user_prompt")) or isinstance(raw.get("messages"), list):
        return False
    events = raw.get("events") if isinstance(raw.get("events"), list) else raw.get("trajectory")
    if not isinstance(events, list):
        return False
    return not any(isinstance(e, dict) and any(_has_value(e.get(k)) for k in _RAW_ONLY_FIELDS)
                   for e in events)


def _id_hint_blinded(raw: Dict[str, Any]) -> bool:
    return "trajectory_id" in raw and "run_id" not in raw


def record_id(raw: Dict[str, Any]) -> Any:
    return raw.get("trajectory_id") if raw.get("trajectory_id") is not None else raw.get("run_id")


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


def _shape(args: Dict[str, Any], blinded: bool) -> Tuple[Dict[str, str], int]:
    """(argument key -> type descriptor, number of raw values found in a blinded log).

    Blinded logs already hold descriptors. A raw value inside a blinded log is
    described (never kept) and counted, because it means sanitization missed it.
    """
    shape, raw_values = {}, 0
    for k, v in sorted(args.items(), key=lambda kv: str(kv[0])):
        if blinded and is_descriptor(v):
            shape[str(k)] = v
        else:
            shape[str(k)] = describe(v)
            raw_values += blinded
    return shape, raw_values


def _clean_id(value: Any) -> Any:
    """A call id usable as a dict key (str or int), else None."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    return value


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
    """Return (working record, issues, normalization stats) for one raw or blinded run."""
    issues: List[Dict[str, Any]] = []
    blinded = is_blinded(raw)
    if blinded != _id_hint_blinded(raw):
        _issue(issues, "warning", "format_hint_mismatch",
               "content looks %s but the id key suggests otherwise" % ("blinded" if blinded else "raw"))
    parsed = parse_record(raw)
    if parsed.source_format is None:
        _issue(issues, "error", "no_trajectory", "record has neither 'events' nor 'messages'")
    for t in parsed.unknown_event_types:
        _issue(issues, "warning", "unknown_event_type", str(t))
    if parsed.malformed_events:
        _issue(issues, "warning", "malformed_event", "%d non-object entries" % parsed.malformed_events)
    if parsed.runner_events_removed:
        _issue(issues, "warning", "runner_event_removed",
               "%d events with actor=runner" % parsed.runner_events_removed)
    bad_ids = sum(1 for e in parsed.events if e["call_id"] is not None and _clean_id(e["call_id"]) is None)
    if bad_ids:
        _issue(issues, "warning", "invalid_tool_call_id", "%d ids that are not strings or integers" % bad_ids)
    raw_values = 0

    out: List[Dict[str, Any]] = []
    times: List[Optional[float]] = []
    raw_steps: List[Any] = []
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
            raw_steps.append(None)
        elif not blinded:  # blinded logs carry no text by design
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
            else:
                ev["arg_shape"], n_raw = _shape(ev["args"], blinded)
                raw_values += n_raw
                if tx.adds_recipients(name, ev["arg_shape"]):
                    ev["egress"] = True
            call_id = _clean_id(src["call_id"])
            if call_id is not None:
                if call_id in by_raw_id:
                    _issue(issues, "warning", "duplicate_tool_call_id", ev["call_ref"])
                by_raw_id[call_id] = ev
            open_calls.append(ev)
        elif src["type"] == "tool_result":
            ev["text"] = src["text"] if src["error"] is None else str(src["error"])
            ev["is_error"] = src["error"] is not None
            ev["error_class"] = src["error_class"]
            name = tx.canonical_tool_name(src["tool"])
            call_id = _clean_id(src["call_id"])
            if call_id is not None:
                call = by_raw_id.get(call_id)
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
            ev["error_class"] = src["error_class"]
        else:
            ev["text"] = src["text"]
        out.append(ev)
        times.append(_parse_time(src["timestamp"]))
        raw_steps.append(src["raw_step"])

    for call in open_calls:
        _issue(issues, "warning", "tool_call_without_result", "%s %s" % (call["call_ref"], call["tool"]))
    if raw_values:
        _issue(issues, "warning", "non_descriptor_argument",
               "%d argument values in a blinded log were not type descriptors (described, not kept)" % raw_values)

    # The runner logs the closing answer twice: agent_message, then agent_final in the same turn.
    # Same turn = same logged step; without step numbers, identical text.
    def duplicate(i: int) -> bool:
        if not (out[i]["type"] == "agent_message" and i + 1 < len(out) and out[i + 1]["type"] == "agent_final"):
            return False
        if raw_steps[i] is not None and raw_steps[i + 1] is not None:
            return raw_steps[i] == raw_steps[i + 1]
        return out[i]["text"] is not None and out[i]["text"] == out[i + 1]["text"]
    keep = [not duplicate(i) for i in range(len(out))]
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
    if not any(e["actor"] == "agent" for e in out):  # empty or agent-less runs still get a feature row
        _issue(issues, "warning", "no_agent_events")

    known = [t for t in times if t is not None]
    if not blinded and len(known) < len([e for e in out if e["actor"] != "user"]):
        _issue(issues, "info", "missing_timestamps")
    t0 = min(known) if known else None
    for i, (ev, t) in enumerate(zip(out, times)):
        ev["idx"] = i
        ev["t_rel"] = round(t - t0, 3) if t is not None else None

    if parsed.reasoning_removed:
        _issue(issues, "info", "reasoning_removed", str(parsed.reasoning_removed))
    if parsed.exposure_markers_removed:
        _issue(issues, "info", "exposure_marker_removed", str(parsed.exposure_markers_removed))

    final_present = raw.get("final_output_present")
    working = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "taxonomy_version": tx.TAXONOMY_VERSION,
        "trajectory_id": record_id(raw),
        "final_output_present": final_present if isinstance(final_present, bool) else None,
        "events": out,
        "blinded": blinded,  # working record only; never written
    }
    n_results = sum(1 for e in out if e["type"] == "tool_result" and e["call_ref"])
    stats = {
        "source_format": "blinded_events" if blinded else parsed.source_format,
        "n_events": len(out),
        "n_tool_calls": n_calls,
        "n_linked_results": n_results,
        "stripped_keys": sorted(parsed.stripped_keys | {"record." + k for k in raw if k not in _RECORD_CONSUMED}),
    }
    return working, issues, stats


def structural_view(working: Dict[str, Any]) -> Dict[str, Any]:
    """Leakage-safe canonical record: structure only, no text, values or user message."""
    events, signatures = [], {}
    for ev in working["events"]:
        if ev["type"] == "user_message":
            continue
        out = {k: ev[k] for k in _COMMON_KEYS}
        out.update(dict.fromkeys(STRUCT_EVENT_KEYS[len(_COMMON_KEYS):]))
        if ev["type"] == "tool_call":
            shape = ev["arg_shape"]
            if shape is not None:
                out["arg_count"] = len(shape)
                out["arg_shape"] = dict(shape)
                out["n_missing_args"], out["n_extra_args"] = argument_mismatch(ev["tool"], shape)
            # same args_ref <=> same tool and same argument keys and types within this run
            key = (ev["tool"], json.dumps(shape, sort_keys=True))
            out["args_ref"] = signatures.setdefault(key, "a%d" % len(signatures))
        out["idx"] = len(events)
        events.append(out)
    record = {k: working[k] for k in RECORD_KEYS if k != "events"}
    record["events"] = events
    return record
