#!/usr/bin/env python3
"""Download the solver/GUI libraries as wheels for the student installers.

Installers ship these so the first-time setup works without internet and
always installs the same versions on every student machine.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDENT = Path(__file__).resolve().parent
CACHE = STUDENT / "dist" / "_cache" / "wheels"

# Runtime dependencies, kept in step with pyproject.toml.
RUNTIME = [
    "numpy",
    "scipy",
    "shapely",
    "fastapi",
    "uvicorn[standard]",
    "httpx",
]
# Needed to build structural-toolbox itself, and to create the venv on the
# Windows embeddable Python, which has no venv module.
TOOLING = ["pip", "setuptools", "wheel"]
WINDOWS_TOOLING = ["virtualenv"]
# pip evaluates environment markers on the host PC. Downloading macOS wheels
# from Windows therefore skips uvloop (required by uvicorn[standard] on Unix).
MACOS_EXTRA = ["uvloop"]

# One pip run per architecture, with every macOS version tag that ships wheels.
# pip treats the first tag as highest priority, so the oldest macOS comes first
# to keep the wheels usable on the oldest Mac we support. Some packages ship
# only universal2 wheels, so those tags are listed as a fallback.
PLATFORM_GROUPS = {
    "windows": {
        "win_amd64": ["win_amd64"],
    },
    "macos": {
        "arm64": [
            "macosx_11_0_arm64",
            "macosx_12_0_arm64",
            "macosx_13_0_arm64",
            "macosx_14_0_arm64",
            "macosx_10_9_universal2",
            "macosx_10_13_universal2",
        ],
        "x86_64": [
            "macosx_10_9_x86_64",
            "macosx_10_12_x86_64",
            "macosx_10_13_x86_64",
            "macosx_10_14_x86_64",
            "macosx_10_15_x86_64",
            "macosx_11_0_x86_64",
            "macosx_10_9_universal2",
            "macosx_10_13_universal2",
        ],
    },
}


def python_version(version_file: Path) -> str:
    full = version_file.read_text(encoding="utf-8").strip()
    return ".".join(full.split(".")[:2])


def download(dest: Path, requirements: list[str], platform_tags: list[str], py_version: str) -> None:
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--python-version",
        py_version,
        "--dest",
        str(dest),
    ]
    for tag in platform_tags:
        cmd += ["--platform", tag]
    cmd += requirements

    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-8:]
        raise SystemExit(
            "pip download failed for platforms "
            + ", ".join(platform_tags)
            + ":\n  "
            + "\n  ".join(tail)
        )


def download_pure(dest: Path, requirements: list[str], py_version: str) -> None:
    """Pure-Python wheels, which carry no platform tag."""
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--python-version",
        py_version,
        "--platform",
        "any",
        "--dest",
        str(dest),
    ] + requirements
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-6:]
        raise SystemExit("pip download failed for pure wheels:\n  " + "\n  ".join(tail))


def build(target: str, py_version: str) -> Path:
    dest = CACHE / target
    dest.mkdir(parents=True, exist_ok=True)

    requirements = list(RUNTIME)
    if target == "windows":
        requirements += WINDOWS_TOOLING
    elif target == "macos":
        requirements += MACOS_EXTRA

    print("Downloading wheels for " + target + " (Python " + py_version + ")")
    for name, tags in PLATFORM_GROUPS[target].items():
        print("  " + name)
        download(dest, requirements, tags, py_version)
    download_pure(dest, TOOLING, py_version)

    wheels = sorted(dest.glob("*.whl"))
    if not wheels:
        raise SystemExit("No wheels were downloaded into " + str(dest))
    total = sum(w.stat().st_size for w in wheels) / (1024 * 1024)
    print("  {0} wheels, {1:.1f} MB".format(len(wheels), total))
    return dest


def copy_into_payload(source: Path, payload: Path) -> None:
    dest = payload / "wheels"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    names = []
    for wheel in sorted(source.glob("*.whl")):
        shutil.copy2(wheel, dest / wheel.name)
        names.append(wheel.name)
    (dest / "WHEELS.txt").write_text("\n".join(names) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=sorted(PLATFORM_GROUPS))
    parser.add_argument("--payload", help="Copy the wheels into this payload folder")
    args = parser.parse_args()

    py_version = python_version(STUDENT / "PYTHON_EMBED_VERSION")
    dest = build(args.target, py_version)
    if args.payload:
        copy_into_payload(dest, Path(args.payload))
        print("  copied into " + str(Path(args.payload) / "wheels"))


if __name__ == "__main__":
    main()
