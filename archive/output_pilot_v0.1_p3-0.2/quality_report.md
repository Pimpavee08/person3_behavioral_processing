# Person 3 Quality Report

Input: `../P2_for_P3_P4/raw_runs.jsonl`

p3 version: 0.2.0  
canonical schema: p3-canonical-0.1  
taxonomy: p3-taxonomy-0.2  
feature set: p3-features-0.2  

## 1. Summary

| Item | Count |
| --- | --- |
| Lines read | 54 |
| Runs indexed | 54 |
| Structurally valid (features written) | 54 |
| Excluded from features | 0 |
| Issues: error / warning / info | 0 / 0 / 133 |

## 2. Runs by source LLM and execution status

| source_llm | completed |
| --- | --- |
| LLM-A | 18 |
| LLM-B | 18 |
| LLM-C | 18 |

## 3. Issues

| severity | code | issues | runs | LLM-A | LLM-B | LLM-C |
| --- | --- | --- | --- | --- | --- | --- |
| info | duplicate_final_merged | 53 | 53 | 18 | 17 | 18 |
| info | exposure_marker_removed | 26 | 26 | 9 | 9 | 8 |
| info | user_prompt_from_manifest | 54 | 54 | 18 | 18 | 18 |

## 4. Tool call / result pairing

| source_llm | tool calls | linked results | paired |
| --- | --- | --- | --- |
| LLM-A | 41 | 41 | 100.0% |
| LLM-B | 41 | 41 | 100.0% |
| LLM-C | 39 | 39 | 100.0% |

## 5. Unmapped tools

None.

## 6. Raw fields removed during normalization

Everything outside the canonical schema is dropped. Keys seen in this input:

| raw key | seen for |
| --- | --- |
| record.attempt_id | LLM-A, LLM-B, LLM-C |
| record.completed_at | LLM-A, LLM-B, LLM-C |
| record.condition | LLM-A, LLM-B, LLM-C |
| record.execution_status | LLM-A, LLM-B, LLM-C |
| record.final_output_present | LLM-A, LLM-B, LLM-C |
| record.injection | LLM-A, LLM-B, LLM-C |
| record.injection_task_id | LLM-A, LLM-B, LLM-C |
| record.llm_calls | LLM-A, LLM-B, LLM-C |
| record.model_id | LLM-A, LLM-B, LLM-C |
| record.provider | LLM-A, LLM-B, LLM-C |
| record.repetition_id | LLM-A, LLM-B, LLM-C |
| record.reproducibility | LLM-A, LLM-B, LLM-C |
| record.runner_traceback | LLM-A, LLM-B, LLM-C |
| record.scenario_group_id | LLM-A, LLM-B, LLM-C |
| record.scenario_id | LLM-A, LLM-B, LLM-C |
| record.schema_version | LLM-A, LLM-B, LLM-C |
| record.source_llm | LLM-A, LLM-B, LLM-C |
| record.split | LLM-A, LLM-B, LLM-C |
| record.started_at | LLM-A, LLM-B, LLM-C |
| record.steps_used | LLM-A, LLM-B, LLM-C |
| record.suite | LLM-A, LLM-B, LLM-C |
| record.termination_reason | LLM-A, LLM-B, LLM-C |
| record.usage_total | LLM-A, LLM-B, LLM-C |
| record.user_task_id | LLM-A, LLM-B, LLM-C |

## 7. Feature matrix

| Item | Value |
| --- | --- |
| Rows | 54 |
| Features (features_extended.csv) | 69 |
| Core features (features.csv) | 57 |
| Features with missing values | 1 |
| Constant features | 17 |

| feature | missing rows |
| --- | --- |
| mean_agent_latency_s | 1 |

Constant in this input (no information; expected on small or mock data): `n_unmapped_tool_calls`, `n_destructive`, `n_act_update`, `n_act_delete`, `n_act_publish`, `n_act_share`, `n_act_admin`, `n_reads_after_first_write`, `trans_WR`, `trans_WE`, `trans_ER`, `trans_EW`, `trans_EE`, `n_destructive_after_freetext`, `n_calls_without_result`, `ended_with_final`, `n_steps_text_and_call`

