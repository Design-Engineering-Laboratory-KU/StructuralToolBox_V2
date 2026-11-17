"""Structural-index verification payloads for the GUI."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, Optional

from stb_gui.model_json import model_display_path, normalize_model_relpath, project_root, resolve_model_path
from stb_loads.equilibrium import get_cached_solved_model
from stb_practice import build_structural_indices
from stb_project import load_project_for_dat, project_path_for_dat


PRACTICE_TABS = (
    {"id": "summary", "label": "Summary", "enabled": True},
    {"id": "drift", "label": "Story drift", "enabled": True},
    {"id": "eccentricity", "label": "Eccentricity", "enabled": True},
    {"id": "rigidity", "label": "Rigidity ratio", "enabled": True},
    {"id": "warnings", "label": "Warnings", "enabled": True},
)


def _project_rel_path(full: str) -> str:
    return model_display_path(project_path_for_dat(full))


def _fmt_ratio(value: Optional[float]) -> str:
    if value is None:
        return "-"
    if value <= 0:
        return "-"
    return "1/{0:.0f}".format(1.0 / value)


def _fmt_num(value: Optional[float], places: int = 3) -> str:
    if value is None:
        return "-"
    return ("{0:." + str(places) + "f}").format(value)


def _summary_rows(result) -> list:
    rows = []
    rows.append({
        "label": "対象水平荷重ケース",
        "value": ", ".join(
            "{0} LC{1}".format(c.axis.upper(), c.load_case) for c in result.lateral_cases
        ) or "-",
    })
    max_drift = _max_value(result.story_drifts, lambda r: r.drift_angle if r.is_story_max else None)
    max_re = _max_value(result.eccentricities, lambda r: max(
        v for v in (r.re_x, r.re_y) if v is not None
    ) if (r.re_x is not None or r.re_y is not None) else None)
    min_rs = _min_value(result.rigidity_ratios, lambda r: r.rigidity_ratio)
    rows.extend([
        {"label": "最大層間変形角", "value": _fmt_num(max_drift, 6), "note": _fmt_ratio(max_drift)},
        {"label": "最大偏心率", "value": _fmt_num(max_re, 3)},
        {"label": "最小剛性率", "value": _fmt_num(min_rs, 3)},
        {"label": "警告数", "value": str(len(result.warnings))},
    ])
    return rows


def _max_value(items: Iterable[Any], getter):
    vals = []
    for item in items:
        v = getter(item)
        if v is not None:
            vals.append(v)
    return max(vals) if vals else None


def _min_value(items: Iterable[Any], getter):
    vals = []
    for item in items:
        v = getter(item)
        if v is not None:
            vals.append(v)
    return min(vals) if vals else None


def _strip_pdf_section_reference(text: str) -> str:
    text = re.sub(r"PDF\s*2\.5\s*節", "", str(text))
    text = re.sub(r"PDF\s*2\.5", "", text)
    return " ".join(text.split())


def build_practice_summary_view(mdl, project, dat_relpath: str, full: str) -> Dict[str, Any]:
    result = build_structural_indices(mdl, project)
    story_rows = [{
        "story": s.name,
        "elevation": float(s.elevation),
        "height": float(s.height),
        "top_elevation": float(s.elevation) + float(s.height),
    } for s in getattr(project, "stories", ())]
    return {
        "kind": "practice",
        "title": "構造指標 - 層間変形角・偏心率・剛性率",
        "dat_path": normalize_model_relpath(dat_relpath),
        "project_path": _project_rel_path(full),
        "tabs": list(PRACTICE_TABS),
        "active_tab": "summary",
        "summary": _summary_rows(result),
        "story_rows": story_rows,
        "lateral_cases": list(result.tables["lateral_cases"]),
        "story_drift_rows": list(result.tables["story_drifts"]),
        "member_stiffness_rows": list(result.tables["member_stiffnesses"]),
        "eccentricity_rows": list(result.tables["eccentricities"]),
        "rigidity_ratio_rows": list(result.tables["rigidity_ratios"]),
        "warnings": [_strip_pdf_section_reference(w) for w in result.warnings],
        "notes": [
            "解析後処理による構造指標です。",
            "段違い梁・中間層・混構造の詳細補正は初期実装では未考慮です。",
        ],
    }


def load_practice_summary_view_for_model(dat_relpath: str) -> Dict[str, Any]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)
    project = load_project_for_dat(full, required=True)
    mdl = get_cached_solved_model(full)
    if mdl is None:
        raise ValueError(
            "Analysis results are not available. Run Solve in the main window first."
        )
    return build_practice_summary_view(mdl, project, dat_relpath, full)
