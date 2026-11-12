"""§6 to §15: analysis, member checks, structural indices, findings, echo."""

from stb_checks import wood_joints as joints
from stb_checks import wood_standard as ws
from stb_reports.calc_book import figures
from stb_reports.calc_book.common import dict_table, fmt
from stb_reports.calc_book.context import KIND_BEAM, KIND_COLUMN, KIND_OTHER
from stb_reports.calc_book.document import Cell, Column, Heading, PageBreak, Table, Text, key_value_table

KILO = 1.0e-3
DOF_NAMES = ("TX", "TY", "TZ", "RX", "RY", "RZ")


def chapter_analysis(ctx):
    mdl = ctx.mdl
    cases = figures.report_load_cases(ctx)
    blocks = [
        Heading(1, "§６．応力解析"),
        Heading(2, "6.1 架構モデル"),
        Heading(3, "6.1.1 モデル化の条件"),
        Text("部材は両端に剛接またはピンを持つ線材としてモデル化する。部材の変形は曲げ、せん断、軸方向およびねじりを考慮する。"),
        Heading(3, "6.1.2 構造モデル図"),
    ]
    blocks.extend(figures.model_figures(ctx))
    blocks.append(Heading(3, "6.1.3 支点条件"))
    blocks.append(Table(
        columns=(Column("節点", 0.6), Column("層", 0.6), Column("Y軸", 0.6), Column("X軸", 0.6)) + tuple(Column(n, 0.5) for n in DOF_NAMES),
        rows=tuple(
            (str(c.nd.id),) + ctx.naming.node_location(c.nd) + tuple("固定" if v else "自由" for v in c.csts)
            for c in sorted(mdl.cons, key=lambda c: (ctx.naming.node_location(c.nd), c.nd.id))
        ),
        font_size=6.5,
    ))

    blocks.append(Heading(2, "6.2 応力図"))
    for lc in cases:
        blocks.append(Heading(3, "6.2.{0} {1}".format(cases.index(lc) + 1, ctx.lc_label(lc))))
        blocks.extend(figures.stress_figures(ctx, lc))

    blocks.append(Heading(2, "6.3 応力表"))
    for lc in cases:
        blocks.extend(_force_tables(ctx, lc, "6.3.{0}".format(cases.index(lc) + 1)))

    blocks.append(Heading(2, "6.4 変形図"))
    for lc in cases:
        blocks.append(Heading(3, "6.4.{0} {1}".format(cases.index(lc) + 1, ctx.lc_label(lc))))
        blocks.extend(figures.deformation_figures(ctx, lc))

    blocks.append(Heading(2, "6.5 節点変位表"))
    for lc in cases:
        blocks.append(_displacement_table(ctx, lc, "6.5.{0}".format(cases.index(lc) + 1)))

    blocks.append(Heading(2, "6.6 支点反力"))
    for lc in cases:
        figure = figures.reaction_figure(ctx, lc)
        blocks.append(Heading(3, "6.6.{0} {1}".format(cases.index(lc) + 1, ctx.lc_label(lc))))
        if figure is not None:
            blocks.append(figure)
        blocks.append(_reaction_table(ctx, lc))
    return blocks


def _two_lines(a, b, places=2):
    return fmt(a, places) + "\n" + fmt(b, places)


def _force_rows(ctx, members, clc):
    rows = []
    for e in members:
        level, frame, span = ctx.naming.member_location(e)
        f = [float(v) * KILO for v in e.forces[:, clc]]
        rows.append((
            frame, level, span, "左端\n右端",
            _two_lines(f[0], f[6]), _two_lines(f[1], f[7]), _two_lines(f[2], f[8]),
            _two_lines(f[3], f[9]), _two_lines(f[4], f[10]), _two_lines(f[5], f[11]),
            fmt(f[12]), fmt(f[13]),
        ))
    return tuple(rows)


_FORCE_COLUMNS = (
    Column("通り", 0.8), Column("層", 0.8), Column("軸-軸", 1.1), Column("", 0.6),
    Column("N"), Column("Qy"), Column("Qz"), Column("Mx"), Column("My"), Column("Mz"), Column("Mcy"), Column("Mcz"),
)
_KIND_LABELS = ((KIND_BEAM, "梁"), (KIND_COLUMN, "柱"), (KIND_OTHER, "その他の部材"))


def _force_tables(ctx, lc, number):
    clc = ctx.lc_index(lc)
    blocks = [Heading(3, "{0} {1}".format(number, ctx.lc_label(lc)))]
    for kind, label in _KIND_LABELS:
        members = ctx.members_sorted(kind)
        if members:
            blocks.append(Table(
                columns=_FORCE_COLUMNS,
                rows=_force_rows(ctx, members, clc),
                title=label,
                unit="(kN, kN・m)  N は引張を正とする",
                font_size=6.2,
            ))
    return blocks


