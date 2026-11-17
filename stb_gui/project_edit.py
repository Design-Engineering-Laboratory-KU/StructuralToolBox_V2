"""Editable project.json form schema for the GUI."""

from __future__ import annotations

from typing import Any, Dict, List

from stb_project.schema import (
    ALLOWED_BASE_MASS_POLICIES,
    ALLOWED_FLOOR_LOAD_ROLES,
    ALLOWED_LOAD_COMBINATION_DURATIONS,
    ALLOWED_MASS_ROLES,
    ALLOWED_MEMBER_KINDS,
    ALLOWED_REPORT_FORMATS,
    ALLOWED_REPORT_MODES,
    ALLOWED_ROUGHNESS_CATEGORIES,
    ALLOWED_SEISMIC_WEIGHT_ROLES,
    ALLOWED_WIND_DIAPHRAGM_INPUT_MODES,
    ALLOWED_WIND_DIRECTIONS,
    ALLOWED_WIND_FACES,
    ALLOWED_WIND_PRESSURE_MODES,
    ALLOWED_WIND_SURFACE_ROLES,
    DEFAULT_SEISMIC_RT,
    DEFAULT_SEISMIC_STEEL_RATIO_ALPHA,
    DEFAULT_SEISMIC_TC,
)
from stb_project import ProjectDefinition, effective_seismic_ci
from stb_project.wall_quantity_settings import (
    ALLOWED_BRACE_LAYOUTS,
    ALLOWED_BRACE_SECTIONS,
    ALLOWED_INSULATION_MODES,
    ALLOWED_QUASI_WALL_MATERIALS,
    ALLOWED_QUASI_WALL_TYPES,
    ALLOWED_SEISMIC_WEIGHT_METHODS,
    ALLOWED_SOLAR_MODES,
    ALLOWED_WALL_DIRECTIONS,
    ALLOWED_WALL_KINDS,
    ALLOWED_WALL_QUANTITY_STANDARDS,
    EXTERIOR_WALL_LABELS_JA,
    ROOF_LABELS_JA,
)


