"""木造壁量計算書 (確認申請用ドラフト) — Markdown / HTML.

The report is assembled once as a list of blocks (headings, paragraphs, tables,
SVG figures) and rendered to Markdown or to a print-ready HTML page (A4; use the
browser's print to PDF). Table layouts follow the 確認申請・審査マニュアル 第3版
(表3-11 準耐力壁等の割合, 表3-12 壁量判定, 表3-13 四分割法判定).
"""

from dataclasses import dataclass
from datetime import datetime
import html
import os
import re
from typing import List, Optional, Tuple

from stb_checks.wall_quantity import build_wall_quantity_summary
from stb_reports.wall_quantity_figures import render_n_value_plan_svg, render_wall_plan_svg


REFERENCES = (
    "建築基準法施行令第46条第4項、昭和56年建設省告示第1100号（令和6年国土交通省告示第447号等による改正）",
    "建築基準法施行令第47条第1項、平成12年建設省告示第1460号（柱頭・柱脚の接合方法）",
    "建築基準法施行令第43条第1項・第6項、平成12年建設省告示第1349号（柱の小径）",
    "国土交通省「木造建築物における省エネ化等による建築物の重量化に対応するための必要な壁量等の基準に関する補足資料」（令和6年7月8日）",
    "「改正建築基準法 2階建ての木造一戸建て住宅（軸組構法）等の確認申請・審査マニュアル」第3版（2024年11月）",
    "（公財）日本住宅・木材技術センター「壁量等の基準（令和7年施行）に対応した表計算ツール（在来軸組工法用）」ver1.2",
)

MANUAL_NOTES = (
    "本計算書は Structural Toolbox による自動集計の下書きです。入力条件（床面積・見付面積・仕様・壁倍率・柱位置）と判定結果を設計者が確認してください。",
    "柱の小径で「柱に壁が取り付く方向は検討不要」とする扱いは、解説の公表前のため本計算書では考慮していません（全方向で検討）。",
    "接合金物の品番・性能（Zマーク金物又は同等認定品）は図面で別途指定してください。",
)

DIRECTION_LABEL = {"x": "X方向", "y": "Y方向"}
KIND_LABEL = {
    "brace": "筋かい", "panel": "面材", "other": "耐力壁",
    "quasi": "準耐力壁", "hanging_waist": "垂れ壁・腰壁",
}
LOCATION_LABEL = {"outer": "外周部", "inner": "内部"}


@dataclass(frozen=True)
class WallQuantityReport:
    markdown: str
    html: str
    warnings: Tuple[str, ...]
    status: str
    summary: object


# ---------------------------------------------------------------------------
# Public API


def build_wall_quantity_report(mdl, project, generated_at: Optional[datetime] = None,
                               program_version: str = "") -> WallQuantityReport:
    summary = build_wall_quantity_summary(mdl, project)
    blocks = _blocks(mdl, project, summary, generated_at or datetime.now(), program_version)
    title = _title(project)
    return WallQuantityReport(
        markdown=render_markdown(blocks),
        html=render_html(blocks, title),
        warnings=summary.warnings,
        status=summary.overall_status,
        summary=summary,
    )