def _displacement_table(ctx, lc, number):
    clc = ctx.lc_index(lc)
    rows = []
    for node in sorted(ctx.mdl.nds, key=lambda n: (ctx.naming.node_location(n), n.id)):
        if node.disps is None or getattr(node, "auto_generated", False):
            continue
        d = node.disps[:, clc]
        rows.append(
            ctx.naming.node_location(node)
            + tuple(fmt(float(d[i]) * 1000.0, 3) for i in range(3))
            + tuple(fmt(float(d[i]), 5) for i in range(3, 6))
        )
    return Table(
        columns=(Column("層"), Column("Y軸"), Column("X軸"), Column("Ux (mm)"), Column("Uy (mm)"), Column("Uz (mm)"), Column("θx (rad)"), Column("θy (rad)"), Column("θz (rad)")),
        rows=tuple(rows),
        title="{0} {1}".format(number, ctx.lc_label(lc)),
        font_size=6.2,
    )


def _reaction_table(ctx, lc):
    clc = ctx.lc_index(lc)
    rows = []
    totals = [0.0] * 6
    for c in sorted(ctx.mdl.cons, key=lambda c: (ctx.naming.node_location(c.nd), c.nd.id)):
        if c.nd.reacts is None:
            continue
        values = [float(c.nd.reacts[clc, i]) * KILO for i in range(6)]
        totals = [a + b for a, b in zip(totals, values)]
        rows.append(ctx.naming.node_location(c.nd) + tuple(fmt(v) for v in values))
    rows.append((Cell("合計", 3, bold=True),) + tuple(fmt(v) for v in totals))
    return Table(
        columns=(Column("層"), Column("Y軸"), Column("X軸"), Column("Rx (kN)"), Column("Ry (kN)"), Column("Rz (kN)"), Column("Mx (kN・m)"), Column("My (kN・m)"), Column("Mz (kN・m)")),
        rows=tuple(rows),
        font_size=6.2,
    )


# --- §7 ----------------------------------------------------------------------

def chapter_checks(ctx):
    wood = ctx.wood
    blocks = [Heading(1, "§７．断面検定")]
    if wood is None:
        blocks.append(Text("木造部材の検定は実施しない。"))
        return blocks

    if wood.method != "standard":
        blocks.append(Text(
            "本章の検定は簡易法であり、荷重継続期間と座屈を考慮していない。申請に用いる場合は基準強度を設定して再計算すること。",
            bold=True,
        ))
    blocks.extend(_check_policy(ctx))
    blocks.append(Heading(2, "7.3 断面検定比図"))
    ratios = {c.element_id: c.combined_ratio for c in wood.element_checks}
    blocks.extend(figures.ratio_figures(ctx, ratios))
    blocks.append(Heading(2, "7.4 検定結果一覧"))
    blocks.append(Table(
        columns=(Column("分類"), Column("種別", 0.7), Column("検定数", 0.6), Column("最大検定比", 0.8), Column("判定", 0.6)),
        rows=tuple(
            (m["name"], m["kind"], str(m["checked_count"]), fmt(m["max_ratio"], 3), m["status"])
            for m in wood.tables.member_classes
        ),
        width_ratio=0.8,
    ))

    if wood.method == "standard":
        for number, kind, title in (("7.5", "column", "柱の断面検定表"), ("7.6", "beam", "はりの断面検定表"), ("7.7", "brace", "筋かいの断面検定表")):
            checks = [c for c in wood.element_checks if c.kind == kind and c.standard is not None]
            if checks:
                blocks.append(Heading(2, number + " " + title))
                blocks.extend(_check_card(ctx, c) for c in _sorted_checks(ctx, checks))
    else:
        blocks.append(Heading(2, "7.5 部材別の検定（簡易法）"))
        blocks.append(dict_table(
            ("element_id", "member_class", "kind", "governing_load_case", "axial_ratio", "bending_ratio", "shear_ratio", "deflection_ratio", "combined_ratio", "status"),
            wood.tables.element_checks,
            {"element_id": "部材", "member_class": "分類", "kind": "種別", "governing_load_case": "支配LC", "axial_ratio": "軸力比", "bending_ratio": "曲げ比", "shear_ratio": "せん断比", "deflection_ratio": "たわみ比", "combined_ratio": "検定比", "status": "判定"},
        ))

    blocks.extend(_joint_sections(ctx))

    if wood.tables.wall_checks:
        blocks.append(Heading(2, "7.9 耐力壁の断面検定表"))
        blocks.append(dict_table(
            ("wall_id", "wall_name", "direction", "wall_magnification", "wall_length", "wall_height", "allowable_shear_capacity_Qa", "analysis_shear_force_Q", "utilization_ratio", "governing_load_case", "status"),
            wood.tables.wall_checks,
            {"wall_id": "壁", "wall_name": "名称", "direction": "方向", "wall_magnification": "壁倍率", "wall_length": "L (m)", "wall_height": "H (m)", "allowable_shear_capacity_Qa": "Qa (kN)", "analysis_shear_force_Q": "Q (kN)", "utilization_ratio": "Q/Qa", "governing_load_case": "LC", "status": "判定"},
            places={"wall_magnification": 2, "wall_length": 3, "wall_height": 3, "allowable_shear_capacity_Qa": 2, "analysis_shear_force_Q": 2, "utilization_ratio": 3},
            font_size=6.5,
        ))
    blocks.extend(_floor_section(ctx))
    blocks.extend(_unchecked_section(wood))
    return blocks


