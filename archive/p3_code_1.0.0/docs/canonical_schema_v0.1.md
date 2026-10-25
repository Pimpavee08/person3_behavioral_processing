# Canonical Trajectory Schema v0.1

> Superseded by `feature_schema_v1.0.md` (frozen 2026-10-03). Kept for reference.

Owner: Person 3 (Behavioral Processing)
Status: Draft for team review. Run on the 54-run Person 2 pilot (2026-10-02).
Schema ID: `p3-canonical-0.1` / Taxonomy: `p3-taxonomy-0.2` / Features: `p3-features-0.2`

## 1. Purpose

One representation of an agent run that is identical no matter which
source LLM or provider produced it. Behavioral features are computed
from this representation and from nothing else.

## 2. Accepted raw input

One JSON object per line (`raw_runs.jsonl`). The run must carry `run_id`
and one of:

| Layout | Field | Shape |
| --- | --- | --- |
| Contract events | `events` | Event list of data_contract_v0.1 section 5 |
| Chat transcript | `messages` | AgentDojo, OpenAI/Groq or Anthropic message list |

Field aliases accepted in the contract layout:

| Canonical meaning | Accepted raw keys |
| --- | --- |
| event type | `event_type`, `type` |
| tool name | `tool_name`, `name`, `function` |
| call id | `tool_call_id`, `call_id`, `tool_use_id`, `id` |
| arguments | `tool_arguments`, `arguments`, `args`, `input` (object or JSON string) |
| result | `tool_result`, `result`, `output`, `content` |
| text | `content`, `content_text`, `text`, `message` |
| time | `timestamp`, `time`, `ts` (ISO 8601 or epoch seconds) |

The user instruction is taken from a `user_message` event, else from the
record field `user_prompt`, else from the manifest (`--manifest`).

## 3. Canonical record

```json
{"schema_version": "p3-canonical-0.1", "taxonomy_version": "p3-taxonomy-0.1",
 "run_id": "...", "events": [ ... ]}
```

These four keys are the whole record. It is built from a whitelist, so
scenario, model, provider, condition, labels, usage and reproducibility
metadata cannot appear in it.

## 4. Canonical event

| Field | Type | Meaning |
| --- | --- | --- |
| `idx` | int | Position in the run, 0..n-1 |
| `step` | int / null | Model turn, recomputed (section 5). null for the user message |
| `type` | string | `user_message`, `agent_message`, `tool_call`, `tool_result`, `agent_final`, `execution_error` |
| `actor` | string | `user`, `agent`, `tool`, `runtime` |
| `call_ref` | string / null | `c0`, `c1`, ... in call order. Same value on a call and its result |
| `tool` | string / null | Tool name, lower-cased, provider namespace removed |
| `action` | string / null | Canonical action (section 6) |
| `effect` | string / null | `read`, `write`, `unknown` |
| `domain` | string / null | Resource domain (section 6) |
| `source_trust` | string / null | Read tools only (section 6) |
| `egress` | bool | Sends data/value to another party or grants access |
| `destructive` | bool | Deletes or revokes |
| `tool_mapped` | bool | false when the tool is not in the taxonomy table |
| `args` | object / null | Parsed arguments. null when they could not be parsed |
| `text` | string / null | Message text, tool result, or error message |
| `is_error` | bool | Tool error or execution error |
| `t_rel` | number / null | Seconds since the first timestamped event |

Tool results copy the tool fields of the call they answer.

## 5. Normalization rules

1. Order. `event_index` decides the order. If the file order disagrees,
   events are re-sorted and `event_order_violation` is reported.
2. Steps. A step is one model turn: consecutive agent events with no
   tool result or user message between them. Provider `step_index` is
   ignored. Parallel tool calls therefore share a step.
3. Call linking. A result is linked to its call by the raw call id. When
   the log has no ids, it is linked to the oldest pending call of the
   same tool (`result_linked_by_position`). Raw ids are then replaced by
   `c0`, `c1`, ...
4. Arguments. JSON strings and objects both become objects.
5. Final answer. A text turn that ends the trajectory is `agent_final`.
   When the runner logs the closing answer twice (`agent_message` then
   `agent_final` with the same text, as the Person 2 runner does), only
   the `agent_final` is kept (`duplicate_final_merged`).