def build_project_edit_form(project: ProjectDefinition) -> Dict[str, Any]:
    seismic = project.load_conditions.seismic
    load_combinations = project.load_conditions.load_combinations
    ci_eff = effective_seismic_ci(seismic) if (seismic.ci > 0 and seismic.rt is not None) else None
    wind = project.load_conditions.wind
    wood = project.design_checks.wood
    b = project.building
    d = b.designer
    r = project.report

    sections: List[Dict[str, Any]] = [
        {
            "id": "model",
            "title": "モデル",
            "fields": [
                {"path": "model.dat", "label": "解析ファイル (.dat)", "type": "text", "value": project.dat_path},
                {"path": "schema", "label": "スキーマ版", "type": "number", "value": project.schema},
            ],
        },
        {
            "id": "building",
            "title": "建築情報",
            "fields": [
                {"path": "building.name", "label": "建築名称", "type": "text", "value": b.name},
                {"path": "building.location", "label": "所在地", "type": "text", "value": b.location},
                {"path": "building.use", "label": "用途", "type": "text", "value": b.use},
                {"path": "building.structure", "label": "構造", "type": "text", "value": b.structure},
                {"path": "building.calculation_route", "label": "計算ルート", "type": "text", "value": b.calculation_route},
                {"path": "building.designer.name", "label": "設計者", "type": "text", "value": d.name},
                {"path": "building.designer.qualification", "label": "資格", "type": "text", "value": d.qualification},
                {"path": "building.designer.license_number", "label": "登録番号", "type": "text", "value": d.license_number},
                {"path": "building.designer.contact", "label": "連絡先", "type": "text", "value": d.contact},
            ],
        },
        {
            "id": "grids",
            "title": "通り芯",
            "table": {
                "path": "grids",
                "label": "通り芯一覧",
                "columns": [
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "direction", "label": "方向", "type": "select", "options": ["x", "y"]},
                    {"path": "coordinate", "label": "座標 m", "type": "number"},
                ],
                "rows": [
                    {"name": g.name, "direction": g.direction, "coordinate": g.coordinate}
                    for g in project.grids
                ],
            },
        },
        {
            "id": "stories",
            "title": "階",
            "table": {
                "path": "stories",
                "label": "階情報",
                "columns": [
                    {"path": "name", "label": "階", "type": "text"},
                    {"path": "elevation", "label": "床レベル m", "type": "number"},
                    {"path": "height", "label": "階高 m", "type": "number"},
                ],
                "rows": [
                    {"name": s.name, "elevation": s.elevation, "height": s.height}
                    for s in project.stories
                ],
            },
        },
        {
            "id": "member_classes",
            "title": "部材クラス",
            "table": {
                "path": "member_classes",
                "label": "部材クラス",
                "columns": [
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "kind", "label": "種別", "type": "select", "options": list(ALLOWED_MEMBER_KINDS)},
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "element_ids", "label": "要素 ID (カンマ区切り)", "type": "csv_int"},
                    {"path": "use", "label": "用途", "type": "text"},
                    {"path": "notes", "label": "メモ", "type": "text"},
                ],
                "rows": [
                    {
                        "name": c.name,
                        "kind": c.kind,
                        "story": c.story,
                        "element_ids": c.element_ids,
                        "use": c.use,
                        "notes": c.notes,
                    }
                    for c in project.member_classes
                ],
            },
        },
        {
            "id": "load_conditions",
            "title": "荷重条件",
            "fields": [
                {
                    "path": "load_conditions.seismic.ci",
                    "label": "Ci (入力)",
                    "type": "number",
                    "value": seismic.ci if seismic.ci > 0 else "",
                    "hint": "Z×C0 相当（Rt 除く）",
                },
                {
                    "path": "load_conditions.seismic.rt",
                    "label": "Rt (振動特性係数)",
                    "type": "number",
                    "value": seismic.rt if seismic.rt is not None else "",
                    "hint": "未入力なら T/Tc から自動算定",
                },
                {
                    "path": "load_conditions.seismic.design_period_s",
                    "label": "設計用1次固有周期 T (sec)",
                    "type": "number",
                    "value": seismic.design_period_s if seismic.design_period_s is not None else "",
                    "hint": "未入力なら T=(0.02+0.01α)h",
                },
                {
                    "path": "load_conditions.seismic.height_m",
                    "label": "建物高さ h (m)",
                    "type": "number",
                    "value": seismic.height_m if seismic.height_m is not None else "",
                    "hint": "未入力なら階情報から算定",
                },
                {
                    "path": "load_conditions.seismic.steel_ratio_alpha",
                    "label": "鋼構造高さ比 α",
                    "type": "number",
                    "value": seismic.steel_ratio_alpha,
                    "hint": "0〜1。省略時 {0}".format(DEFAULT_SEISMIC_STEEL_RATIO_ALPHA),
                },
                {
                    "path": "load_conditions.seismic.tc",
                    "label": "地盤係数 Tc",
                    "type": "number",
                    "value": seismic.tc,
                    "hint": "省略時 {0}（第2種地盤）".format(DEFAULT_SEISMIC_TC),
                },
                {
                    "path": "load_conditions.seismic.base_level",
                    "label": "基礎・土台レベル (階)",
                    "type": "text",
                    "value": seismic.base_level or "",
                    "hint": "地震載荷階として扱わない床レベル",
                },
                {
                    "path": "load_conditions.seismic.base_elevation",
                    "label": "基礎レベル標高 m",
                    "type": "number",
                    "value": seismic.base_elevation if seismic.base_elevation is not None else "",
                    "hint": "base_level 未指定時の代替",
                },
                {
                    "path": "load_conditions.seismic.base_mass_policy",
                    "label": "基礎レベル質量の扱い",
                    "type": "select",
                    "options": list(ALLOWED_BASE_MASS_POLICIES),
                    "value": seismic.base_mass_policy,
                },
                {
                    "path": "load_conditions.seismic.dead_load_lc",
                    "label": "DL 荷重ケース (legacy override)",
                    "type": "optional_int",
                    "value": seismic.dead_load_lc,
                },
                {
                    "path": "load_conditions.seismic.live_load_lc",
                    "label": "LL 荷重ケース (legacy override)",
                    "type": "optional_int",
                    "value": seismic.live_load_lc,
                },
                {
                    "path": "load_conditions.seismic.live_load_factor",
                    "label": "活荷重係数",
                    "type": "number",
                    "value": seismic.live_load_factor,
                },
            ],
            "readonly": [
                {
                    "label": "Ci (有効 = Ci×Rt)",
                    "value": ci_eff if (ci_eff is not None and ci_eff > 0) else None,
                    "hint": "Rt未入力時は自動算定（表示は loads seismic 実行時）",
                },
            ],
            "table": {
                "path": "load_conditions.diaphragms",
                "label": "ダイアフラム ↔ 階",
                "columns": [
                    {"path": "id", "label": "DIAP ID", "type": "number"},
                    {"path": "story", "label": "階", "type": "text"},
                ],
                "rows": [
                    {"id": d.diaphragm_id, "story": d.story}
                    for d in project.load_conditions.diaphragms
                ],
            },
        },
        {
            "id": "floor_loads",
            "title": "床荷重",
            "table": {
                "path": "load_conditions.floor_loads",
                "label": "Project 管理の床積載荷重（.dat へ DLOD TYPE 4 として同期）",
                "columns": [
                    {"path": "diaphragm_id", "label": "DIAP ID", "type": "number"},
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "role", "label": "用途", "type": "select", "options": list(ALLOWED_FLOOR_LOAD_ROLES)},
                    {"path": "load_case", "label": "LC", "type": "number"},
                    {"path": "name", "label": "LNME 名称", "type": "text"},
                    {"path": "pressure_kN_m2", "label": "荷重 kN/m2", "type": "number"},
                ],
                "rows": [
                    {
                        "story": f.story,
                        "diaphragm_id": f.diaphragm_id,
                        "role": f.role,
                        "load_case": f.load_case,
                        "name": f.name,
                        "pressure_kN_m2": f.pressure_kN_m2,
                    }
                    for f in project.load_conditions.floor_loads
                ],
            },
        },
        {
            "id": "seismic_weight_load_cases",
            "title": "地震重量LC",
            "table": {
                "path": "load_conditions.seismic.weight_load_cases",
                "label": "地震重量に用いる荷重ケース",
                "columns": [
                    {"path": "load_case", "label": "LC", "type": "number"},
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "factor", "label": "係数", "type": "number"},
                    {"path": "role", "label": "用途", "type": "select", "options": list(ALLOWED_SEISMIC_WEIGHT_ROLES)},
                ],
                "rows": [
                    {
                        "name": c.name,
                        "load_case": c.load_case,
                        "factor": c.factor,
                        "role": c.role,
                    }
                    for c in seismic.weight_load_cases
                ],
            },
        },
        {
            "id": "seismic_directions",
            "title": "地震方向",
            "table": {
                "path": "load_conditions.seismic.directions",
                "label": "地震方向 ↔ 荷重ケース",
                "columns": [
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "axis", "label": "軸", "type": "select", "options": ["x", "y"]},
                    {"path": "load_case", "label": "LC", "type": "number"},
                    {"path": "sign", "label": "符号 (+1/-1)", "type": "number"},
                ],
                "rows": [
                    {
                        "name": d.name,
                        "axis": d.axis,
                        "load_case": d.load_case,
                        "sign": d.sign,
                    }
                    for d in seismic.directions
                ],
            },
        },
        {
            "id": "seismic_masses",
            "title": "地震質量",
            "table": {
                "path": "load_conditions.seismic_masses",
                "label": "地震質量 ↔ DLOD 出力先",
                "columns": [
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "mass_role", "label": "役割", "type": "select", "options": list(ALLOWED_MASS_ROLES)},
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "weight", "label": "重量 kN (空欄=LC集計)", "type": "number"},
                    {"path": "include_in_total_seismic_weight", "label": "ΣWiに含む", "type": "bool"},
                    {"path": "include_in_alpha_denominator", "label": "αi分母に含む", "type": "bool"},
                    {"path": "generate_diaphragm_load", "label": "DLOD出力", "type": "bool"},
                    {"path": "application_level", "label": "適用レベル", "type": "text"},
                    {"path": "application_diaphragm", "label": "適用DIAP", "type": "optional_int"},
                ],
                "rows": [
                    {
                        "name": m.name,
                        "mass_role": m.mass_role,
                        "story": m.story or "",
                        "weight": m.weight if m.weight is not None else "",
                        "include_in_total_seismic_weight": m.include_in_total_seismic_weight,
                        "include_in_alpha_denominator": m.include_in_alpha_denominator,
                        "generate_diaphragm_load": m.generate_diaphragm_load,
                        "application_level": m.application_level or "",
                        "application_diaphragm": (
                            m.application_diaphragm if m.application_diaphragm is not None else ""
                        ),
                    }
                    for m in project.load_conditions.seismic_masses
                ],
            },
        },
        {
            "id": "design_checks",
            "title": "設計検討 (木造)",
            "fields": [
                {"path": "design_checks.wood.enabled", "label": "有効", "type": "bool", "value": wood.enabled},
                {
                    "path": "design_checks.wood.load_cases",
                    "label": "荷重ケース (カンマ区切り)",
                    "type": "csv_int",
                    "value": list(wood.load_cases),
                },
                {
                    "path": "design_checks.wood.deflection_limit_ratio",
                    "label": "たわみ限界 (L/×)",
                    "type": "number",
                    "value": wood.deflection_limit_ratio,
                },
                {
                    "path": "design_checks.wood.allowable_stresses.bending",
                    "label": "許容曲げ N/mm²",
                    "type": "number",
                    "value": wood.allowable_stresses.bending,
                },
                {
                    "path": "design_checks.wood.allowable_stresses.shear",
                    "label": "許容せん断 N/mm²",
                    "type": "number",
                    "value": wood.allowable_stresses.shear,
                },
                {
                    "path": "design_checks.wood.allowable_stresses.compression",
                    "label": "許容圧縮 N/mm²",
                    "type": "number",
                    "value": wood.allowable_stresses.compression,
                },
                {
                    "path": "design_checks.wood.allowable_stresses.tension",
                    "label": "許容引張 N/mm²",
                    "type": "number",
                    "value": wood.allowable_stresses.tension,
                },
            ],
        },
        {
            "id": "load_combinations",
            "title": "荷重組合せ",
            "table": {
                "path": "load_conditions.load_combinations",
                "label": "荷重組合せ",
                "columns": [
                    {"path": "load_case", "label": "LC", "type": "number"},
                    {"path": "name", "label": "名称", "type": "text"},
                    {
                        "path": "duration",
                        "label": "区分",
                        "type": "select",
                        "options": list(ALLOWED_LOAD_COMBINATION_DURATIONS),
                        "option_labels": {
                            "LONG_TERM": "長期",
                            "SHORT_TERM": "短期",
                        },
                    },
                    {"path": "factors", "label": "係数 (カンマ区切り)", "type": "csv_number"},
                    {"path": "load_cases", "label": "元LC (カンマ区切り)", "type": "csv_int"},
                ],
                "rows": [
                    {
                        "load_case": c.load_case,
                        "name": c.name,
                        "duration": c.duration,
                        "factors": list(c.factors),
                        "load_cases": list(c.load_cases),
                    }
                    for c in load_combinations
                ],
            },
        },
        {
            "id": "wind",
            "title": "風荷重 (全体解析)",
            "table": {
                "path": "load_conditions.wind.cases",
                "label": "風荷重ケース",
                "columns": [
                    {"path": "id", "label": "Case ID", "type": "number"},
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "load_case", "label": "LC", "type": "number"},
                    {"path": "direction", "label": "荷重作用方向", "type": "select", "options": list(ALLOWED_WIND_DIRECTIONS)},
                    {"path": "V0", "label": "V0 m/s", "type": "number"},
                    {"path": "roughness_category", "label": "粗度", "type": "select", "options": list(ALLOWED_ROUGHNESS_CATEGORIES)},
                    {"path": "Gf", "label": "Gf", "type": "number"},
                    {"path": "pressure_mode", "label": "pressure_mode", "type": "select", "options": list(ALLOWED_WIND_PRESSURE_MODES)},
                    {"path": "use_Kz", "label": "use_Kz", "type": "bool"},
                    {"path": "Cf_default", "label": "Cf_default", "type": "number"},
                    {"path": "diaphragm_input_mode", "label": "入力方式", "type": "select", "options": list(ALLOWED_WIND_DIAPHRAGM_INPUT_MODES)},
                ],
                "rows": [
                    {
                        "id": c.case_id,
                        "name": c.name,
                        "load_case": c.load_case,
                        "direction": c.direction,
                        "V0": c.v0,
                        "roughness_category": c.roughness_category,
                        "Gf": c.gf if c.gf is not None else "",
                        "pressure_mode": c.pressure_mode,
                        "use_Kz": c.use_kz,
                        "Cf_default": c.cf_default,
                        "diaphragm_input_mode": c.diaphragm_input_mode,
                    }
                    for c in wind.cases
                ],
            },
        },
        {
            "id": "wind_surfaces",
            "title": "風受圧面",
            "table": {
                "path": "load_conditions.wind.surfaces",
                "label": "受圧面一覧",
                "columns": [
                    {"path": "id", "label": "Surface ID", "type": "number"},
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "wind_case_id", "label": "Case ID", "type": "number"},
                    {"path": "surface_role", "label": "面種別", "type": "select", "options": list(ALLOWED_WIND_SURFACE_ROLES)},
                    {"path": "face_direction", "label": "面位置", "type": "select", "options": list(ALLOWED_WIND_FACES)},
                    {"path": "z_bottom", "label": "Z下 m", "type": "number"},
                    {"path": "z_top", "label": "Z上 m", "type": "number"},
                    {"path": "width", "label": "幅 m", "type": "number"},
                    {"path": "Cf", "label": "Cf", "type": "number"},
                    {"path": "force_eccentricity_m", "label": "偏心e m", "type": "number"},
                ],
                "rows": [
                    {
                        "id": s.surface_id,
                        "name": s.name,
                        "wind_case_id": s.wind_case_id,
                        "surface_role": s.surface_role,
                        "face_direction": s.face_direction,
                        "z_bottom": s.z_bottom,
                        "z_top": s.z_top,
                        "width": s.width,
                        "Cf": s.cf if s.cf is not None else "",
                        "force_eccentricity_m": s.force_eccentricity_m if s.force_eccentricity_m is not None else "",
                    }
                    for s in wind.surfaces
                ],
            },
        },
        {
            "id": "report",
            "title": "帳票",
            "fields": [
                {"path": "report.title", "label": "タイトル", "type": "text", "value": r.title},
                {"path": "report.mode", "label": "モード", "type": "select", "options": list(ALLOWED_REPORT_MODES), "value": r.mode},
                {"path": "report.language", "label": "言語", "type": "text", "value": r.language},
                {"path": "report.format", "label": "形式", "type": "select", "options": list(ALLOWED_REPORT_FORMATS), "value": r.format},
                {"path": "report.include_manual_items", "label": "手入力項目を含む", "type": "bool", "value": r.include_manual_items},
                {"path": "report.include_warnings", "label": "警告を含む", "type": "bool", "value": r.include_warnings},
            ],
        },
    ]

    raw_wall_quantity = project.to_dict().get("wall_quantity")
    if raw_wall_quantity is not None:
        sections[-1:-1] = _build_wall_quantity_sections(raw_wall_quantity)

    return {"sections": sections}


