"""Raw trajectory parsing.

Turns one raw run record into a flat list of provider-neutral intermediate
events. Two raw layouts are accepted:

* ``events``   - the event list of data_contract_v0.1 section 5.
* ``messages`` - a chat transcript in AgentDojo, OpenAI/Groq or Anthropic shape.

Nothing is interpreted here beyond "what kind of event is this and where are
its fields". Linking, re-indexing and tool mapping happen in normalize.py.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

_EVENT_TYPES = {
    "agent_message": "agent_message",
    "assistant_message": "agent_message",
    "assistant": "agent_message",
    "tool_call": "tool_call",
    "function_call": "tool_call",
    "tool_use": "tool_call",
    "tool_result": "tool_result",
    "function_result": "tool_result",
    "tool_response": "tool_result",
    "agent_final": "agent_final",
    "final_answer": "agent_final",
    "final": "agent_final",
    "user_message": "user_message",
    "user": "user_message",
    "execution_error": "execution_error",
    "error": "execution_error",
    # Removed from the canonical trajectory, only counted:
    "injected_content_delivered": "exposure_marker",  # runner instrumentation = evaluation evidence
    "system_message": "system_message",
    "system": "system_message",
    "reasoning": "reasoning",
    "thinking": "reasoning",
}

_TYPE_KEYS = ("event_type", "type")
_TOOL_KEYS = ("tool_name", "name", "function")
_CALL_ID_KEYS = ("tool_call_id", "call_id", "tool_use_id", "id")
_ARGS_KEYS = ("tool_arguments", "arguments", "args", "input")
_RESULT_KEYS = ("tool_result", "result", "output", "content")
_TEXT_KEYS = ("content", "content_text", "text", "message")
_TS_KEYS = ("timestamp", "time", "ts")
_EVENT_CONSUMED = set(
    _TYPE_KEYS + _TOOL_KEYS + _CALL_ID_KEYS + _ARGS_KEYS + _RESULT_KEYS + _TEXT_KEYS + _TS_KEYS
    + ("event_index", "step_index", "actor", "error", "is_error")
)
_MESSAGE_CONSUMED = {"role", "content", "tool_calls", "tool_call_id", "tool_call", "name", "error"} | set(_TS_KEYS)

_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)
_ERROR_CLASS_RE = re.compile(r"^\s*([A-Za-z_][\w.]*(?:Error|Exception|Warning))\b")
_REASONING_BLOCKS = {"thinking", "redacted_thinking", "reasoning"}


@dataclass
class ParsedRun:
    events: List[Dict[str, Any]] = field(default_factory=list)
    source_format: Optional[str] = None
    reasoning_removed: int = 0
    exposure_markers_removed: int = 0
    system_messages_removed: int = 0
    malformed_events: int = 0
    unknown_event_types: List[str] = field(default_factory=list)
    stripped_keys: Set[str] = field(default_factory=set)


def _first(d: Dict[str, Any], keys: Tuple[str, ...]) -> Any:
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return None


def _event(etype: str, **kw: Any) -> Dict[str, Any]:
    ev = {"type": etype, "tool": None, "call_id": None, "args": None, "text": None,
          "error": None, "error_class": None, "timestamp": None, "raw_index": None, "raw_step": None}
    ev.update(kw)
    return ev


def error_of(value: Any) -> Tuple[Optional[str], Optional[str]]:
    """(error message, error class) from an error string or a blinded {error_present, error_class} field.

    Only the exception class name is kept as structure; the message text is never featurized.
    """
    if isinstance(value, dict):
        if not value.get("error_present"):
            return None, None
        cls = value.get("error_class") or "UNSPECIFIED"
        return cls, cls
    if value is None or value is False or value == "":
        return None, None
    text = str(value)
    match = _ERROR_CLASS_RE.match(text)
    return text, match.group(1) if match else "UNSPECIFIED"


def _stringify(value: Any) -> Optional[str]:
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _strip_think(text: Optional[str], out: ParsedRun) -> Optional[str]:
    if not text:
        return text
    cleaned, n = _THINK_RE.subn("", text)
    out.reasoning_removed += n
    return cleaned.strip() if n else text


def _flatten_content(content: Any, out: ParsedRun) -> str:
    """Text of a message content field (string or list of content blocks)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return _stringify(content) or ""
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
            continue
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype in _REASONING_BLOCKS:
            out.reasoning_removed += 1
            continue
        if btype in ("tool_use", "tool_result"):
            continue
        value = block.get("text", block.get("content"))
        if value is not None:
            parts.append(value if isinstance(value, str) else _stringify(value))
    return "\n".join(parts)


