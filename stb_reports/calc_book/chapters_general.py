"""§1 to §5: general matters, design policy, program use, loads, preparation."""

from stb_checks import wood_standard as ws
from stb_reports.calc_book.common import dict_table, fmt, markdown_blocks
from stb_reports.calc_book.document import Column, Heading, Table, Text, key_value_table
from stb_reports.draft import MANUAL_CONFIRMATION_ITEMS

SECTION_SHAPES = {0: "矩形", 1: "円形", 2: "I形", 3: "円形鋼管", 4: "角形鋼管"}


def _building_extent(mdl):
    xs = [n.x for n in mdl.nds]
    ys = [n.y for n in mdl.nds]
    zs = [n.z for n in mdl.nds]
    return max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)


def chapter_general(ctx, figures):
    b = ctx.project.building
    dx, dy, dz = _building_extent(ctx.mdl)
    blocks = [
        Heading(1, "§１．一般事項"),
        Heading(2, "1.1 建築物の構造設計概要"),
        key_value_table([
            ("建築物名称", b.name),
            ("建築場所", b.location),
            ("主要用途", b.use),
            ("構造種別", b.structure),
            ("計算ルート", b.calculation_route),
            ("階数", "{0}（解析モデルの層数）".format(len(ctx.project.stories)) if ctx.project.stories else None),
            ("モデルの平面寸法", "X方向 {0} m × Y方向 {1} m".format(fmt(dx), fmt(dy))),
            ("モデルの高さ", "{0} m".format(fmt(dz))),
            ("設計者", b.designer.name),
            ("資格", b.designer.qualification),
            ("登録番号", b.designer.license_number),
            ("連絡先", b.designer.contact),
        ]),
    ]
    blocks.extend(figures.plan_chapter(ctx))
    blocks.extend(figures.elevation_chapter(ctx))
    blocks.extend(_section_lists(ctx))
    return blocks


def _section_lists(ctx):
    mdl = ctx.mdl
    counts = {}
    for e in ctx.real_members():
        counts[e.sec.id] = counts.get(e.sec.id, 0) + 1
    rows = []
    for sec in mdl.secs:
        if counts.get(sec.id):
            dims = " × ".join(fmt(d * 1000.0, 0) for d in sec.dims)
            rows.append((sec.name, SECTION_SHAPES.get(sec.type, str(sec.type)), dims, sec.mat.name, str(counts[sec.id])))

    class_rows = [
        {
            "name": c["name"],
            "kind": c["kind"],
            "story": c["story"],
            "count": c["count"],
            "total_length": c["total_length"],
            "total_weight": c["total_weight"] * 1.0e-3,
        }
        for c in ctx.practice.tables.member_classes
    ]
    blocks = [
        Heading(2, "1.4 断面リスト"),
        Heading(3, "1.4.1 部材断面リスト"),
        Table(
            columns=(Column("符号"), Column("形状", 0.7), Column("寸法 (mm)", 1.2), Column("材料"), Column("部材数", 0.6)),
            rows=tuple(rows),
            width_ratio=0.8,
        ),
    ]
    if class_rows:
        blocks.append(Heading(3, "1.4.2 部材分類"))
        blocks.append(dict_table(
            ("name", "kind", "story", "count", "total_length", "total_weight"),
            class_rows,
            {"name": "分類", "kind": "種別", "story": "層", "count": "部材数", "total_length": "合計長さ (m)", "total_weight": "自重 (kN)"},
            places={"total_length": 2, "total_weight": 2},
        ))
    blocks.extend(_joint_list(ctx))
    blocks.extend(_floor_list(ctx))
    return blocks


def _joint_list(ctx):
    types = ctx.project.design_checks.wood.joint_types
    if not types:
        return []
    return [
        Heading(3, "1.4.3 接合金物リスト"),
        Table(
            columns=(
                Column("符号", 1.2),
                Column("圧縮 長期\n(kN)"), Column("圧縮 短期\n(kN)"), Column("引張 長期\n(kN)"), Column("引張 短期\n(kN)"),
                Column("曲げ 長期\n(kN・m)"), Column("曲げ 短期\n(kN・m)"), Column("せん断 長期\n(kN)"), Column("せん断 短期\n(kN)"),
            ),
            rows=tuple(
                (j.name, fmt(j.compression_long, 1), fmt(j.compression_short, 1), fmt(j.tension_long, 1), fmt(j.tension_short, 1),
                 fmt(j.moment_long, 1), fmt(j.moment_short, 1), fmt(j.shear_long, 1), fmt(j.shear_short, 1))
                for j in types
            ),
            note="積雪時の許容応力は、長期（積雪）＝長期×1.3、短期（積雪）＝短期×0.8 とする。",
            font_size=6.5,
        ),
    ]


