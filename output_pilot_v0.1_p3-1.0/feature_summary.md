# Primary feature summary

54 runs. Mean per source LLM (n in the header). No labels or conditions are used here.
Large differences between LLMs point to features that identify the source model.

Constant across all runs (left out below): `n_unmapped_tool_calls`, `n_destructive`, `n_act_update`, `n_act_delete`, `n_act_publish`, `n_act_share`, `n_act_admin`, `n_reads_after_first_write`, `trans_WR`, `trans_WE`, `trans_ER`, `trans_EW`, `trans_EE`, `n_destructive_after_freetext`, `n_calls_without_result`, `n_empty_results`, `n_unparseable_args`, `n_calls_missing_required`, `n_calls_extra_args`, `frac_arg_bool`, `ended_with_final`, `n_steps_text_and_call`

| feature | LLM-A (n=18) | LLM-B (n=18) | LLM-C (n=18) |
|---|---:|---:|---:|
| `n_tool_calls` | 2.28 | 2.28 | 2.17 |
| `n_unique_tools` | 2.00 | 1.94 | 1.89 |
| `trajectory_length` | 6.56 | 6.56 | 6.33 |
| `n_read` | 1.94 | 1.83 | 1.67 |
| `n_write` | 0.33 | 0.44 | 0.50 |
| `n_egress` | 0.17 | 0.17 | 0.33 |
| `frac_write` | 0.08 | 0.16 | 0.19 |
| `frac_egress` | 0.03 | 0.07 | 0.12 |
| `n_act_retrieve` | 0.83 | 0.89 | 0.72 |
| `n_act_list` | 0.78 | 0.72 | 0.61 |
| `n_act_search` | 0.33 | 0.22 | 0.33 |
| `n_act_create` | 0.11 | 0.11 | 0.11 |
| `n_act_send_message` | 0.11 | 0.11 | 0.17 |
| `n_act_transfer_value` | 0.06 | 0.06 | 0.11 |
| `n_act_reserve` | 0.06 | 0.17 | 0.11 |
| `n_domains` | 1.28 | 1.33 | 1.28 |
| `n_domain_switches` | 0.39 | 0.39 | 0.33 |
| `n_write_domains` | 0.33 | 0.44 | 0.50 |
| `n_writes_new_domain` | 0.11 | 0.22 | 0.28 |
| `action_entropy` | 0.42 | 0.44 | 0.52 |
| `has_write` | 0.33 | 0.39 | 0.50 |
| `first_write_pos` | 0.92 | 0.84 | 0.81 |
| `n_write_bursts` | 0.33 | 0.39 | 0.50 |
| `max_read_streak` | 1.94 | 1.83 | 1.67 |
| `n_repeated_calls` | 0.00 | 0.00 | 0.06 |
| `n_tool_revisits` | 0.00 | 0.06 | 0.11 |
| `max_same_tool_run` | 1.28 | 1.28 | 1.11 |
| `trans_RR` | 0.27 | 0.33 | 0.27 |
| `trans_RW` | 0.08 | 0.14 | 0.12 |
| `trans_RE` | 0.04 | 0.13 | 0.21 |
| `trans_WW` | 0.00 | 0.01 | 0.00 |
| `n_freetext_reads` | 0.94 | 1.00 | 0.89 |
| `n_writes_after_freetext` | 0.22 | 0.39 | 0.39 |
| `n_egress_after_freetext` | 0.06 | 0.11 | 0.22 |
| `frac_writes_after_freetext` | 0.22 | 0.33 | 0.39 |
| `n_calls_after_last_freetext` | 0.39 | 0.44 | 0.50 |
| `n_tool_errors` | 0.00 | 0.06 | 0.06 |
| `frac_tool_errors` | 0.00 | 0.01 | 0.03 |
| `n_retry_after_error` | 0.00 | 0.00 | 0.06 |
| `mean_args_per_call` | 1.13 | 1.25 | 1.39 |
| `max_args_per_call` | 1.78 | 1.94 | 2.28 |
| `n_calls_without_args` | 0.28 | 0.22 | 0.22 |
| `frac_arg_str` | 0.76 | 0.82 | 0.80 |
| `frac_arg_number` | 0.13 | 0.12 | 0.08 |
| `frac_arg_collection` | 0.11 | 0.06 | 0.06 |
| `frac_arg_empty` | 0.00 | 0.00 | 0.01 |
| `n_steps` | 3.28 | 3.11 | 3.17 |
| `max_calls_per_step` | 1.00 | 1.17 | 0.94 |
| `mean_calls_per_step` | 1.00 | 1.08 | 0.94 |
| `n_agent_text_msgs` | 1.00 | 0.94 | 1.00 |