def _unchecked_section(wood):
    unchecked = [c for c in wood.element_checks if wood.method == "standard" and c.standard is None]
    if not unchecked:
        return []
    return [
        Heading(2, "7.11 未検定の部材"),
        Text("基準強度が未設定の材料、または矩形以外の断面を持つ部材は検定していない。", size=7.5),
        Table(
            columns=(Column("部材"), Column("断面"), Column("材料")),
            rows=tuple((str(c.element_id), c.section, c.material) for c in unchecked),
            width_ratio=0.6,
        ),
    ]


def _bay(coordinate, grids):
    """The grid interval holding a coordinate, as (name, name, length) or None."""

    for (low, low_name), (high, high_name) in zip(grids, grids[1:]):
        if low <= coordinate <= high:
            return low_name, high_name, high - low
    return None


def _floor_panels(ctx, checks):
    """Group triangles by floor level and grid bay, keeping the worst one of each."""

    naming = ctx.naming
    panels = {}
    for check in checks:
        x, y, z = check.centroid
        x_bay = _bay(x, naming.x_grids)
        y_bay = _bay(y, naming.y_grids)
        key = (naming.level(z), check.diaphragm_id, x_bay, y_bay)
        if key not in panels or check.ratio > panels[key].ratio:
            panels[key] = check
    return sorted(panels.items(), key=lambda item: (item[0][0], item[0][1], str(item[0][2]), str(item[0][3])))


_FLOOR_COLUMNS = (
    Column("符号", 1.0), Column("位置", 1.4), Column("床倍率", 0.6), Column("方向", 0.5), Column("長さ\n(mm)", 0.7),
    Column("せん断流\n(kN/m)", 0.8), Column("QD\n(kN)", 0.7), Column("Qa\n(kN)", 0.7), Column("QD/Qa", 0.7), Column("荷重ケース", 1.0),
)


def _floor_rows(ctx, key, check):
    level, _diaphragm, x_bay, y_bay = key
    span = lambda bay, value, axis: (bay[0] + "-" + bay[1]) if bay else axis + "=" + fmt(value, 3)
    x, y, _z = check.centroid
    location = level + "\n" + span(x_bay, x, "x") + ", " + span(y_bay, y, "y")
    mark = "*" if check.ratio > 1.0 else ""
    rows = []
    for direction, bay in (("X", x_bay), ("Y", y_bay)):
        length = bay[2] if bay else None
        rows.append((
            check.diaphragm if not rows else "",
            location if not rows else "",
            fmt(check.multiplier, 2) if not rows else "",
            direction,
            fmt(length * 1000.0, 0) if length else "-",
            fmt(check.shear_flow, 2),
            fmt(check.shear_flow * length, 2) if length else "-",
            fmt(check.allowable * length, 2) if length else "-",
            fmt(check.ratio, 3) + mark,
            ctx.lc_label(check.load_case),
        ))
    return rows


def _floor_section(ctx):
    wood = ctx.wood
    rigid = [d.name for d in ctx.mdl.diaps if not d.uses_membrane_stiffness]
    if not wood.floor_checks and not rigid:
        return []
    blocks = [Heading(2, "7.10 スラブの断面検定表"), Heading(3, "7.10.1 木造床の設計")]
    blocks.append(Text(
        "せん断流は床面内の X-Y 方向のせん断応力度に厚さを乗じた値とし、QD = せん断流 × 長さ、Qa = 1.96 × 床倍率 × 長さ とする。"
        "区画ごとに、区画内で最大の検定値となる要素の値を示す。",
        size=7.5,
    ))
    if rigid:
        blocks.append(Text(
            "剛床または面内剛性を持たない床（" + "、".join(rigid) + "）は面内せん断力を算出しないため、本検定の対象外とする。",
            size=7.5,
        ))
    if wood.floor_checks:
        blocks.append(Table(
            columns=_FLOOR_COLUMNS,
            rows=tuple(row for key, check in _floor_panels(ctx, wood.floor_checks) for row in _floor_rows(ctx, key, check)),
            font_size=6.3,
        ))
    return blocks


