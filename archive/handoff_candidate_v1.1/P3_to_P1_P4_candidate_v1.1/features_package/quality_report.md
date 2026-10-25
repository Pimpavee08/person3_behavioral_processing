# Person 3 Quality Report

Input: `../P2_P3_candidate_package/trajectories_sanitized.jsonl`

p3 version: 1.1.0  
data contract: data_contract_v0.2  
canonical schema: p3-canonical-0.4  
taxonomy: p3-taxonomy-0.3  
feature set: p3-features-1.1  
frozen schema sha256: 2f794f2d65dd3e63c8857a6d616e0a40fe0a39a29f7a7319e2fc5558c1c63ee5  

## 1. Summary

| Item | Count |
| --- | --- |
| Lines read | 1158 |
| Trajectories indexed | 1158 |
| Structurally valid (features written) | 1158 |
| Excluded from features | 0 |
| Issues: error / warning / info | 0 / 13 / 1136 |

## 2. Trajectories by suite and execution status

| suite | n/a |
| --- | --- |
| banking | 183 |
| slack | 252 |
| travel | 237 |
| workspace | 486 |

## 3. Issues

| severity | code | issues | trajectories | banking | slack | travel | workspace |
| --- | --- | --- | --- | --- | --- | --- | --- |
| warning | unmapped_tool | 13 | 8 | 0 | 0 | 13 | 0 |
| info | duplicate_final_merged | 1132 | 1132 | 180 | 251 | 232 | 469 |
| info | no_final_message | 4 | 4 | 0 | 1 | 0 | 3 |

## 4. Tool call / result pairing

| suite | tool calls | linked results | paired |
| --- | --- | --- | --- |
| banking | 427 | 427 | 100.0% |
| slack | 1359 | 1359 | 100.0% |
| travel | 1501 | 1501 | 100.0% |
| workspace | 1189 | 1189 | 100.0% |

## 5. Unmapped tools

Tool names outside the 69 AgentDojo v1 tools (e.g. names the model invented). They stay in the trajectory and are counted by `n_unmapped_tool_calls`.

| tool | calls |
| --- | --- |
| get_all_car_rental_companies | 8 |
| get_car_rental_companies_in_city | 1 |
| get_car_rental_price_per_day | 1 |
| get_hotel_address | 1 |
| get_hotel_prices | 1 |
| get_price_per_day | 1 |

## 6. Raw fields removed during normalization

Everything outside the canonical schema is dropped. Keys seen in this input:

| raw key | seen for |
| --- | --- |
| record.schema_version | banking, slack, travel, workspace |
| record.steps_used | banking, slack, travel, workspace |
| record.suite | banking, slack, travel, workspace |

## 7. Feature matrix

| Item | Value |
| --- | --- |
| Rows | 1158 |
| Primary features (features.csv) | 77 |
| Primary features with missing values | 0 |
| Constant primary features | 2 |
| Secondary features fully empty (no text/time in input) | 12 |

Constant in this input (no information here): `n_calls_without_result`, `n_unparseable_args`
