from dataclasses import dataclass
import html
import math
import os
import platform
from datetime import datetime
from typing import Optional, Tuple

from stb_checks import build_wood_check_summary
from stb_practice import build_practice_summary, build_structural_indices
from stb_project import ProjectDefinition


MANUAL_CONFIRMATION_ITEMS = (
    "風圧力の詳細算定、受圧面積、風力係数は設計者が別途確認する。",
    "基礎・地盤、地耐力、転倒の検討は本MVP帳票の対象外として別途確認する。",
    "接合金物、柱脚・柱頭金物、筋かい端部の詳細検定は別途確認する。",
    "確認申請用の略伏図・略軸組図・各種図面は本帳票を下書きとして別途整える。",
)


@dataclass(frozen=True)
class ReportDraft:
    markdown: str
    html: str
    warnings: Tuple[str, ...]


def build_confirmation_draft(
    mdl,
    project: ProjectDefinition,
    analysis_text: str = "",
    generated_at: Optional[datetime] = None,
    program_version: str = "",
):
    markdown = render_confirmation_draft_markdown(
        mdl,
        project,
        analysis_text=analysis_text,
        generated_at=generated_at,
        program_version=program_version,
    )
    html_text = render_confirmation_draft_html(markdown, title=_report_title(project))
    warnings = _collect_warnings(mdl, project)
    return ReportDraft(markdown=markdown, html=html_text, warnings=warnings)


def write_confirmation_draft(
    output_path,
    mdl,
    project: ProjectDefinition,
    output_format: Optional[str] = None,
    analysis_text: str = "",
    generated_at: Optional[datetime] = None,
    program_version: str = "",
):
    draft = build_confirmation_draft(
        mdl,
        project,
        analysis_text=analysis_text,
        generated_at=generated_at,
        program_version=program_version,
    )
    fmt = output_format or project.report.format
    if fmt == "markdown":
        text = draft.markdown
    elif fmt == "html":
        text = draft.html
    else:
        raise ValueError("Unsupported report format: " + str(fmt))

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir != "" and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    f = open(output_path, "w", encoding="utf-8")
    try:
        f.write(text)
    finally:
        f.close()
    return draft


