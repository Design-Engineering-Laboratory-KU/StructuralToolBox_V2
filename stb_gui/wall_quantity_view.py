"""木造壁量計算書 (HTML) for the GUI."""

from __future__ import annotations

import html

from stb_engine import parse_input
from stb_gui.model_json import resolve_model_path
from stb_project import load_project_for_dat, project_path_for_dat


def render_wall_quantity_report_html(rel_path: str) -> str:
    """Build the report for the .dat at ``rel_path``. Raises ValueError with a user-facing message."""
    from stb_engine.version import __version__ as stb_version
    from stb_reports import build_wall_quantity_report

    full = resolve_model_path(rel_path)
    project = load_project_for_dat(full)
    if project is None:
        raise ValueError(
            "プロジェクトファイルがありません: " + project_path_for_dat(full)
            + "（Project… で作成し、wall_quantity を設定してください）"
        )
    if not project.wall_quantity.enabled:
        raise ValueError("project.json に wall_quantity（壁量計算の条件）が設定されていません。docs/project_format.md を参照してください。")
    with open(full, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    mdl = parse_input(lines)
    mdl.filepath = full
    return build_wall_quantity_report(mdl, project, program_version=stb_version).html


def error_page_html(message: str) -> str:
    return (
        "<!doctype html><html lang=\"ja\"><head><meta charset=\"utf-8\"><title>壁量計算書</title>"
        "<style>body{font-family:sans-serif;margin:32px;color:#1f2328;background:#fff}"
        "p{background:#fff8c5;border:1px solid #d4a72c;padding:12px 16px;border-radius:6px}</style></head>"
        "<body><h1>壁量計算書を作成できませんでした</h1><p>" + html.escape(message) + "</p></body></html>"
    )