def _check_policy(ctx):
    settings = ctx.project.design_checks.wood
    blocks = [Heading(2, "7.1 断面検定方針")]
    if settings.conditions:
        rows = []
        for c in settings.conditions:
            target = c.member_class or {"beam": "はり", "column": "柱", "brace": "筋かい"}.get(c.kind, c.kind)
            rows.append((
                target,
                fmt(c.area_reduction_percent, 0),
                fmt(c.section_modulus_reduction_percent, 0),
                fmt(c.shear_area_reduction_percent, 0),
                fmt(c.buckling_factor_y, 2),
                fmt(c.buckling_factor_z, 2),
                fmt(c.lateral_buckling_coefficient, 2),
                "考慮" if c.biaxial_bending else "考慮しない",
                fmt(c.deflection_ratio_long_term, 0) + " / " + fmt(c.deflection_mm_long_term, 0),
            ))
        blocks.append(Table(
            columns=(Column("対象"), Column("断面積\n低減%", 0.6), Column("断面係数\n低減%", 0.6), Column("せん断\n低減%", 0.6), Column("座屈長\n係数y", 0.6), Column("座屈長\n係数z", 0.6), Column("横座屈\nle係数", 0.6), Column("2軸曲げ", 0.8), Column("長期たわみ制限\nL/n / mm")),
            rows=tuple(rows),
            title="7.1.1 部材の計算条件",
            font_size=6.5,
        ))
    blocks.append(Heading(2, "7.2 検定用荷重ケース"))
    cases = figures.report_load_cases(ctx)
    durations = {c.load_case: c.duration for c in ctx.project.load_conditions.load_combinations}
    durations.update({d.load_case: d.duration for d in settings.load_case_durations})
    blocks.append(Table(
        columns=(Column("荷重ケース", 0.7), Column("名称"), Column("区分")),
        rows=tuple((str(lc), ctx.lc_label(lc), ws.DURATION_LABELS.get(durations.get(lc), "長期（未指定）")) for lc in cases),
        width_ratio=0.6,
    ))
    return blocks


def _sorted_checks(ctx, checks):
    def key(c):
        return ctx.naming.member_location(ctx.mdl.FindElemFromEid(c.element_id)), c.element_id

    return sorted(checks, key=key)


_JOINT_COLUMNS = (
    Column("部材", 1.5), Column("位置", 0.6), Column("金物", 1.0), Column("区分", 0.6), Column("応力", 0.5),
    Column("設計応力", 0.8), Column("許容応力", 0.8), Column("検定値", 0.7), Column("荷重ケース", 1.0), Column("組合せ", 0.7),
)


def _joint_rows(ctx, check):
    e = ctx.mdl.FindElemFromEid(check.element_id)
    level, frame, span = ctx.naming.member_location(e)
    member = "{0}\n{1}, {2}\n{3}".format(e.sec.name, level, frame, span)
    rows = []
    for group in check.groups:
        for index, c in enumerate(group.components):
            mark = "*" if c.ratio > 1.0 else ""
            combined = fmt(group.combined_ratio, 3) + ("*" if group.combined_ratio > 1.0 else "") if index == 0 else ""
            rows.append((
                member if not rows else "",
                joints.END_LABELS[check.end] if not rows else "",
                check.joint if not rows else "",
                group.term if index == 0 else "",
                c.label, fmt(c.value), fmt(c.capacity), fmt(c.ratio, 3) + mark, ctx.lc_label(c.load_case), combined,
            ))
    if check.messages:
        rows.append((Cell("メッセージ", 3, bold=True), Cell(" ".join(check.messages), 7, align="left")))
    return rows


def _joint_sections(ctx):
    checks = ctx.wood.joint_checks
    if not checks:
        return []
    def location(c):
        return ctx.naming.member_location(ctx.mdl.FindElemFromEid(c.element_id)), c.element_id, c.end

    interaction = ctx.project.design_checks.wood.joint_interaction
    method = "組合せは N/Na + M/Ma + Q/Qa の和で検定する。" if interaction == "linear" else "組合せの検定は行わず、応力ごとに検定する。"
    blocks = [Heading(2, "7.8 柱はり接合部の断面検定表"), Text(method, size=7.5)]
    for number, kind, title in (("7.8.1", "beam", "木造梁接合金物の設計"), ("7.8.2", "column", "木造柱接合金物の設計")):
        group = sorted((c for c in checks if c.kind == kind), key=location)
        if group:
            blocks.append(Heading(3, number + " " + title))
            blocks.append(Table(
                columns=_JOINT_COLUMNS,
                rows=tuple(row for check in group for row in _joint_rows(ctx, check)),
                unit="(kN, kN・m)  N は引張を正とする",
                font_size=6.2,
            ))
    return blocks


_CARD_COLUMNS = (Column("", 1.0), Column("", 1.0), Column("", 1.0), Column("", 1.0), Column("", 1.0))


def _stress(value):
    return fmt(value / ws.STRESS_UNIT, 2)


def _card_row(label, values):
    return (Cell(label, bold=True),) + tuple(values)


def _section_lines(check):
    p = check.standard.properties
    first = "Ae={0}  Zey={1}  Zez={2}  i={3}".format(
        fmt(p.area * 1.0e4, 1), fmt(p.section_modulus_y * 1.0e6, 1), fmt(p.section_modulus_z * 1.0e6, 1), fmt(min(p.radius_y, p.radius_z) * 1.0e3, 1)
    )
    second = "lky={0}  lkz={1}  λ={2}  η={3}".format(
        fmt(p.buckling_length_y * 1.0e3, 0), fmt(p.buckling_length_z * 1.0e3, 0), fmt(p.slenderness, 1), fmt(p.eta, 2)
    )
    if p.lateral_cs is None:
        return first + "\n" + second
    return first + "\n" + second + "\nCk={0}  Cs={1}  Cb={2}  le={3}".format(
        fmt(p.lateral_ck, 2), fmt(p.lateral_cs, 2), fmt(p.lateral_cb, 2), fmt(p.lateral_length * 1.0e3, 0)
    )


