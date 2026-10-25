# P3 Preprocessing Notes (feature set 1.2)

Code `p3` 1.2.1, feature schema `p3-features-1.2` (frozen 2026-10-10).

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

Questions about labels or data provenance go to P1.

## Decisions

- **One rule set for all trajectories.** Nothing depends on the source model.
- **Hallucinated tool names** (13 calls, e.g. `get_all_car_rental_companies`, `get_hotel_prices`) are kept as observed behaviour. They are counted by `n_unmapped_tool_calls`, and their missing/extra argument checks are left empty.
- **Duplicated final answer.** The runner logs the closing answer as `agent_message` plus `agent_final` in the same step. These 1,132 pairs are kept as one final answer. The 79 `agent_message` events that sit beside tool calls stay and are counted by `n_agent_messages`.
- **Missing final answer.** Four trajectories have no `agent_final`; all four hit `steps_used = 15` (step limit). As P2 noted, this is normal: `ended_with_final = 0`, `final_output_present = 0`.
- **`final_output_present` versus `ended_with_final`.**
  - `final_output_present` is P2's flag: it is 0 for 26 trajectories, which is the 4 above plus 22 whose final answer was empty.
  - `ended_with_final` is 1 whenever an `agent_final` event exists.
- **Parallel tool calls.** Some turns contain 2–6 calls. Steps are counted as model turns, and a call in the same turn as a failed call is not counted as a retry.
- **No data-set-level processing.** There is no scaling, imputation, feature selection or PCA. Ratios over zero items are 0 by definition, not imputed.
- **Runner-generated events** (`actor = runner`) are removed before anything is counted. None remain in the candidate set; P2 removed 1,037 markers upstream.

## Robustness rules (1.2)

- **Bad records.** A record that cannot be read or processed (bad UTF-8, broken or deeply nested JSON, an id that is not a plain token, unexpected types) is listed in `quality_issues.csv` with no feature row. `id_validation.json` then reports FAIL. The rest of the batch is unaffected.
- **Output folder.** The output folder is built aside and replaced whole. A folder holding files the tool did not write is refused.
- **Text cells.** Cells that would start a spreadsheet formula (`=`, `+`, `-`, `@`) are prefixed with `'` in CSV files. Input text in Markdown reports is shown as escaped code.

## Known limitations

- Strings arrive only as `STR`, so an empty string cannot be told from a non-empty one.
- Repeats are measured at the level of argument keys and types, not values.
- `source_trust` follows tool semantics. An injection placed in a structured field, such as a Slack channel name, is not marked as free text.
- The whole input file is held in memory. That is a few MB for 1,158 trajectories; reading it as a stream would be needed only at hundreds of thousands of trajectories.