def write_wall_quantity_report(output_path, mdl, project, output_format=None,
                               generated_at: Optional[datetime] = None, program_version: str = ""):
    report = build_wall_quantity_report(mdl, project, generated_at=generated_at, program_version=program_version)
    fmt = output_format or ("markdown" if str(output_path).lower().endswith(".md") else "html")
    if fmt == "markdown":
        text = report.markdown
    elif fmt == "html":
        text = report.html
    else:
        raise ValueError("Unsupported report format: " + str(fmt))
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(output_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return report


# ---------------------------------------------------------------------------
# Blocks


class _B:
    """Block constructors: ("h", level, text), ("p", text), ("ul", items), ("table", head, rows, opts), ("svg", svg, caption)."""

    @staticmethod
    def h(level, text):
        return ("h", level, text)

    @staticmethod
    def p(text, cls=""):
        return ("p", text, cls)

    @staticmethod
    def ul(items):
        return ("ul", tuple(items))

    @staticmethod
    def table(head, rows, cls=""):
        return ("table", tuple(head), tuple(tuple(r) for r in rows), cls)

    @staticmethod
    def svg(svg, caption):
        return ("svg", svg, caption)

    @staticmethod
    def page_break():
        return ("break",)


def _title(project):
    name = project.building.name.strip()
    return (name + " 壁量計算書").strip() if name else "壁量計算書"


def _blocks(mdl, project, s, generated_at, program_version):
    b = []
    b.append(_B.h(1, _title(project)))
    b.append(_B.p("木造軸組構法（2025年4月施行の壁量基準）による壁量・壁配置のバランス・柱頭柱脚の接合方法・柱の小径の計算書です。", "lead"))
    b.append(_B.table(("項目", "内容"), [
        ("物件名", _v(project.building.name)),
        ("所在地", _v(project.building.location)),
        ("用途", _v(project.building.use)),
        ("構造", _v(project.building.structure) if project.building.structure else "木造軸組構法"),
        ("階数", "地上{0}階".format(len(s.seismic.stories))),
        ("延べ面積", "{0:.2f} m²".format(sum(d.floor_area_m2 for d in s.seismic.stories))),
        ("建物の高さ h", "{0:.3f} m".format(s.seismic.building_height_m)),
        ("設計者", " ".join(v for v in (project.building.designer.qualification, project.building.designer.name) if v) or "-"),
        ("登録番号", _v(project.building.designer.license_number)),
        ("作成日", generated_at.strftime("%Y-%m-%d")),
        ("使用プログラム", "Structural Toolbox" + ((" " + program_version) if program_version else "")),
        ("解析入力", _v(os.path.basename(getattr(mdl, "filepath", "") or ""))),
    ], "kv"))
    b.append(_B.h(2, "総合判定"))
    b.append(_B.table(("検討項目", "判定"), _overall_rows(s), "summary"))

    b.append(_B.h(2, "1. 準拠基準・適用範囲"))
    b.append(_B.ul(REFERENCES))
    b.append(_B.table(("項目", "値", "適用範囲", "判定"),
                      [(r["item"], r["value"], r["limit"], r["status"]) for r in s.applicability]))

    b.append(_B.page_break())
    b.extend(_seismic_blocks(project, s))
    b.extend(_wind_blocks(s))
    b.append(_B.page_break())
    b.extend(_existing_wall_blocks(project, s))
    b.extend(_wall_judgement_blocks(s))
    if s.balance is not None:
        b.append(_B.page_break())
        b.extend(_balance_blocks(project, s))
    if s.n_values is not None:
        b.append(_B.page_break())
        b.extend(_n_value_blocks(project, s))
    if s.column_size is not None:
        b.append(_B.page_break())
        b.extend(_column_blocks(s))
    b.append(_B.h(2, "注意事項・警告"))
    b.append(_B.ul(MANUAL_NOTES))
    if s.warnings:
        b.append(_B.h(3, "計算時の警告"))
        b.append(_B.ul(s.warnings))
    return b


def _overall_rows(s):
    rows = [("壁量（地震力・風圧力）", s.status)]
    rows.append(("壁配置のバランス（四分割法）", s.balance.status if s.balance is not None else "未検討"))
    rows.append(("柱頭・柱脚の接合方法（N値計算法）",
                 (s.n_values.status if s.n_values.status == "NG" else "仕様選定済")
                 if s.n_values is not None else "未検討"))
    rows.append(("柱の小径", s.column_size.status if s.column_size is not None else "未検討"))
    rows.append(("総合", s.overall_status))
    return rows


def _seismic_blocks(project, s):
    seis = s.seismic
    b = [_B.h(2, "2. 地震力に対する必要壁量")]
    b.append(_B.p("床面積当たりの必要壁量 Lw = (Ai・C0・Σwi) / (0.0196・Afi) [cm/m²]、"
                  "Ai = 1 + (1/√αi − αi)・2T/(1+3T)、T = 0.03h。Lw は小数点以下を切り上げる。"))
    if seis.method == "spec":
        b.append(_B.p("Σwi は（公財）日本住宅・木材技術センター 表計算ツール（在来軸組工法用 ver1.2）と同じ方法で、"
                      "仕様ごとの単位荷重から算定する（外壁荷重は 6m×16.5m の基準平面・開口率9%で床面積当たりに換算）。"))
        b.append(_B.h(3, "2.1 単位荷重"))
        b.append(_B.table(("部位", "荷重 (N/m²)", "備考"),
                          [(i.label, _n(i.value_N_m2, 1), i.basis) for i in seis.load_items]))
    else:
        b.append(_B.p("Σwi は各階が地震時に負担する固定荷重と積載荷重の和として直接入力した値による。"))
    b.append(_B.h(3, "2.2 床面積当たりの必要壁量"))
    rows = []
    for d in reversed(seis.stories):
        rows.append((d.story + "階", _n(d.floor_area_m2, 2), _n(d.height_m, 3), _n(d.weight_kN, 2),
                     _n(d.alpha, 3), _n(d.ai, 3), _n(d.lw_raw_cm_m2, 2), _n(d.lw_cm_m2, 0),
                     _n(d.required_cm, 2)))
    b.append(_B.table(("階", "床面積 Af (m²)", "階高 (m)", "Σwi (kN)", "αi", "Ai", "Lw 計算値", "Lw (cm/m²)",
                       "必要壁量 (cm)"), rows))
    b.append(_B.p("C0 = {0:g}、建物の高さ h = {1:.3f} m、T = {2:.4f} 秒".format(
        seis.c0, seis.building_height_m, seis.period_s), "note"))
    if seis.single_story_lw_cm_m2 is not None:
        b.append(_B.p("四分割法で用いる平屋の床面積に乗ずる数値: {0:g} cm/m²".format(seis.single_story_lw_cm_m2), "note"))
    return b


def _wind_blocks(s):
    b = [_B.h(2, "3. 風圧力に対する必要壁量")]
    b.append(_B.p("必要壁量 = 見付面積 × 見付面積に乗ずる数値。見付面積は各階の床面からの高さ1.35m以下を除いた部分。"))
    rows = []
    for c in sorted(s.checks, key=lambda c: (-_story_index(s, c.story), c.direction)):
        rows.append((c.story + "階", DIRECTION_LABEL[c.direction], _n(c.wind_area_m2, 2),
                     _n(c.wind_coefficient_cm_m2, 0), _n(c.wind_required_cm, 2)))
    b.append(_B.table(("階", "方向", "見付面積 (m²)", "係数 (cm/m²)", "必要壁量 (cm)"), rows))
    b.append(_B.p("X方向の見付面積は X方向の耐力壁が負担する風（X方向に吹く風）を受ける立面（YZ面）の面積。", "note"))
    return b


def _existing_wall_blocks(project, s):
    b = [_B.h(2, "4. 存在壁量")]
    b.append(_B.p("存在壁量 = Σ(壁倍率 × 壁の長さ)。耐力壁の壁倍率は同一軸組で合計7.0を上限とし、"
                  "階高3.2m超の筋かいは αh = 3.5Ld/H0 (≤1.0) を乗じる。"))
    for d in reversed(s.seismic.stories):
        for direction in ("x", "y"):
            walls = [w for w in s.walls if w.story == d.story and w.direction == direction]
            if not walls:
                continue
            b.append(_B.h(3, "{0}階 {1}".format(d.story, DIRECTION_LABEL[direction])))
            rows = []
            for w in sorted(walls, key=lambda w: (w.source, _pos(w), w.ref)):
                rows.append((
                    ("WWLL " if w.source == "WWLL" else "") + w.ref,
                    w.name if w.name != w.ref else "-",
                    KIND_LABEL.get(w.kind, w.kind),
                    _coord_text(w),
                    _n(w.length_m, 3),
                    _n(w.multiplier_input, 2),
                    _n(w.alpha_h, 3) if w.alpha_h != 1.0 else "-",
                    _n(w.multiplier, 2) + (" *" if w.capped else ""),
                    _n(w.amount_cm, 2),
                ))
            total_b = sum(w.amount_cm for w in walls if w.source == "WWLL")
            total_q = sum(w.amount_cm for w in walls if w.source == "QUASI")
            rows.append(("計", "", "", "", "", "", "", "耐力壁", _n(total_b, 2)))
            if total_q:
                rows.append(("", "", "", "", "", "", "", "準耐力壁等", _n(total_q, 2)))
            b.append(_B.table(("記号", "名称", "種類", "位置 (m)", "長さ (m)", "倍率", "αh", "採用倍率", "壁量 (cm)"), rows))
    if any(w.capped for w in s.walls):
        b.append(_B.p("* 同一軸組の壁倍率の合計が7.0を超えるため7.0に調整した値。", "note"))
    b.append(_B.h(3, "準耐力壁等の必要壁量に対する割合（表3-11）"))
    rows = []
    for c in _ordered_checks(s):
        ratio = c.quasi_raw_cm / c.required_cm if c.required_cm > 0 else 0.0
        rows.append((c.story + "階 " + DIRECTION_LABEL[c.direction], _n(c.required_cm, 2), _n(c.quasi_raw_cm, 2),
                     _n(ratio, 2), "OK" if not c.quasi_exceeds_half else "1/2超"))
    b.append(_B.table(("階・方向", "必要壁量 A (cm)", "準耐力壁等 B (cm)", "B/A", "判定 (≤1/2)"), rows))
    return b


def _wall_judgement_blocks(s):
    b = [_B.h(2, "5. 壁量判定（表3-12）")]
    rows = []
    for c in _ordered_checks(s):
        rows.append((
            c.story + "階 " + DIRECTION_LABEL[c.direction],
            _n(c.floor_area_m2, 2), _n(c.lw_cm_m2, 0), _n(c.seismic_required_cm, 2),
            _n(c.wind_area_m2, 2), _n(c.wind_coefficient_cm_m2, 0), _n(c.wind_required_cm, 2),
            _n(c.required_cm, 2) + ("（地震）" if c.governing == "seismic" else "（風）"),
            _n(c.bearing_cm, 2), _n(c.quasi_counted_cm, 2), _n(c.existing_cm, 2),
            _n(c.ratio, 2), c.status,
        ))
    b.append(_B.table((
        "階・方向", "床面積 (m²)", "係数 (cm/m²)", "地震力 (cm)", "見付面積 (m²)", "係数 (cm/m²)", "風圧力 (cm)",
        "必要壁量 (cm)", "耐力壁 (cm)", "準耐力壁等 (cm)", "存在壁量 (cm)", "充足率", "判定",
    ), rows, "wide"))
    b.append(_B.p("各階・各方向で 必要壁量（地震力・風圧力の大きい方）≤ 存在壁量 であることを確認する。"
                  "準耐力壁等は必要壁量の1/2まで算入する。", "note"))
    return b


def _balance_blocks(project, s):
    bal = s.balance
    b = [_B.h(2, "6. 壁配置のバランス（四分割法・表3-13）")]
    b.append(_B.p("各階・各方向について平面を1/4に区切った側端部分の 壁量充足率 = 存在壁量 / 必要壁量 を求め、"
                  "両側とも1.0を超えるか、壁率比（小さい側/大きい側）が0.5以上であることを確認する。"
                  "1階の側端部分は、上に2階がかかる場合は2階建ての1階、かからない場合は平屋の数値を用いる。"))
    if bal.includes_quasi_walls:
        b.append(_B.p("準耐力壁等が必要壁量の1/2を超えるため、準耐力壁等を含めて検討する。", "note"))
    else:
        b.append(_B.p("準耐力壁等は算入しない（耐力壁のみで検討）。", "note"))
    rows = []
    for c in sorted(bal.checks, key=lambda c: (-_story_index(s, c.story), c.direction)):
        for i, st in enumerate(c.strips):
            rows.append((
                c.story + "階" if i == 0 else "",
                DIRECTION_LABEL[c.direction] if i == 0 else "",
                st.side,
                _n(st.area_m2, 2),
                _n(st.lw_cm_m2, 0) + ("（平屋）" if st.lw_basis == "平屋" else ""),
                _n(st.required_cm, 2),
                _n(st.existing_cm, 2),
                _ratio(st.fill_ratio),
                "OK" if st.fill_ratio > 1.0 else "NG",
                _ratio(c.wall_ratio) if i == 0 else "",
                (c.status + ("（実態倍率でも確認）" if c.actual_checked else "")) if i == 0 else "",
            ))
    b.append(_B.table(("階", "方向", "位置", "有効面積 (m²)", "壁量係数 (cm/m²)", "必要壁量 (cm)", "存在壁量 (cm)",
                       "充足率", "充足率判定 (>1.0)", "壁率比", "判定"), rows, "wide"))
    if any(c.actual_checked for c in bal.checks):
        rows = []
        for c in bal.checks:
            rows.append((c.story + "階 " + DIRECTION_LABEL[c.direction],
                         _ratio(c.strips[0].fill_ratio_actual), _ratio(c.strips[1].fill_ratio_actual),
                         _ratio(c.wall_ratio_actual), c.status_actual))
        b.append(_B.h(3, "実態倍率（7.0上限を適用しない倍率）による確認"))
        b.append(_B.table(("階・方向", "充足率（一方）", "充足率（他方）", "壁率比", "判定"), rows))
    for d in reversed(s.seismic.stories):
        svg = render_wall_plan_svg(project, s, d.story)
        if svg:
            b.append(_B.svg(svg, "{0}階 耐力壁配置図・四分割線".format(d.story)))
    return b


def _n_value_blocks(project, s):
    nv = s.n_values
    b = [_B.h(2, "7. 柱頭・柱脚の接合方法（N値計算法）")]
    b.append(_B.p("平屋・2階建ての2階・2階のない1階部分: N = A1×B1×H1/2.7 − L。"
                  "2階建ての1階で上に2階がある部分: N = A1×B1×H1/2.7 + A2×B2×H2/2.7 − L。"
                  "H は横架材の上端の相互間の垂直距離（3.2m以下は2.7）。"
                  "A は柱の両側の壁倍率の差（筋かいは表3-14の補正値を加算）、B は出隅0.8・その他0.5、"
                  "L は平屋等で出隅0.4・その他0.6、2階建ての1階で出隅1.0・その他1.6。X・Y両方向で求め大きい方を採用する。"))
    if not nv.includes_quasi_walls:
        b.append(_B.p("準耐力壁等は壁倍率0として計算する（壁倍率1.5超の準耐力壁等を除く）。", "note"))
    for d in reversed(s.seismic.stories):
        cols = [c for c in nv.columns if c.story == d.story]
        if not cols:
            continue
        b.append(_B.h(3, "{0}階".format(d.story)))
        rows = []
        for c in cols:
            dx = _dir(c, "x")
            dy = _dir(c, "y")
            rows.append((
                c.name or "-",
                "({0}, {1})".format(_n(c.x, 3), _n(c.y, 3)),
                "出隅" if c.corner else "-",
                _dir_text(dx), _dir_text(dy),
                _n(c.n, 2) + "（" + DIRECTION_LABEL[c.governing_direction][0] + "）",
                "（" + c.joint + "）" if c.joint != "要検討" else "要検討",
                _n(c.required_kN, 1),
            ))
        head = ("柱", "位置 (m)", "出隅", "X方向 A1/A2/L → N", "Y方向 A1/A2/L → N", "採用N", "接合部仕様", "必要耐力 (kN)")
        b.append(_B.table(head, rows, "wide"))
        svg = render_n_value_plan_svg(project, s, d.story)
        if svg:
            b.append(_B.svg(svg, "{0}階 柱頭・柱脚の接合部仕様".format(d.story)))
    b.append(_B.table(("記号", "N値", "必要耐力 (kN)", "接合方法の例"), [
        ("（い）", "0.0以下", "0.0", "短ほぞ差し・かすがい打ち"),
        ("（ろ）", "0.65以下", "3.4", "長ほぞ差し込み栓打ち・L字型かど金物"),
        ("（は）", "1.0以下", "5.1", "T字型かど金物・山形プレート"),
        ("（に）", "1.4以下", "7.5", "羽子板ボルト・短ざく金物"),
        ("（ほ）", "1.6以下", "8.5", "羽子板ボルト＋スクリュー釘"),
        ("（へ）", "1.8以下", "10.0", "引き寄せ金物 10kN"),
        ("（と）", "2.8以下", "15.0", "引き寄せ金物 15kN"),
        ("（ち）", "3.7以下", "20.0", "引き寄せ金物 20kN"),
        ("（り）", "4.7以下", "25.0", "引き寄せ金物 25kN"),
        ("（ぬ）", "5.6以下", "30.0", "引き寄せ金物 15kN×2"),
    ]))
    return b


def _column_blocks(s):
    cs = s.column_size
    b = [_B.h(2, "8. 柱の小径")]
    b.append(_B.p("柱の必要小径 de は告示の座屈の算定式（表計算ツールの方法2-1・2-2）により、"
                  "外周部の柱の負担荷重 Wd と荷重負担面積 5m²、横架材相互間の垂直距離 l から求める。"
                  "有効細長比は150以下とする。Wd は固定荷重と積載荷重（柱算定用 1300N/m²）の和で、積雪荷重は含まない。"))
    rows = []
    for r in reversed(cs.stories):
        rows.append((r.story + "階", _n(r.length_mm, 0), _n(r.outer_load_kN_m2, 3), _n(r.inner_load_kN_m2, 3),
                     r.material_label, _n(r.fc_n_mm2, 1), r.required_ratio_text, _n(r.required_mm, 0),
                     _n(r.default_required_mm, 0)))
    b.append(_B.table(("階", "l (mm)", "Wd 外周部 (kN/m²)", "Wd 内部 (kN/m²)", "柱材", "Fc (N/mm²)", "de/l",
                       "必要小径 de (mm)", "参考: すぎ無等級 (mm)"), rows, "wide"))
    if cs.model_columns:
        b.append(_B.h(3, "使用する柱の確認"))
        rows = []
        for c in cs.model_columns:
            rows.append((c.story + "階", c.section, "{0:g}×{1:g}".format(c.b_mm, c.d_mm), len(c.element_ids),
                         _n(c.required_mm, 0), _n(c.slenderness, 1), c.status))
        b.append(_B.table(("階", "断面", "寸法 (mm)", "本数", "必要小径 (mm)", "有効細長比", "判定"), rows))
    b.append(_B.h(3, "柱の負担可能面積（方法2-3）"))
    rows = []
    for r in reversed(cs.stories):
        for location in ("outer", "inner"):
            vals = [a for a in r.allowable_areas if a["location"] == location]
            rows.append((r.story + "階", LOCATION_LABEL[location],
                         *[_area(a["allowable_m2"]) for a in sorted(vals, key=lambda a: a["size_mm"])]))
    b.append(_B.table(("階", "柱の位置", "105角 (m²)", "120角 (m²)"), rows))
    if cs.tributary_checks:
        rows = [(t.name or "-", t.story + "階", LOCATION_LABEL[t.location], "{0:g}×{1:g}".format(t.b_mm, t.d_mm),
                 _n(t.area_m2, 2), _area(t.allowable_m2), t.status) for t in cs.tributary_checks]
        b.append(_B.table(("柱", "階", "位置", "寸法 (mm)", "負担面積 (m²)", "負担可能面積 (m²)", "判定"), rows))
    return b


# ---------------------------------------------------------------------------
# Rendering


def render_markdown(blocks) -> str:
    out: List[str] = []
    for blk in blocks:
        kind = blk[0]
        if kind == "h":
            out.extend(["#" * blk[1] + " " + blk[2], ""])
        elif kind == "p":
            out.extend([blk[1], ""])
        elif kind == "ul":
            out.extend(["- " + item for item in blk[1]])
            out.append("")
        elif kind == "table":
            head, rows = blk[1], blk[2]
            out.append("| " + " | ".join(_md(h) for h in head) + " |")
            out.append("|" + "|".join("---" for _ in head) + "|")
            for row in rows:
                out.append("| " + " | ".join(_md(c) for c in row) + " |")
            out.append("")
        elif kind == "svg":
            out.extend(["*図: " + blk[2] + "（HTML版に掲載）*", ""])
    return "\n".join(out).rstrip() + "\n"


def render_html(blocks, title) -> str:
    body: List[str] = []
    for blk in blocks:
        kind = blk[0]
        if kind == "h":
            body.append("<h{0}>{1}</h{0}>".format(blk[1], html.escape(blk[2])))
        elif kind == "p":
            cls = ' class="{0}"'.format(blk[2]) if blk[2] else ""
            body.append("<p{0}>{1}</p>".format(cls, html.escape(blk[1])))
        elif kind == "ul":
            body.append("<ul>" + "".join("<li>{0}</li>".format(html.escape(i)) for i in blk[1]) + "</ul>")
        elif kind == "table":
            head, rows, cls = blk[1], blk[2], blk[3]
            parts = ['<div class="table-wrap"><table{0}>'.format(' class="{0}"'.format(cls) if cls else "")]
            parts.append("<thead><tr>" + "".join("<th>{0}</th>".format(html.escape(h)) for h in head) + "</tr></thead>")
            parts.append("<tbody>")
            for row in rows:
                parts.append("<tr>" + "".join(_td(c) for c in row) + "</tr>")
            parts.append("</tbody></table></div>")
            body.append("".join(parts))
        elif kind == "svg":
            body.append('<figure>{0}<figcaption>{1}</figcaption></figure>'.format(blk[1], html.escape(blk[2])))
        elif kind == "break":
            body.append('<div class="page-break"></div>')
    return _HTML_TEMPLATE.format(title=html.escape(title), body="\n".join(body))


def _td(value):
    text = str(value)
    cls = ""
    if text in ("OK", "仕様選定済"):
        cls = ' class="ok"'
    elif text.startswith("NG") or text in ("要検討", "1/2超"):
        cls = ' class="ng"'
    elif not _NUMERIC_CELL.match(text):
        cls = ' class="t"'
    return "<td{0}>{1}</td>".format(cls, html.escape(text))


_NUMERIC_CELL = re.compile(r"^[-+]?[\d,]*\.?\d+(\s*[*（(].*)?$|^∞$|^-$")


_HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --ink:#1f2328; --muted:#59636e; --line:#c9d1d9; --head:#f3f5f7; --ok:#1a7f37; --ng:#cf222e; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #e9ecef; color: var(--ink);
  font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", "Noto Sans JP", sans-serif; font-size: 10.5pt; line-height: 1.55; }}
.sheet {{ background: #fff; max-width: 210mm; margin: 16px auto; padding: 16mm 14mm; box-shadow: 0 1px 4px rgba(0,0,0,.15); }}
.toolbar {{ max-width: 210mm; margin: 16px auto 0; text-align: right; }}
.toolbar button {{ font: inherit; padding: 6px 14px; border: 1px solid var(--line); border-radius: 6px; background: #fff; cursor: pointer; }}
h1 {{ font-size: 18pt; margin: 0 0 6px; border-bottom: 2px solid var(--ink); padding-bottom: 6px; }}
h2 {{ font-size: 13pt; margin: 22px 0 8px; padding-left: 8px; border-left: 4px solid var(--ink); }}
h3 {{ font-size: 11pt; margin: 14px 0 6px; }}
p {{ margin: 6px 0; }} p.lead {{ color: var(--muted); }} p.note {{ color: var(--muted); font-size: 9pt; }}
ul {{ margin: 6px 0; padding-left: 20px; }}
.table-wrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 9pt; }}
th, td {{ border: 1px solid var(--line); padding: 3px 6px; vertical-align: top; }}
th {{ background: var(--head); font-weight: 600; text-align: center; }}
td {{ text-align: right; font-variant-numeric: tabular-nums; }}
td:first-child, td.t {{ text-align: left; }}
table.kv td, table.summary td {{ text-align: left; }} table.kv td:first-child {{ width: 30%; background: #fafbfc; }}
table.wide {{ font-size: 8pt; }}
td.ok {{ color: var(--ok); font-weight: 600; text-align: center; }} td.ng {{ color: var(--ng); font-weight: 700; text-align: center; }}
figure {{ margin: 10px 0 16px; text-align: center; break-inside: avoid; }}
figure svg {{ max-width: 100%; height: auto; }}
figcaption {{ font-size: 9pt; color: var(--muted); margin-top: 4px; }}
@page {{ size: A4; margin: 12mm; }}
@media print {{
  body {{ background: #fff; }} .toolbar {{ display: none; }}
  .sheet {{ box-shadow: none; margin: 0; padding: 0; max-width: none; }}
  .page-break {{ display: none; }} .page-break + * {{ break-before: page; }}
  tr, figure {{ break-inside: avoid; }} .table-wrap {{ overflow: visible; }}
}}
</style>
</head>
<body>
<div class="toolbar"><button type="button" onclick="window.print()">印刷 / PDF保存</button></div>
<main class="sheet">
{body}
</main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Formatting helpers


def _v(value):
    return value if value not in (None, "") else "-"


def _n(value, places):
    if value is None:
        return "-"
    if value == float("inf"):
        return "∞"
    return ("{0:,." + str(places) + "f}").format(value)


def _ratio(value):
    return "∞" if value == float("inf") else "{0:.2f}".format(value)


def _area(value):
    return "細長比超過" if value is None else "{0:.1f}".format(value)


def _md(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def _story_index(s, story):
    for i, d in enumerate(s.seismic.stories):
        if d.story == story:
            return i
    return 0


def _ordered_checks(s):
    return sorted(s.checks, key=lambda c: (-_story_index(s, c.story), c.direction))


def _pos(w):
    if w.x_center is None:
        return (1e9, 1e9)
    return (w.y_center, w.x_center) if w.direction == "x" else (w.x_center, w.y_center)


def _coord_text(w):
    if w.end_a is None:
        return "-"
    if w.direction == "x":
        return "y={0}, x={1}〜{2}".format(_n(w.end_a[1], 3), _n(min(w.end_a[0], w.end_b[0]), 3),
                                         _n(max(w.end_a[0], w.end_b[0]), 3))
    return "x={0}, y={1}〜{2}".format(_n(w.end_a[0], 3), _n(min(w.end_a[1], w.end_b[1]), 3),
                                     _n(max(w.end_a[1], w.end_b[1]), 3))


def _dir(c, direction):
    for d in c.directions:
        if d.direction == direction:
            return d
    return None


def _dir_text(d):
    if d is None:
        return "-"
    a1 = _n(d.a1, 2) + ("(補正{0:+.1f})".format(d.brace_correction) if d.brace_correction else "")
    if d.b2:
        return "{0}/{1}/{2} → {3}".format(a1, _n(d.a2, 2), _n(d.l, 1), _n(d.n, 2))
    return "{0}/-/{1} → {2}".format(a1, _n(d.l, 1), _n(d.n, 2))