def _parse_contract_events(raw_events: List[Any], out: ParsedRun) -> None:
    for e in raw_events:
        if not isinstance(e, dict):
            out.malformed_events += 1
            continue
        raw_type = _first(e, _TYPE_KEYS)
        etype = _EVENT_TYPES.get(str(raw_type).strip().lower())
        if etype is None:
            out.unknown_event_types.append(str(raw_type))
            continue
        out.stripped_keys.update("event." + k for k in e if k not in _EVENT_CONSUMED)
        if etype == "reasoning":
            out.reasoning_removed += 1
            continue
        if etype == "exposure_marker":
            out.exposure_markers_removed += 1
            continue
        if etype == "system_message":
            out.system_messages_removed += 1
            continue
        ev = _event(etype, timestamp=_first(e, _TS_KEYS),
                    raw_index=e.get("event_index"), raw_step=e.get("step_index"))
        if etype == "tool_call":
            ev["tool"] = _first(e, _TOOL_KEYS)
            ev["call_id"] = _first(e, _CALL_ID_KEYS)
            ev["args"] = _first(e, _ARGS_KEYS)
        elif etype == "tool_result":
            ev["tool"] = _first(e, _TOOL_KEYS)
            ev["call_id"] = _first(e, _CALL_ID_KEYS)
            ev["text"] = _stringify(_first(e, _RESULT_KEYS))
            raw_error = e.get("error")
            if raw_error is None and e.get("is_error"):
                raw_error = ev["text"] or "error"
            ev["error"], ev["error_class"] = error_of(raw_error)
        elif etype == "execution_error":
            ev["error"], ev["error_class"] = error_of(_first(e, ("error",) + _TEXT_KEYS))
            if ev["error"] is None:
                ev["error"], ev["error_class"] = "execution_error", "UNSPECIFIED"
        else:
            ev["text"] = _strip_think(_flatten_content(_first(e, _TEXT_KEYS), out), out)
        out.events.append(ev)


def _tool_call_fields(tc: Dict[str, Any]) -> Tuple[Any, Any, Any]:
    """(name, arguments, id) of an OpenAI-style or AgentDojo-style tool call."""
    fn = tc.get("function")
    if isinstance(fn, dict):  # OpenAI / Groq: {"id", "type", "function": {"name", "arguments"}}
        return fn.get("name"), fn.get("arguments"), tc.get("id")
    return fn or tc.get("name"), _first(tc, ("args", "arguments", "input")), tc.get("id")


def _parse_messages(messages: List[Any], out: ParsedRun) -> None:
    for m in messages:
        if not isinstance(m, dict):
            out.malformed_events += 1
            continue
        role = m.get("role")
        ts = _first(m, _TS_KEYS)
        content = m.get("content")
        blocks = [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []
        out.stripped_keys.update("message." + k for k in m if k not in _MESSAGE_CONSUMED)
        if role == "system":
            out.system_messages_removed += 1
        elif role == "user":
            for b in blocks:  # Anthropic returns tool results inside a user message
                if b.get("type") == "tool_result":
                    text = _flatten_content(b.get("content"), out)
                    err, cls = error_of((text or "error") if b.get("is_error") else None)
                    out.events.append(_event(
                        "tool_result", call_id=b.get("tool_use_id"), text=text, timestamp=ts,
                        error=err, error_class=cls))
            text = _flatten_content(content, out)
            if text:
                out.events.append(_event("user_message", text=text, timestamp=ts))
        elif role == "assistant":
            text = _strip_think(_flatten_content(content, out), out)
            calls = [_tool_call_fields(tc) for tc in (m.get("tool_calls") or []) if isinstance(tc, dict)]
            calls += [(b.get("name"), b.get("input"), b.get("id")) for b in blocks if b.get("type") == "tool_use"]
            if text or not calls:
                out.events.append(_event("agent_message", text=text or "", timestamp=ts))
            for name, args, call_id in calls:
                out.events.append(_event("tool_call", tool=name, args=args, call_id=call_id, timestamp=ts))
        elif role == "tool":
            tool_call = m.get("tool_call") if isinstance(m.get("tool_call"), dict) else {}
            err, cls = error_of(m.get("error"))
            out.events.append(_event(
                "tool_result", tool=m.get("name") or _tool_call_fields(tool_call)[0],
                call_id=m.get("tool_call_id"), text=_flatten_content(content, out),
                error=err, error_class=cls, timestamp=ts))
        else:
            out.unknown_event_types.append("role:%s" % role)


def parse_record(raw: Dict[str, Any]) -> ParsedRun:
    out = ParsedRun()
    events = _first(raw, ("events", "trajectory"))
    if isinstance(events, list):
        out.source_format = "events"
        _parse_contract_events(events, out)
    elif isinstance(raw.get("messages"), list):
        out.source_format = "messages"
        _parse_messages(raw["messages"], out)
    return out
