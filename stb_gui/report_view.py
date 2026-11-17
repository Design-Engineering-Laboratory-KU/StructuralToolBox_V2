"""Calculation book (PDF) for the GUI."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile

from stb_engine import parse_input, solve_model
from stb_gui.model_json import resolve_model_path
from stb_project import apply_load_combinations_to_model, load_project_for_dat, project_path_for_dat


def build_report_pdf_for_model(rel_path: str):
    """Solve the .dat at ``rel_path`` and return (pdf bytes, file name)."""
    from stb_engine.version import __version__ as stb_version
    from stb_reports.calc_book import write_calc_book_pdf

    full = resolve_model_path(rel_path)
    project = load_project_for_dat(full)
    if project is None:
        raise ValueError(
            "プロジェクトファイルがありません: " + project_path_for_dat(full) + "（Project… で作成してください）"
        )
    with open(full, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    mdl = parse_input(lines)
    mdl.filepath = full
    apply_load_combinations_to_model(mdl, project)
    with contextlib.redirect_stdout(io.StringIO()):
        solve_model(mdl)

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "book.pdf")
        write_calc_book_pdf(path, mdl, project, program_version=stb_version)
        with open(path, "rb") as fh:
            data = fh.read()
    stem = os.path.splitext(os.path.basename(full))[0]
    return data, stem + "_計算書.pdf"
