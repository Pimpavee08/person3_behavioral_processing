# Canonical Trajectory Schema v0.2

> Superseded by `feature_schema_v1.0.md` (frozen 2026-10-03). Kept for reference.

Owner: Person 3 (Behavioral Processing)
Status: Draft for team review. Aligned with Data Contract v0.2.
IDs: canonical `p3-canonical-0.2` / taxonomy `p3-taxonomy-0.2` / features `p3-features-0.3` / code `p3` 0.3.0
Supersedes: `canonical_schema_v0.1.md` (kept for reference)

## 1. What changed from v0.1

| Change | Reason (Data Contract v0.2) |
| --- | --- |
| The written trajectory has no raw text and no argument values | §5 Event normalization, §11 Raw text restriction |
| Arguments are kept as `arg_count`, `arg_types`, `args_ref` | §5 Tool-call events (permitted structural properties) |
| Results are kept as `result_type`; messages as `has_text` | §5 Tool-result and agent-message events |
| Primary features are computed from the written trajectory only | §11 Prohibited feature sources |
| 10 argument/result structure features added | §11 Permitted structural behavior |
| `run_index.csv` adds `user_task_id`, `repetition_index`, `attempt_index` | §3 Repetitions and attempts, §12 Split validation |
| Batch check for several attempts of one run | §3, §9 Retry handling |
| Exposure fields checked for IPI runs | §12 Exposure validation |
| v0.2 execution-status vocabulary accepted | §9 |
| Package ships `preprocessing_metadata.json` and `checksums.sha256` | §2 P3 artifacts, §12 Package validation |

## 2. Accepted raw input

Unchanged from v0.1: one JSON object per line, with `events` (Data
Contract event list, including the Person 2 runner layout) or `messages`
(AgentDojo, OpenAI/Groq or Anthropic). Text may be in `content`,
`content_text`, `text` or `message`.

## 3. Two records per run

| Record | Contains | Where it lives | Used for |
| --- | --- | --- | --- |
| Working record | Structure, raw text, parsed argument values | Memory only | Non-primary features (`features_extended.csv`) |
| Structural record | Structure only | `canonical_trajectories.jsonl` | Primary features (`features.csv`) |

Record keys: `schema_version`, `taxonomy_version`, `run_id`, `events`.
`run_id` is the join key. In the Person 2 pilot it spells out the source
LLM and condition, so it must never be used as a feature.

## 4. Structural event

| Field | Type | Meaning |
| --- | --- | --- |
| `idx` | int | Position in the run, 0..n-1 |
| `step` | int / null | Model turn, recomputed. null for the user message |
| `type` | string | `user_message`, `agent_message`, `tool_call`, `tool_result`, `agent_final`, `execution_error` |
| `actor` | string | `user`, `agent`, `tool`, `runtime` |
| `call_ref` | string / null | `c0`, `c1`, ... Same value on a call and its result |
| `tool` | string / null | AgentDojo tool name (kept for preprocessing, §11) |
| `action`, `effect`, `domain`, `source_trust` | string / null | Normalized tool categories (section 6) |
| `egress`, `destructive`, `tool_mapped` | bool | Tool properties |
| `arg_count` | int / null | Tool calls: number of arguments. null if they could not be parsed |
| `arg_types` | object / null | Tool calls: argument key -> type label (section 5) |
| `args_ref` | string / null | Tool calls: `a0`, `a1`, ... Equal only for the same tool with identical arguments in this run |
| `result_type` | string / null | Tool results: `value`, `empty`, `error` |
| `has_text` | bool / null | Messages: whether the message had any text |
| `is_error` | bool | Tool error or execution error |
| `t_rel` | number / null | Seconds since the first event. Kept for audit; not a primary feature |

## 5. Argument type labels

`str`, `empty_str`, `number` (int and float together, so `10` and `10.0`
do not split by model style), `bool`, `list`, `empty_list`, `object`,
`empty_object`, `null`, `other`.

## 6. Normalization rules

1. Order by `event_index`. If the file order disagrees, events are re-sorted (`event_order_violation`).
2. A step is one model turn: consecutive agent events with no tool result
   or user message in between. Provider and runner step numbers are ignored.
3. Results link to calls by raw call id, else by position (`result_linked_by_position`).
   Raw ids are replaced by `c0`, `c1`, ...
4. A closing answer logged as `agent_message` then `agent_final` with
   identical text is kept once (`duplicate_final_merged`).
5. Removed before anything else: `injected_content_delivered` and other
   runner markers, system messages, hidden reasoning (`thinking` blocks,
   `<think>...</think>`). They are never counted in trajectory length.
6. Every raw key outside this schema is dropped, including `usage_total`,
   `llm_calls`, `reproducibility`, `injection` and identity fields.

## 7. Tool taxonomy

69 distinct AgentDojo v1 tools. The tool lists were checked against both
`main` and the frozen commit `a75aba7631d3ca5fb7ab938965c97ead2f9ff84b`
and are identical. Attributes and values are the same as in v0.1. The
only argument-dependent rule is that `create_calendar_event` with
non-empty `participants` is egress. It reads whether the list is empty,
never the participant values.

## 8. Features

`feature_dictionary.csv` lists all 79 features.

- **Primary (67, `features.csv`):** volume, action mix, sequence and
  transitions, behaviour after free-text reads, errors and result
  structure, argument structure, termination, turn shape.
- **Non-primary (12, `features_extended.csv` only):**
  - `text_derived` (10): tool-result sizes, message lengths, argument provenance.
  - `timing` (2): run duration, model latency.

The test suite enforces that primary features do not depend on text: it
rewrites every string in a run, keeping which strings are equal or
empty, and requires identical primary features.

## 9. Package contents

| File | Detector input? |
| --- | --- |
| `features.csv` | Yes, after dropping `run_id` |
| `features_extended.csv` | Only for separately justified ablations |
| `canonical_trajectories.jsonl` | Source of `features.csv` |
| `run_index.csv` | No. Partitioning, splitting and reporting only |
| `feature_dictionary.csv`, `feature_summary.md` | Documentation |
| `quality_report.md`, `quality_issues.csv` | Data-quality evidence |
| `preprocessing_metadata.json` | Versions, input hashes, rules |
| `checksums.sha256` | SHA-256 of every file above (LF, lowercase) |

## 10. Not implemented

- Missing/extra argument indicators against the tool signature (§5).
  These need the AgentDojo function signatures at the frozen commit.
  Today a malformed call appears only through `n_unparseable_args` and
  the tool error the environment returns.
