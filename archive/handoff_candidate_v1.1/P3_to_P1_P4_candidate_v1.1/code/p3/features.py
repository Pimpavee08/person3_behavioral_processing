"""Structural behavioral features, one row per run.

Every feature is a fixed, label-independent rule over what the agent
observably did. Nothing here reads the manifest, the payload file, attacker
goals or labels.

Primary (core) features are computed by core_features() from the structural
canonical record only (normalize.structural_view), which holds no text, no
tool-result content and only type descriptors for arguments. The same record
comes out of raw logs and of P2's blinded logs, so the primary features are
identical for both (data_contract_v0.2 section 11). Every feature is computed
per trajectory; nothing is fitted on the data set.

Features with a ``caution`` are not primary. extended_features() computes them
from the in-memory working record:

Secondary features are empty for blinded logs, which carry no text or time.

* timing       - wall-clock values. They follow hardware, load and model speed.
* text_derived - computed from message, argument or tool-result text (lengths,
  where argument values came from). Tool-result sizes also grow when a payload
  is present, even if the agent ignored it.

features.csv holds the core set. features_extended.csv adds the cautioned
features for separately justified ablations.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from . import tool_taxonomy as tx
from .descriptors import type_label
from .normalize import structural_view

FEATURE_SET_VERSION = "p3-features-1.1"
MIN_ATOM_LEN = 4  # shorter argument strings match too easily to say where they came from
_COARSE = ("R", "W", "E")
_EMPTY_TYPES = {"null", "empty_str", "empty_list", "empty_object"}

TIMING, TEXT = "timing", "text_derived"

# (name, group, caution, description)
_SPECS: List[Tuple[str, str, str, str]] = [
    ("n_tool_calls", "volume", "", "Tool calls issued by the agent."),
    ("n_tool_results", "volume", "", "Tool results logged (including errors)."),
    ("n_unique_tools", "volume", "", "Distinct tools called."),
    ("n_unmapped_tool_calls", "volume", "", "Calls to tools outside the taxonomy (e.g. hallucinated names)."),
    ("trajectory_length", "volume", "",
     "Events in the structural trajectory: calls, results, agent messages, final answer, execution errors "
     "(runner markers, user message, system messages, reasoning and the duplicated final message removed)."),
    ("total_result_chars", "volume", TEXT, "Characters returned by all tool results."),
    ("mean_result_chars", "volume", TEXT, "Mean characters per tool result."),
    ("n_read", "action_mix", "", "Read-effect tool calls."),
    ("n_write", "action_mix", "", "Write-effect (state-changing) tool calls."),
    ("n_egress", "action_mix", "", "Calls that send data/value to another party or grant access."),
    ("n_destructive", "action_mix", "", "Calls that delete or revoke."),
    ("frac_write", "action_mix", "", "n_write / n_tool_calls."),
    ("frac_egress", "action_mix", "", "n_egress / n_tool_calls."),
] + [
    ("n_act_" + a, "action_mix", "", "Tool calls with canonical action '%s'." % a) for a in tx.ACTIONS
] + [
    ("n_domains", "action_mix", "", "Distinct resource domains touched."),
    ("n_domain_switches", "action_mix", "", "Consecutive calls whose domains differ."),
    ("n_write_domains", "action_mix", "", "Distinct domains touched by write calls."),
    ("n_writes_new_domain", "action_mix", "", "Write calls in a domain no earlier call touched."),
    ("action_entropy", "action_mix", "", "Shannon entropy (bits) of the canonical-action distribution."),
    ("has_write", "sequence", "", "1 if any write call."),
    ("first_write_pos", "sequence", "", "Index of first write / n_tool_calls; 1.0 when there is no write."),
    ("n_reads_after_first_write", "sequence", "", "Read calls issued after the first write."),
    ("n_write_bursts", "sequence", "", "Maximal runs of consecutive write calls."),
    ("max_read_streak", "sequence", "", "Longest run of consecutive read calls."),
    ("n_repeated_call_shapes", "sequence", "",
     "Calls with the same tool and the same argument keys and types as an earlier call."),
    ("n_tool_revisits", "sequence", "", "Calls to a tool used earlier but not by the directly preceding call (loop back)."),
    ("max_same_tool_run", "sequence", "", "Longest run of consecutive calls to the same tool."),
] + [
    ("trans_%s%s" % (a, b), "sequence", "",
     "Share of consecutive call pairs going %s->%s (R=read, W=internal write, E=egress write)." % (a, b))
    for a in _COARSE for b in _COARSE
] + [
    ("n_freetext_reads", "exposure_structure", "", "Reads returning third-party free text."),
    ("n_writes_after_freetext", "exposure_structure", "", "Writes in a later step than the first free-text read."),
    ("n_egress_after_freetext", "exposure_structure", "", "Egress calls in a later step than the first free-text read."),
    ("n_destructive_after_freetext", "exposure_structure", "", "Destructive calls in a later step than the first free-text read."),
    ("frac_writes_after_freetext", "exposure_structure", "", "n_writes_after_freetext / n_write."),
    ("n_calls_after_last_freetext", "exposure_structure", "", "Calls in a later step than the last free-text read."),
    ("n_tool_errors", "errors", "", "Tool results that are errors."),
    ("frac_tool_errors", "errors", "", "n_tool_errors / n_tool_calls."),
    ("n_retry_after_error", "errors", "", "Calls to the same tool directly after its errored call."),
    ("n_calls_without_result", "errors", "", "Calls with no logged result."),
    ("n_error_valueerror", "errors", "", "Tool results with error class ValueError."),
    ("n_error_validationerror", "errors", "", "Tool results with error class ValidationError."),
    ("n_error_keyerror", "errors", "", "Tool results with error class KeyError."),
    ("n_error_other", "errors", "", "Tool results with any other or unspecified error class."),
    ("mean_args_per_call", "arguments", "", "Mean number of arguments per parsed call."),
    ("max_args_per_call", "arguments", "", "Most arguments in one call."),
    ("n_calls_without_args", "arguments", "", "Calls with zero arguments."),
    ("n_unparseable_args", "arguments", "", "Calls whose arguments could not be parsed (malformed call)."),
    ("n_calls_missing_required", "arguments", "", "Calls missing a required argument of the tool signature."),
    ("n_calls_extra_args", "arguments", "", "Calls with an argument the tool signature does not define."),
    ("frac_arg_str", "arguments", "", "Share of argument values that are strings."),
    ("frac_arg_number", "arguments", "", "Share of argument values that are numbers."),
    ("frac_arg_bool", "arguments", "", "Share of argument values that are booleans."),
    ("frac_arg_collection", "arguments", "", "Share of argument values that are non-empty lists or objects."),
    ("frac_arg_empty", "arguments", "", "Share of argument values that are null, empty lists or empty objects."),
    ("n_write_arg_atoms", "provenance", TEXT, "String argument values (>=%d chars) of write calls." % MIN_ATOM_LEN),
    ("frac_write_args_from_user", "provenance", TEXT, "Share of those values that appear in the user prompt."),
    ("frac_write_args_from_tool", "provenance", TEXT, "Share that appear only in an earlier tool result."),
    ("frac_write_args_from_freetext", "provenance", TEXT, "Share that appear only in an earlier free-text tool result."),
    ("frac_write_args_novel", "provenance", TEXT, "Share that appear in neither (composed by the agent)."),
    ("n_egress_calls_freetext_args", "provenance", TEXT,
     "Egress calls with an argument value traceable only to a free-text tool result."),
    ("ended_with_final", "termination", "", "1 if the trajectory ends with a final agent answer event."),
    ("final_output_present", "termination", "",
     "Runner flag: 1 if a non-empty final output exists, 0 if not; empty when the log lacks the flag."),
    ("n_steps", "shape", "", "Model turns (consecutive agent events count as one)."),
    ("max_calls_per_step", "shape", "", "Most tool calls issued in one turn."),
    ("mean_calls_per_step", "shape", "", "Mean tool calls per turn that has calls."),
    ("n_agent_messages", "shape", "", "Agent messages other than the final answer (e.g. a message beside tool calls)."),
    ("n_steps_message_and_call", "shape", "", "Turns containing both an agent message and a tool call."),
    ("final_text_len", "shape", TEXT, "Characters in the final answer."),
    ("mean_agent_text_len", "shape", TEXT, "Mean characters per agent text message."),
    ("duration_s", "shape", TIMING, "Seconds from first to last timestamped event."),
    ("mean_agent_latency_s", "shape", TIMING, "Mean seconds between an agent event and the event before it."),
]

FEATURE_NAMES = [s[0] for s in _SPECS]
CORE_FEATURE_NAMES = [s[0] for s in _SPECS if not s[2]]
EXTENDED_ONLY_NAMES = [s[0] for s in _SPECS if s[2]]


def feature_dictionary() -> List[Dict[str, Any]]:
    return [{"feature": n, "group": g, "caution": c, "description": d} for n, g, c, d in _SPECS]


def _ratio(a: float, b: float) -> float:
    return a / b if b else 0.0


def core_features(structural: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Primary features from a structural canonical record (no text, no argument values)."""
    events = structural["events"]
    calls = [e for e in events if e["type"] == "tool_call"]
    results = [e for e in events if e["type"] == "tool_result"]
    result_of = {e["call_ref"]: e for e in results if e["call_ref"]}
    messages = [e for e in events if e["type"] == "agent_message"]
    n = len(calls)
    f: Dict[str, Optional[float]] = dict.fromkeys(CORE_FEATURE_NAMES, 0)

    # ---- volume / action mix ----
    writes = [c for c in calls if c["effect"] == tx.WRITE]
    f["n_tool_calls"] = n
    f["n_tool_results"] = len(results)
    f["n_unique_tools"] = len({c["tool"] for c in calls})
    f["n_unmapped_tool_calls"] = sum(1 for c in calls if not c["tool_mapped"])
    f["trajectory_length"] = len(events)
    f["n_read"] = sum(1 for c in calls if c["effect"] == tx.READ)
    f["n_write"] = len(writes)
    f["n_egress"] = sum(1 for c in calls if c["egress"])
    f["n_destructive"] = sum(1 for c in calls if c["destructive"])
    f["frac_write"] = _ratio(len(writes), n)
    f["frac_egress"] = _ratio(f["n_egress"], n)
    actions = Counter(c["action"] for c in calls)
    for a in tx.ACTIONS:
        f["n_act_" + a] = actions.get(a, 0)
    domains = [c["domain"] for c in calls]
    f["n_domains"] = len(set(domains))
    f["n_domain_switches"] = sum(1 for a, b in zip(domains, domains[1:]) if a != b)
    f["n_write_domains"] = len({c["domain"] for c in writes})
    f["n_writes_new_domain"] = sum(
        1 for i, c in enumerate(calls) if c["effect"] == tx.WRITE and c["domain"] not in domains[:i])
    f["action_entropy"] = -sum(_ratio(k, n) * math.log2(_ratio(k, n)) for k in actions.values()) if n else 0.0

    # ---- sequence ----
    classes = [tx.coarse_class(c["effect"], c["egress"]) for c in calls]
    is_write = [k in ("W", "E") for k in classes]
    f["has_write"] = int(any(is_write))
    first_write = is_write.index(True) if any(is_write) else None
    f["first_write_pos"] = _ratio(first_write, n) if first_write is not None else 1.0
    if first_write is not None:
        f["n_reads_after_first_write"] = classes[first_write:].count("R")
    f["n_write_bursts"] = sum(1 for i, w in enumerate(is_write) if w and (i == 0 or not is_write[i - 1]))
    streak = 0
    for k in classes:
        streak = streak + 1 if k == "R" else 0
        f["max_read_streak"] = max(f["max_read_streak"], streak)
    signatures = [c["args_ref"] for c in calls]
    f["n_repeated_call_shapes"] = sum(1 for i, s in enumerate(signatures) if s in signatures[:i])
    tools = [c["tool"] for c in calls]
    f["n_tool_revisits"] = sum(1 for i, t in enumerate(tools) if i and tools[i - 1] != t and t in tools[:i])
    run = 0
    for i, t in enumerate(tools):
        run = run + 1 if i and tools[i - 1] == t else 1
        f["max_same_tool_run"] = max(f["max_same_tool_run"], run)
    pairs = Counter((a, b) for a, b in zip(classes, classes[1:]) if a in _COARSE and b in _COARSE)
    for a in _COARSE:
        for b in _COARSE:
            f["trans_%s%s" % (a, b)] = _ratio(pairs.get((a, b), 0), sum(pairs.values()))

    # ---- exposure structure: what happens after third-party free text was read ----
    free_steps = [c["step"] for c in calls if c["source_trust"] == tx.FREE]
    f["n_freetext_reads"] = len(free_steps)
    if free_steps:
        after_first = [c for c in calls if c["step"] > min(free_steps)]
        f["n_writes_after_freetext"] = sum(1 for c in after_first if c["effect"] == tx.WRITE)
        f["n_egress_after_freetext"] = sum(1 for c in after_first if c["egress"])
        f["n_destructive_after_freetext"] = sum(1 for c in after_first if c["destructive"])
        f["frac_writes_after_freetext"] = _ratio(f["n_writes_after_freetext"], len(writes))
        f["n_calls_after_last_freetext"] = sum(1 for c in calls if c["step"] > max(free_steps))

    # ---- errors and result structure ----
    errored = {r["call_ref"] for r in results if r["is_error"] and r["call_ref"]}
    f["n_tool_errors"] = sum(1 for r in results if r["is_error"])
    f["frac_tool_errors"] = _ratio(f["n_tool_errors"], n)
    f["n_retry_after_error"] = sum(
        1 for a, b in zip(calls, calls[1:]) if a["call_ref"] in errored and a["tool"] == b["tool"])
    f["n_calls_without_result"] = sum(1 for c in calls if c["call_ref"] not in result_of)
    classes_seen = Counter(r["error_class"] for r in results if r["is_error"])
    f["n_error_valueerror"] = classes_seen.pop("ValueError", 0)
    f["n_error_validationerror"] = classes_seen.pop("ValidationError", 0)
    f["n_error_keyerror"] = classes_seen.pop("KeyError", 0)
    f["n_error_other"] = sum(classes_seen.values())

    # ---- argument structure (counts and type descriptors, never values) ----
    parsed = [c for c in calls if c["arg_shape"] is not None]
    counts = [c["arg_count"] for c in parsed]
    f["mean_args_per_call"] = _ratio(sum(counts), len(counts))
    f["max_args_per_call"] = max(counts) if counts else 0
    f["n_calls_without_args"] = counts.count(0)
    f["n_unparseable_args"] = n - len(parsed)
    f["n_calls_missing_required"] = sum(1 for c in parsed if c["n_missing_args"])
    f["n_calls_extra_args"] = sum(1 for c in parsed if c["n_extra_args"])
    types = Counter(type_label(d) for c in parsed for d in c["arg_shape"].values())
    total = sum(types.values())
    f["frac_arg_str"] = _ratio(types["str"], total)
    f["frac_arg_number"] = _ratio(types["number"], total)
    f["frac_arg_bool"] = _ratio(types["bool"], total)
    f["frac_arg_collection"] = _ratio(types["list"] + types["object"], total)
    f["frac_arg_empty"] = _ratio(sum(types[t] for t in _EMPTY_TYPES), total)

    # ---- termination and shape ----
    f["ended_with_final"] = int(bool(events) and events[-1]["type"] == "agent_final")
    present = structural.get("final_output_present")
    f["final_output_present"] = None if present is None else int(present)
    per_step = Counter(c["step"] for c in calls)
    f["n_steps"] = len({e["step"] for e in events if e["actor"] == "agent"})
    f["max_calls_per_step"] = max(per_step.values()) if per_step else 0
    f["mean_calls_per_step"] = _ratio(n, len(per_step))
    f["n_agent_messages"] = len(messages)
    f["n_steps_message_and_call"] = len({e["step"] for e in messages} & set(per_step))
    return f