def render_confirmation_draft_markdown(
    mdl,
    project: ProjectDefinition,
    analysis_text: str = "",
    generated_at: Optional[datetime] = None,
    program_version: str = "",
):
    generated_at = generated_at or datetime.now()
    practice = build_practice_summary(mdl, project)
    indices = build_structural_indices(mdl, project)
    wood = build_wood_check_summary(mdl, project) if project.design_checks.wood.enabled else None
    analysis = _analysis_summary(mdl, analysis_text)
    warnings = _collect_warnings_from_summaries(practice, wood, project, mdl=mdl, indices=indices)

    lines = []
    lines.append("# " + _report_title(project))
    lines.append("")
    lines.append("この帳票は確認申請前の検算・下書き用ドラフトです。未対応項目と手作業確認項目を含めて最終確認してください。")
    lines.append("")
    lines.extend(_table([
        ("作成日時", generated_at.strftime("%Y-%m-%d %H:%M:%S")),
        ("プログラム", "Structural Toolbox" + ((" " + program_version) if program_version else "")),
        ("実行環境", platform.platform()),
        ("解析入力", _value(getattr(mdl, "filepath", ""))),
        ("プロジェクト", _value(project.source_path)),
    ]))
    lines.append("")

    lines.append("## 1. 一般事項")
    lines.append("")
    lines.extend(_table([
        ("物件名", project.building.name),
        ("所在地", project.building.location),
        ("用途", project.building.use),
        ("構造種別", project.building.structure),
        ("計算ルート", project.building.calculation_route),
        ("設計者", project.building.designer.name),
        ("資格", project.building.designer.qualification),
        ("登録番号", project.building.designer.license_number),
        ("連絡先", project.building.designer.contact),
    ]))
    lines.append("")

    lines.append("## 2. 設計方針・使用材料")
    lines.append("")
    lines.append("- 解析方法: 3D線形静的解析")
    lines.append("- 対象範囲: 木造平屋MVPの確認申請補助計算書ドラフト")
    lines.append("- 出力方針: 中間表を優先し、未対応項目は警告または手作業確認として明示")
    wood_settings = project.design_checks.wood
    lines.append("- 木造検定: " + ("有効" if wood_settings.enabled else "無効"))
    if wood_settings.enabled and wood_settings.materials:
        lines.append("- 検定方式: 許容応力度計算（荷重継続期間・座屈を考慮）")
        lines.append("")
        lines.append("### 木材の基準強度 (N/mm2)")
        lines.append("")
        lines.extend(_dict_table(
            ("name", "compression", "tension", "bending", "shear", "bearing"),
            [
                {
                    "name": m.name,
                    "compression": m.compression,
                    "tension": m.tension,
                    "bending": m.bending,
                    "shear": m.shear,
                    "bearing": m.bearing,
                }
                for m in wood_settings.materials
            ],
            {"name": "材料", "compression": "Fc", "tension": "Ft", "bending": "Fb", "shear": "Fs", "bearing": "Fcv"},
        ))
        lines.append("")
        lines.extend(_table([
            ("検定荷重ケース", ", ".join(str(lc) for lc in wood_settings.load_cases) or "全荷重ケース"),
        ]))
    elif wood_settings.enabled:
        lines.append("- 検定方式: 簡易法（荷重継続期間・座屈は未考慮。申請用の検定には基準強度の設定が必要）")
        lines.append("")
        lines.extend(_table([
            ("曲げ許容応力度 N/mm2", _fmt(wood_settings.allowable_stresses.bending)),
            ("せん断許容応力度 N/mm2", _fmt(wood_settings.allowable_stresses.shear)),
            ("圧縮許容応力度 N/mm2", _fmt(wood_settings.allowable_stresses.compression)),
            ("引張許容応力度 N/mm2", _fmt(wood_settings.allowable_stresses.tension)),
            ("たわみ制限", "L/{0}".format(_fmt(wood_settings.deflection_limit_ratio))),
            ("検定荷重ケース", ", ".join(str(lc) for lc in wood_settings.load_cases) or "全荷重ケース"),
        ]))
    lines.append("")

    lines.append("## 3. 解析モデル概要")
    lines.append("")
    lines.extend(_table([
        ("節点数", len(mdl.nds)),
        ("部材数", len(mdl.elms)),
        ("支点数", len(mdl.cons)),
        ("荷重ケース", ", ".join(str(lc) for lc in mdl.lcs)),
    ]))
    lines.append("")
    lines.append("### 通り")
    lines.append("")
    lines.extend(_dict_table(
        ("name", "direction", "coordinate", "node_ids", "element_ids"),
        practice.tables.grids,
        {"name": "通り", "direction": "方向", "coordinate": "座標 m", "node_ids": "節点", "element_ids": "部材"},
    ))
    lines.append("")
    lines.append("### 層")
    lines.append("")
    lines.extend(_dict_table(
        ("name", "elevation", "height", "node_ids", "element_ids"),
        practice.tables.stories,
        {"name": "層", "elevation": "基準高さ m", "height": "高さ m", "node_ids": "節点", "element_ids": "部材"},
    ))
    lines.append("")
    lines.append("### 部材分類")
    lines.append("")
    lines.extend(_dict_table(
        ("name", "kind", "story", "use", "count", "total_length", "total_weight"),
        practice.tables.member_classes,
        {
            "name": "分類",
            "kind": "種別",
            "story": "層",
            "use": "用途",
            "count": "部材数",
            "total_length": "合計長さ m",
            "total_weight": "自重 N",
        },
    ))
    lines.append("")

    lines.extend(_render_load_condition_section(mdl, project))
    lines.append("")

    lines.append("## 5. 解析結果サマリ")
    lines.append("")
    lines.extend(_table([
        ("最大節点変位 m", _fmt(analysis["max_displacement"])),
        ("最大支点反力 kN", _fmt(analysis["max_reaction"] * 1.0e-3)),
        ("最大部材端力 kN/kNm", _fmt(analysis["max_element_force"] * 1.0e-3)),
        ("解析出力 NDSP", "あり" if "NDSP" in analysis_text else "未確認"),
        ("解析出力 REAC", "あり" if "REAC" in analysis_text else "未確認"),
        ("解析出力 EFRC", "あり" if "EFRC" in analysis_text else "未確認"),
    ]))
    lines.append("")

    lines.append("## 6. 重心・剛心・偏心率")
    lines.append("")
    if practice.center_of_mass is None:
        lines.append("- 重心: 算定不可")
    else:
        lines.append("- 重心: X={0} m, Y={1} m".format(
            _fmt(practice.center_of_mass.x),
            _fmt(practice.center_of_mass.y),
        ))
    lines.append("")
    lines.extend(_table([
        ("X方向剛心 X m", _fmt_optional(practice.center_of_rigidity_x.x)),
        ("X方向剛心 Y m", _fmt_optional(practice.center_of_rigidity_x.y)),
        ("X方向偏心距離 m", _fmt_optional(practice.eccentricity_x.eccentricity)),
        ("X方向弾力半径 m", _fmt_optional(practice.eccentricity_x.elastic_radius)),
        ("X方向偏心率", _fmt_optional(practice.eccentricity_x.eccentricity_ratio)),
        ("Y方向剛心 X m", _fmt_optional(practice.center_of_rigidity_y.x)),
        ("Y方向剛心 Y m", _fmt_optional(practice.center_of_rigidity_y.y)),
        ("Y方向偏心距離 m", _fmt_optional(practice.eccentricity_y.eccentricity)),
        ("Y方向弾力半径 m", _fmt_optional(practice.eccentricity_y.elastic_radius)),
        ("Y方向偏心率", _fmt_optional(practice.eccentricity_y.eccentricity_ratio)),
    ]))
    lines.append("")
    lines.append("### 重量集計")
    lines.append("")
    lines.extend(_dict_table(
        ("source", "element_id", "story", "x", "y", "weight"),
        practice.tables.masses,
        {"source": "根拠", "element_id": "部材", "story": "層", "x": "X m", "y": "Y m", "weight": "重量 N"},
    ))
    lines.append("")
    lines.append("### 剛性集計")
    lines.append("")
    lines.extend(_dict_table(
        ("element_id", "member_class", "story", "x", "y", "kx", "ky"),
        practice.tables.rigidities,
        {"element_id": "部材", "member_class": "分類", "story": "層", "x": "X m", "y": "Y m", "kx": "Kx", "ky": "Ky"},
    ))
    lines.append("")

    lines.append("## 7. 層間変形角・偏心率・剛性率")
    lines.append("")
    lines.append("解析後処理による構造指標です。段違い梁・中間層・混構造の詳細補正は初期実装では未考慮です。")
    lines.append("")
    lines.append("### 層間変形角（階最大）")
    lines.append("")
    lines.extend(_dict_table(
        ("story", "direction", "load_case", "element_id", "drift_m", "height_m", "drift_angle", "inverse_ratio", "status"),
        [r for r in indices.tables["story_drifts"] if r.get("is_story_max")],
        {
            "story": "階",
            "direction": "方向",
            "load_case": "LC",
            "element_id": "部材",
            "drift_m": "δ m",
            "height_m": "h m",
            "drift_angle": "δ/h",
            "inverse_ratio": "逆数",
            "status": "状態",
        },
    ))
    lines.append("")
    lines.append("### ASTIM式ベース偏心率")
    lines.append("")
    lines.extend(_dict_table(
        ("story", "xg", "yg", "xs", "ys", "ex", "ey", "re_x", "re_y", "fe_x", "fe_y", "status"),
        indices.tables["eccentricities"],
        {
            "story": "階",
            "xg": "Xg",
            "yg": "Yg",
            "xs": "Xs",
            "ys": "Ys",
            "ex": "ex",
            "ey": "ey",
            "re_x": "Rex",
            "re_y": "Rey",
            "fe_x": "FeX",
            "fe_y": "FeY",
            "status": "状態",
        },
    ))
    lines.append("")
    lines.append("### 剛性率")
    lines.append("")
    lines.extend(_dict_table(
        ("story", "direction", "load_case", "drift_m", "height_m", "drift_angle", "inverse_ratio", "mean_inverse_ratio", "rigidity_ratio", "fs", "status"),
        indices.tables["rigidity_ratios"],
        {
            "story": "階",
            "direction": "方向",
            "load_case": "LC",
            "drift_m": "δ (m)",
            "height_m": "h (m)",
            "drift_angle": "δ/h",
            "inverse_ratio": "rs",
            "mean_inverse_ratio": "r̄s",
            "rigidity_ratio": "Rs",
            "fs": "Fs",
            "status": "状態",
        },
    ))
    lines.append("")

    lines.append("## 8. 木造梁・柱・筋かいの基本検定")
    lines.append("")
    if wood is None:
        lines.append("木造検定は project.design_checks.wood.enabled が false のため未実施です。")
    else:
        lines.extend(_table([
            ("総合判定", wood.status),
            ("最大検定比", _fmt(wood.max_ratio)),
        ]))
        lines.append("")
        lines.append("### 部材分類別")
        lines.append("")
        lines.extend(_dict_table(
            ("name", "kind", "checked_count", "max_ratio", "status"),
            wood.tables.member_classes,
            {"name": "分類", "kind": "種別", "checked_count": "検定数", "max_ratio": "最大検定比", "status": "判定"},
        ))
        lines.append("")
        lines.append("### 部材別")
        lines.append("")
        lines.extend(_dict_table(
            (
                "element_id",
                "member_class",
                "kind",
                "governing_load_case",
                "axial_ratio",
                "bending_ratio",
                "shear_ratio",
                "deflection_ratio",
                "combined_ratio",
                "status",
            ),
            wood.tables.element_checks,
            {
                "element_id": "部材",
                "member_class": "分類",
                "kind": "種別",
                "governing_load_case": "支配LC",
                "axial_ratio": "軸力比",
                "bending_ratio": "曲げ比",
                "shear_ratio": "せん断比",
                "deflection_ratio": "たわみ比",
                "combined_ratio": "検定比",
                "status": "判定",
            },
        ))
        lines.append("")
        if wood.tables.standard_sections:
            lines.extend(_render_standard_wood_tables(wood))
        lines.append("### 耐力壁別")
        lines.append("")
        lines.extend(_dict_table(
            (
                "wall_id",
                "wall_name",
                "direction",
                "wall_magnification",
                "wall_length",
                "wall_height",
                "allowable_shear_capacity_Qa",
                "analysis_shear_force_Q",
                "utilization_ratio",
                "governing_load_case",
                "status",
            ),
            wood.tables.wall_checks,
            {
                "wall_id": "壁ID",
                "wall_name": "壁名",
                "direction": "方向",
                "wall_magnification": "壁倍率",
                "wall_length": "壁長 m",
                "wall_height": "壁高 m",
                "allowable_shear_capacity_Qa": "Qa kN",
                "analysis_shear_force_Q": "Q kN",
                "utilization_ratio": "検定比",
                "governing_load_case": "支配LC",
                "status": "判定",
            },
        ))
    lines.append("")

    lines.append("## 9. 照合メモ")
    lines.append("")
    lines.append("手計算・既存表計算との照合では、次の値を優先して確認してください。")
    lines.append("")
    lines.extend(_table([
        ("重心 X/Y", _point_text(practice.center_of_mass)),
        ("X方向偏心率", _fmt_optional(practice.eccentricity_x.eccentricity_ratio)),
        ("Y方向偏心率", _fmt_optional(practice.eccentricity_y.eccentricity_ratio)),
        ("木造最大検定比", _fmt(wood.max_ratio) if wood is not None else "-"),
        ("最大変位 m", _fmt(analysis["max_displacement"])),
        ("最大反力 kN", _fmt(analysis["max_reaction"] * 1.0e-3)),
    ]))
    lines.append("")

    if project.report.include_warnings:
        lines.append("## 10. 警告・注意")
        lines.append("")
        if warnings:
            for warning in warnings:
                lines.append("- " + warning)
        else:
            lines.append("- 警告はありません。")
        lines.append("")

    if project.report.include_manual_items:
        lines.append("## 11. 手作業確認項目")
        lines.append("")
        for item in MANUAL_CONFIRMATION_ITEMS:
            lines.append("- " + item)
        lines.append("")

    lines.append("## 12. 総合所見ドラフト")
    lines.append("")
    lines.append(_overall_comment(wood, warnings))
    lines.append("")
    return "\n".join(lines)