def _floor_list(ctx):
    diaphragms = ctx.mdl.diaps
    if not diaphragms:
        return []
    types = {"RIGID": "剛床", "SEMI_RIGID": "半剛床", "FLEXIBLE": "柔床"}
    multipliers = {f.diaphragm: f.multiplier for f in ctx.project.design_checks.wood.floor_multipliers}
    return [
        Heading(3, "1.4.4 床リスト"),
        Table(
            columns=(Column("符号", 0.6), Column("名称", 1.4), Column("種別"), Column("床倍率")),
            rows=tuple(
                (str(d.id), d.name, types.get(str(d.type).upper(), str(d.type)), fmt(multipliers.get(d.id, d.timber_multiplier), 2))
                for d in diaphragms
            ),
            width_ratio=0.6,
        ),
    ]


def chapter_policy(ctx):
    wood = ctx.project.design_checks.wood
    method = "許容応力度計算（荷重継続期間・座屈を考慮）" if wood.materials else "簡易法（荷重継続期間・座屈は未考慮）"
    blocks = [
        Heading(1, "§２．設計方針と使用材料"),
        Heading(2, "2.1 構造設計方針"),
        Heading(3, "2.1.1 構造設計方針"),
        Text("架構を線材および面要素の3次元モデルに置換し、線形静的解析により応力と変形を求める。"),
        Text("許容応力度計算により、各部材に生じる応力が許容応力度以下であることを確認する。"),
        Heading(3, "2.1.2 設計上準拠した指針・規準類"),
        Text("建築基準法・同施行令および関連告示。使用する規準類は設計者が確認し、本書に追記する。"),
        Heading(2, "2.2 構造計算方針"),
        Heading(3, "2.2.1 使用プログラム"),
        key_value_table([
            ("プログラム名称", "Structural Toolbox"),
            ("バージョン", ctx.program_version),
            ("解析方法", "3次元線形静的解析"),
            ("木造部材の検定方式", method if wood.enabled else "実施しない"),
        ]),
        Heading(3, "2.2.2 計算ルート"),
        Text(ctx.project.building.calculation_route or "計算ルートは未設定。設計者が記入する。"),
        Heading(2, "2.3 使用材料・許容応力度"),
        Heading(3, "2.3.1 材料定数"),
        Table(
            columns=(Column("材料"), Column("ヤング係数\n(N/mm2)"), Column("せん断弾性係数\n(N/mm2)"), Column("単位体積重量\n(kN/m3)")),
            rows=tuple(
                (m.name, fmt(m.E * 1.0e-6, 0), fmt(m.G * 1.0e-6, 0), fmt(m.gamma * 1.0e-3, 2))
                for m in ctx.mdl.mats
                if not getattr(m, "auto_generated", False)
            ),
            width_ratio=0.8,
        ),
    ]
    if wood.materials:
        blocks.append(Heading(3, "2.3.2 木材の許容応力度"))
        blocks.append(_wood_allowable_table(wood))
    elif wood.enabled:
        blocks.append(Heading(3, "2.3.2 許容応力度（簡易法）"))
        a = wood.allowable_stresses
        blocks.append(key_value_table([
            ("曲げ (N/mm2)", fmt(a.bending)),
            ("せん断 (N/mm2)", fmt(a.shear)),
            ("圧縮 (N/mm2)", fmt(a.compression)),
            ("引張 (N/mm2)", fmt(a.tension)),
        ], width_ratio=0.5))
    return blocks


def _wood_allowable_table(wood):
    rows = []
    for m in wood.materials:
        rows.append((m.name, "基準強度", fmt(m.compression), fmt(m.tension), fmt(m.bending), fmt(m.shear), fmt(m.bearing)))
        for duration in ws.DURATION_ORDER:
            f = ws.DURATION_FACTORS[duration]
            rows.append((
                "", ws.DURATION_LABELS[duration],
                fmt(m.compression * f), fmt(m.tension * f), fmt(m.bending * f), fmt(m.shear * f), fmt(m.bearing * f),
            ))
    return Table(
        columns=(Column("材料", 1.4), Column("区分"), Column("圧縮"), Column("引張"), Column("曲げ"), Column("せん断"), Column("めり込み")),
        rows=tuple(rows),
        unit="(N/mm2)",
        note="曲げの基準強度・許容応力度には、部材の寸法に応じた係数を別途乗じる。",
    )


def chapter_program(ctx):
    blocks = [
        Heading(1, "§３．プログラムの使用状況"),
        Heading(2, "3.1 実行環境"),
        key_value_table([
            ("プログラム", "Structural Toolbox " + ctx.program_version),
            ("入力ファイル", getattr(ctx.mdl, "filepath", "")),
            ("入力データID", ctx.input_id),
            ("作成日時", ctx.generated_at.strftime("%Y/%m/%d %H:%M:%S")),
        ]),
        Heading(2, "3.2 メッセージ一覧"),
    ]
    if ctx.warnings:
        blocks.extend(Text("・" + w, size=7.5, indent=8.0) for w in ctx.warnings)
    else:
        blocks.append(Text("メッセージはない。"))
    blocks.append(Heading(2, "3.3 設計者が別途確認する項目"))
    blocks.extend(Text("・" + item, size=7.5, indent=8.0) for item in MANUAL_CONFIRMATION_ITEMS)
    return blocks


