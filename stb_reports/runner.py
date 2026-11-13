"""Run reports end to end (shared by ``stb report`` / ``stb wallcalc`` and the GUI)."""

from __future__ import annotations

import contextlib
import io
import os
from typing import Optional, Tuple

from stb_reports.draft import ReportDraft, build_confirmation_draft

REPORT_EXTENSIONS = {".html": "html", ".htm": "html", ".md": "markdown", ".pdf": "pdf"}
FORMAT_EXTENSIONS = {"html": ".html", "markdown": ".md", "pdf": ".pdf"}

# report kind -> suffix of the default output name (<stem><suffix><ext>)
REPORT_KINDS = {"confirmation": "_report", "wall_quantity": "_wallcalc"}


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


def default_report_output_path(input_path, kind="confirmation", output_format="html") -> str:
    """``foo.project.json`` / ``foo.dat`` -> ``foo_report.html`` (``foo_wallcalc.pdf`` ...) next to it."""

    input_path = os.path.abspath(input_path)
    folder, name = os.path.split(input_path)
    if name.lower().endswith(".project.json"):
        stem = name[: -len(".project.json")]
    else:
        stem = os.path.splitext(name)[0]
    suffix = REPORT_KINDS.get(kind, "_report")
    ext = FORMAT_EXTENSIONS.get(output_format or "html", ".html")
    return os.path.join(folder, stem + suffix + ext)


def report_format_for_path(output_path) -> Optional[str]:
    """Format implied by the output extension, or None when it is not a report extension."""

    return REPORT_EXTENSIONS.get(os.path.splitext(str(output_path))[1].lower())


def _read_model(dat_path):
    from stb_engine import parse_input

    if not os.path.isfile(dat_path):
        raise IOError("Input file not found: " + dat_path)
    with open(dat_path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    mdl = parse_input(lines)
    mdl.filepath = dat_path
    return mdl


def _write_report(output_path, fmt, markdown_text, html_text, newline=None):
    """Write markdown / html text, or print the html to PDF."""

    if fmt == "pdf":
        from stb_reports.pdf import html_to_pdf

        html_to_pdf(html_text, output_path)
        return
    if fmt == "markdown":
        text = markdown_text
    elif fmt == "html":
        text = html_text
    else:
        raise ValueError("Unsupported report format: " + str(fmt))
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir != "" and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(output_path, "w", encoding="utf-8", newline=newline) as fh:
        fh.write(text)


def generate_confirmation_report(
    input_path,
    output_path,
    output_format: Optional[str] = None,
    program_version: str = "",
    quiet: bool = False,
) -> Tuple[ReportDraft, object, str]:
    """Parse, apply load combinations, solve and write the 確認申請補助計算書.

    Returns ``(draft, project, dat_path)``. Raises IOError / ValueError /
    StbParseError / StbSolveError / PdfExportError.
    """

    from stb_engine import format_results, solve_model
    from stb_project import apply_load_combinations_to_model

    project, dat_path = resolve_report_input(input_path)
    mdl = _read_model(dat_path)
    apply_load_combinations_to_model(mdl, project)
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            solve_model(mdl)
    else:
        solve_model(mdl)
    txt = format_results(mdl)
    draft = build_confirmation_draft(
        mdl,
        project,
        analysis_text=txt,
        program_version=program_version,
    )
    # Same as before PDF support: --format, else project.report.format; a .pdf
    # output path always means PDF.
    if output_format is None and report_format_for_path(output_path) == "pdf":
        output_format = "pdf"
    fmt = output_format or project.report.format
    _write_report(output_path, fmt, draft.markdown, draft.html)
    return draft, project, dat_path


def generate_wall_quantity_report(
    input_path,
    output_path,
    output_format: Optional[str] = None,
    program_version: str = "",
):
    """Parse (no solve) and write the 木造壁量計算書. Returns ``(report, project, dat_path)``."""

    from stb_reports.wall_quantity_report import build_wall_quantity_report

    project, dat_path = resolve_report_input(input_path)
    if not project.wall_quantity.enabled:
        raise ValueError("project.wall_quantity is not set (see docs/project_format.md)")
    mdl = _read_model(dat_path)
    report = build_wall_quantity_report(mdl, project, program_version=program_version)
    fmt = output_format or report_format_for_path(output_path) or "html"
    _write_report(output_path, fmt, report.markdown, report.html, newline="\n")
    return report, project, dat_path
