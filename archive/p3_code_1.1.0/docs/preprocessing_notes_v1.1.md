# P3 Preprocessing Notes (feature set 1.1)

Code `p3` 1.1.0, feature schema `p3-features-1.1` (frozen 2026-10-10).

## Input

| From | File | Notes |
| --- | --- | --- |
| P2 | `trajectories_sanitized.jsonl` (1,158 blinded trajectories), `SCHEMA.json`, `README.txt`, `validation_report.json` | Received unpacked. The zip was not available, so P2's zip SHA-256 (`4C107981…0BDC`) could not be checked. The SHA-256 of `trajectories_sanitized.jsonl` is recorded in `preprocessing_metadata.json` |

P2's README marks the package "NOT released until P1 approval". These outputs are a candidate on the same terms.

P3 did not receive, and did not try to reconstruct:
- labels, model identity or splits
- assistant text or tool-result content
- the original ids or the `trajectory_id` mapping
- `eval_evidence`, snapshots, evaluator outputs or adjudication notes

## Decisions

- **One rule set for all trajectories.** Nothing depends on the source model.
- **Hallucinated tool names** (13 calls, e.g. `get_all_car_rental_companies`, `get_hotel_prices`) are kept as observed behaviour. They are counted by `n_unmapped_tool_calls`, and their missing/extra argument checks are left empty.
- **Duplicated final answer.** The runner logs the closing answer as `agent_message` plus `agent_final` in the same step. These 1,132 pairs are kept as one final answer. The 79 `agent_message` events that sit beside tool calls stay and are counted by `n_agent_messages`.
- **Missing final answer.** Four trajectories have no `agent_final`; all four hit `steps_used = 15` (step limit). They are valid: `ended_with_final = 0`, `final_output_present = 0`.
- **`final_output_present` versus `ended_with_final`.**
  - `final_output_present` is P2's flag: it is 0 for 26 trajectories, which is the 4 above plus 22 whose final answer was empty.
  - `ended_with_final` is 1 whenever an `agent_final` event exists.
- **Parallel tool calls.** Some turns contain 2–6 calls even though the runner asked for no parallel calls. Steps are counted as model turns, so this is visible in `max_calls_per_step` and `mean_calls_per_step`.
- **No data-set-level processing.** There is no scaling, imputation, feature selection or PCA. Missing values stay empty (for example, `frac_arg_*` when a trajectory has no arguments is 0 by definition, not imputed).

## Known limitations

- Strings arrive only as `STR`, so an empty string cannot be told from a non-empty one.
- Repeats are measured at the level of argument keys and types, not values.
- `source_trust` follows tool semantics. An injection placed in a structured field, such as a Slack channel name, is not marked as free text.