def _render_standard_wood_tables(wood):
    lines = ["### 部材の断面性能・座屈", ""]
    lines.extend(_dict_table(
        (
            "element_id",
            "section",
            "material",
            "area_e_100mm2",
            "z_y_e_1000mm3",
            "z_z_e_1000mm3",
            "radius_min_mm",
            "lk_y_mm",
            "lk_z_mm",
            "slenderness",
            "eta",
            "ck",
            "cs",
            "cb",
            "le_mm",
            "messages",
        ),
        wood.tables.standard_sections,
        {
            "element_id": "部材",
            "section": "断面",
            "material": "材料",
            "area_e_100mm2": "Ae ×100mm2",
            "z_y_e_1000mm3": "Zey ×1000mm3",
            "z_z_e_1000mm3": "Zez ×1000mm3",
            "radius_min_mm": "i mm",
            "lk_y_mm": "lky mm",
            "lk_z_mm": "lkz mm",
            "slenderness": "λ",
            "eta": "η",
            "ck": "Ck",
            "cs": "Cs",
            "cb": "Cb",
            "le_mm": "le mm",
            "messages": "メッセージ",
        },
    ))
    lines.extend(["", "### 荷重継続期間別の検定", ""])
    lines.extend(_dict_table(
        (
            "element_id",
            "duration",
            "load_case",
            "location",
            "axial_kn",
            "moment_y_knm",
            "moment_z_knm",
            "shear_kn",
            "fc",
            "ft",
            "fb_y",
            "fb_z",
            "fs",
            "sigma_n",
            "sigma_by",
            "sigma_bz",
            "tau",
            "sigma_cv",
            "stress_ratio",
            "shear_ratio",
            "bearing_ratio",
            "deflection_mm",
            "deflection_ratio",
            "ratio",
        ),
        wood.tables.standard_results,
        {
            "element_id": "部材",
            "duration": "区分",
            "load_case": "LC",
            "location": "位置",
            "axial_kn": "N kN（引張+）",
            "moment_y_knm": "My kN・m",
            "moment_z_knm": "Mz kN・m",
            "shear_kn": "Q kN",
            "fc": "fc",
            "ft": "ft",
            "fb_y": "fby",
            "fb_z": "fbz",
            "fs": "fs",
            "sigma_n": "σn",
            "sigma_by": "σby",
            "sigma_bz": "σbz",
            "tau": "τ",
            "sigma_cv": "σcv",
            "stress_ratio": "σ/f",
            "shear_ratio": "τ/fs",
            "bearing_ratio": "σcv/fcv",
            "deflection_mm": "δ mm",
            "deflection_ratio": "δ比",
            "ratio": "検定比",
        },
    ))
    lines.append("")
    return lines