def _check_card(ctx, check):
    """One member's check, laid out by duration like a conventional check sheet."""

    e = ctx.mdl.FindElemFromEid(check.element_id)
    level, frame, span = ctx.naming.member_location(e)
    results = list(check.standard.results)[:4]
    while len(results) < 4:
        results.append(None)

    def row(label, getter):
        return _card_row(label, [getter(r) if r is not None else "" for r in results])

    deflection = lambda r: "-" if r.deflection is None else "{0} ({1})".format(fmt(r.deflection * 1000.0, 2), fmt(r.deflection_ratio, 3))
    rows = (
        (Cell("記号", bold=True), Cell("{0} ({1}, {2}, {3})  部材{4}  {5}".format(check.section, level, frame, span, check.element_id, check.material), 4)),
        (Cell("断面性能", bold=True), Cell(_section_lines(check), 4, align="left")),
        _card_row("区分", [ws.DURATION_LABELS[r.duration] if r else "" for r in results]),
        row("荷重ケース", lambda r: ctx.lc_label(r.load_case)),
        row("位置", lambda r: ws.location_label(r.location)),
        row("N (kN)", lambda r: fmt(r.axial * KILO)),
        row("My (kN・m)", lambda r: fmt(r.moment_y * KILO)),
        row("Mz (kN・m)", lambda r: fmt(r.moment_z * KILO)),
        row("Q (kN)", lambda r: fmt(r.shear * KILO)),
        row("fc / ft", lambda r: _stress(r.allowable_compression) + " / " + _stress(r.allowable_tension)),
        row("fby / fbz", lambda r: _stress(r.allowable_bending_y) + " / " + _stress(r.allowable_bending_z)),
        row("fs", lambda r: _stress(r.allowable_shear)),
        row("σn", lambda r: _stress(r.sigma_n)),
        row("σby / σbz", lambda r: _stress(r.sigma_by) + " / " + _stress(r.sigma_bz)),
        row("τ", lambda r: _stress(r.tau)),
        row("σ/f", lambda r: fmt(r.combined_stress_ratio, 3) + ("*" if r.combined_stress_ratio > 1.0 else "")),
        row("τ/fs", lambda r: fmt(r.shear_ratio, 3) + ("*" if r.shear_ratio > 1.0 else "")),
        row("σcv/fcv", lambda r: fmt(r.bearing_ratio, 3)),
        row("δ mm (比)", deflection),
        (Cell("判定", bold=True), Cell(check.status + ("  " + " ".join(check.messages) if check.messages else ""), 4)),
    )
    return Table(columns=_CARD_COLUMNS, rows=rows, show_header=False, font_size=6.3, width_ratio=0.86, keep_together=True)


# --- §8 onward ---------------------------------------------------------------

def chapters_indices(ctx):
    tables = ctx.indices.tables
    drift_rows = [r for r in tables["story_drifts"] if r.get("is_story_max")]
    return [
        Heading(1, "§８．壁量、柱量"),
        Text("壁量計算を行う場合は、壁量計算書を別冊として添付する。"),
        Heading(1, "§９．層間変形角・剛性率"),
        Heading(2, "9.1 層間変形角"),
        dict_table(
            ("story", "direction", "load_case", "element_id", "drift_m", "height_m", "drift_angle", "inverse_ratio", "status"),
            drift_rows,
            {"story": "階", "direction": "方向", "load_case": "LC", "element_id": "部材", "drift_m": "δ (m)", "height_m": "h (m)", "drift_angle": "δ/h", "inverse_ratio": "逆数", "status": "状態"},
            places={"drift_m": 5, "height_m": 3, "drift_angle": 5, "inverse_ratio": 1},
        ),
        Heading(2, "9.2 剛性率"),
        dict_table(
            ("story", "direction", "load_case", "drift_m", "height_m", "drift_angle", "inverse_ratio", "mean_inverse_ratio", "rigidity_ratio", "fs", "status"),
            tables["rigidity_ratios"],
            {"story": "階", "direction": "方向", "load_case": "LC", "drift_m": "δ (m)", "height_m": "h (m)", "drift_angle": "δ/h", "inverse_ratio": "rs", "mean_inverse_ratio": "r̄s", "rigidity_ratio": "Rs", "fs": "Fs", "status": "状態"},
            places={"drift_m": 5, "height_m": 3, "drift_angle": 5, "inverse_ratio": 1, "mean_inverse_ratio": 1, "rigidity_ratio": 2, "fs": 2},
            font_size=6.5,
        ),
        Heading(1, "§１０．偏心率"),
        Heading(2, "10.1 偏心率"),
        dict_table(
            ("story", "xg", "yg", "xs", "ys", "ex", "ey", "re_x", "re_y", "fe_x", "fe_y", "status"),
            tables["eccentricities"],
            {"story": "階", "xg": "Xg", "yg": "Yg", "xs": "Xs", "ys": "Ys", "ex": "ex", "ey": "ey", "re_x": "Rex", "re_y": "Rey", "fe_x": "FeX", "fe_y": "FeY", "status": "状態"},
            places={"xg": 3, "yg": 3, "xs": 3, "ys": 3, "ex": 3, "ey": 3, "re_x": 3, "re_y": 3, "fe_x": 3, "fe_y": 3},
            unit="(m)",
            font_size=6.5,
        ),
        Heading(1, "§１１．保有水平耐力"),
        Text("本プログラムでは保有水平耐力計算を行わない。"),
    ]


