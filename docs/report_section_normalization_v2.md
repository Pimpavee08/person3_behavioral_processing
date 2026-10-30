# Report text: Trajectory Processing and Normalization (Person 3) - v2 (with Algorithm 1)

Suggested place: after Section III-F (or as a new subsection "III-F.1 Implementation"), and before III-G.
All numbers below come from the actual runs.
New in v2: Algorithm 1 (end of F.1). It is already written in LaTeX and needs
`\usepackage{algorithm}` and `\usepackage{algpseudocode}` in the preamble.

---

## F.1 Implementation of Trajectory Processing and Normalization

We implemented the processing and normalization stage as a small Python package (`p3`) that uses only the Python standard library. It takes the raw trajectory file produced by the execution environment and outputs (1) one normalized trajectory per run and (2) one feature vector per run. The same code and the same rules are applied to every run, no matter which LLM produced it. The code never reads the labels (benign/IPI), the attack goal, the attack payload, or the identity of the source model.

Algorithm 1 summarizes the whole procedure (in LaTeX: `Algorithm~\ref{alg:p3_normalization}`).

**Input data.** The execution team gave us 1,158 trajectories from the three source LLMs on AgentDojo v1 (workspace 486, slack 252, travel 237, banking 183). Before giving us the file, they had already removed the assistant text, the tool-result text, the timestamps, all label and model information, and the runner's injection markers, and had replaced every run id with a random `trajectory_id`. Tool arguments kept only their key names; each value was replaced by its type, for example `STR`, `INT` or `LIST[2]:STR`. We first built and tested the pipeline on a 54-run pilot (9 scenarios × benign/IPI × 3 LLMs) in the raw format, and then on the 1,158 blinded trajectories. The pipeline accepts both formats and turns them into the same normalized form.

**Step 1: Log parsing.** Each trajectory is a list of events (`tool_call`, `tool_result`, `agent_message`, `agent_final`). We sort the events by their event index so the original order is kept. Events created by the runner (actor = runner, such as `injected_content_delivered`) are removed before anything is counted. If kept, these markers would tell the detector directly which runs were attacked.

**Step 2: Cleaning the event sequence.**
- *Steps.* We count steps again ourselves as "model turns": a new step starts each time the model speaks after a tool result. We do not use the step numbers written by the runner, so all models are counted in the same way. Several tool calls sent in one turn (parallel calls) belong to the same step.
- *Call–result linking.* Each tool result is linked to the tool call it answers using the call id. The ids are then renamed to `c0`, `c1`, … so no provider-specific id format is left. All 4,476 tool calls were linked to a result.
- *Duplicated final answer.* The runner logs the final answer twice, once as `agent_message` and once as `agent_final`, in the same step. We keep only one copy, which removed 1,132 duplicates. Without this, every run would look like it had one extra message.

**Step 3: Action and tool-name mapping.** AgentDojo v1 has 69 different tools. Using raw tool names would let the detector memorize tasks or suites instead of learning behavior. We therefore built a mapping table that describes every tool with a few common attributes (Table I). The table was written only from what each tool does, without looking at which tools the attacks use.

TABLE I
CANONICAL TOOL ATTRIBUTES

| Attribute | Values | Example |
| --- | --- | --- |
| action | retrieve, list, search, create, update, delete, send_message, transfer_value, publish, reserve, share, admin | `send_money` → transfer_value |
| effect | read, write | `get_webpage` → read |
| domain | finance, messaging, email, calendar, file, web, travel, account, contact, system | `search_emails` → email |
| source of read data | own data, third-party structured data, third-party free text | `read_file` → third-party free text |
| egress | sends data or money to another party | `send_email`, `post_webpage` |
| destructive | deletes or removes something | `delete_file` |

If a model calls a tool name that does not exist, we keep the call because it is real behavior. It gets a rough category from its verb (`get_` → read, `send_` → write) and is marked as unmapped. In our data there were 13 such calls (for example `get_all_car_rental_companies`).

**Step 4: Argument abstraction.** We never keep argument values, because the pilot showed that injected text can end up inside tool arguments. Each argument is reduced to its key and its type. We also compare the argument keys with the real tool signature taken from the AgentDojo source code (commit `a75aba76`). This tells us whether a call is missing a required argument or adds an unknown one. A call that has the same tool and the same argument keys and types as an earlier call is marked as a repeat.

**Step 5: Metadata removal.** The normalized trajectory is built from a whitelist of fields, so anything not on the list is dropped. Dropped items include model name, provider, run id, call ids, token usage, timestamps, message text, tool-result text and the user prompt. Each normalized event keeps only structural information: position, step, event type, the canonical tool attributes, error flag and error type, argument count and types, and the missing/extra argument counts.