def render_confirmation_draft_html(markdown_text, title="Structural Toolbox Report"):
    body = _markdown_to_html(markdown_text)
    return "\n".join([
        "<!doctype html>",
        '<html lang="ja">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>{0}</title>".format(html.escape(title)),
        "<style>",
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.6;margin:2rem;color:#1f2937;}",
        "h1,h2,h3{line-height:1.25;color:#111827;} table{border-collapse:collapse;width:100%;margin:1rem 0;}",
        "th,td{border:1px solid #d1d5db;padding:0.35rem 0.5rem;vertical-align:top;} th{background:#f3f4f6;text-align:left;}",
        "code{background:#f3f4f6;padding:0.1rem 0.25rem;border-radius:0.2rem;} .note{color:#4b5563;}",
        "</style>",
        "</head>",
        "<body>",
        body,
        "</body>",
        "</html>",
        "",
    ])


def _report_title(project):
    return project.report.title or (project.building.name + " 確認申請補助計算書ドラフト").strip()


def _collect_warnings(mdl, project):
    practice = build_practice_summary(mdl, project)
    indices = build_structural_indices(mdl, project)
    wood = build_wood_check_summary(mdl, project) if project.design_checks.wood.enabled else None
    return _collect_warnings_from_summaries(practice, wood, project, mdl=mdl, indices=indices)


