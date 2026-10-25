"""Assemble the folders and zips P3 sends to the team.

    python tools/build_handoff.py

Creates, next to this project folder:
    P3_to_P4/ + P3_to_P4.zip   features package, P4 handoff notes, mock data for pipeline development
    P3_to_P1/ + P3_to_P1.zip   features package, freeze declaration, P3 report

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

from p3.schema import schema_sha256  # noqa: E402

DEST = os.path.dirname(ROOT)
PACKAGE = os.path.join(ROOT, "output_pilot_v0.1_p3-1.0")
MOCK_FILES = {
    "features.csv": os.path.join(ROOT, "output_mock", "features.csv"),
    "run_index.csv": os.path.join(ROOT, "output_mock", "run_index.csv"),
    "adjudicated_labels.mock.jsonl": os.path.join(ROOT, "mock", "adjudicated_labels.mock.jsonl"),
}
MARKER = "00_READ_ME_FIRST.md"


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_package() -> None:
    with open(os.path.join(PACKAGE, "checksums.sha256"), encoding="utf-8") as fh:
        for line in fh:
            digest, name = line.rstrip("\n").split("  ", 1)
            if sha256(os.path.join(PACKAGE, name)) != digest:
                raise SystemExit("package checksum mismatch: %s" % name)
    with open(os.path.join(PACKAGE, "feature_schema.json"), encoding="utf-8") as fh:
        if json.load(fh)["schema_sha256"] != schema_sha256():
            raise SystemExit("package was built with a different feature schema; rebuild it first")


def fresh_dir(path: str) -> None:
    if os.path.exists(path):
        if not os.path.exists(os.path.join(path, MARKER)):
            raise SystemExit("%s exists and was not made by this script; not touching it" % path)
        shutil.rmtree(path)
    os.makedirs(path)


def finish(folder: str) -> str:
    """Write checksums for everything in the folder, then zip it."""
    files = []
    for base, _, names in os.walk(folder):
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


def build(name: str, readme: str, extra_docs: list, with_mock: bool) -> str:
    folder = os.path.join(DEST, name)
    fresh_dir(folder)
    shutil.copyfile(os.path.join(ROOT, "handoff", readme), os.path.join(folder, MARKER))
    for doc in extra_docs:
        shutil.copyfile(os.path.join(ROOT, doc), os.path.join(folder, os.path.basename(doc)))
    shutil.copytree(PACKAGE, os.path.join(folder, "features_package"))
    if with_mock:
        os.makedirs(os.path.join(folder, "mock_for_pipeline_dev"))
        for target, source in MOCK_FILES.items():
            shutil.copyfile(source, os.path.join(folder, "mock_for_pipeline_dev", target))
    return finish(folder)


def main() -> int:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    verify_package()
    for archive in (build("P3_to_P4", "P4_READ_ME_FIRST.md", ["HANDOFF_P4.md"], with_mock=True),
                    build("P3_to_P1", "P1_READ_ME_FIRST.md", ["PILOT_REPORT_P3.md"], with_mock=False)):
        print("%s (%d KB)" % (archive, os.path.getsize(archive) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
