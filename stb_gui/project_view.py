"""Human-readable project.json view payload for the GUI."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from stb_project import (
    DEFAULT_SEISMIC_RT,
    DEFAULT_SEISMIC_TC,
    ProjectDefinition,
    ProjectSchemaError,
    SCHEMA_VERSION,
    effective_seismic_ci,
    load_project_for_dat,
    project_path_for_dat,
    validate_project_dict,
)
from stb_project.floor_loads import sync_project_floor_dlod_lines
from stb_project.load_combinations import sync_project_lcmb_lines
from stb_project.load_names import sync_project_lnme_lines
from stb_loads import compute_seismic_distribution, generate_dlod_records, sync_seismic_dlod_lines
from stb_engine import parse_input
from stb_gui.dat_edit import validate_dat_text
from stb_gui.dat_format_headers import write_dat_text
from stb_gui.project_edit import build_project_edit_form
from stb_gui.model_json import normalize_model_relpath, project_root, resolve_model_path


_MEMBER_KIND_LABELS = {
    "beam": "梁",
    "column": "柱",
    "brace": "ブレース",
    "foundation_beam": "基礎梁",
    "panel": "パネル",
    "support": "支点",
    "lateral_resisting_element": "耐震要素",
    "other": "その他",
}

_REPORT_MODE_LABELS = {
    "practice": "実務 (practice)",
    "education": "教育 (education)",
    "debug": "デバッグ (debug)",
}


def project_relpath_for_model(dat_relpath: str) -> Optional[str]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    if not dat_relpath:
        return None
    full = resolve_model_path(dat_relpath)
    rel = os.path.relpath(project_path_for_dat(full), project_root()).replace("\\", "/")
    return rel


def default_project_dict_for_dat(dat_relpath: str) -> Dict[str, Any]:
    """Return a minimal valid project.json payload for a .dat model."""

    dat_relpath = normalize_model_relpath(dat_relpath)
    if not dat_relpath:
        raise ValueError("Model path is empty")
    dat_name = os.path.basename(dat_relpath)
    stem = os.path.splitext(dat_name)[0] or dat_name
    return {
        "schema": SCHEMA_VERSION,
        "model": {"dat": dat_name},
        "building": {
            "name": stem,
            "location": "",
            "use": "",
            "structure": "",
            "calculation_route": "",
            "designer": {
                "name": "",
                "qualification": "",
                "license_number": "",
                "contact": "",
            },
        },
        "grids": [],
        "stories": [],
        "member_classes": [],
        "design_checks": {
            "wood": {
                "enabled": False,
                "load_cases": [],
                "deflection_limit_ratio": 0.0,
                "allowable_stresses": {
                    "bending": 0.0,
                    "shear": 0.0,
                    "compression": 0.0,
                    "tension": 0.0,
                },
            },
        },
        "report": {
            "title": stem,
            "mode": "practice",
            "language": "ja",
            "format": "markdown",
            "include_manual_items": True,
            "include_warnings": True,
        },
    }


def build_new_project_template_view(dat_relpath: str) -> Dict[str, Any]:
    """Editable project view payload for a model without a sidecar file."""

    dat_relpath = normalize_model_relpath(dat_relpath)
    raw = default_project_dict_for_dat(dat_relpath)
    project = validate_project_dict(raw)
    project_rel = project_relpath_for_model(dat_relpath) or ""
    title_name = project.building.name or os.path.splitext(os.path.basename(dat_relpath))[0]
    return {
        "found": False,
        "draft": True,
        "dat_path": dat_relpath,
        "project_path": project_rel,
        "title": title_name + " — project.json (新規)",
        "sections": [
            {
                "id": "new",
                "title": "新規 project.json",
                "rows": [
                    {"label": "保存先", "value": project_rel},
                    {"label": "解析ファイル", "value": project.dat_path},
                    {
                        "label": "説明",
                        "value": "内容を編集して「保存」で project.json を作成します。",
                    },
                ],
            }
        ],
        "edit": build_project_edit_form(project),
        "raw": project.to_dict(),
    }


def load_project_view_for_model(dat_relpath: str) -> Dict[str, Any]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)
    project_path = project_path_for_dat(full)
    project_rel = os.path.relpath(project_path, project_root()).replace("\\", "/")

    if not os.path.isfile(project_path):
        return {
            "found": False,
            "dat_path": dat_relpath,
            "project_path": project_rel,
            "title": "プロジェクト設定",
            "sections": [
                {
                    "id": "missing",
                    "title": "サイドカー未作成",
                    "rows": [
                        {
                            "label": "期待パス",
                            "value": project_rel,
                        },
                        {
                            "label": "説明",
                            "value": "この .dat に対応する project.json が見つかりません。「新規作成」から作成できます。",
                        },
                    ],
                }
            ],
            "raw": None,
        }

    project = load_project_for_dat(full, required=True)
    return build_project_view(project, project_rel, dat_relpath)


def save_project_json_for_model(dat_relpath: str, raw: dict) -> Dict[str, Any]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)
    project_path = project_path_for_dat(full)

    try:
        project = validate_project_dict(raw)
    except ProjectSchemaError as ex:
        raise ValueError(str(ex))

    with open(full, "r", encoding="utf-8") as fh:
        dat_lines = fh.read().splitlines()

    updated_lines = sync_project_lnme_lines(dat_lines, project)
    updated_lines = sync_project_floor_dlod_lines(updated_lines, project)
    updated_lines = _sync_project_seismic_dlod_lines(updated_lines, project, full)
    updated_lines = sync_project_lcmb_lines(updated_lines, project)
    updated_text = _join_dat_lines(updated_lines)
    validate_dat_text(updated_text)

    os.makedirs(os.path.dirname(project_path) or ".", exist_ok=True)
    with open(project_path, "w", encoding="utf-8") as fh:
        json.dump(project.to_dict(), fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    write_dat_text(full, updated_text)

    return load_project_view_for_model(dat_relpath)


def _join_dat_lines(lines: List[str]) -> str:
    text = "\n".join(lines)
    if lines and lines[-1] != "":
        text += "\n"
    return text


def _sync_project_seismic_dlod_lines(lines: List[str], project: ProjectDefinition, dat_path: str) -> List[str]:
    if not project.load_conditions.floor_loads:
        return lines
    input_text = _join_dat_lines(lines)
    validate_dat_text(input_text)
    mdl = parse_input(input_text.splitlines())
    mdl.filepath = dat_path
    try:
        result = compute_seismic_distribution(mdl, project)
    except ValueError:
        return lines
    dloads = generate_dlod_records(result)
    if not dloads:
        return lines
    return sync_seismic_dlod_lines(lines, dloads)


def build_project_view(
    project: ProjectDefinition,
    project_rel: str,
    dat_relpath: str,
) -> Dict[str, Any]:
    seismic = project.load_conditions.seismic
    ci_eff = effective_seismic_ci(seismic) if (seismic.ci > 0 and seismic.rt is not None) else None

    sections: List[Dict[str, Any]] = []

    sections.append({
        "id": "model",
        "title": "モデル",
        "rows": [
            {"label": "解析ファイル (.dat)", "value": project.dat_path},
            {"label": "サイドカー", "value": project_rel},
            {"label": "スキーマ版", "value": str(project.schema)},
        ],
    })

    b = project.building
    designer_rows = [
        {"label": "建築名称", "value": _display(b.name)},
        {"label": "所在地", "value": _display(b.location)},
        {"label": "用途", "value": _display(b.use)},
        {"label": "構造", "value": _display(b.structure)},
        {"label": "計算ルート", "value": _display(b.calculation_route)},
    ]
    d = b.designer
    if any([d.name, d.qualification, d.license_number, d.contact]):
        designer_rows.extend([
            {"label": "設計者", "value": _display(d.name)},
            {"label": "資格", "value": _display(d.qualification)},
            {"label": "登録番号", "value": _display(d.license_number)},
            {"label": "連絡先", "value": _display(d.contact)},
        ])
    sections.append({"id": "building", "title": "建築情報", "rows": designer_rows})

    x_grids = [g for g in project.grids if g.direction == "x"]
    y_grids = [g for g in project.grids if g.direction == "y"]
    sections.append({
        "id": "grids",
        "title": "通り芯",
        "tables": [
            {
                "title": "X 方向",
                "columns": ["名称", "座標 m"],
                "rows": [[g.name, _num(g.coordinate)] for g in x_grids] or [["—", "—"]],
            },
            {
                "title": "Y 方向",
                "columns": ["名称", "座標 m"],
                "rows": [[g.name, _num(g.coordinate)] for g in y_grids] or [["—", "—"]],
            },
        ],
    })

    sections.append({
        "id": "stories",
        "title": "階",
        "tables": [{
            "title": "階情報",
            "columns": ["階", "床レベル m", "階高 m"],
            "rows": [
                [s.name, _num(s.elevation), _num(s.height)]
                for s in project.stories
            ] or [["—", "—", "—"]],
        }],
    })

    sections.append({
        "id": "member_classes",
        "title": "部材クラス",
        "tables": [{
            "title": "分類",
            "columns": ["名称", "種別", "階", "要素 ID 数", "用途"],
            "rows": [
                [
                    c.name,
                    _MEMBER_KIND_LABELS.get(c.kind, c.kind),
                    _display(c.story),
                    str(len(c.element_ids)),
                    _display(c.use),
                ]
                for c in project.member_classes
            ] or [["—", "—", "—", "—", "—"]],
        }],
    })

    seismic_rows = [
        {
            "label": "Ci (入力)",
            "value": _num(seismic.ci) if seismic.ci > 0 else "未設定",
            "hint": "Z×C0 相当の基底剪断係数（Rt 除く）",
        },
        {
            "label": "Rt (振動特性係数)",
            "value": _num(seismic.rt) if seismic.rt is not None else "自動",
            "hint": "未入力時は T/Tc から自動算定（既定Rt={0}は使わない）".format(DEFAULT_SEISMIC_RT),
        },
        {
            "label": "設計用1次固有周期 T",
            "value": _num(seismic.design_period_s) if seismic.design_period_s is not None else "自動",
            "hint": "未入力時は T=(0.02+0.01α)h",
        },
        {
            "label": "建物高さ h",
            "value": (_num(seismic.height_m) + " m") if seismic.height_m is not None else "自動",
        },
        {
            "label": "鋼構造高さ比 α",
            "value": _num(seismic.steel_ratio_alpha),
        },
        {
            "label": "地盤係数 Tc",
            "value": _num(seismic.tc) if seismic.tc is not None else _num(DEFAULT_SEISMIC_TC),
        },
        {
            "label": "Ci (有効 = Ci×Rt)",
            "value": _num(ci_eff) if (ci_eff is not None and ci_eff > 0) else ("自動算定" if seismic.ci > 0 else "—"),
            "hint": "V = Ci(有効) × ΣWi に使用",
        },
        {
            "label": "基礎・土台レベル",
            "value": _display(seismic.base_level) if seismic.base_level else (
                _num(seismic.base_elevation) + " m" if seismic.base_elevation is not None else "—"
            ),
            "hint": "このレベルの質量は原則 DLOD へ自動出力しない",
        },
        {
            "label": "基礎レベル質量の扱い",
            "value": seismic.base_mass_policy,
        },
    ]
    if seismic.dead_load_lc is not None:
        seismic_rows.append({
            "label": "DL 荷重ケース (override)",
            "value": str(seismic.dead_load_lc),
        })
    if seismic.live_load_lc is not None:
        seismic_rows.append({
            "label": "LL 荷重ケース (override)",
            "value": str(seismic.live_load_lc),
        })
    if seismic.live_load_factor:
        seismic_rows.append({
            "label": "活荷重係数",
            "value": _num(seismic.live_load_factor),
        })
    if seismic.directions:
        dir_table = {
            "title": "地震方向 (legacy override)",
            "columns": ["名称", "軸", "LC", "符号"],
            "rows": [
                [d.name, d.axis.upper(), str(d.load_case), "+" if d.sign >= 0 else "-"]
                for d in seismic.directions
            ],
        }
    else:
        dir_table = None
    if seismic.weight_load_cases:
        weight_lc_table = {
            "title": "地震重量LC",
            "columns": ["LC", "名称", "係数", "用途"],
            "rows": [
                [str(c.load_case), _display(c.name), _num(c.factor), c.role]
                for c in seismic.weight_load_cases
            ],
        }
    else:
        weight_lc_table = None

    load_section: Dict[str, Any] = {
        "id": "load_conditions",
        "title": "荷重条件",
        "rows": seismic_rows,
    }
    tables = []
    if weight_lc_table:
        tables.append(weight_lc_table)
    if dir_table:
        tables.append(dir_table)
    tables.append({
        "title": "ダイアフラム ↔ 階",
        "columns": ["DIAP ID", "階"],
        "rows": [
            [str(d.diaphragm_id), d.story]
            for d in project.load_conditions.diaphragms
        ] or [["—", "—"]],
    })
    tables.append({
        "title": "床荷重 (Project 管理 / DLOD TYPE 4)",
        "columns": ["階", "DIAP ID", "用途", "LC", "名称", "kN/m2"],
        "rows": [
            [
                _display(f.story),
                str(f.diaphragm_id),
                f.role,
                str(f.load_case),
                _display(f.name),
                _num(f.pressure_kN_m2),
            ]
            for f in project.load_conditions.floor_loads
        ] or [["—", "—", "—", "—", "—", "—"]],
    })
    load_section["tables"] = tables
    sections.append(load_section)

    wood = project.design_checks.wood
    if wood.enabled or wood.load_cases or wood.deflection_limit_ratio or wood.materials:
        wood_tables = [{
            "title": "許容応力度 (N/mm²)",
            "columns": ["曲げ", "せん断", "圧縮", "引張"],
            "rows": [[
                _num(wood.allowable_stresses.bending),
                _num(wood.allowable_stresses.shear),
                _num(wood.allowable_stresses.compression),
                _num(wood.allowable_stresses.tension),
            ]],
        }]
        if wood.materials:
            wood_tables = [{
                "title": "基準強度 (N/mm²)",
                "columns": ["材料", "Fc", "Ft", "Fb", "Fs", "Fcv"],
                "rows": [
                    [m.name, _num(m.compression), _num(m.tension), _num(m.bending), _num(m.shear), _num(m.bearing)]
                    for m in wood.materials
                ],
            }]
        sections.append({
            "id": "design_checks",
            "title": "設計検討 (木造)",
            "rows": [
                {"label": "有効", "value": "はい" if wood.enabled else "いいえ"},
                {"label": "検定方式", "value": "許容応力度計算" if wood.materials else "簡易法"},
                {"label": "荷重ケース", "value": ", ".join(str(lc) for lc in wood.load_cases) or "—"},
                {"label": "たわみ限界 (L/×)", "value": _num(wood.deflection_limit_ratio) if wood.deflection_limit_ratio else "—"},
            ],
            "tables": wood_tables,
        })

    r = project.report
    sections.append({
        "id": "report",
        "title": "帳票",
        "rows": [
            {"label": "タイトル", "value": _display(r.title)},
            {"label": "モード", "value": _REPORT_MODE_LABELS.get(r.mode, r.mode)},
            {"label": "言語", "value": _display(r.language)},
            {"label": "形式", "value": r.format.upper()},
            {"label": "手入力項目を含む", "value": "はい" if r.include_manual_items else "いいえ"},
            {"label": "警告を含む", "value": "はい" if r.include_warnings else "いいえ"},
        ],
    })

    return {
        "found": True,
        "dat_path": dat_relpath,
        "project_path": project_rel,
        "title": (b.name or "プロジェクト設定") + " — project.json",
        "sections": sections,
        "edit": build_project_edit_form(project),
        "raw": project.to_dict(),
    }


def _display(value: str) -> str:
    text = str(value or "").strip()
    return text if text else "—"


def _num(value: float) -> str:
    if value is None:
        return "—"
    if abs(value - round(value)) < 1.0e-9:
        return str(int(round(value)))
    return "{0:g}".format(float(value))