def _foundation_details(ctx):
    foundation = ctx.foundation
    settings = ctx.project.foundation
    soil = settings.soil
    blocks = [
        Heading(2, "12.1 基礎概要"),
        key_value_table([
            ("基礎形式", "べた基礎"),
            ("支持地盤", soil.name),
            ("基礎の面積", fmt(foundation.total_area, 2) + " m2"),
            ("基礎自重（耐圧版・付加荷重・基礎梁）", fmt(foundation.foundation_weight, 1) + " kN"),
            ("コンクリート", "{0} (Fc={1})".format(settings.concrete.name, fmt(settings.concrete.fc, 1))),
        ], width_ratio=0.7),
        Heading(2, "12.2 基礎配置"),
        Heading(3, "12.2.1 部材リスト"),
        Table(
            columns=(Column("符号"), Column("厚さ (mm)", 0.7), Column("短辺 端部"), Column("短辺 中央"), Column("長辺 端部"), Column("長辺 中央")),
            rows=tuple((s.name, fmt(s.thickness, 0), s.short.end, s.short.mid, s.long.end, s.long.mid) for s in settings.slab_types),
            title="耐圧版",
        ),
    ]
    if settings.beam_types:
        blocks.append(Table(
            columns=(Column("符号"), Column("b × D (mm)"), Column("上端筋"), Column("下端筋"), Column("あばら筋"), Column("主筋"), Column("あばら筋材質")),
            rows=tuple(
                (b.name, "{0} × {1}".format(fmt(b.b, 0), fmt(b.d, 0)), b.top, b.bottom, b.stirrup, b.main_rebar, b.stirrup_rebar)
                for b in settings.beam_types
            ),
            title="基礎梁",
        ))
    blocks.append(Heading(3, "12.2.2 基礎配置図"))
    blocks.append(figures.foundation_figure(ctx))
    blocks.extend(_bearing_section(ctx))
    blocks.extend(_overturning_section(ctx))
    return blocks


def _bearing_section(ctx):
    foundation = ctx.foundation
    soil = ctx.project.foundation.soil
    rows = []
    for c in foundation.panels:
        p = c.panel
        location = "{0}-{1}, {2}-{3}".format(p.x_names[0], p.x_names[1], p.y_names[0], p.y_names[1])
        case = ctx.lc_label(c.short_load_case) if c.short_load_case is not None else "-"
        rows.append((
            p.slab, location, fmt(c.long_pressure, 1), fmt(c.average_long_pressure, 1), fmt(c.short_pressure, 1),
            fmt(c.allowable_long, 1), fmt(c.allowable_short, 1), fmt(c.long_ratio, 3), fmt(c.short_ratio, 3), case, c.status,
        ))
    return [
        Heading(2, "12.3 地耐力検討"),
        Heading(3, "12.3.1 許容地耐力"),
        Table(
            columns=(Column("長期 (kN/m2)"), Column("短期 (kN/m2)"), Column("地盤のヤング率 (kN/m2)")),
            rows=((fmt(soil.bearing_long, 1), fmt(soil.bearing_short, 1), fmt(soil.young, 1)),),
            width_ratio=0.6,
        ),
        Heading(3, "12.3.2 地耐力検討"),
        Text(
            "接地圧は、支点反力を支点に接する耐圧版へ面積比で配分した値に、基礎自重の等分布圧を加えて求める。"
            "長期検定 = max(Lσ, avLσ) / Lqa、短期検定 = Sσ / Sqa とする。",
            size=7.5,
        ),
        Table(
            columns=(
                Column("符号", 0.6), Column("位置", 1.3), Column("Lσ"), Column("avLσ"), Column("Sσ"), Column("Lqa"), Column("Sqa"),
                Column("長期検定"), Column("短期検定"), Column("短期\n荷重ケース", 1.0), Column("判定", 0.5),
            ),
            rows=tuple(rows),
            unit="(kN/m2)",
            font_size=6.5,
        ),
    ]


