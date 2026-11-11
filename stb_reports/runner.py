"""Run the confirmation-draft report end to end (shared by ``stb report`` and the GUI)."""

from __future__ import annotations

import contextlib
import io
import os
from typing import Optional, Tuple

from stb_reports.draft import ReportDraft, write_confirmation_draft

REPORT_EXTENSIONS = {".html": "html", ".htm": "html", ".md": "markdown"}


def resolve_report_input(input_path) -> Tuple[object, str]:
    """Return ``(project, dat_path)`` for a project JSON or a .dat with a sidecar."""

    from stb_project import load_project_file, load_project_for_dat

    input_path = os.path.abspath(input_path)
    if input_path.lower().endswith(".json"):
        project = load_project_file(input_path)
        dat_path = project.dat_path
        if not os.path.isabs(dat_path):
            dat_path = os.path.join(os.path.dirname(input_path), dat_path)
    else:
        dat_path = input_path
        project = load_project_for_dat(dat_path, required=True)
    return project, dat_path


def default_report_output_path(input_path) -> str:
    """``foo.project.json`` / ``foo.dat`` -> ``foo_report.html`` in the same folder."""

    input_path = os.path.abspath(input_path)
    folder, name = os.path.split(input_path)
    lower = name.lower()
    if lower.endswith(".project.json"):
        stem = name[: -len(".project.json")]
    else:
        stem = os.path.splitext(name)[0]
    return os.path.join(folder, stem + "_report.html")


def report_format_for_path(output_path) -> Optional[str]:
    """Format implied by the output extension, or None when it is not a report extension."""

    return REPORT_EXTENSIONS.get(os.path.splitext(str(output_path))[1].lower())


def generate_confirmation_report(
    input_path,
    output_path,
    output_format: Optional[str] = None,
    program_version: str = "",
    quiet: bool = False,
) -> Tuple[ReportDraft, object, str]:
    """Parse, apply load combinations, solve and write the report.

    Returns ``(draft, project, dat_path)``. Raises IOError / ValueError /
    StbParseError / StbSolveError like the CLI did before this was shared.
    """

    from stb_engine import format_results, parse_input, solve_model
    from stb_project import apply_load_combinations_to_model

    project, dat_path = resolve_report_input(input_path)
    if not os.path.isfile(dat_path):
        raise IOError("Input file not found: " + dat_path)
    with open(dat_path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    mdl = parse_input(lines)
    mdl.filepath = dat_path
    apply_load_combinations_to_model(mdl, project)
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            solve_model(mdl)
    else:
        solve_model(mdl)
    txt = format_results(mdl)
    draft = write_confirmation_draft(
        output_path,
        mdl,
        project,
        output_format=output_format,
        analysis_text=txt,
        program_version=program_version,
    )
    return draft, project, dat_path
