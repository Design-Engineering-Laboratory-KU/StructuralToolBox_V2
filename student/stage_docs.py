#!/usr/bin/env python3
"""Copy the student guides to the payload root under short names.

Windows PowerShell 5.1 reads .ps1 files as ANSI, which mangles Japanese string
literals, so the builders call this instead of matching those names in script.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

GUIDES = {
    "windows": {
        "学生用_インストール_Windows.md": "はじめ方_インストーラ版.md",
        "学生用_はじめ方_Windows.md": "はじめ方_Windows.md",
    },
    "macos": {
        "学生用_インストール_Mac.md": "はじめ方_インストーラ版.md",
        "学生用_はじめ方_Mac.md": "はじめ方_Mac.md",
    },
}


def stage(payload: Path, target: str, repo_root: Path) -> list[str]:
    copied = []
    for source_name, dest_name in GUIDES[target].items():
        source = repo_root / "docs" / source_name
        if not source.is_file():
            raise SystemExit("Guide is missing: " + str(source))
        shutil.copyfile(source, payload / dest_name)
        copied.append(dest_name)
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=sorted(GUIDES))
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    for name in stage(Path(args.payload), args.target, repo_root):
        print("OK: " + name)


if __name__ == "__main__":
    main()
