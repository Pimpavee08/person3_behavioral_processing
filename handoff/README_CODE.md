# P3 code (p3 1.2.1)

Normalization and structural feature extraction. Standard library only. Tested on Python 3.12 and 3.14; the sources use Python 3.9 syntax.

| Path | Purpose |
| --- | --- |
| `p3/parsers.py` | Parse raw, blinded or chat-message trajectories |
| `p3/descriptors.py` | Argument type descriptors (STR, INT, LIST[n]:T, …) |
| `p3/tool_taxonomy.py`, `p3/tool_signatures.py` | Normalized tool categories; tool signatures at AgentDojo `a75aba76` |
| `p3/normalize.py` | Canonical trajectory and leakage-safe structural view |
| `p3/features.py` | Feature definitions (primary and secondary) |
| `p3/schema.py` | Frozen-schema check: definitions hash and feature-code hash |
| `p3/pipeline.py` | End-to-end run: read → accept ids → process each record → write the package |
| `p3/validation.py`, `p3/reports.py`, `p3/common.py` | Input validation; quality report and feature summary; shared helpers |
| `p3/leakage.py`, `p3/fsutil.py` | Leakage guards; safe output folders |
| `schema/feature_schema_p3-features-1.2.json` | Frozen schema; the pipeline refuses to run if definitions or feature code differ |
| `tests/test_p3.py` | 49 unit tests. Tests that need the team's data folders skip themselves when the folders are absent |
| `tools/make_mock_logs.py`, `tools/freeze_schema.py` | Synthetic logs for development; schema freezing |

Reproduce the candidate package (from this `code/` folder). The output folder must be new, empty, or an earlier output of this tool:

```bash
python -m p3 --raw path/to/trajectories_sanitized.jsonl --out out_dir --expected 1158
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```
