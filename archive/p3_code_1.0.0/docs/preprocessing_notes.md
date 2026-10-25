# P3 Preprocessing Notes

Feature schema `p3-features-1.0` (frozen 2026-10-03), code `p3` 1.0.0.

## What P3 received

| From | Files |
| --- | --- |
| P1 | `data_contract_v0.2.md`, `experiment_protocol_v0.2.md`. Also the whole handoff v0.1 folder: manifest (which includes `attacker_goal`), `pilot_payloads.json`, `ground_truth_protocol.md` v0.1, `pilot_preflight.csv` and `evaluator_baseline_review.csv` (static checks with no agent run, not per-run outputs). Only the manifest is read by the pipeline, for `user_prompt` and the scenario/payload-hash check. The payloads feed only the mock-log generator. No attacker goal, payload or expected action reaches any feature |
| P2 | `raw_runs.jsonl`, `run_metadata.txt`, `checksums.sha256`, and a written situation report |

P3 did **not** receive `approved_labels_pilot_v0.2.csv`,
`eval_evidence.jsonl`, pre/post snapshots, evaluator outputs, adjudication
notes or `pilot_adjudication_working_v0.2.csv`.

## Disclosure: what P3 saw before the freeze

So reviewers can judge independence:

1. P2's situation report gave **aggregate** counts per model
   (`attack_ok` 0 / 1 / 2) and suggested `condition` as a temporary label.
   No per-run label was given.
2. P3 inspected raw trajectories, including tool arguments, while
   checking normalization. This showed which IPI runs called
   attacker-directed tools. The observations went to P1 as adjudication
   hints (`PILOT_REPORT_P3.md` §4); P1 owns all labels.
3. One rule was added after that inspection: `create_calendar_event` with
   non-empty `participants` counts as egress. The gap was already listed
   in P3 v0.1 before any real data arrived. The rule reads only whether
   the list is empty.
4. Earlier P3 builds (0.2, 0.3, now in `archive/`) produced descriptive
   tables of feature means split by `condition`. No feature was added,
   removed or changed because of those tables. From 1.0 on, summaries
   are split by source LLM only, and the package no longer carries
   `condition` or `injection_encountered`.

## Decisions

- `user_prompt` is missing from the P2 raw records. It is taken from the
  manifest only to mark that a user turn exists. No primary feature uses
  its text.
- The final answer was logged twice by the P2 runner (`agent_message` +
  `agent_final`, same text). It is kept once so that LLMs are not
  penalised for a logging artifact.
- Steps are recomputed as model turns. The runner's `step_index` is
  ignored so that every LLM is counted the same way.
- `run_id` from P2 contains the source LLM and the condition. It stays in
  every table as the join key and must be dropped before training.
- The pilot's nine scenario groups are development data (Protocol v0.2 §9).
  They were used to validate preprocessing, not to select features by
  label.

## Known limitations

- 22 of the 72 primary features are constant in the pilot: trajectories
  are short (2.2 tool calls on average) and no destructive, publish, share
  or admin tools were called. Full-experiment data may differ.
- Tool signatures cover the 69 AgentDojo v1 tools. A new tool appears as
  `unmapped_tool` and its missing/extra checks are left empty.
- `source_trust` follows tool semantics. An injection placed in a
  structured field, such as a Slack channel name, is not marked as free text.