def _overturning_section(ctx):
    foundation = ctx.foundation
    blocks = [Heading(2, "12.6 転倒の検討"), Heading(3, "12.6.1 転倒の検討")]
    if foundation.overturning:
        blocks.append(Table(
            columns=(Column("方向", 0.5), Column("水平力による\nモーメント (kN・m)"), Column("層せん断力\nQ1 (kN)"), Column("転倒モーメント\nMT (kN・m)"), Column("建物重量W\n(kN)"), Column("重心位置g\n(m)"), Column("W・g\n(kN・m)"), Column("荷重ケース"), Column("判定", 0.5)),
            rows=tuple(
                (o.direction, fmt(o.level_moment), fmt(o.base_shear), fmt(o.moment), fmt(o.weight), fmt(o.arm), fmt(o.resisting_moment), ctx.lc_label(o.load_case), o.status)
                for o in foundation.overturning
            ),
            font_size=6.5,
        ))
    else:
        blocks.append(Text("水平力を含む短期の荷重ケースがないため省略する。", size=7.5))
    settings = ctx.project.foundation
    blocks.append(Text(
        "MT = Σ(水平力 × 支点からの高さ) + Q1 × (α + β) とする。α = {0} mm（地上1階層の地盤面からの高さ）、β = {1} mm（基礎底深さ）。g は基礎の圧縮側最外端から重心までの距離とする。".format(
            fmt(settings.first_floor_height, 0), fmt(settings.embedment_depth, 0)
        ),
        size=7.5,
    ))
    blocks.append(Heading(3, "12.6.2 転倒モーメントによる短期接地圧の検討"))
    blocks.append(Table(
        columns=(Column("方向", 0.5), Column("高さ (m)"), Column("基礎幅 (m)"), Column("塔状比"), Column("制限"), Column("判定", 0.5)),
        rows=tuple((s.direction, fmt(s.height), fmt(s.width), fmt(s.ratio), "≦2.5", s.status) for s in foundation.slenderness),
        title="建物の塔状比",
        width_ratio=0.7,
    ))
    if foundation.short_pressure_check_omitted:
        blocks.append(Text("塔状比が 2.5 以下、または長期許容地耐力が 30 kN/m2 以上のため、転倒に対する短期接地圧の検討を省略する。", size=7.5))
    elif foundation.short_pressure:
        blocks.append(Table(
            columns=(Column("方向", 0.5), Column("σ0 = W/A"), Column("σb = MT/Z"), Column("αe"), Column("短期接地圧"), Column("短期許容地耐力"), Column("検定比"), Column("判定", 0.5)),
            rows=tuple(
                (c.direction, fmt(c.sigma0, 1), fmt(c.sigma_b, 1), fmt(c.alpha_e, 3), fmt(c.pressure, 1), fmt(c.allowable, 1), fmt(c.ratio, 3), c.status)
                for c in foundation.short_pressure
            ),
            title="短期接地圧の検討",
            unit="(kN/m2)",
            font_size=6.5,
        ))
    else:
        blocks.append(Text("短期接地圧の検討の条件に該当するが、水平力を含む荷重ケースがないため検討していない。", size=7.5, bold=True))
    return blocks


def _foundation_beam_section(ctx):
    result = ctx.foundation_beams
    if result is None:
        return [Heading(2, "12.5 基礎梁の検討"), Text("基礎梁が設定されていないため省略する。", size=7.5)]
    rows = []
    for check in result.checks:
        name = "{0}\n{1}, {2}-{3}\n{4}×{5}".format(check.beam, check.frame, check.span[0], check.span[1], fmt(check.width, 0), fmt(check.depth, 0))
        for index, s in enumerate(check.sections):
            star = lambda v: fmt(v, 3) + ("*" if v > 1.0 else "")
            rows.append((
                name if index == 0 else "", s.location,
                fmt(s.long_moment, 1), fmt(s.short_top, 1), fmt(s.short_bottom, 1), fmt(s.long_shear, 1), fmt(s.design_shear, 1),
                star(s.long_moment_ratio), star(s.top_ratio), star(s.bottom_ratio),
                fmt(s.allowable_long_shear, 1), fmt(s.allowable_short_shear, 1), star(s.long_shear_ratio), star(s.short_shear_ratio),
            ))
    allow_rows = tuple(
        (c.beam, "{0}, {1}-{2}".format(c.frame, c.span[0], c.span[1]), c.top, c.bottom, c.stirrup, fmt(c.pw * 100.0, 2), fmt(c.allowable_long, 1), fmt(c.allowable_short_top, 1), fmt(c.allowable_short_bottom, 1), c.status)
        for c in result.checks
    )
    return [
        Heading(2, "12.5 基礎梁の検討"),
        Heading(3, "12.5.1 計算方法"),
        Text(
            "常時荷重時は、耐圧版に上部構造の支点反力による地反力が等分布荷重として作用するものとし、版の両方向に45度の分割で伝達して荷重項とする。"
            "柱位置をピン支持とする基礎梁のみのモデルで応力を求める。"
            "水平荷重時は、上部構造の支点反力の増分を外力とし、地盤バネで支持した格子梁モデルにより応力を求める。"
            "短期設計用せん断力は QL + 1.5 × Q（増分）とする。付着の検討および地盤バネの浮上りは考慮していない。",
            size=7.5,
        ),
        Heading(3, "12.5.2 部材の許容耐力"),
        Table(
            columns=(Column("符号", 0.6), Column("位置", 1.2), Column("上端筋"), Column("下端筋"), Column("あばら筋"), Column("pw (%)", 0.6), Column("MaL"), Column("Mas,U"), Column("Mas,D"), Column("判定", 0.5)),
            rows=allow_rows,
            unit="(kN・m)",
            font_size=6.5,
        ),
        Heading(3, "12.5.3 基礎梁断面検定表"),
        Table(
            columns=(
                Column("符号・位置", 1.4), Column("", 0.55), Column("ML"), Column("Ms,U"), Column("Ms,D"), Column("QL"), Column("QD"),
                Column("ML/\nMaL"), Column("Ms,U/\nMas,U"), Column("Ms,D/\nMas,D"), Column("QaL"), Column("Qas"), Column("QL/\nQaL"), Column("QD/\nQas"),
            ),
            rows=tuple(rows),
            unit="(kN, kN・m)",
            font_size=6.0,
        ),
    ]


