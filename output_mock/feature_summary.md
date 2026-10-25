# Primary feature summary

54 runs. Mean per source LLM (n in the header). No labels or conditions are used here.
Large differences between LLMs point to features that identify the source model.

Constant across all runs (left out below): `n_unmapped_tool_calls`, `n_act_share`, `n_act_admin`, `n_tool_revisits`, `trans_WR`, `trans_WE`, `trans_EW`, `n_empty_results`, `n_unparseable_args`, `n_calls_missing_required`, `n_calls_extra_args`, `frac_arg_bool`, `frac_arg_empty`

| feature | A (n=18) | B (n=18) | C (n=18) |
|---|---:|---:|---:|
| `n_tool_calls` | 3.00 | 2.94 | 3.11 |
| `n_unique_tools` | 2.28 | 2.22 | 2.06 |
| `trajectory_length` | 7.94 | 9.89 | 8.17 |
| `n_read` | 2.28 | 2.44 | 2.50 |
| `n_write` | 0.72 | 0.50 | 0.61 |
| `n_egress` | 0.50 | 0.33 | 0.22 |
| `n_destructive` | 0.00 | 0.00 | 0.06 |
| `frac_write` | 0.19 | 0.14 | 0.21 |
| `frac_egress` | 0.12 | 0.09 | 0.09 |
| `n_act_retrieve` | 1.06 | 1.06 | 1.61 |
| `n_act_list` | 0.83 | 1.00 | 0.56 |
| `n_act_search` | 0.39 | 0.39 | 0.33 |
| `n_act_create` | 0.11 | 0.06 | 0.11 |
| `n_act_update` | 0.00 | 0.06 | 0.00 |
| `n_act_delete` | 0.00 | 0.00 | 0.06 |
| `n_act_send_message` | 0.22 | 0.17 | 0.11 |
| `n_act_transfer_value` | 0.17 | 0.11 | 0.11 |
| `n_act_publish` | 0.11 | 0.00 | 0.00 |
| `n_act_reserve` | 0.11 | 0.11 | 0.22 |
| `n_domains` | 1.50 | 1.44 | 1.44 |
| `n_domain_switches` | 0.61 | 0.50 | 0.44 |
| `n_write_domains` | 0.61 | 0.50 | 0.50 |
| `n_writes_new_domain` | 0.39 | 0.17 | 0.33 |
| `action_entropy` | 0.66 | 0.57 | 0.59 |
| `has_write` | 0.50 | 0.50 | 0.50 |
| `first_write_pos` | 0.78 | 0.86 | 0.79 |
| `n_reads_after_first_write` | 0.28 | 0.00 | 0.00 |
| `n_write_bursts` | 0.61 | 0.50 | 0.50 |
| `max_read_streak` | 2.00 | 2.44 | 2.50 |
| `n_repeated_calls` | 0.22 | 0.39 | 0.67 |
| `max_same_tool_run` | 1.50 | 1.67 | 2.00 |
| `trans_RR` | 0.29 | 0.46 | 0.26 |
| `trans_RW` | 0.13 | 0.07 | 0.13 |
| `trans_RE` | 0.14 | 0.14 | 0.18 |
| `trans_WW` | 0.00 | 0.00 | 0.05 |
| `trans_ER` | 0.02 | 0.00 | 0.00 |
| `trans_EE` | 0.03 | 0.00 | 0.00 |
| `n_freetext_reads` | 1.22 | 1.00 | 1.67 |
| `n_writes_after_freetext` | 0.67 | 0.39 | 0.50 |
| `n_egress_after_freetext` | 0.44 | 0.22 | 0.17 |
| `n_destructive_after_freetext` | 0.00 | 0.00 | 0.06 |
| `frac_writes_after_freetext` | 0.44 | 0.39 | 0.39 |
| `n_calls_after_last_freetext` | 1.00 | 0.50 | 0.61 |
| `n_tool_errors` | 0.22 | 0.44 | 0.17 |
| `frac_tool_errors` | 0.07 | 0.11 | 0.04 |
| `n_retry_after_error` | 0.22 | 0.39 | 0.17 |
| `n_calls_without_result` | 0.06 | 0.00 | 0.00 |
| `mean_args_per_call` | 1.49 | 1.19 | 1.45 |
| `max_args_per_call` | 2.22 | 2.11 | 2.17 |
| `n_calls_without_args` | 0.28 | 0.56 | 0.22 |
| `frac_arg_str` | 0.78 | 0.80 | 0.79 |
| `frac_arg_number` | 0.13 | 0.11 | 0.13 |
| `frac_arg_collection` | 0.08 | 0.09 | 0.08 |
| `ended_with_final` | 0.94 | 1.00 | 0.94 |
| `n_steps` | 3.39 | 3.61 | 4.06 |
| `max_calls_per_step` | 1.33 | 1.28 | 1.00 |
| `mean_calls_per_step` | 1.11 | 1.08 | 1.00 |
| `n_agent_text_msgs` | 0.94 | 3.00 | 0.94 |
| `n_steps_text_and_call` | 0.06 | 2.00 | 0.00 |
