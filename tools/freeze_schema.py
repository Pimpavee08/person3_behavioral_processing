"""Write the frozen feature schema for the current FEATURE_SET_VERSION. Never overwrites.

    python tools/freeze_schema.py --date 2026-10-03
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from p3.features import feature_dictionary  # noqa: E402
from p3.schema import CODE_MODULES, FROZEN_PATH, code_sha256, schema_body, schema_sha256  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", required=True, help="freeze date, YYYY-MM-DD")
    args = parser.parse_args()
    if os.path.exists(FROZEN_PATH):
        print("already frozen: %s (bump FEATURE_SET_VERSION to change features)" % FROZEN_PATH)
        return 1
    body = schema_body()
    descriptions = {d["feature"]: d["description"] for d in feature_dictionary()}
    for row in body["primary_features"] + body["secondary_features"]:
        row["description"] = descriptions[row["feature"]]
    frozen = {
        "status": "frozen",
        "frozen_at": args.date,
        "frozen_by": "Person 3",
        "label_isolation": "Defined and frozen without P1 approved labels, eval_evidence, environment "
                           "snapshots, evaluator outputs or adjudication notes.",
        "change_policy": "Do not edit. Any change to features, taxonomy, signatures, structural keys or the "
                         "feature-computing code needs a new feature_set_version and a notice to the team.",
        "primary_input": "features.csv holds exactly primary_features, in this order, after trajectory_id.",
        "schema_sha256": schema_sha256(),
        "code_sha256": code_sha256(),
        "code_modules": ["p3/" + m for m in CODE_MODULES],
        **body,
    }
    os.makedirs(os.path.dirname(FROZEN_PATH), exist_ok=True)
    with open(FROZEN_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(frozen, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("frozen %s -> %s" % (body["feature_set_version"], FROZEN_PATH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