def chapter_loads(ctx):
    mdl = ctx.mdl
    blocks = [Heading(1, "§４．荷重・外力"), Heading(2, "4.1 荷重ケース")]
    durations = {c.load_case: c.duration for c in ctx.project.load_conditions.load_combinations}
    durations.update({d.load_case: d.duration for d in ctx.project.design_checks.wood.load_case_durations})
    blocks.append(Table(
        columns=(Column("荷重ケース", 0.7), Column("名称"), Column("荷重継続期間")),
        rows=tuple(
            (str(lc), ctx.lc_label(lc), ws.DURATION_LABELS.get(durations.get(lc), "-"))
            for lc in mdl.lcs
        ),
        width_ratio=0.7,
    ))
    if mdl.lcmbs:
        blocks.append(Heading(2, "4.2 荷重組合せ"))
        blocks.append(Table(
            columns=(Column("荷重ケース", 0.7), Column("名称"), Column("組合せ", 2.5, "left")),
            rows=tuple(
                (
                    str(c.lc),
                    c.name,
                    " + ".join("{0} × {1}".format(fmt(f), ctx.lc_label(lc)) for f, lc in zip(c.fcs, c.lcs)),
                )
                for c in mdl.lcmbs
            ),
        ))
    blocks.extend(_gravity_sections(ctx))
    blocks.extend(_wind_section(ctx))
    blocks.extend(_seismic_section(ctx))
    return blocks


def _gravity_sections(ctx):
    from stb_loads.equilibrium import seed_solved_model_cache
    from stb_loads.gravity_format import build_dead_load_report, build_live_load_report

    seed_solved_model_cache(ctx.mdl)
    blocks = []
    for number, title, builder in (("4.3", "固定荷重", build_dead_load_report), ("4.4", "積載荷重", build_live_load_report)):
        try:
            report = builder(ctx.mdl, ctx.project)
        except ValueError as ex:
            blocks.append(Heading(2, number + " " + title))
            blocks.append(Text("算定条件が設定されていないため省略する。（" + str(ex) + "）", size=7.5))
            continue
        if not report["found"]:
            continue
        blocks.append(Heading(2, number + " " + title))
        blocks.append(dict_table(
            ("story", "story_level_m", "height_m", "weight_kN"),
            report["story_rows"],
            {"story": "層", "story_level_m": "基準高さ (m)", "height_m": "階高 (m)", "weight_kN": "重量 (kN)"},
            places={"story_level_m": 3, "height_m": 3, "weight_kN": 2},
        ))
    return blocks


def _optional_report(title, build):
    try:
        text = build()
    except (ValueError, KeyError) as ex:
        return [Heading(2, title), Text("算定条件が設定されていないため省略する。（" + str(ex) + "）", size=7.5)]
    return [Heading(2, title)] + markdown_blocks(text)


def _wind_section(ctx):
    from stb_loads import compute_wind_distribution, render_wind_markdown

    return _optional_report(
        "4.5 風圧力",
        lambda: render_wind_markdown(compute_wind_distribution(ctx.mdl, ctx.project), ctx.project, mdl=ctx.mdl),
    )


def _seismic_section(ctx):
    from stb_loads import compute_seismic_distribution, render_seismic_markdown

    return _optional_report(
        "4.6 地震力",
        lambda: render_seismic_markdown(compute_seismic_distribution(ctx.mdl, ctx.project), ctx.project, mdl=ctx.mdl),
    )


def chapter_preparation(ctx):
    mdl = ctx.mdl
    return [
        Heading(1, "§５．準備計算"),
        Heading(2, "5.1 剛性に関する計算条件"),
        key_value_table([
            ("節点数", len(mdl.nds)),
            ("部材数", len(mdl.elms)),
            ("支点数", len(mdl.cons)),
            ("ダイアフラム数", len(mdl.diaps)),
            ("耐力壁数", len(mdl.wwalls)),
        ], width_ratio=0.5),
        Heading(2, "5.2 部材の断面性能"),
        Table(
            columns=(Column("符号"), Column("A\n(cm2)"), Column("Iy\n(cm4)"), Column("Iz\n(cm4)"), Column("J\n(cm4)"), Column("Zy\n(cm3)"), Column("Zz\n(cm3)")),
            rows=tuple(
                (
                    s.name,
                    fmt(s.A * 1.0e4, 1),
                    fmt(s.Iy * 1.0e8, 1),
                    fmt(s.Iz * 1.0e8, 1),
                    fmt(s.J * 1.0e8, 1),
                    fmt(s.Wy * 1.0e6, 1),
                    fmt(s.Wz * 1.0e6, 1),
                )
                for s in mdl.secs
                if not getattr(s, "auto_generated", False)
            ),
        ),
    ]