def _collect_warnings_from_summaries(practice, wood, project, mdl=None, indices=None):
    warnings = list(getattr(mdl, "input_warnings", []) or []) if mdl is not None else []
    warnings.extend(practice.warnings)
    if indices is not None:
        warnings.extend(indices.warnings)
    if wood is not None:
        warnings.extend(wood.warnings)
    if project.report.mode != "practice":
        warnings.append("Report mode is {0}; confirmation draft assumes practice mode.".format(project.report.mode))
    return tuple(warnings)


def _analysis_summary(mdl, analysis_text):
    return {
        "max_displacement": _max_nodal_displacement(mdl),
        "max_reaction": _max_reaction(mdl),
        "max_element_force": _max_element_force(mdl),
        "has_text": bool(analysis_text),
    }


def _max_nodal_displacement(mdl):
    values = []
    for node in mdl.nds:
        disps = getattr(node, "disps", None)
        if disps is None:
            continue
        for i in range(disps.shape[1]):
            values.append(math.sqrt(float(disps[0, i]) ** 2 + float(disps[1, i]) ** 2 + float(disps[2, i]) ** 2))
    return max(values + [0.0])


def _max_reaction(mdl):
    values = []
    for constraint in mdl.cons:
        reacts = getattr(constraint.nd, "reacts", None)
        if reacts is None:
            continue
        for i in range(reacts.shape[0]):
            values.append(math.sqrt(float(reacts[i, 0]) ** 2 + float(reacts[i, 1]) ** 2 + float(reacts[i, 2]) ** 2))
    return max(values + [0.0])