**Step 6: Validation and quality checks.** Every input record is checked before use. A broken record (bad JSON, bad id, wrong data types) is written to an issue list and skipped, and the rest of the batch continues. For the 1,158 trajectories:
- 0 errors
- all 1,158 `trajectory_id`s were unique, with no missing or duplicated ids
- the counts of tool calls (4,476), final answers (1,154) and error types (ValueError 187, ValidationError 13, KeyError 2, unspecified 13) matched the execution team's own validation report exactly

Four trajectories have no final answer because they reached the 15-step limit. They are valid and are kept.

**Algorithm 1** (paste as-is into LaTeX):

```latex
\begin{algorithm}[t]
\caption{Trajectory normalization and structural feature extraction}
\label{alg:p3_normalization}
\begin{algorithmic}[1]
\Require trajectory file $\mathcal{T}$; tool map $\varphi$ (69 tools); tool signatures $\Sigma$; frozen schema $\Phi$
\Ensure normalized trajectories $\mathcal{N}$; feature table $F$
\State stop if the feature code differs from $\Phi$; $\mathcal{N} \gets \emptyset$; $F \gets \emptyset$
\ForAll{records $r \in \mathcal{T}$}
    \State \textbf{if} $r$ is unreadable or its ID is invalid or repeated \textbf{then} log an issue; \textbf{continue}
    \State $E \gets$ events of $r$ in index order, without runner, system and reasoning events
    \State link results to calls; rename call IDs to $c_0, c_1, \dots$; merge a duplicated final answer; recount steps
    \ForAll{tool calls $e \in E$}
        \State $e \gets \bigl(\varphi(e.\mathit{tool}),$ argument types, missing/extra keys vs.\ $\Sigma\bigr)$ \Comment{unknown tool: verb prefix}
    \EndFor
    \State keep whitelisted structural fields only; $\mathcal{N} \gets \mathcal{N} \cup \{E\}$
    \State \textbf{if} no error for $r$ \textbf{then} $F \gets F \cup \{(r.\mathit{id}, \textsc{Features}(E))\}$ \Comment{77 features}
\EndFor
\State \textbf{assert} every \texttt{trajectory\_id} is unique and has one feature row
\State \Return $\mathcal{N}, F$
\end{algorithmic}
\end{algorithm}
```

## G.1 Implemented Behavioral Features

From each normalized trajectory we compute 77 structural features (Table II). All features are counts or ratios computed from one trajectory at a time, and nothing is fitted on the whole dataset. Scaling and feature selection are left to the detector stage, where they are fitted on training data only.

TABLE II
STRUCTURAL FEATURE GROUPS (77 FEATURES)

| Group | # | Examples |
| --- | --- | --- |
| Volume | 5 | trajectory length, number of tool calls, tool results, unique tools, unmapped tools |
| Action mix | 23 | number of reads, writes, egress and destructive calls, count per canonical action, number of domains, action entropy |
| Sequence | 17 | position of the first write, repeated calls, revisits of an earlier tool, longest run of the same tool, read/write/egress transitions (9) |
| After third-party text | 6 | writes or egress calls made after the agent read third-party free text (e.g. an email or web page) |
| Errors | 8 | number and ratio of tool errors, retries after an error, error types |
| Arguments | 11 | arguments per call, calls with missing or extra arguments, share of string/number/list arguments |
| Termination | 2 | ended with a final answer, final output present |
| Shape | 5 | number of steps, calls per step, agent messages beside tool calls |

The "after third-party text" group is our structural version of *external-instruction following* (Section III-G). It does not read any text. It only checks whether the agent changed something or sent data out after it had read content written by someone else.

## Leakage control and reproducibility

- **No label information in the features.** No feature uses the label, the attack goal, the payload, the scenario id or the model name. The feature table has only `trajectory_id` as its key. Suite information is stored in a separate file as metadata and is never used as a feature.
- **Tests against leakage.** One test rewrites every string in a run and checks that no feature changes. Another test checks that a raw run and its blinded copy give exactly the same features.
- **Frozen feature set.** We froze the feature set (version `p3-features-1.2`) before any labels were given to the detector team. The frozen file stores a hash of the feature definitions and a hash of the code that computes them, and the pipeline refuses to run if either one changes. This prevents the features from being adjusted after the detector results are seen.
- **Same output when run again.** Running the shipped code again gives a byte-identical feature file. Processing all 1,158 trajectories takes about one second on a normal laptop.

## Limitations of this stage

- **Strings are only typed.** All strings arrive as the type `STR`, so we cannot tell an empty string from a non-empty one.
- **Repeats ignore values.** A repeated call is detected by tool name and argument types, not by argument values.
- **Third-party text is defined per tool.** The "third-party free text" label comes from what each tool does. An injection placed in a structured field, such as a Slack channel name, is therefore not counted as free text.
- **Normalization does not remove model differences.** As stated in Section III-F, models can still behave differently after normalization. Some features, such as calls per step, may still reveal the source model. This is measured in the cross-model evaluation.
