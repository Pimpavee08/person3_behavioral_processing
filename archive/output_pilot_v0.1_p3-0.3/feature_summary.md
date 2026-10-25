# Core feature summary

54 runs. Mean per source LLM and condition (n per cell in the header).
Descriptive only: with a handful of runs per cell these differences are not evidence of an effect.

Constant across all runs (left out below): `n_unmapped_tool_calls`, `n_destructive`, `n_act_update`, `n_act_delete`, `n_act_publish`, `n_act_share`, `n_act_admin`, `n_reads_after_first_write`, `trans_WR`, `trans_WE`, `trans_ER`, `trans_EW`, `trans_EE`, `n_destructive_after_freetext`, `n_calls_without_result`, `n_empty_results`, `n_unparseable_args`, `frac_arg_bool`, `ended_with_final`, `n_steps_text_and_call`

| feature | LLM-A benign (n=9) | LLM-A ipi (n=9) | LLM-B benign (n=9) | LLM-B ipi (n=9) | LLM-C benign (n=9) | LLM-C ipi (n=9) |
|---|---:|---:|---:|---:|---:|---:|
| `n_tool_calls` | 2.56 | 2.00 | 2.11 | 2.44 | 2.44 | 1.89 |
| `n_unique_tools` | 2.22 | 1.78 | 2.00 | 1.89 | 2.00 | 1.78 |
| `n_read` | 2.11 | 1.78 | 1.56 | 2.11 | 2.00 | 1.33 |
| `n_write` | 0.44 | 0.22 | 0.56 | 0.33 | 0.44 | 0.56 |
| `n_egress` | 0.22 | 0.11 | 0.22 | 0.11 | 0.22 | 0.44 |
| `frac_write` | 0.12 | 0.04 | 0.18 | 0.13 | 0.15 | 0.22 |
| `frac_egress` | 0.04 | 0.02 | 0.08 | 0.06 | 0.07 | 0.17 |
| `n_act_retrieve` | 0.89 | 0.78 | 0.78 | 1.00 | 0.89 | 0.56 |
| `n_act_list` | 0.89 | 0.67 | 0.56 | 0.89 | 0.78 | 0.44 |
| `n_act_search` | 0.33 | 0.33 | 0.22 | 0.22 | 0.33 | 0.33 |
| `n_act_create` | 0.11 | 0.11 | 0.11 | 0.11 | 0.11 | 0.11 |
| `n_act_send_message` | 0.11 | 0.11 | 0.11 | 0.11 | 0.11 | 0.22 |
| `n_act_transfer_value` | 0.11 | 0.00 | 0.11 | 0.00 | 0.11 | 0.11 |
| `n_act_reserve` | 0.11 | 0.00 | 0.22 | 0.11 | 0.11 | 0.11 |
| `n_domains` | 1.33 | 1.22 | 1.33 | 1.33 | 1.33 | 1.22 |
| `n_domain_switches` | 0.56 | 0.22 | 0.44 | 0.33 | 0.33 | 0.33 |
| `n_write_domains` | 0.44 | 0.22 | 0.56 | 0.33 | 0.44 | 0.56 |
| `n_writes_new_domain` | 0.11 | 0.11 | 0.22 | 0.22 | 0.22 | 0.33 |
| `action_entropy` | 0.49 | 0.34 | 0.53 | 0.36 | 0.45 | 0.59 |
| `has_write` | 0.44 | 0.22 | 0.44 | 0.33 | 0.44 | 0.56 |
| `first_write_pos` | 0.88 | 0.96 | 0.82 | 0.87 | 0.85 | 0.78 |
| `n_write_bursts` | 0.44 | 0.22 | 0.44 | 0.33 | 0.44 | 0.56 |
| `max_read_streak` | 2.11 | 1.78 | 1.56 | 2.11 | 2.00 | 1.33 |
| `n_repeated_calls` | 0.00 | 0.00 | 0.00 | 0.00 | 0.11 | 0.00 |
| `trans_RR` | 0.26 | 0.28 | 0.24 | 0.42 | 0.39 | 0.15 |
| `trans_RW` | 0.14 | 0.03 | 0.14 | 0.13 | 0.14 | 0.11 |
| `trans_RE` | 0.05 | 0.03 | 0.15 | 0.11 | 0.13 | 0.30 |
| `trans_WW` | 0.00 | 0.00 | 0.03 | 0.00 | 0.00 | 0.00 |
| `n_freetext_reads` | 1.00 | 0.89 | 0.89 | 1.11 | 1.00 | 0.78 |
| `n_writes_after_freetext` | 0.33 | 0.11 | 0.44 | 0.33 | 0.33 | 0.44 |
| `n_egress_after_freetext` | 0.11 | 0.00 | 0.11 | 0.11 | 0.11 | 0.33 |
| `frac_writes_after_freetext` | 0.33 | 0.11 | 0.33 | 0.33 | 0.33 | 0.44 |
| `n_calls_after_last_freetext` | 0.56 | 0.22 | 0.56 | 0.33 | 0.44 | 0.56 |
| `n_tool_errors` | 0.00 | 0.00 | 0.00 | 0.11 | 0.11 | 0.00 |
| `frac_tool_errors` | 0.00 | 0.00 | 0.00 | 0.02 | 0.06 | 0.00 |
| `n_retry_after_error` | 0.00 | 0.00 | 0.00 | 0.00 | 0.11 | 0.00 |
| `mean_args_per_call` | 1.20 | 1.07 | 1.33 | 1.16 | 1.31 | 1.47 |
| `max_args_per_call` | 2.00 | 1.56 | 2.11 | 1.78 | 2.22 | 2.33 |
| `n_calls_without_args` | 0.33 | 0.22 | 0.22 | 0.22 | 0.33 | 0.11 |
| `frac_arg_str` | 0.78 | 0.74 | 0.82 | 0.82 | 0.79 | 0.80 |
| `frac_arg_number` | 0.15 | 0.11 | 0.13 | 0.11 | 0.13 | 0.02 |
| `frac_arg_collection` | 0.07 | 0.15 | 0.05 | 0.07 | 0.06 | 0.06 |
| `frac_arg_empty` | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.00 |
| `n_steps` | 3.56 | 3.00 | 3.11 | 3.11 | 3.44 | 2.89 |
| `max_calls_per_step` | 1.00 | 1.00 | 1.00 | 1.33 | 1.00 | 0.89 |
| `mean_calls_per_step` | 1.00 | 1.00 | 1.00 | 1.17 | 1.00 | 0.89 |
| `n_agent_text_msgs` | 1.00 | 1.00 | 1.00 | 0.89 | 1.00 | 1.00 |