def _render_load_condition_section(mdl, project: ProjectDefinition):
    seismic = project.load_conditions.seismic
    try:
        from stb_project import resolve_seismic_c0_z
        resolve_seismic_c0_z(seismic)
    except ValueError:
        return [
            "## 4. 荷重条件",
            "",
            "- 地震力 Ai 分布: project.load_conditions.seismic が未設定のため省略",
        ]

    from stb_loads import compute_seismic_distribution
    from stb_loads.format import render_seismic_markdown

    try:
        result = compute_seismic_distribution(mdl, project)
    except ValueError as ex:
        return [
            "## 4. 荷重条件",
            "",
            "- 地震力 Ai 分布: " + str(ex),
        ]

    lines = ["## 4. 荷重条件", ""]
    report_body = render_seismic_markdown(result, project).splitlines()
    for line in report_body[2:]:
        lines.append(line)
    return lines


def _max_element_force(mdl):
    values = []
    for element in mdl.elms:
        forces = getattr(element, "forces", None)
        if forces is None:
            continue
        for i in range(forces.shape[1]):
            values.extend(abs(float(forces[j, i])) for j in range(forces.shape[0]))
    return max(values + [0.0])


def _table(rows):
    lines = ["| 項目 | 値 |", "|---|---|"]
    for key, value in rows:
        lines.append("| {0} | {1} |".format(_md(key), _md(_value(value))))
    return lines