def _build_wall_quantity_sections(wq: Dict[str, Any]) -> List[Dict[str, Any]]:
    seismic = wq.get("seismic", {})
    wind = wq.get("wind", {})
    solar = seismic.get("solar", {})
    ceiling = seismic.get("ceiling_insulation", {})
    wall_insulation = seismic.get("wall_insulation", {})
    column_size = wq.get("column_size", {})

    def options_with_blank(values):
        return [""] + list(values)

    return [
        {
            "id": "wall_quantity",
            "title": "壁量計算",
            "fields": [
                {"path": "wall_quantity.enabled", "label": "有効", "type": "bool", "value": wq.get("enabled", True)},
                {
                    "path": "wall_quantity.standard",
                    "label": "基準",
                    "type": "select",
                    "options": list(ALLOWED_WALL_QUANTITY_STANDARDS),
                    "value": wq.get("standard", "2025"),
                },
                {
                    "path": "wall_quantity.seismic.method",
                    "label": "地震重量の算定方法",
                    "type": "select",
                    "options": list(ALLOWED_SEISMIC_WEIGHT_METHODS),
                    "option_labels": {"spec": "仕様から算定", "direct": "階重量を直接入力"},
                    "value": seismic.get("method", "spec"),
                },
                {"path": "wall_quantity.seismic.c0", "label": "標準せん断力係数 C0", "type": "number", "value": seismic.get("c0", 0.2)},
                {
                    "path": "wall_quantity.seismic.building_height_m",
                    "label": "建物高さ m",
                    "type": "optional_number",
                    "value": seismic.get("building_height_m"),
                },
                {
                    "path": "wall_quantity.seismic.single_story_lw_cm_m2",
                    "label": "平屋部分 Lw cm/m²",
                    "type": "optional_number",
                    "value": seismic.get("single_story_lw_cm_m2"),
                },
                {
                    "path": "wall_quantity.seismic.roof",
                    "label": "屋根仕様",
                    "type": "select",
                    "options": options_with_blank(ROOF_LABELS_JA.keys()),
                    "option_labels": ROOF_LABELS_JA,
                    "value": seismic.get("roof", ""),
                },
                {
                    "path": "wall_quantity.seismic.exterior_wall",
                    "label": "外壁仕様",
                    "type": "select",
                    "options": options_with_blank(EXTERIOR_WALL_LABELS_JA.keys()),
                    "option_labels": EXTERIOR_WALL_LABELS_JA,
                    "value": seismic.get("exterior_wall", ""),
                },
                {
                    "path": "wall_quantity.seismic.solar.mode",
                    "label": "太陽光設備",
                    "type": "select",
                    "options": list(ALLOWED_SOLAR_MODES),
                    "value": solar.get("mode", "none"),
                },
                {
                    "path": "wall_quantity.seismic.solar.mass_kg",
                    "label": "太陽光設備質量 kg",
                    "type": "number",
                    "value": solar.get("mass_kg", 0.0),
                },
                {
                    "path": "wall_quantity.seismic.ceiling_insulation.mode",
                    "label": "天井断熱",
                    "type": "select",
                    "options": list(ALLOWED_INSULATION_MODES),
                    "value": ceiling.get("mode", "default"),
                },
                {
                    "path": "wall_quantity.seismic.ceiling_insulation.layers",
                    "label": "天井断熱層 (JSON)",
                    "type": "json",
                    "value": ceiling.get("layers", []),
                },
                {
                    "path": "wall_quantity.seismic.wall_insulation.mode",
                    "label": "壁断熱",
                    "type": "select",
                    "options": list(ALLOWED_INSULATION_MODES),
                    "value": wall_insulation.get("mode", "default"),
                },
                {
                    "path": "wall_quantity.seismic.wall_insulation.layers",
                    "label": "壁断熱層 (JSON)",
                    "type": "json",
                    "value": wall_insulation.get("layers", []),
                },
                {
                    "path": "wall_quantity.wind.coefficient_cm_m2",
                    "label": "風圧用係数 cm/m²",
                    "type": "number",
                    "value": wind.get("coefficient_cm_m2", 50.0),
                },
                {
                    "path": "wall_quantity.quasi_over_half_verified",
                    "label": "準耐力壁過半確認済み",
                    "type": "bool",
                    "value": wq.get("quasi_over_half_verified", False),
                },
                {
                    "path": "wall_quantity.column_size.enabled",
                    "label": "柱の小径検定",
                    "type": "bool",
                    "value": column_size.get("enabled", True),
                },
                {
                    "path": "wall_quantity.column_size.check_model_columns",
                    "label": "モデル柱を検定",
                    "type": "bool",
                    "value": column_size.get("check_model_columns", True),
                },
            ],
        },
        {
            "id": "wall_quantity_stories",
            "title": "壁量計算 — 階",
            "table": {
                "path": "wall_quantity.stories",
                "label": "階別入力",
                "columns": [
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "floor_area_m2", "label": "床面積 m²", "type": "number"},
                    {"path": "height_m", "label": "階高 m", "type": "optional_number"},
                    {"path": "weight_kN", "label": "階重量 kN", "type": "optional_number"},
                    {"path": "wind_area_x_m2", "label": "見付面積X m²", "type": "number"},
                    {"path": "wind_area_y_m2", "label": "見付面積Y m²", "type": "number"},
                    {"path": "plan_polygons", "label": "平面形状 (JSON)", "type": "json"},
                ],
                "rows": list(wq.get("stories", [])),
            },
        },
        {
            "id": "wall_quantity_walls",
            "title": "壁量計算 — 耐力壁",
            "table": {
                "path": "wall_quantity.walls",
                "label": "WWLL別設定",
                "columns": [
                    {"path": "wwll_id", "label": "WWLL ID", "type": "optional_int"},
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "kind", "label": "種別", "type": "select", "options": list(ALLOWED_WALL_KINDS)},
                    {"path": "multiplier", "label": "倍率", "type": "optional_number"},
                    {"path": "exclude", "label": "除外", "type": "bool"},
                    {"path": "brace_section", "label": "筋かい断面", "type": "select", "options": options_with_blank(ALLOWED_BRACE_SECTIONS)},
                    {"path": "brace_layout", "label": "筋かい配置", "type": "select", "options": options_with_blank(ALLOWED_BRACE_LAYOUTS)},
                    {"path": "notes", "label": "メモ", "type": "text"},
                ],
                "rows": list(wq.get("walls", [])),
            },
        },
        {
            "id": "wall_quantity_columns",
            "title": "壁量計算 — 柱",
            "table": {
                "path": "wall_quantity.columns",
                "label": "N値計算の柱上書き",
                "columns": [
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "x", "label": "X m", "type": "number"},
                    {"path": "y", "label": "Y m", "type": "number"},
                    {"path": "corner", "label": "出隅", "type": "bool"},
                    {"path": "name", "label": "名称", "type": "text"},
                ],
                "rows": list(wq.get("columns", [])),
            },
        },
        {
            "id": "wall_quantity_quasi_walls",
            "title": "壁量計算 — 準耐力壁",
            "table": {
                "path": "wall_quantity.quasi_walls",
                "label": "準耐力壁・垂れ壁・腰壁",
                "columns": [
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "direction", "label": "方向", "type": "select", "options": list(ALLOWED_WALL_DIRECTIONS)},
                    {"path": "length_m", "label": "長さ m", "type": "number"},
                    {"path": "type", "label": "種別", "type": "select", "options": list(ALLOWED_QUASI_WALL_TYPES)},
                    {"path": "material", "label": "材料", "type": "select", "options": list(ALLOWED_QUASI_WALL_MATERIALS)},
                    {"path": "base_multiplier", "label": "基準倍率", "type": "optional_number"},
                    {"path": "material_height_m", "label": "面材高さ m", "type": "number"},
                    {"path": "clear_height_m", "label": "内法高さ m", "type": "number"},
                    {"path": "x", "label": "X m", "type": "optional_number"},
                    {"path": "y", "label": "Y m", "type": "optional_number"},
                    {"path": "notes", "label": "メモ", "type": "text"},
                ],
                "rows": list(wq.get("quasi_walls", [])),
            },
        },
        {
            "id": "wall_quantity_column_stories",
            "title": "壁量計算 — 柱の小径",
            "table": {
                "path": "wall_quantity.column_size.stories",
                "label": "階別の柱材条件",
                "columns": [
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "jas", "label": "JAS区分", "type": "text"},
                    {"path": "species", "label": "樹種", "type": "text"},
                    {"path": "grade", "label": "等級", "type": "text"},
                    {"path": "fc_n_mm2", "label": "Fc N/mm²", "type": "optional_number"},
                    {"path": "label", "label": "表示名", "type": "text"},
                    {"path": "length_mm", "label": "柱長 mm", "type": "optional_number"},
                    {"path": "outer_load_kN_m2", "label": "外周荷重 kN/m²", "type": "optional_number"},
                    {"path": "inner_load_kN_m2", "label": "内部荷重 kN/m²", "type": "optional_number"},
                ],
                "rows": list(column_size.get("stories", [])),
            },
        },
        {
            "id": "wall_quantity_tributary_checks",
            "title": "壁量計算 — 柱負担面積",
            "table": {
                "path": "wall_quantity.column_size.tributary_checks",
                "label": "柱の負担面積検定",
                "columns": [
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "location", "label": "位置", "type": "select", "options": ["outer", "inner"]},
                    {"path": "b_mm", "label": "幅 b mm", "type": "number"},
                    {"path": "d_mm", "label": "せい d mm", "type": "number"},
                    {"path": "area_m2", "label": "負担面積 m²", "type": "number"},
                ],
                "rows": list(column_size.get("tributary_checks", [])),
            },
        },
    ]