def _atoms(value: Any) -> List[str]:
    """Case-folded string leaves of an argument structure."""
    if isinstance(value, str):
        s = value.strip().casefold()
        return [s] if len(s) >= MIN_ATOM_LEN else []
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, (list, tuple)):
        return [a for v in value for a in _atoms(v)]
    return []


def extended_features(working: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Non-primary features that need text or timing (working record only)."""
    events = working["events"]
    calls = [e for e in events if e["type"] == "tool_call"]
    writes = [c for c in calls if c["effect"] == tx.WRITE]
    results = [e for e in events if e["type"] == "tool_result"]
    texts = [e for e in events if e["type"] in ("agent_message", "agent_final") and e["text"]]
    finals = [e for e in events if e["type"] == "agent_final"]
    f: Dict[str, Optional[float]] = dict.fromkeys(EXTENDED_ONLY_NAMES, 0)
    if working.get("blinded"):  # no text, values or timestamps to measure
        return dict.fromkeys(EXTENDED_ONLY_NAMES)

    result_chars = [len(r["text"] or "") for r in results]
    f["total_result_chars"] = sum(result_chars)
    f["mean_result_chars"] = _ratio(sum(result_chars), len(result_chars))

    # provenance: where did the argument values of write calls come from
    user_msgs = [e["text"] or "" for e in events if e["type"] == "user_message"]
    user_text = " ".join(user_msgs).casefold()
    origin = Counter()
    for c in writes:
        seen_all = " \x00 ".join((r["text"] or "").casefold() for r in results if r["idx"] < c["idx"])
        seen_free = " \x00 ".join((r["text"] or "").casefold() for r in results
                                  if r["idx"] < c["idx"] and r["source_trust"] == tx.FREE)
        free_only = False
        for atom in _atoms(c["args"]):
            origin["atoms"] += 1
            if atom in user_text:
                origin["user"] += 1
            elif atom in seen_all:
                origin["tool"] += 1
                if atom in seen_free:
                    origin["free"] += 1
                    free_only = True
            else:
                origin["novel"] += 1
        f["n_egress_calls_freetext_args"] += int(free_only and c["egress"])
    f["n_write_arg_atoms"] = origin["atoms"]
    for name, key in (("frac_write_args_from_user", "user"), ("frac_write_args_from_tool", "tool"),
                      ("frac_write_args_from_freetext", "free"), ("frac_write_args_novel", "novel")):
        f[name] = _ratio(origin[key], origin["atoms"])
    if not user_msgs and origin["atoms"]:  # cannot tell user-supplied from agent-composed values
        for name in ("frac_write_args_from_user", "frac_write_args_from_tool",
                     "frac_write_args_from_freetext", "frac_write_args_novel",
                     "n_egress_calls_freetext_args"):
            f[name] = None

    f["final_text_len"] = len(finals[-1]["text"] or "") if finals else 0
    f["mean_agent_text_len"] = _ratio(sum(len(e["text"]) for e in texts), len(texts))
    timed = [e["t_rel"] for e in events if e["t_rel"] is not None]
    f["duration_s"] = max(timed) - min(timed) if timed else None
    gaps = [e["t_rel"] - p["t_rel"] for p, e in zip(events, events[1:])
            if e["actor"] == "agent" and p["actor"] != "agent"
            and e["t_rel"] is not None and p["t_rel"] is not None]
    f["mean_agent_latency_s"] = _ratio(sum(gaps), len(gaps)) if gaps else None
    return f


def extract_features(working: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """All features of one run, in FEATURE_NAMES order."""
    f = core_features(structural_view(working))
    f.update(extended_features(working))
    return {name: f[name] for name in FEATURE_NAMES}
