# P3 Feature Schema v1.0 (FROZEN)

Owner: Person 3 (Trajectory Normalization / Feature Extraction)
Frozen: 2026-10-03, before any P1 label reached P4
Governing spec: Data Contract v0.2, Experiment Protocol v0.2
Machine-readable copy: `feature_schema.json` (`schema_sha256` = 855628e7ea1c5cf380019c38fe04dcd5491945c03e2517cbb218ed4758923779)

| Component | Version |
| --- | --- |
| Feature set | `p3-features-1.0` |
| Canonical trajectory | `p3-canonical-0.3` |
| Tool taxonomy | `p3-taxonomy-0.2` (69 AgentDojo v1 tools) |
| Tool signatures | AgentDojo commit `a75aba7631d3ca5fb7ab938965c97ead2f9ff84b` |
| Code | `p3` 1.0.0 |

Supersedes `canonical_schema_v0.1.md` and `canonical_schema_v0.2.md`.

## 1. Freeze rule

The schema was defined without P1 approved labels, `eval_evidence.jsonl`,
environment snapshots, evaluator outputs or adjudication notes. After this
date, any change to the features, the taxonomy, the tool signatures or the
structural event keys requires a new `feature_set_version` and a notice to
the team. The pipeline refuses to run if the code no longer matches the
frozen hash. Descriptions are not hashed, so wording can be corrected.

## 2. Pipeline

raw trajectory → clean/normalize → remove leakage-prone signals →
canonical structural trajectory → structural features → frozen schema

1. Parse the raw events (P2 runner layout, other Data Contract event lists,
   or AgentDojo/OpenAI/Anthropic messages).
2. Remove `injected_content_delivered` and other runner markers, system
   messages and hidden reasoning before anything else. They are never
   counted in any length or count.
3. Order events by `event_index`, recompute steps as model turns, link
   results to calls, replace raw call ids with `c0`, `c1`, ..., and keep a
   closing answer that was logged twice only once.
4. Map every tool to normalized categories (section 4).
5. Write the structural trajectory: no raw text, no argument values.
6. Compute the primary features from the structural trajectory only.

## 3. Structural event (`canonical_trajectories.jsonl`)

| Field | Meaning |
| --- | --- |
| `idx`, `step`, `type`, `actor`, `call_ref` | Position, model turn, event type, actor, call/result link |
| `tool` | AgentDojo tool name. Kept for preprocessing; features use categories or identity counts |
| `action`, `effect`, `domain`, `source_trust`, `egress`, `destructive`, `tool_mapped` | Normalized tool categories |
| `arg_count` | Number of arguments (null if they could not be parsed) |
| `arg_types` | Argument key -> type label (`str`, `empty_str`, `number`, `bool`, `list`, `empty_list`, `object`, `empty_object`, `null`, `other`) |
| `n_missing_args`, `n_extra_args` | Missing required / undefined argument keys versus the tool signature |
| `args_ref` | `a0`, `a1`, ... Equal only for the same tool with identical arguments in this run |
| `result_type` | `value`, `empty` or `error` |
| `has_text` | Whether a message had text |
| `is_error` | Tool or execution error |
| `t_rel` | Seconds since the first event. Audit only, never a primary feature |

## 4. Normalized tool categories

| Attribute | Values |
| --- | --- |
| `action` | retrieve, list, search, create, update, delete, send_message, transfer_value, publish, reserve, share, admin |
| `effect` | read, write |
| `domain` | finance, messaging, email, calendar, file, web, travel, account, contact, system |
| `source_trust` (reads) | own, third_party_structured, third_party_freetext |
| `egress` | Sends data/value to another party or grants access. `create_calendar_event` counts only when `participants` is non-empty (emptiness checked, values not read) |
| `destructive` | Deletes or revokes |

The categories come from what each tool does. The injection-vector list
and attacker goals were not used.

## 5. Primary features (72, `features.csv`)

| Group | n | Features |
| --- | --- | --- |
| volume | 4 | n_tool_calls, n_unique_tools, n_unmapped_tool_calls, trajectory_length |
| action_mix | 23 | n_read, n_write, n_egress, n_destructive, frac_write, frac_egress, n_act_* (12 actions), n_domains, n_domain_switches, n_write_domains, n_writes_new_domain, action_entropy |
| sequence | 17 | has_write, first_write_pos, n_reads_after_first_write, n_write_bursts, max_read_streak, n_repeated_calls, n_tool_revisits, max_same_tool_run, trans_RR … trans_EE (9 transitions over read / internal write / egress write) |
| exposure_structure | 6 | n_freetext_reads, n_writes_after_freetext, n_egress_after_freetext, n_destructive_after_freetext, frac_writes_after_freetext, n_calls_after_last_freetext |
| errors | 5 | n_tool_errors, frac_tool_errors, n_retry_after_error, n_calls_without_result, n_empty_results |
| arguments | 11 | mean_args_per_call, max_args_per_call, n_calls_without_args, n_unparseable_args, n_calls_missing_required, n_calls_extra_args, frac_arg_str, frac_arg_number, frac_arg_bool, frac_arg_collection, frac_arg_empty |
| termination | 1 | ended_with_final |
| shape | 5 | n_steps, max_calls_per_step, mean_calls_per_step, n_agent_text_msgs, n_steps_text_and_call |

Definitions are in `feature_dictionary.csv`. How the P1 recommendations
map to these features:

| P1 recommendation | Features |
| --- | --- |
| agent step count | n_steps |
| tool-call count | n_tool_calls |
| unique tool count | n_unique_tools |
| normalized tool categories | n_read/n_write/n_egress/n_destructive, n_act_*, n_domains |
| action order | first_write_pos, n_reads_after_first_write, n_write_bursts, the exposure_structure group |
| tool transitions | trans_* |
| repeated actions | n_repeated_calls, n_retry_after_error |
| loops | n_tool_revisits, max_same_tool_run, max_read_streak |
| tool error indicators | n_tool_errors, frac_tool_errors, n_empty_results |
| argument count / type | mean/max_args_per_call, n_calls_without_args, frac_arg_* |
| missing/extra argument structure | n_calls_missing_required, n_calls_extra_args, n_unparseable_args |
| canonical trajectory length | trajectory_length |

## 6. Secondary features (12, `features_extended.csv` only)

These are not primary detector input (Data Contract v0.2 §11). Use them
only in a separately justified analysis.

- `text_derived` (10): total/mean result chars, final/agent text length,
  six argument-provenance features.
- `timing` (2): duration_s, mean_agent_latency_s.

## 7. Guarantees checked by the test suite

- Rewriting every string in a run (keeping which strings are equal or
  empty) leaves every primary feature unchanged.
- Removing runner markers from a raw run leaves every feature unchanged.
- Changing scenario, model, provider or label fields in the raw record
  leaves the output unchanged.
- No feature column name is a label, attack, evaluator or identity field.
- The structural trajectory has exactly the whitelisted keys and no text
  or argument values.
- The tool signatures agree with all 121 tool calls in the pilot: no
  missing or extra keys on any call.
