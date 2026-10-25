# P3 Feature Schema v1.2 (FROZEN)

Owner: Person 3 (Trajectory Normalization / Feature Extraction)
Frozen: 2026-10-10, before any label for the candidate set reached P4
Governing spec: Data Contract v0.2 and the P2 → P3 candidate-package rules
Machine-readable copy: `feature_schema.json`
- `schema_sha256` = 1c8adb151a5687f4fb4543bfb167c35766947cd7f17af588894983c7ec6f31d3 (definitions)
- `code_sha256` = e5e40caf6ebad8394ec90adce94bd20aed82f7cd68215a6dc0b711ec13b68be7 (feature-computing code)

| Component | Version |
| --- | --- |
| Feature set | `p3-features-1.2` |
| Canonical trajectory | `p3-canonical-0.5` |
| Tool taxonomy | `p3-taxonomy-0.3` (69 AgentDojo v1 tools) |
| Tool signatures | AgentDojo commit `a75aba7631d3ca5fb7ab938965c97ead2f9ff84b` |
| Code | `p3` 1.2.1 (refactor of 1.2.0; byte-identical feature output) |

Supersedes `p3-features-1.1` (same day; never paired with labels). `p3-features-1.0` (pilot v0.1) stays valid for the package it produced. Old code is archived in `archive/p3_code_1.0.0/` and `archive/p3_code_1.1.0/`.

## 1. Changes

### 1.1 → 1.2 (code review, 2026-10-10)

| Change | Effect on the candidate set |
| --- | --- |
| `n_retry_after_error` counts the next call to the same tool only when it comes in a **later turn** than the failed call. A call issued in the same turn was sent before the error could be seen | 9 of 1,158 trajectories change (11 same-turn pairs no longer counted) |
| `action_entropy` no longer writes `-0.0` | Text only (208 cells); values are equal |
| The freeze also hashes the source of the feature-computing modules (`code_sha256`). Any change to how a feature is computed now stops the pipeline until a new version is frozen | No value change |
| Raw vs blinded input is decided from the content (text, results, timestamps), not from which id key is present. A raw value found in a blinded log is described as a type (never kept) and reported | No value change |
| Events with `actor = runner` are removed before anything is counted (P2 rule), whatever their event type | No value change (no such events) |
| Empty or agent-less trajectories get a feature row (warning instead of exclusion) | No value change (none in the set) |
| Robustness: a malformed record is reported and skipped instead of stopping the batch; ids must be plain tokens; `error_present` strings are read correctly; `<think>` removal is linear time | No value change |
| Output: built in a staging folder and swapped in whole; an output folder with foreign files is refused; spreadsheet-formula text is escaped in CSV; Markdown reports escape input text | No value change |

### 1.0 → 1.1 (blinded input)

| Change | Reason |
| --- | --- |
| The key column is `trajectory_id` | P2 rule: the feature table is keyed by `trajectory_id` only |
| Arguments are stored as descriptors (`STR`, `INT`, `FLOAT`, `BOOL`, `NULL`, `LIST[n]:T`, `OBJECT{k:T}`) | Values are not available |
| `n_repeated_calls` → `n_repeated_call_shapes`; `n_empty_results` removed; `n_agent_text_msgs` → `n_agent_messages`; `n_steps_text_and_call` → `n_steps_message_and_call` | Text, values and result content are not available |
| Added `n_tool_results`, `n_error_valueerror`, `n_error_validationerror`, `n_error_keyerror`, `n_error_other`, `final_output_present` | Allowed in the P2 rules |
| The user message is not part of the structural trajectory | Blinded logs have no user turn |

## 2. Freeze rule

The schema was defined without labels, model identity, splits, `eval_evidence`, snapshots, evaluator outputs, adjudication notes or the `trajectory_id` mapping.

The pipeline refuses to run if either of these differs from `feature_schema.json`:
- the definitions: feature list, taxonomy, tool signatures and structural keys
- the code of `parsers.py`, `descriptors.py`, `tool_taxonomy.py`, `tool_signatures.py`, `normalize.py` and `features.py`

Any change therefore needs a new `feature_set_version` and a notice to the team.

## 3. Processing (identical for every trajectory)

1. Parse the events: P2 raw runner, P2 blinded, other Data Contract event lists, or AgentDojo/OpenAI/Anthropic messages.
2. Remove runner-generated events (`actor = runner`, `injected_content_delivered`), system messages and hidden reasoning before anything is counted.
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

The 10 `text_derived` and 2 `timing` features need text and timestamps. They are empty for blinded logs, and the file is not written for them.

## 8. Guarantees checked by the test suite (49 tests)

- A raw run and its blinded copy give identical primary features.
- Rewriting every string in a raw run leaves the primary features unchanged.
- Removing runner markers or adding `actor = runner` events leaves the features unchanged.
- Model, scenario and label fields in the input do not change the output.
- No feature column is a label, model, split, key or metadata field.
- Editing a feature-computing module makes the pipeline refuse to run. A CRLF copy of the same code is accepted.
- Malformed records are reported without stopping the batch.
- A rerun into an old output folder leaves no stale file, and a folder with foreign files is refused.
- Formula-like text in CSV cells is escaped.
- A feature function that returns a misspelt or missing feature name stops the run.
- The candidate set's `features.csv` has a fixed SHA-256 (golden output).
- The sources parse as Python 3.9 syntax. The suite runs on Python 3.12 and 3.14.
- For the candidate set:
  - 1,158 unique ids and 1,158 feature rows.
  - Error-class totals and `tool_call` / `agent_final` counts equal P2's `validation_report.json`.
