# Feature README (p3-features-1.1)

Key column: `trajectory_id`. Every other column of `features.csv` is one primary feature below, in this order.
All values are computed per trajectory by fixed rules; nothing is scaled, imputed or selected.
An empty cell means the value cannot be computed from that trajectory.

| # | feature | group | description |
| --- | --- | --- | --- |
| 1 | `n_tool_calls` | volume | Tool calls issued by the agent. |
| 2 | `n_tool_results` | volume | Tool results logged (including errors). |
| 3 | `n_unique_tools` | volume | Distinct tools called. |
| 4 | `n_unmapped_tool_calls` | volume | Calls to tools outside the taxonomy (e.g. hallucinated names). |
| 5 | `trajectory_length` | volume | Events in the structural trajectory: calls, results, agent messages, final answer, execution errors (runner markers, user message, system messages, reasoning and the duplicated final message removed). |
| 6 | `n_read` | action_mix | Read-effect tool calls. |
| 7 | `n_write` | action_mix | Write-effect (state-changing) tool calls. |
| 8 | `n_egress` | action_mix | Calls that send data/value to another party or grant access. |
| 9 | `n_destructive` | action_mix | Calls that delete or revoke. |
| 10 | `frac_write` | action_mix | n_write / n_tool_calls. |
| 11 | `frac_egress` | action_mix | n_egress / n_tool_calls. |
| 12 | `n_act_retrieve` | action_mix | Tool calls with canonical action 'retrieve'. |
| 13 | `n_act_list` | action_mix | Tool calls with canonical action 'list'. |
| 14 | `n_act_search` | action_mix | Tool calls with canonical action 'search'. |
| 15 | `n_act_create` | action_mix | Tool calls with canonical action 'create'. |
| 16 | `n_act_update` | action_mix | Tool calls with canonical action 'update'. |
| 17 | `n_act_delete` | action_mix | Tool calls with canonical action 'delete'. |
| 18 | `n_act_send_message` | action_mix | Tool calls with canonical action 'send_message'. |
| 19 | `n_act_transfer_value` | action_mix | Tool calls with canonical action 'transfer_value'. |
| 20 | `n_act_publish` | action_mix | Tool calls with canonical action 'publish'. |
| 21 | `n_act_reserve` | action_mix | Tool calls with canonical action 'reserve'. |
| 22 | `n_act_share` | action_mix | Tool calls with canonical action 'share'. |
| 23 | `n_act_admin` | action_mix | Tool calls with canonical action 'admin'. |
| 24 | `n_domains` | action_mix | Distinct resource domains touched. |
| 25 | `n_domain_switches` | action_mix | Consecutive calls whose domains differ. |
| 26 | `n_write_domains` | action_mix | Distinct domains touched by write calls. |
| 27 | `n_writes_new_domain` | action_mix | Write calls in a domain no earlier call touched. |
| 28 | `action_entropy` | action_mix | Shannon entropy (bits) of the canonical-action distribution. |
| 29 | `has_write` | sequence | 1 if any write call. |
| 30 | `first_write_pos` | sequence | Index of first write / n_tool_calls; 1.0 when there is no write. |
| 31 | `n_reads_after_first_write` | sequence | Read calls issued after the first write. |
| 32 | `n_write_bursts` | sequence | Maximal runs of consecutive write calls. |
| 33 | `max_read_streak` | sequence | Longest run of consecutive read calls. |
| 34 | `n_repeated_call_shapes` | sequence | Calls with the same tool and the same argument keys and types as an earlier call. |
| 35 | `n_tool_revisits` | sequence | Calls to a tool used earlier but not by the directly preceding call (loop back). |
| 36 | `max_same_tool_run` | sequence | Longest run of consecutive calls to the same tool. |
| 37 | `trans_RR` | sequence | Share of consecutive call pairs going R->R (R=read, W=internal write, E=egress write). |
| 38 | `trans_RW` | sequence | Share of consecutive call pairs going R->W (R=read, W=internal write, E=egress write). |
| 39 | `trans_RE` | sequence | Share of consecutive call pairs going R->E (R=read, W=internal write, E=egress write). |
| 40 | `trans_WR` | sequence | Share of consecutive call pairs going W->R (R=read, W=internal write, E=egress write). |
| 41 | `trans_WW` | sequence | Share of consecutive call pairs going W->W (R=read, W=internal write, E=egress write). |
| 42 | `trans_WE` | sequence | Share of consecutive call pairs going W->E (R=read, W=internal write, E=egress write). |
| 43 | `trans_ER` | sequence | Share of consecutive call pairs going E->R (R=read, W=internal write, E=egress write). |
| 44 | `trans_EW` | sequence | Share of consecutive call pairs going E->W (R=read, W=internal write, E=egress write). |
| 45 | `trans_EE` | sequence | Share of consecutive call pairs going E->E (R=read, W=internal write, E=egress write). |
| 46 | `n_freetext_reads` | exposure_structure | Reads returning third-party free text. |
| 47 | `n_writes_after_freetext` | exposure_structure | Writes in a later step than the first free-text read. |
| 48 | `n_egress_after_freetext` | exposure_structure | Egress calls in a later step than the first free-text read. |
| 49 | `n_destructive_after_freetext` | exposure_structure | Destructive calls in a later step than the first free-text read. |
| 50 | `frac_writes_after_freetext` | exposure_structure | n_writes_after_freetext / n_write. |
| 51 | `n_calls_after_last_freetext` | exposure_structure | Calls in a later step than the last free-text read. |
| 52 | `n_tool_errors` | errors | Tool results that are errors. |
| 53 | `frac_tool_errors` | errors | n_tool_errors / n_tool_calls. |
| 54 | `n_retry_after_error` | errors | Calls to the same tool directly after its errored call. |
| 55 | `n_calls_without_result` | errors | Calls with no logged result. |
| 56 | `n_error_valueerror` | errors | Tool results with error class ValueError. |
| 57 | `n_error_validationerror` | errors | Tool results with error class ValidationError. |
| 58 | `n_error_keyerror` | errors | Tool results with error class KeyError. |
| 59 | `n_error_other` | errors | Tool results with any other or unspecified error class. |
| 60 | `mean_args_per_call` | arguments | Mean number of arguments per parsed call. |
| 61 | `max_args_per_call` | arguments | Most arguments in one call. |
| 62 | `n_calls_without_args` | arguments | Calls with zero arguments. |
| 63 | `n_unparseable_args` | arguments | Calls whose arguments could not be parsed (malformed call). |
| 64 | `n_calls_missing_required` | arguments | Calls missing a required argument of the tool signature. |
| 65 | `n_calls_extra_args` | arguments | Calls with an argument the tool signature does not define. |
| 66 | `frac_arg_str` | arguments | Share of argument values that are strings. |
| 67 | `frac_arg_number` | arguments | Share of argument values that are numbers. |
| 68 | `frac_arg_bool` | arguments | Share of argument values that are booleans. |
| 69 | `frac_arg_collection` | arguments | Share of argument values that are non-empty lists or objects. |
| 70 | `frac_arg_empty` | arguments | Share of argument values that are null, empty lists or empty objects. |
| 71 | `ended_with_final` | termination | 1 if the trajectory ends with a final agent answer event. |
| 72 | `final_output_present` | termination | Runner flag: 1 if a non-empty final output exists, 0 if not; empty when the log lacks the flag. |
| 73 | `n_steps` | shape | Model turns (consecutive agent events count as one). |
| 74 | `max_calls_per_step` | shape | Most tool calls issued in one turn. |
| 75 | `mean_calls_per_step` | shape | Mean tool calls per turn that has calls. |
| 76 | `n_agent_messages` | shape | Agent messages other than the final answer (e.g. a message beside tool calls). |
| 77 | `n_steps_message_and_call` | shape | Turns containing both an agent message and a tool call. |

## Secondary features (`features_extended.csv`, not primary input)

| feature | caution | description |
| --- | --- | --- |
| `total_result_chars` | text_derived | Characters returned by all tool results. |
| `mean_result_chars` | text_derived | Mean characters per tool result. |
| `n_write_arg_atoms` | text_derived | String argument values (>=4 chars) of write calls. |
| `frac_write_args_from_user` | text_derived | Share of those values that appear in the user prompt. |
| `frac_write_args_from_tool` | text_derived | Share that appear only in an earlier tool result. |
| `frac_write_args_from_freetext` | text_derived | Share that appear only in an earlier free-text tool result. |
| `frac_write_args_novel` | text_derived | Share that appear in neither (composed by the agent). |
| `n_egress_calls_freetext_args` | text_derived | Egress calls with an argument value traceable only to a free-text tool result. |
| `final_text_len` | text_derived | Characters in the final answer. |
| `mean_agent_text_len` | text_derived | Mean characters per agent text message. |
| `duration_s` | timing | Seconds from first to last timestamped event. |
| `mean_agent_latency_s` | timing | Mean seconds between an agent event and the event before it. |