def _dict_table(keys, rows, labels):
    lines = ["| " + " | ".join(_md(labels.get(key, key)) for key in keys) + " |"]
    lines.append("|" + "|".join("---" for _key in keys) + "|")
    if not rows:
        lines.append("| " + " | ".join("-" for _key in keys) + " |")
        return lines
    for row in rows:
        lines.append("| " + " | ".join(_md(_format_cell(row.get(key))) for key in keys) + " |")
    return lines


def _format_cell(value):
    if isinstance(value, float):
        return _fmt(value)
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) if value else "-"
    if value is None:
        return "-"
    return value


def _fmt(value):
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(value) >= 100000.0 or (abs(value) > 0.0 and abs(value) < 0.001):
        return "{0:.3e}".format(value)
    return "{0:.3f}".format(value)


def _fmt_optional(value):
    return "-" if value is None else _fmt(value)


def _point_text(point):
    if point is None:
        return "-"
    return "X={0} m, Y={1} m".format(_fmt(point.x), _fmt(point.y))


def _value(value):
    if value is None or value == "":
        return "-"
    return value


def _md(value):
    text = str(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def _overall_comment(wood, warnings):
    if wood is not None and wood.status == "OK" and not warnings:
        return "本MVP帳票の自動集計範囲ではNG項目はありません。手作業確認項目を確認したうえで提出用計算書へ反映してください。"
    if wood is not None and wood.status == "NG":
        return "木造基本検定にNG項目があります。部材別検定表と入力条件を確認し、断面・荷重・許容応力度を見直してください。"
    return "警告または未対応項目があります。警告・手作業確認項目を確認し、必要な検算を追記してください。"


def _markdown_to_html(markdown_text):
    html_lines = []
    in_ul = False
    lines = markdown_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("|"):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            html_lines.append(_markdown_table_to_html(table_lines))
            continue
        if line.startswith("- "):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append("<li>{0}</li>".format(html.escape(line[2:])))
        else:
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            if line.startswith("# "):
                html_lines.append("<h1>{0}</h1>".format(html.escape(line[2:])))
            elif line.startswith("## "):
                html_lines.append("<h2>{0}</h2>".format(html.escape(line[3:])))
            elif line.startswith("### "):
                html_lines.append("<h3>{0}</h3>".format(html.escape(line[4:])))
            elif line.strip() == "":
                html_lines.append("")
            else:
                html_lines.append("<p>{0}</p>".format(html.escape(line)))
        i += 1
    if in_ul:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def _markdown_table_to_html(lines):
    rows = [_split_markdown_row(line) for line in lines]
    rows = [row for row in rows if not _is_separator_row(row)]
    if not rows:
        return ""
    out = ["<table>", "<thead>", "<tr>"]
    for cell in rows[0]:
        out.append("<th>{0}</th>".format(html.escape(cell)))
    out.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows[1:]:
        out.append("<tr>")
        for cell in row:
            out.append("<td>{0}</td>".format(html.escape(cell)))
        out.append("</tr>")
    out.extend(["</tbody>", "</table>"])
    return "\n".join(out)


def _split_markdown_row(line):
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip().replace("\\|", "|") for cell in text.split("|")]


def _is_separator_row(row):
    if not row:
        return False
    return all(set(cell.replace(":", "").strip()) <= set("-") for cell in row)

