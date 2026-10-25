# Person 3 Quality Report

Input: `mock/raw_runs.mock.jsonl`

p3 version: 1.0.0  
data contract: data_contract_v0.2  
canonical schema: p3-canonical-0.3  
taxonomy: p3-taxonomy-0.2  
feature set: p3-features-1.0  
frozen schema sha256: 855628e7ea1c5cf380019c38fe04dcd5491945c03e2517cbb218ed4758923779  

## 1. Summary

| Item | Count |
| --- | --- |
| Lines read | 54 |
| Runs indexed | 54 |
| Structurally valid (features written) | 54 |
| Excluded from features | 0 |
| Issues: error / warning / info | 0 / 1 / 34 |

## 2. Runs by source LLM and execution status

| source_llm | completed | model_api_error | step_limit |
| --- | --- | --- | --- |
| A | 17 | 1 | 0 |
| B | 18 | 0 | 0 |
| C | 17 | 0 | 1 |

## 3. Issues

| severity | code | issues | runs | A | B | C |
| --- | --- | --- | --- | --- | --- | --- |
| warning | tool_call_without_result | 1 | 1 | 1 | 0 | 0 |
| info | exposure_marker_removed | 26 | 26 | 9 | 9 | 8 |
| info | no_final_message | 2 | 2 | 1 | 0 | 1 |
| info | non_completed_status | 2 | 2 | 1 | 0 | 1 |
| info | reasoning_removed | 4 | 4 | 0 | 0 | 4 |

## 4. Tool call / result pairing

| source_llm | tool calls | linked results | paired |
| --- | --- | --- | --- |
| A | 54 | 53 | 98.1% |
| B | 53 | 53 | 100.0% |
| C | 56 | 56 | 100.0% |

## 5. Unmapped tools

None.

## 6. Raw fields removed during normalization

Everything outside the canonical schema is dropped. Keys seen in this input:

| raw key | seen for |
| --- | --- |
| event.delivered_event_index | A, B, C |
| event.provider_meta | A, B, C |
| record.api_request_count | A, B, C |
| record.completed_at | A, B, C |
| record.condition | A, B, C |
| record.execution_status | A, B, C |
| record.injection | A, B, C |
| record.injection_task_id | A, B, C |
| record.is_mock | A, B, C |
| record.model_id | A, B, C |
| record.provider | A, B, C |
| record.repetition_id | A, B, C |
| record.reproducibility | A, B, C |
| record.scenario_group_id | A, B, C |
| record.scenario_id | A, B, C |
| record.schema_version | A, B, C |
| record.source_llm | A, B, C |
| record.split | A, B, C |
| record.started_at | A, B, C |
| record.suite | A, B, C |
| record.termination_reason | A, B, C |
| record.usage | A, B, C |
| record.user_task_id | A, B, C |

## 7. Feature matrix

| Item | Value |
| --- | --- |
| Rows | 54 |
| All features (features_extended.csv) | 84 |
| Primary features (features.csv) | 72 |
| Features with missing values | 1 |
| Constant features | 13 |

| feature | missing rows |
| --- | --- |
| mean_agent_latency_s | 1 |

Constant in this input (no information; expected on small or mock data): `n_unmapped_tool_calls`, `n_act_share`, `n_act_admin`, `n_tool_revisits`, `trans_WR`, `trans_WE`, `trans_EW`, `n_empty_results`, `n_unparseable_args`, `n_calls_missing_required`, `n_calls_extra_args`, `frac_arg_bool`, `frac_arg_empty`