6. Removed, and counted in the quality report:
   - `injected_content_delivered` events. They are runner instrumentation
     and reveal `ipi_present`; they belong to evaluation, not to the
     detector input.
   - Reasoning: `thinking` / `reasoning` blocks and `<think>...</think>`.
   - System messages.
   - Every raw key outside the tables above (`provider_meta`, `usage`,
     response ids, stop reasons, ...).

## 6. Tool taxonomy

Defined in `p3/tool_taxonomy.py` for all 69 distinct AgentDojo v1 tools
(45 read, 24 write; 11 egress, 4 destructive; 17 free-text reads). It was
written from what each tool does. The injection-vector list, attacker
goals and expected attack actions were not consulted.

| Attribute | Values |
| --- | --- |
| `action` | retrieve, list, search, create, update, delete, send_message, transfer_value, publish, reserve, share, admin |
| `domain` | finance, messaging, email, calendar, file, web, travel, account, contact, system |
| `source_trust` | `own` (the user's own account or system state), `third_party_structured` (listings: names, prices, addresses), `third_party_freetext` (mail, pages, files, reviews, transaction subjects, event descriptions) |

Consequence of not consulting the vector list: a vector that sits in a
structured field (for example a Slack channel name) is not marked as
free text. This is intended.

Tools outside the table get `tool_mapped = false` and a class guessed
from the verb prefix (`get_`, `send_`, `delete_`, ...).

One argument-dependent rule (v0.2): `create_calendar_event` is egress when
`participants` is non-empty, because the invitation reaches other people.
v0.1 listed this as a known gap; the pilot contains such a call.

## 7. Issue codes

| Severity | Code | Meaning |
| --- | --- | --- |
| error | `invalid_json`, `missing_run_id`, `duplicate_run_id` | Record excluded from all outputs |
| error | `no_trajectory`, `no_agent_events`, `missing_tool_name` | Indexed, no feature row |
| error | `invalid_condition`, `scenario_not_in_manifest`, `payload_hash_mismatch` | Indexed, no feature row |
| warning | `tool_call_without_result`, `orphan_tool_result`, `duplicate_tool_call_id` | Pairing problem |
| warning | `unparseable_tool_arguments`, `unmapped_tool`, `unknown_event_type`, `malformed_event` | Content problem |
| warning | `event_order_violation`, `duplicate_event_index` | Ordering problem |
| warning | `missing_user_prompt`, `missing_identity_field`, `missing_execution_status`, `unknown_execution_status`, `missing_payload_hash` | Missing metadata |
| info | `result_linked_by_position`, `missing_event_index`, `missing_timestamps`, `no_final_message`, `non_completed_status`, `user_prompt_from_manifest` | Worth knowing |
| info | `duplicate_final_merged` | Closing answer was logged twice |
| info | `reasoning_removed`, `exposure_marker_removed` | Expected removals |

No run is dropped silently. Every excluded record has a row in
`quality_issues.csv`.

## 8. Output files

| File | Content | Detector input? |
| --- | --- | --- |
| `canonical_trajectories.jsonl` | One canonical record per run | Source for features only |
| `features.csv` | `run_id` + 57 core features | Yes, after dropping `run_id` |
| `features_extended.csv` | `run_id` + all 69 features | Only for ablations the team approves |
| `feature_dictionary.csv` | Name, group, caution, description | Documentation |
| `feature_summary.md` | Core feature means by source LLM and condition | No |
| `run_index.csv` | `run_id`, source_llm, suite, scenario group, condition, split, status, injection_encountered, validity | No. Join and reporting only |
| `quality_issues.csv` | One row per issue | No |
| `quality_report.md` | Summary of the above | No |

## 9. Feature cautions

The team design (D2) limits detector features to structure: no text
content, no timing, no tokens. `feature_dictionary.csv` therefore marks
12 of the 69 features, and `features.csv` leaves them out:

- `timing` (2): `duration_s`, `mean_agent_latency_s`.
- `text_derived` (10): tool-result sizes, final/agent text lengths and the
  six provenance features (they compare argument strings with earlier
  text). Tool-result sizes also grow when a payload is present, even if
  the agent ignored it.

The remaining 57 are the core set. `run_id` is a join key, not a feature:
in the Person 2 pilot it spells out the source LLM and the condition.
