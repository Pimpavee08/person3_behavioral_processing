"""Assemble the folders and zips P3 sends to the team.

    python tools/build_handoff.py            # candidate set (feature schema 1.1)
    python tools/build_handoff.py pilot      # pilot v0.1 (feature schema 1.0), rebuild only

Creates, next to this project folder:
    candidate: P3_to_P1_P4_candidate_v1.1/ + .zip   features package, code, notes for P1 and P4
    pilot:     P3_to_P4/ + .zip, P3_to_P1/ + .zip    pilot features package, notes, mock data

Every folder gets its own checksums.sha256 that lists only files inside it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from p3.schema import FROZEN_PATH, schema_sha256  # noqa: E402

DEST = os.path.dirname(ROOT)
MARKER = "00_READ_ME_FIRST.md"
CANDIDATE_PACKAGE = os.path.join(ROOT, "output_candidate_p3-1.1")
PILOT_PACKAGE = os.path.join(ROOT, "output_pilot_v0.1_p3-1.0")
PILOT_SCHEMA = os.path.join(ROOT, "schema", "feature_schema_p3-features-1.0.json")
MOCK_FILES = {
    "features.csv": os.path.join(ROOT, "output_mock", "features.csv"),
    "run_index.csv": os.path.join(ROOT, "output_mock", "run_index.csv"),
    "adjudicated_labels.mock.jsonl": os.path.join(ROOT, "mock", "adjudicated_labels.mock.jsonl"),
}
CODE_FILES = ["tools/make_mock_logs.py", "tools/freeze_schema.py", "tests/test_p3.py"]


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_package(package: str, schema_hash: str) -> None:
    with open(os.path.join(package, "checksums.sha256"), encoding="utf-8") as fh:
        for line in fh:
            digest, name = line.rstrip("\n").split("  ", 1)
            if sha256(os.path.join(package, name)) != digest:
                raise SystemExit("package checksum mismatch: %s" % name)
    with open(os.path.join(package, "feature_schema.json"), encoding="utf-8") as fh:
        if json.load(fh)["schema_sha256"] != schema_hash:
            raise SystemExit("%s was built with a different feature schema; rebuild it first" % package)


def fresh_dir(path: str) -> None:
    if os.path.exists(path):
        if not os.path.exists(os.path.join(path, MARKER)):
            raise SystemExit("%s exists and was not made by this script; not touching it" % path)
        shutil.rmtree(path)
    os.makedirs(path)


def finish(folder: str) -> str:
    """Write checksums for everything in the folder, then zip it."""
    files = []
    for base, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in names:
            rel = os.path.relpath(os.path.join(base, name), folder).replace(os.sep, "/")
            if rel != "checksums.sha256":
                files.append(rel)
    with open(os.path.join(folder, "checksums.sha256"), "w", encoding="utf-8", newline="\n") as fh:
        for rel in sorted(files):
            fh.write("%s  %s\n" % (sha256(os.path.join(folder, rel)), rel))
    archive = folder + ".zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(files) + ["checksums.sha256"]:
            zf.write(os.path.join(folder, rel), os.path.basename(folder) + "/" + rel)
    return archive


def build(name: str, readme: str, package: str, extra_docs=(), with_mock=False, with_code=False) -> str:
    folder = os.path.join(DEST, name)
    fresh_dir(folder)
    shutil.copyfile(os.path.join(ROOT, "handoff", readme), os.path.join(folder, MARKER))
    for doc in extra_docs:
        shutil.copyfile(os.path.join(ROOT, doc), os.path.join(folder, os.path.basename(doc)))
    shutil.copytree(package, os.path.join(folder, "features_package"))
    if with_mock:
        os.makedirs(os.path.join(folder, "mock_for_pipeline_dev"))
        for target, source in MOCK_FILES.items():
            shutil.copyfile(source, os.path.join(folder, "mock_for_pipeline_dev", target))
    if with_code:
        code = os.path.join(folder, "code")
        shutil.copytree(os.path.join(ROOT, "p3"), os.path.join(code, "p3"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        for rel in CODE_FILES + [os.path.relpath(FROZEN_PATH, ROOT)]:
            os.makedirs(os.path.join(code, os.path.dirname(rel)), exist_ok=True)
            shutil.copyfile(os.path.join(ROOT, rel), os.path.join(code, rel))
        shutil.copyfile(os.path.join(ROOT, "handoff", "README_CODE.md"), os.path.join(code, "README_CODE.md"))
    return finish(folder)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("which", nargs="?", default="candidate", choices=["candidate", "pilot"])
    args = parser.parse_args()
    if args.which == "candidate":
        verify_package(CANDIDATE_PACKAGE, schema_sha256())
        archives = [build("P3_to_P1_P4_candidate_v1.1", "CANDIDATE_READ_ME_FIRST.md", CANDIDATE_PACKAGE,
                          with_code=True)]
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
