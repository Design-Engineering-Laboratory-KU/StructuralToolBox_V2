#!/usr/bin/env python3
"""Write install_manifest.txt: every file a payload ships, one relative path per line.

The cleaners that run before an upgrade (clean_old_install.ps1 on Windows,
mac/clean_old_install.sh on macOS) treat a .dat/.out/.gh file as the user's own
only when it is not listed here, so shipped examples are replaced while models
the user saved are kept.
"""

from __future__ import annotations

import argparse
from pathlib import Path

MANIFEST_NAME = "install_manifest.txt"


def write(payload: Path) -> Path:
    files = sorted(
        path.relative_to(payload).as_posix()
        for path in payload.rglob("*")
        if path.is_file()
    )
    files.append(MANIFEST_NAME)
    target = payload / MANIFEST_NAME
    target.write_text("\n".join(sorted(set(files))) + "\n", encoding="utf-8", newline="\n")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    args = parser.parse_args()
    target = write(args.payload)
    print(f"OK: {target.name} ({sum(1 for _ in target.open(encoding='utf-8'))} files)")


if __name__ == "__main__":
    main()
