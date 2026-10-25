"""Safe publication of output folders: no stale files, no half-written packages, nothing foreign deleted."""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
from typing import List

CHECKSUMS = "checksums.sha256"


class OutputDirError(RuntimeError):
    pass


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def all_files(folder: str) -> List[str]:
    files = []
    for base, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        files += [os.path.relpath(os.path.join(base, n), folder).replace(os.sep, "/") for n in names]
    return sorted(files)


def write_checksums(folder: str) -> None:
    """checksums.sha256 listing every file in the folder (LF, lowercase hex)."""
    lines = ["%s  %s\n" % (sha256(os.path.join(folder, rel)), rel)
             for rel in all_files(folder) if rel != CHECKSUMS]
    with open(os.path.join(folder, CHECKSUMS), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("".join(lines))


def foreign_files(folder: str) -> List[str]:
    """Files in a folder that its checksums.sha256 does not list (all files when it has none)."""
    listed = set()
    path = os.path.join(folder, CHECKSUMS)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            listed = {line.rstrip("\n").split("  ", 1)[-1] for line in fh if line.strip()}
    return [f for f in all_files(folder) if f != CHECKSUMS and f not in listed]


def check_replaceable(final: str) -> None:
    """`final` may be absent, empty, or an earlier package whose files are all in its checksums."""
    if not os.path.exists(final):
        return
    if not os.path.isdir(final):
        raise OutputDirError("%s exists and is not a folder" % final)
    foreign = foreign_files(final)
    if foreign:
        raise OutputDirError("%s holds files this tool did not write (%s%s); choose a new output folder"
                             % (final, ", ".join(foreign[:5]), ", ..." if len(foreign) > 5 else ""))


def staging_dir(final: str) -> str:
    """A fresh empty folder next to `final` to build into."""
    parent = os.path.dirname(os.path.abspath(final))
    os.makedirs(parent, exist_ok=True)
    return tempfile.mkdtemp(prefix=os.path.basename(os.path.abspath(final)) + ".staging-", dir=parent)


def publish_dir(staging: str, final: str) -> None:
    """Replace `final` with the finished `staging` folder.

    The old folder is renamed away first; on Windows that fails while any of its
    files is open, and then nothing has changed yet.
    """
    check_replaceable(final)
    if not os.path.exists(final):
        os.replace(staging, final)
        return
    backup = tempfile.mkdtemp(prefix=os.path.basename(os.path.abspath(final)) + ".old-",
                              dir=os.path.dirname(os.path.abspath(final)))
    os.rmdir(backup)
    os.replace(final, backup)
    try:
        os.replace(staging, final)
    except BaseException:
        os.replace(backup, final)
        raise
    shutil.rmtree(backup, ignore_errors=True)
    if os.path.exists(backup):
        print("warning: could not delete old copy %s" % backup, file=sys.stderr)

