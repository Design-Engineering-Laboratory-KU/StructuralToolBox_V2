#!/usr/bin/env python3
"""Turn a copied source tree into the Simple or Full edition payload.

The Windows and macOS builders both call this right after copying the source,
so the two platforms cannot disagree on what each edition contains. Full ships
the tree as it is. Simple removes the code and data of the Full-only features.
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

SIMPLE = "simple"
FULL = "full"
EDITIONS = (SIMPLE, FULL)

# Paths relative to the payload root.
FULL_ONLY_PATHS = (
    "stb_reports",
    "stb_checks",
    "stb_practice",
    "stb_cli/full_commands.py",
    "stb_gui/full_routes.py",
    "stb_gui/project_view.py",
    "stb_gui/project_edit.py",
    "stb_gui/loads_view.py",
    "stb_gui/practice_view.py",
    "stb_gui/wall_quantity_view.py",
    "stb_gui/report_view.py",
    "stb_gui/static/loads_verify.css",
    "stb_gui/static/loads_verify.html",
    "stb_gui/static/loads_verify.js",
    "stb_gui/static/practice_verify.css",
    "stb_gui/static/practice_verify.html",
    "stb_gui/static/practice_verify.js",
    "docs/project_format.md",
    "docs/project_overview.md",
    "docs/report_gap_map.md",
    "data/practice_wood_single_story.dat",
    "data/sample_wall_quantity_2f.dat",
    "report.md",
    "scripts/profile_loads_api.py",
    "scripts/profile_loads_view.py",
    # The test suite exercises every Full feature.
    "tests",
)
FULL_ONLY_GLOBS = ("data/*.project.json",)
FULL_ONLY_MODULES = (
    "stb_reports",
    "stb_checks",
    "stb_practice",
    "stb_cli.full_commands",
    "stb_gui.full_routes",
    "stb_gui.project_view",
    "stb_gui.project_edit",
    "stb_gui.loads_view",
    "stb_gui.practice_view",
    "stb_gui.wall_quantity_view",
    "stb_gui.report_view",
)

INDEX_HTML = "stb_gui/static/index.html"
FULL_ONLY_BUTTONS = ("btnGuiMode", "btnProject", "btnLoads", "btnPractice", "btnWallQuantity", "btnCalcBook")

README = "README.md"
# pyproject.toml names this file, so the install needs it to exist.
SIMPLE_README = """# Structural Toolbox

3D linear static analysis for frame structures.

Open the GUI from the Start menu or the launcher in this folder. The input
format is described in docs/input_format.md.
"""

# Trees that hold third-party code, or that are not part of the application.
_SKIPPED_SCAN_DIRS = {"python-embed", "wheels", ".venv", "vendor", "__pycache__"}


class EditionError(Exception):
    """The payload does not match the requested edition."""


def _remove(path: Path) -> None:
    if path.is_dir():
        for child in path.iterdir():
            _remove(child)
        path.rmdir()
    elif path.exists():
        path.unlink()


def _button_pattern(button_id: str) -> re.Pattern:
    return re.compile(r'^[ \t]*<button id="' + button_id + r'"[^\n]*</button>[ \t]*\r?\n', re.MULTILINE)


def _strip_full_only_buttons(payload: Path) -> None:
    path = payload / INDEX_HTML
    with path.open(encoding="utf-8", newline="") as fh:
        text = fh.read()
    for button_id in FULL_ONLY_BUTTONS:
        text, count = _button_pattern(button_id).subn("", text, count=1)
        if count != 1:
            raise EditionError("index.html has no one-line button with id " + button_id)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def apply(payload: Path, edition: str) -> None:
    """Make the payload the given edition, then verify it."""
    if edition == SIMPLE:
        for rel in FULL_ONLY_PATHS:
            _remove(payload / rel)
        for pattern in FULL_ONLY_GLOBS:
            for path in payload.glob(pattern):
                _remove(path)
        _strip_full_only_buttons(payload)
        (payload / README).write_text(SIMPLE_README, encoding="utf-8", newline="\n")
    verify(payload, edition)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names.update(node.module + "." + alias.name for alias in node.names)
    return names


def _is_full_only(module: str) -> bool:
    return any(module == name or module.startswith(name + ".") for name in FULL_ONLY_MODULES)


def _application_sources(payload: Path):
    for path in payload.rglob("*.py"):
        if not _SKIPPED_SCAN_DIRS.intersection(path.relative_to(payload).parts):
            yield path


def verify(payload: Path, edition: str) -> None:
    """Raise EditionError unless the payload is really the given edition."""
    if edition not in EDITIONS:
        raise EditionError("Unknown edition: " + edition)

    html = (payload / INDEX_HTML).read_text(encoding="utf-8")
    buttons = ['id="' + button_id + '"' in html for button_id in FULL_ONLY_BUTTONS]
    present = [rel for rel in FULL_ONLY_PATHS if (payload / rel).exists()]

    if edition == FULL:
        missing = [rel for rel in FULL_ONLY_PATHS if rel not in present]
        if missing or not all(buttons):
            raise EditionError("Not a Full payload; missing: " + ", ".join(missing or ["GUI buttons"]))
        return

    present += [path.as_posix() for pattern in FULL_ONLY_GLOBS for path in payload.glob(pattern)]
    if present or any(buttons):
        raise EditionError("Not a Simple payload; found: " + ", ".join(present or ["Full-only GUI buttons"]))

    for path in _application_sources(payload):
        leaked = sorted(m for m in _imported_modules(path) if _is_full_only(m))
        if leaked:
            raise EditionError(
                "{0} imports code the Simple edition omits: {1}".format(
                    path.relative_to(payload).as_posix(), ", ".join(leaked)
                )
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edition", choices=EDITIONS)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--verify-only", action="store_true", help="Check the payload without changing it")
    args = parser.parse_args()
    try:
        if args.verify_only:
            verify(args.payload, args.edition)
        else:
            apply(args.payload, args.edition)
    except EditionError as ex:
        raise SystemExit("Edition error: " + str(ex))
    print("OK: " + args.edition + " edition")


if __name__ == "__main__":
    main()