def chapter_foundation(ctx):
    if ctx.foundation is not None:
        return [
            Heading(1, "§１２．基礎・地盤"),
        ] + _foundation_details(ctx) + _foundation_beam_section(ctx) + [
            Heading(2, "12.7 基礎盤の検討"),
            Text("基礎盤の断面検定は別途行い、本書に添付する。", size=7.5),
            Heading(1, "§１３．その他の部材"),
            Text("小屋組等の検討は別途行い、本書に添付する。"),
        ]

    cases = figures.report_load_cases(ctx)
    rows = []
    for lc in cases:
        clc = ctx.lc_index(lc)
        values = [float(c.nd.reacts[clc, 2]) * KILO for c in ctx.mdl.cons if c.nd.reacts is not None]
        if values:
            rows.append((ctx.lc_label(lc), fmt(sum(values), 1), fmt(max(values), 1), fmt(min(values), 1)))
    return [
        Heading(1, "§１２．基礎・地盤"),
        Heading(2, "12.1 基礎設計用の支点反力"),
        Text("地耐力、基礎盤、基礎梁および転倒の検討は別途行い、本書に添付する。各支点の反力は 6.6 による。", size=7.5),
        Table(
            columns=(Column("荷重ケース"), Column("ΣRz (kN)"), Column("最大Rz (kN)"), Column("最小Rz (kN)")),
            rows=tuple(rows),
            width_ratio=0.7,
        ),
        Heading(1, "§１３．その他の部材"),
        Text("小屋組等の検討は別途行い、本書に添付する。"),
    ]


def chapter_findings(ctx):
    wood = ctx.wood
    if wood is None:
        conclusion = "木造部材の検定は実施していない。"
    elif wood.status == "OK":
        conclusion = "検定した部材の検定比はすべて 1.0 以下である（最大 {0}）。".format(fmt(wood.max_ratio, 3))
    elif wood.status == "NG":
        conclusion = "検定比が 1.0 を超える部材、または制限値を超える部材がある（最大 {0}）。断面、荷重および条件を見直すこと。".format(fmt(wood.max_ratio, 3))
    else:
        conclusion = "未検定の部材または未確認の項目がある。§３および§７を確認すること。"
    blocks = [Heading(1, "§１４．総合所見"), Text(conclusion)]
    if ctx.foundation is not None:
        foundation = ctx.foundation
        text = {"OK": "基礎の接地圧および転倒の検討は満足する", "NG": "基礎の接地圧または転倒の検討を満足しない項目がある", "WARN": "基礎の検討に未確認の項目がある"}[foundation.status]
        blocks.append(Text("{0}（最大 {1}）。".format(text, fmt(foundation.max_ratio, 3))))
    if ctx.foundation_beams is not None:
        beam_text = "基礎梁の断面検定は満足する" if ctx.foundation_beams.status == "OK" else "基礎梁の断面検定を満足しない部材がある"
        blocks.append(Text("{0}（最大 {1}）。".format(beam_text, fmt(ctx.foundation_beams.max_ratio, 3))))
    if ctx.warnings:
        blocks.append(Text("【警告・注意メッセージ】", bold=True))
        blocks.append(Text("件数: {0} 件（内容は §３ による）".format(len(ctx.warnings)), size=7.5, indent=8.0))
    blocks.append(Text("本書の法規適合および入力条件の妥当性は、設計者が最終的に確認する。", size=7.5))
    return blocks


def chapter_echo(ctx):
    if not ctx.dat_lines:
        return [Heading(1, "§１５．エコーデータ"), Text("入力ファイルを読み込めなかったため省略する。")]
    return [
        Heading(1, "§１５．エコーデータ"),
        Heading(2, "構造解析データファイル"),
        Table(
            columns=(Column("", 0.5), Column("", 10.0, "left")),
            rows=tuple((str(i + 1), line) for i, line in enumerate(ctx.dat_lines)),
            show_header=False,
            font_size=6.0,
        ),
    ]
