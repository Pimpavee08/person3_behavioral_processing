# P3 code (p3 1.1.0)

Normalization and structural feature extraction. Python 3.9+, standard library only.

| Path | Purpose |
| --- | --- |
| `p3/parsers.py` | Parse raw, blinded or chat-message trajectories |
| `p3/descriptors.py` | Argument type descriptors (STR, INT, LIST[n]:T, …) |
| `p3/tool_taxonomy.py`, `p3/tool_signatures.py` | Normalized tool categories; tool signatures at AgentDojo `a75aba76` |
| `p3/normalize.py` | Canonical trajectory and leakage-safe structural view |
| `p3/features.py` | Feature definitions (primary and secondary) |
| `p3/leakage.py`, `p3/quality.py`, `p3/schema.py`, `p3/pipeline.py` | Leakage guards, validation and reports, frozen-schema check, end-to-end run |
| `schema/feature_schema_p3-features-1.1.json` | Frozen schema; the pipeline refuses to run if the code differs |
| `tests/test_p3.py` | Unit tests. Tests that need the team's data folders skip themselves when the folders are absent |
| `tools/make_mock_logs.py`, `tools/freeze_schema.py` | Synthetic logs for development; schema freezing |

Reproduce the candidate package (from this `code/` folder):

```bash
python -m p3 --raw path/to/trajectories_sanitized.jsonl --out out_dir --expected 1158
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```

The tests that need the team's data folders skip themselves when run from this folder.
