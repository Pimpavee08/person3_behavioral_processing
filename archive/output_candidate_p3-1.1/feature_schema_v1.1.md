# P3 Feature Schema v1.1 (FROZEN)

Owner: Person 3 (Trajectory Normalization / Feature Extraction)
Frozen: 2026-10-10, before any label for the candidate set reached P4
Governing spec: Data Contract v0.2 and the P2 → P3 candidate-package rules
Machine-readable copy: `feature_schema.json` (`schema_sha256` = 2f794f2d65dd3e63c8857a6d616e0a40fe0a39a29f7a7319e2fc5558c1c63ee5)

| Component | Version |
| --- | --- |
| Feature set | `p3-features-1.1` |
| Canonical trajectory | `p3-canonical-0.4` |
| Tool taxonomy | `p3-taxonomy-0.3` (69 AgentDojo v1 tools) |
| Tool signatures | AgentDojo commit `a75aba7631d3ca5fb7ab938965c97ead2f9ff84b` |
| Code | `p3` 1.1.0 |

`p3-features-1.0` (pilot v0.1, 2026-10-03) stays valid for the package it produced. The code is archived in `archive/p3_code_1.0.0/`.

## 1. Why 1.1

P2's blinded candidate package has a different input format:
- `trajectory_id` replaces `run_id`
- argument values are replaced by type descriptors
- assistant text, tool-result content and timestamps are removed
- errors arrive as `{error_present, error_class}`

Several 1.0 features could not be computed from that format. In 1.1, raw logs are first reduced to exactly the blinded structure, so the primary features of a raw run and of its blinded copy are identical (a test enforces this).

| Change from 1.0 | Reason |
| --- | --- |
| Key column is `trajectory_id` | P2 rule: the feature table is keyed by `trajectory_id` only |
| Arguments are stored as descriptors (`STR`, `INT`, `FLOAT`, `BOOL`, `NULL`, `LIST[n]:T`, `OBJECT{k:T}`) | Values are not available; the emptiness of a string is not known |
| `n_repeated_calls` → `n_repeated_call_shapes` | Identical values cannot be checked; a repeat now means the same tool with the same argument keys and types |
| `n_empty_results` removed | Tool-result content is not available |
| `n_agent_text_msgs` → `n_agent_messages`, `n_steps_text_and_call` → `n_steps_message_and_call` | Text presence is not available; agent_message events still are |
| Added `n_tool_results` | P2's list includes the tool-result count |
| Added `n_error_valueerror`, `n_error_validationerror`, `n_error_keyerror`, `n_error_other` | P2's list includes the error type |
| Added `final_output_present` | P2's list includes it (runner flag) |
| User message removed from the structural trajectory; `trajectory_length` no longer counts it | Blinded logs have no user turn |
| Duplicate final answer is detected by "same logged step" | Text is not available to compare |

## 2. Freeze rule

The schema was defined without labels, model identity, splits, `eval_evidence`, snapshots, evaluator outputs, adjudication notes or the `trajectory_id` mapping. Any later change to the features, taxonomy, signatures or structural keys needs a new `feature_set_version` and a notice to the team. The pipeline refuses to run if the code no longer matches the frozen hash.

## 3. Processing (identical for every trajectory)

1. Parse the events: P2 raw runner, P2 blinded, other Data Contract event lists, or AgentDojo/OpenAI/Anthropic messages.
2. Remove runner markers (`injected_content_delivered`), system messages and hidden reasoning.
3. Order by `event_index` and recompute steps as model turns.
4. Link each result to its call and rename call ids to `c0`, `c1`, …
5. Keep a final answer that was logged twice (agent_message + agent_final in the same step) only once.
6. Map every tool to normalized categories (section 5).
7. Reduce arguments to descriptors and compare their keys with the tool signature.
8. Write the structural trajectory, which has no text, values, result content or user message.
9. Compute the primary features per trajectory.
   - No step learns anything from the data set: no scaling, imputation, feature selection or PCA. P4 fits those on training data.
   - No rule depends on the source model or the label.

## 4. Structural event (`canonical_trajectories.jsonl`)

| Field | Meaning |
| --- | --- |
| `idx`, `step`, `type`, `actor`, `call_ref` | Position, model turn, event type, actor, call/result link |
| `tool` | AgentDojo tool name, or the name the model invented |
| `action`, `effect`, `domain`, `source_trust`, `egress`, `destructive`, `tool_mapped` | Normalized tool categories |
| `is_error`, `error_class` | Error flag and exception class (`ValueError`, `KeyError`, `ValidationError`, `UNSPECIFIED`, …) |
| `arg_count`, `arg_shape` | Number of arguments; key → descriptor |
| `n_missing_args`, `n_extra_args` | Missing required and undefined argument keys versus the signature (empty for an unknown tool) |
| `args_ref` | Equal for the same tool with the same argument keys and types within a trajectory |
| `t_rel` | Seconds since the first event (empty for blinded logs; never a primary feature) |

