"""Structured load / external-force verification payloads for the GUI."""

from __future__ import annotations

import os
from typing import Any, Dict

from stb_loads import (
    compute_seismic_distribution,
    compute_wind_distribution,
    generate_dlod_records,
    generate_wind_dlod_records,
)
from stb_loads.equilibrium import invalidate_solved_model_cache
from stb_loads.format import build_seismic_report_view
from stb_loads.gravity_format import build_dead_load_report, build_live_load_report
from stb_loads.wind_format import build_wind_report_view
from stb_gui.model_json import model_display_path, normalize_model_relpath, project_root, resolve_model_path
from stb_gui.model_session import get_model_and_project, invalidate_model_session
from stb_project import project_path_for_dat

def _invalidate_model_cache(full: str) -> None:
    invalidate_model_session(full)
    invalidate_solved_model_cache(full)


LOAD_VERIFY_TABS = (
    {"id": "dead", "label": "固定荷重", "enabled": True},
    {"id": "live", "label": "積載荷重", "enabled": True},
    {"id": "snow", "label": "積雪荷重", "enabled": False},
    {"id": "seismic", "label": "地震荷重", "enabled": True},
    {"id": "wind", "label": "風荷重", "enabled": True},
)


def _load_model_and_project(dat_relpath: str, mdl=None, project=None):
    return get_model_and_project(dat_relpath, mdl=mdl, project=project)


def _project_rel_path(full: str) -> str:
    return model_display_path(project_path_for_dat(full))


def _base_view_fields(kind: str, title: str, active_tab: str, dat_relpath: str, full: str) -> Dict[str, Any]:
    return {
        "kind": kind,
        "dat_path": dat_relpath,
        "project_path": _project_rel_path(full),
        "title": title,
        "tabs": list(LOAD_VERIFY_TABS),
        "active_tab": active_tab,
        "can_apply_dlod": False,
        "dlod_record_count": 0,
    }


def build_dead_loads_view(mdl, project, dat_relpath: str) -> Dict[str, Any]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)
    report = build_dead_load_report(mdl, project)
    view = _base_view_fields(
        "dead",
        "荷重・外力確認 — 固定荷重",
        "dead",
        dat_relpath,
        full,
    )
    view["found"] = report["found"]
    view.update(report)
    return view


def build_live_loads_view(mdl, project, dat_relpath: str) -> Dict[str, Any]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)
    report = build_live_load_report(mdl, project)
    view = _base_view_fields(
        "live",
        "荷重・外力確認 — 積載荷重",
        "live",
        dat_relpath,
        full,
    )
    view["found"] = report["found"]
    view.update(report)
    return view


def build_seismic_loads_view(mdl, project, dat_relpath: str) -> Dict[str, Any]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)

    result = compute_seismic_distribution(mdl, project)
    dloads = generate_dlod_records(result)
    report = build_seismic_report_view(result, project, mdl=mdl)

    view = _base_view_fields(
        "seismic",
        "荷重・外力確認 — 地震荷重",
        "seismic",
        dat_relpath,
        full,
    )
    view.update({
        "found": True,
        "summary": report["summary"],
        "raw_weight_rows": report["raw_weight_rows"],
        "mass_level_rows": report["mass_level_rows"],
        "diaphragm_rows": report["diaphragm_rows"],
        "alpha_i_note": report["alpha_i_note"],
        "wi_above_note": report.get("wi_above_note") or "",
        "report_notice": report["report_notice"],
        "dlod_section_title": report["dlod_section_title"],
        "dlod_section_note": report["dlod_section_note"],
        "qi_fi_rules_text": report["qi_fi_rules_text"],
        "equilibrium_rows": report.get("equilibrium_rows") or [],
        "checks": report.get("checks") or [],
        "warnings": list(result.warnings),
        "dlod_record_count": len(dloads),
        "can_apply_dlod": len(dloads) > 0,
    })
    return view


def build_wind_loads_view(
    mdl,
    project,
    dat_relpath: str,
    *,
    include_visual: bool = True,
) -> Dict[str, Any]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)

    result = compute_wind_distribution(mdl, project)
    dloads = generate_wind_dlod_records(result)
    report = build_wind_report_view(result, project, mdl=mdl, include_visual=include_visual)

    view = _base_view_fields(
        "wind",
        "荷重・外力確認 — 風荷重",
        "wind",
        dat_relpath,
        full,
    )
    view.update({
        "found": bool(result.cases),
        "summary": report["summary"],
        "surface_rows": report["surface_rows"],
        "tributary_rows": report["tributary_rows"],
        "base_wind_rows": report["base_wind_rows"],
        "validation_rows": report["validation_rows"],
        "story_force_rows": report["story_force_rows"],
        "diaphragm_rows": report["diaphragm_rows"],
        "uniform_input_note": report["uniform_input_note"],
        "report_notice": report["report_notice"],
        "dlod_section_title": report["dlod_section_title"],
        "visual": report["visual"],
        "equilibrium_rows": report.get("equilibrium_rows") or [],
        "checks": report.get("checks") or [],
        "warnings": list(result.warnings),
        "dlod_record_count": len(dloads),
        "can_apply_dlod": len(dloads) > 0,
    })
    return view


def load_dead_view_for_model(dat_relpath: str, mdl=None, project=None) -> Dict[str, Any]:
    dat_relpath, _full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)
    return build_dead_loads_view(mdl, project, dat_relpath)


def load_live_view_for_model(dat_relpath: str, mdl=None, project=None) -> Dict[str, Any]:
    dat_relpath, _full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)
    return build_live_loads_view(mdl, project, dat_relpath)


def load_seismic_view_for_model(dat_relpath: str, mdl=None, project=None) -> Dict[str, Any]:
    dat_relpath, _full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)
    return build_seismic_loads_view(mdl, project, dat_relpath)


def load_wind_view_for_model(
    dat_relpath: str,
    mdl=None,
    project=None,
    *,
    include_visual: bool = True,
) -> Dict[str, Any]:
    dat_relpath, _full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)
    return build_wind_loads_view(
        mdl, project, dat_relpath, include_visual=include_visual
    )


def apply_seismic_dlod_for_model(dat_relpath: str, mdl=None, project=None) -> Dict[str, Any]:
    dat_relpath, full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)

    result = compute_seismic_distribution(mdl, project)
    dloads = generate_dlod_records(result)
    from stb_loads import apply_seismic_to_dat

    apply_seismic_to_dat(full, dloads)
    _invalidate_model_cache(full)
    view = build_seismic_loads_view(mdl, project, dat_relpath)
    view["applied"] = True
    view["dlod_record_count"] = len(dloads)
    return view


def apply_wind_dlod_for_model(dat_relpath: str, mdl=None, project=None) -> Dict[str, Any]:
    dat_relpath, full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)

    result = compute_wind_distribution(mdl, project)
    dloads = generate_wind_dlod_records(result)
    from stb_loads import apply_wind_to_dat

    apply_wind_to_dat(full, dloads)
    _invalidate_model_cache(full)
    view = build_wind_loads_view(mdl, project, dat_relpath)
    view["applied"] = True
    view["dlod_record_count"] = len(dloads)
    return view
