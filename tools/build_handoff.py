"""Assemble the folders and zips P3 sends to the team.

    python tools/build_handoff.py            # candidate set (feature schema 1.2)
    python tools/build_handoff.py pilot      # pilot v0.1 (feature schema 1.0), rebuild only

Creates, next to this project folder:
    candidate: P3_to_P1_P4_candidate_v1.2/ + .zip   features package, code, notes for P1 and P4
    pilot:     P3_to_P4/ + .zip, P3_to_P1/ + .zip    pilot features package, notes, mock data

A folder is built aside and swapped in only when complete. An existing folder is
replaced only if every file in it is listed in its checksums.sha256, so files
added by hand are never deleted. Every folder gets its own checksums.sha256.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from p3.fsutil import (CHECKSUMS, all_files, check_replaceable, publish_dir, sha256,  # noqa: E402
                       staging_dir, write_checksums)
from p3.schema import FROZEN_PATH, code_sha256, schema_sha256  # noqa: E402

DEST = os.path.dirname(ROOT)
MARKER = "00_READ_ME_FIRST.md"
CANDIDATE_PACKAGE = os.path.join(ROOT, "output_candidate_p3-1.2")
CANDIDATE_NAME = "P3_to_P1_P4_candidate_v1.2"
PILOT_PACKAGE = os.path.join(ROOT, "output_pilot_v0.1_p3-1.0")
PILOT_SCHEMA = os.path.join(ROOT, "schema", "feature_schema_p3-features-1.0.json")
MOCK_FILES = {
    "features.csv": os.path.join(ROOT, "output_mock", "features.csv"),
    "run_index.csv": os.path.join(ROOT, "output_mock", "run_index.csv"),
    "adjudicated_labels.mock.jsonl": os.path.join(ROOT, "mock", "adjudicated_labels.mock.jsonl"),
}
CODE_FILES = ["tools/make_mock_logs.py", "tools/freeze_schema.py", "tests/test_p3.py"]


def verify_package(package: str, schema_hash: str, code_hash: str = None, need_pass: bool = False) -> None:
    with open(os.path.join(package, CHECKSUMS), encoding="utf-8") as fh:
        listed = {}
        for line in fh:
            digest, name = line.rstrip("\n").split("  ", 1)
            listed[name] = digest
    for name in all_files(package):
        if name != CHECKSUMS and name not in listed:
            raise SystemExit("%s: %s is not in the package checksums" % (package, name))
    for name, digest in listed.items():
        if sha256(os.path.join(package, name)) != digest:
            raise SystemExit("%s: checksum mismatch for %s" % (package, name))
    with open(os.path.join(package, "feature_schema.json"), encoding="utf-8") as fh:
        frozen = json.load(fh)
    if frozen["schema_sha256"] != schema_hash or (code_hash and frozen.get("code_sha256") != code_hash):
        raise SystemExit("%s was built with a different feature schema or code; rebuild it first" % package)
    if need_pass:
        with open(os.path.join(package, "id_validation.json"), encoding="utf-8") as fh:
            if not json.load(fh).get("PASS"):
                raise SystemExit("%s: id_validation.json is not PASS; not shipping it" % package)


def build(name: str, readme: str, package: str, extra_docs=(), with_mock=False, with_code=False) -> str:
    final = os.path.join(DEST, name)
    check_replaceable(final)
    stage = staging_dir(final)
    try:
        shutil.copyfile(os.path.join(ROOT, "handoff", readme), os.path.join(stage, MARKER))
        for doc in extra_docs:
            shutil.copyfile(os.path.join(ROOT, doc), os.path.join(stage, os.path.basename(doc)))
        shutil.copytree(package, os.path.join(stage, "features_package"))
        if with_mock:
            os.makedirs(os.path.join(stage, "mock_for_pipeline_dev"))
            for target, source in MOCK_FILES.items():
                shutil.copyfile(source, os.path.join(stage, "mock_for_pipeline_dev", target))
        if with_code:
            code = os.path.join(stage, "code")
            shutil.copytree(os.path.join(ROOT, "p3"), os.path.join(code, "p3"),
                            ignore=shutil.ignore_patterns("__pycache__"))
            for rel in CODE_FILES + [os.path.relpath(FROZEN_PATH, ROOT)]:
                os.makedirs(os.path.join(code, os.path.dirname(rel)), exist_ok=True)
                shutil.copyfile(os.path.join(ROOT, rel), os.path.join(code, rel))
            shutil.copyfile(os.path.join(ROOT, "handoff", "README_CODE.md"), os.path.join(code, "README_CODE.md"))
        write_checksums(stage)
        zip_tmp = final + ".zip.tmp-%d" % os.getpid()
        with zipfile.ZipFile(zip_tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel in all_files(stage):
                zf.write(os.path.join(stage, rel), name + "/" + rel)
        publish_dir(stage, final)        # folder first: if it is locked, nothing has changed yet
        os.replace(zip_tmp, final + ".zip")
    finally:
        if os.path.exists(stage):
            shutil.rmtree(stage, ignore_errors=True)
        if os.path.exists(final + ".zip.tmp-%d" % os.getpid()):
            os.remove(final + ".zip.tmp-%d" % os.getpid())
    return final + ".zip"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("which", nargs="?", default="candidate", choices=["candidate", "pilot"])
    args = parser.parse_args()
    if args.which == "candidate":
        verify_package(CANDIDATE_PACKAGE, schema_sha256(), code_sha256(), need_pass=True)
        archives = [build(CANDIDATE_NAME, "CANDIDATE_READ_ME_FIRST.md", CANDIDATE_PACKAGE, with_code=True)]
    else:
        with open(PILOT_SCHEMA, encoding="utf-8") as fh:
            verify_package(PILOT_PACKAGE, json.load(fh)["schema_sha256"])
        archives = [build("P3_to_P4", "P4_READ_ME_FIRST.md", PILOT_PACKAGE, ["HANDOFF_P4.md"], with_mock=True),
                    build("P3_to_P1", "P1_READ_ME_FIRST.md", PILOT_PACKAGE, ["PILOT_REPORT_P3.md"])]
    for archive in archives:
        print("%s (%d KB)" % (archive, os.path.getsize(archive) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