Record keys: `schema_version`, `taxonomy_version`, `trajectory_id`, `final_output_present`, `events`.

## 5. Normalized tool categories

| Attribute | Values |
| --- | --- |
| `action` | retrieve, list, search, create, update, delete, send_message, transfer_value, publish, reserve, share, admin |
| `effect` | read, write |
| `domain` | finance, messaging, email, calendar, file, web, travel, account, contact, system |
| `source_trust` (reads) | own, third_party_structured, third_party_freetext |
| `egress` | Sends data/value to another party or grants access. `create_calendar_event` counts when `participants` is a non-empty list |
| `destructive` | Deletes or revokes |

A tool name outside the 69 AgentDojo tools keeps its name, gets `tool_mapped = false` and a verb-prefix class. It is counted by `n_unmapped_tool_calls`. There are 13 such calls in the candidate set.

## 6. Primary features (77, `features.csv`)

| Group | n | Features |
| --- | --- | --- |
| volume | 5 | n_tool_calls, n_tool_results, n_unique_tools, n_unmapped_tool_calls, trajectory_length |
| action_mix | 23 | n_read, n_write, n_egress, n_destructive, frac_write, frac_egress, n_act_* (12), n_domains, n_domain_switches, n_write_domains, n_writes_new_domain, action_entropy |
| sequence | 17 | has_write, first_write_pos, n_reads_after_first_write, n_write_bursts, max_read_streak, n_repeated_call_shapes, n_tool_revisits, max_same_tool_run, trans_RR … trans_EE (9) |
| exposure_structure | 6 | n_freetext_reads, n_writes_after_freetext, n_egress_after_freetext, n_destructive_after_freetext, frac_writes_after_freetext, n_calls_after_last_freetext |
| errors | 8 | n_tool_errors, frac_tool_errors, n_retry_after_error, n_calls_without_result, n_error_valueerror, n_error_validationerror, n_error_keyerror, n_error_other |
| arguments | 11 | mean_args_per_call, max_args_per_call, n_calls_without_args, n_unparseable_args, n_calls_missing_required, n_calls_extra_args, frac_arg_str, frac_arg_number, frac_arg_bool, frac_arg_collection, frac_arg_empty |
| termination | 2 | ended_with_final, final_output_present |
| shape | 5 | n_steps, max_calls_per_step, mean_calls_per_step, n_agent_messages, n_steps_message_and_call |

Every feature is defined in `feature_readme.md` and `feature_dictionary.csv`.

| Allowed in the P2 rules | Features |
| --- | --- |
| trajectory length / step count | trajectory_length, n_steps |
| tool call and tool result counts | n_tool_calls, n_tool_results |
| tool names | Used through categories (n_act_*, n_domains, …) and identity counts (n_unique_tools, n_tool_revisits, n_unmapped_tool_calls). One column per tool name is avoided to limit task memorization (Data Contract §11) |
| unique tool count | n_unique_tools |
| order of tool calls | first_write_pos, n_reads_after_first_write, n_write_bursts, exposure_structure group |
| transitions | trans_*, n_domain_switches, n_steps_message_and_call |
| repeats | n_repeated_call_shapes, n_tool_revisits, max_same_tool_run, n_retry_after_error |
| argument structure and types | the arguments group |
| errors and error types | the errors group |
| final_output_present | final_output_present |

`suite` and `schema_version` are metadata only. They appear in `trajectory_index.csv`, never in `features.csv`.

## 7. Secondary features (12, `features_extended.csv`)

The 10 `text_derived` and 2 `timing` features of 1.0 are unchanged. They need text and timestamps, so they are empty for blinded logs and the file is not written for them.

## 8. Guarantees checked by the test suite (32 tests)

- A raw run and its blinded copy give identical primary features.
- Rewriting every string in a raw run leaves the primary features unchanged.
- Removing runner markers leaves every feature unchanged.
- Model, scenario and label fields in the input do not change the output.
- No feature column is a label, model, split, key or metadata field.
- For the candidate set:
  - 1,158 unique ids and 1,158 feature rows.
  - Error-class totals and `tool_call` / `agent_final` counts equal P2's `validation_report.json`.
