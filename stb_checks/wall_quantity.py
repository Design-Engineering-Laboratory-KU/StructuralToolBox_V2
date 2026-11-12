"""木造壁量計算 (2025年4月施行の壁量基準, 在来軸組構法, 2階建てまで).

References
----------
- 令第46条第4項, 昭和56年建設省告示第1100号 (令和6年国交告第447号等による改正)
- 国土交通省「木造建築物における省エネ化等による建築物の重量化に対応するための
  必要な壁量等の基準に関する補足資料」(令和6年7月8日)
- (公財)日本住宅・木材技術センター「壁量等の基準(令和7年施行)に対応した
  表計算ツール（在来軸組工法用）」ver1.2

Seismic required wall quantity per floor area (cm/m2)::

    Lw = (Ai * C0 * Σwi) / (0.0196 * Afi)
    Ai = 1 + (1/sqrt(αi) - αi) * 2T / (1 + 3T),   T = 0.03 h

With ``method="spec"`` Σwi is built exactly as the 表計算ツール does (unit loads
of roof / exterior wall / insulation / openings / interior walls / floor / live
load, wall loads converted to floor-area loads with the tool's 6 m x 16.5 m
reference plan and 9 % opening ratio, rounding as in the tool). With
``method="direct"`` Σwi is given per story in kN.

Wind required wall quantity: 見付面積 (m2) x coefficient (cm/m2, default 50).

存在壁量: Σ(壁倍率 x 長さ) of rated walls (WWLL, 倍率上限 7.0, 階高 3.2 m 超の
筋かいは αh = 3.5 Ld/H0 で低減) plus 準耐力壁等 (counted up to 1/2 of the
required quantity unless brittle-failure verification is declared).
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Tuple

from stb_project.wall_quantity_settings import (
    EXTERIOR_WALL_LABELS_JA,
    EXTERIOR_WALL_UNIT_LOADS_N_M2,
    ROOF_LABELS_JA,
    ROOF_UNIT_LOADS_N_M2,
    DEFAULT_MULTIPLIER_CAP,
    WallQuantitySettings,
)


# 表計算ツール ver1.2 fixed unit loads (N/m2).
SOLAR_STANDARD_N_M2 = 260.0          # 太陽光発電設備等 あり(260)
CEILING_INSULATION_DEFAULT_N_M2 = 100.0
WALL_INSULATION_DEFAULT_N_M2 = 70.0  # per wall area
OPENING_N_M2 = 400.0                 # 開口部（トリプルガラス）per opening area
INTERIOR_WALL_N_M2_PER_2_8M = 200.0  # 内壁（せっこうボード）per floor area at 2.8 m story height
FLOOR_N_M2 = 610.0                   # 床
LIVE_LOAD_SEISMIC_N_M2 = 600.0       # 積載（地震力算定用）
GRAVITY = 9.8                        # 1 kg = 9.8 N (tool convention)

# Reference plan used by the tool to convert wall loads to floor-area loads.
REF_PLAN_SHORT_M = 6.0
REF_PLAN_LONG_M = 16.5
OPENING_RATIO = 0.09

# Building height convention of the tool: 0.9 m (GL - 土台上端) + Σh + 0.5 m.
HEIGHT_BASE_OFFSET_M = 0.9
HEIGHT_TOP_OFFSET_M = 0.5

WALL_UNIT_KN_PER_M = 1.96            # 壁倍率1 = 1.96 kN/m
LW_DENOMINATOR = 0.0196              # 1.96 kN/m expressed per cm
BRACE_HEIGHT_LIMIT_M = 3.2

APPLICABILITY_MAX_TOTAL_FLOOR_AREA_M2 = 300.0
APPLICABILITY_MAX_HEIGHT_M = 16.0
APPLICABILITY_MAX_STORIES = 2

STORY_Z_TOLERANCE_M = 0.05
SAME_FRAME_TOLERANCE_M = 0.01


class WallQuantityError(ValueError):
    pass


@dataclass(frozen=True)
class SeismicLoadItem:
    key: str
    label: str
    value_N_m2: float
    basis: str


@dataclass(frozen=True)
class StorySeismicDemand:
    story: str
    floor_area_m2: float
    height_m: float
    weight_kN: float               # Σwi
    alpha: float
    ai: float
    lw_raw_cm_m2: float
    lw_cm_m2: float                # rounded up to an integer (tool convention)
    required_cm: float             # Lw x Af


@dataclass(frozen=True)
class SeismicDemand:
    method: str
    c0: float
    building_height_m: float
    period_s: float
    load_items: Tuple[SeismicLoadItem, ...]
    stories: Tuple[StorySeismicDemand, ...]
    # 平屋の床面積に乗ずる数値, used by 四分割法 for 1F side strips with no 2nd floor above.
    single_story_lw_cm_m2: Optional[float] = None


@dataclass(frozen=True)
class WallEntry:
    source: str                    # "WWLL" or "QUASI"
    ref: str                       # WWLL id or quasi wall name
    name: str
    story: str
    direction: str                 # "x" / "y"
    kind: str                      # brace / panel / other / quasi / hanging_waist
    length_m: float
    height_m: Optional[float]
    multiplier_input: float
    alpha_h: float
    multiplier: float              # effective, after αh and the 7.0 cap (shared per frame)
    capped: bool
    amount_cm: float               # multiplier x length(cm)
    x_center: Optional[float] = None
    y_center: Optional[float] = None
    notes: str = ""
    # 実態倍率 (after αh, without the 7.0 cap) - used by N値計算 and the 実態倍率 四分割法 check.
    multiplier_actual: Optional[float] = None
    # Plan end points of the wall line (bottom line); None when the wall has no nodes/position.
    end_a: Optional[Tuple[float, float]] = None
    end_b: Optional[Tuple[float, float]] = None
    brace_section: str = ""
    brace_layout: str = ""         # "single" / "x" (braces only)
    brace_top_end: Optional[Tuple[float, float]] = None  # single brace: end whose column takes the brace top

    @property
    def actual_multiplier(self) -> float:
        return self.multiplier if self.multiplier_actual is None else self.multiplier_actual


@dataclass(frozen=True)
class StoryDirectionCheck:
    story: str
    direction: str
    floor_area_m2: float
    lw_cm_m2: float
    seismic_required_cm: float
    wind_area_m2: float
    wind_coefficient_cm_m2: float
    wind_required_cm: float
    required_cm: float
    governing: str                 # "seismic" / "wind"
    bearing_cm: float              # 耐力壁
    quasi_raw_cm: float            # 準耐力壁等 (before the 1/2 rule)
    quasi_counted_cm: float
    quasi_exceeds_half: bool
    existing_cm: float
    ratio: float
    status: str


@dataclass(frozen=True)
class WallQuantitySummary:
    standard: str
    seismic: SeismicDemand
    walls: Tuple[WallEntry, ...]
    checks: Tuple[StoryDirectionCheck, ...]
    quasi_exceeds_half: bool       # 注1: any story/direction exceeding → treat all as exceeding
    applicability: Tuple[dict, ...]
    warnings: Tuple[str, ...]
    status: str                    # 壁量判定
    balance: Optional["object"] = None    # stb_checks.wall_balance.WallBalanceSummary (四分割法)
    n_values: Optional["object"] = None   # stb_checks.n_value.NValueSummary (柱頭・柱脚)
    column_size: Optional["object"] = None  # stb_checks.column_size.ColumnSizeSummary (柱の小径)

    @property
    def overall_status(self) -> str:
        statuses = [self.status]
        for part in (self.balance, self.n_values, self.column_size):
            if part is not None:
                statuses.append(part.status)
        return "OK" if all(s == "OK" for s in statuses) else "NG"


# ---------------------------------------------------------------------------
# Public API


def build_wall_quantity_summary(mdl, project) -> WallQuantitySummary:
    settings: WallQuantitySettings = project.wall_quantity
    if not settings.enabled:
        raise WallQuantityError("project.wall_quantity is not enabled")
    warnings: List[str] = []

    stories = _ordered_stories(project, settings)
    seismic = compute_seismic_demand(settings, stories)

    walls = _collect_rated_walls(mdl, settings, stories, warnings)
    walls.extend(_collect_quasi_walls(settings, stories, warnings))

    checks, exceeds_half = _check_stories(settings, stories, seismic, walls, warnings)
    applicability = _applicability(stories, seismic)
    for row in applicability:
        if row["status"] != "OK":
            warnings.append("適用範囲: " + row["item"] + " が " + row["limit"] + " を満たしません。")

    from stb_checks.column_size import compute_column_size
    from stb_checks.n_value import compute_n_values
    from stb_checks.wall_balance import compute_wall_balance

    balance = compute_wall_balance(settings, stories, seismic, walls, exceeds_half, warnings)
    n_values = compute_n_values(settings, stories, walls, exceeds_half, warnings)
    column_size = compute_column_size(mdl, settings, stories, warnings)

    warnings = list(dict.fromkeys(warnings))
    status = "OK" if all(c.status == "OK" for c in checks) else "NG"
    return WallQuantitySummary(
        standard=settings.standard,
        seismic=seismic,
        walls=tuple(walls),
        checks=tuple(checks),
        quasi_exceeds_half=exceeds_half,
        applicability=tuple(applicability),
        warnings=tuple(warnings),
        status=status,
        balance=balance,
        n_values=n_values,
        column_size=column_size,
    )


@dataclass(frozen=True)
class _StoryInfo:
    name: str
    elevation: float
    height_m: float
    floor_area_m2: float
    weight_kN: Optional[float]
    wind_area_x_m2: float
    wind_area_y_m2: float
    plan_polygons: Tuple[Tuple[Tuple[float, float], ...], ...] = ()


def _ordered_stories(project, settings) -> List[_StoryInfo]:
    inputs = {s.story: s for s in settings.stories}
    ordered = sorted(project.stories, key=lambda s: s.elevation)
    if not ordered:
        raise WallQuantityError("project.stories is empty")
    if len(ordered) > APPLICABILITY_MAX_STORIES:
        raise WallQuantityError(
            "壁量計算は2階建てまでを対象とします (stories=" + str(len(ordered)) + ")"
        )
    unknown = set(inputs) - set(s.name for s in ordered)
    if unknown:
        raise WallQuantityError(
            "wall_quantity.stories refers to unknown story: " + ", ".join(sorted(unknown))
        )
    out = []
    for st in ordered:
        inp = inputs.get(st.name)
        if inp is None:
            raise WallQuantityError("wall_quantity.stories has no input for story " + st.name)
        height = inp.height_m if inp.height_m is not None else st.height
        if height <= 0.0:
            raise WallQuantityError("story height must be positive: " + st.name)
        out.append(_StoryInfo(
            name=st.name,
            elevation=st.elevation,
            height_m=height,
            floor_area_m2=inp.floor_area_m2,
            weight_kN=inp.weight_kN,
            wind_area_x_m2=inp.wind_area_x_m2,
            wind_area_y_m2=inp.wind_area_y_m2,
            plan_polygons=inp.plan_polygons,
        ))
    return out


# ---------------------------------------------------------------------------
# Seismic demand


def layer_shear_distribution_ai(alpha: float, period_s: float) -> float:
    if alpha <= 0.0:
        raise WallQuantityError("alpha must be positive")
    t = period_s
    return 1.0 + (1.0 / math.sqrt(alpha) - alpha) * 2.0 * t / (1.0 + 3.0 * t)


def compute_seismic_demand(settings: WallQuantitySettings, stories) -> SeismicDemand:
    seismic = settings.seismic
    if seismic.building_height_m is not None:
        height = seismic.building_height_m
    else:
        height = HEIGHT_BASE_OFFSET_M + sum(s.height_m for s in stories) + HEIGHT_TOP_OFFSET_M
    period = 0.03 * height

    if seismic.method == "spec":
        items, weights = _spec_weights(settings, stories)
    else:
        items = ()
        weights = []
        for st in stories:
            if st.weight_kN is None:
                raise WallQuantityError(
                    "wall_quantity.stories[" + st.name + "].weight_kN is required when seismic.method is direct"
                )
            weights.append(st.weight_kN)

    w_base = weights[0]
    out = []
    for st, w in zip(stories, weights):
        alpha = w / w_base
        ai = 1.0 if abs(alpha - 1.0) <= 1.0e-12 else layer_shear_distribution_ai(alpha, period)
        lw_raw = ai * seismic.c0 * w / (LW_DENOMINATOR * st.floor_area_m2)
        lw = round_up(lw_raw, 0)
        out.append(StorySeismicDemand(
            story=st.name,
            floor_area_m2=st.floor_area_m2,
            height_m=st.height_m,
            weight_kN=w,
            alpha=alpha,
            ai=ai,
            lw_raw_cm_m2=lw_raw,
            lw_cm_m2=lw,
            required_cm=lw * st.floor_area_m2,
        ))

    single_lw = None
    if len(stories) == 2:
        if seismic.single_story_lw_cm_m2 is not None:
            single_lw = seismic.single_story_lw_cm_m2
        elif seismic.method == "spec":
            single_lw = _spec_single_story_lw(settings, stories)
    return SeismicDemand(
        method=seismic.method,
        c0=seismic.c0,
        building_height_m=height,
        period_s=period,
        load_items=tuple(items),
        stories=tuple(out),
        single_story_lw_cm_m2=single_lw,
    )


def _spec_single_story_lw(settings, stories) -> float:
    """平屋の床面積に乗ずる数値 with the same specification and the 1F story height."""
    seismic = settings.seismic
    roof_total, wall_ins = _spec_roof_and_wall_insulation(settings, stories)
    wall1, _parts = _wall_floor_load(seismic, stories[0].height_m, wall_ins)
    w_per_area = roof_total / 1000.0 + 0.5 * wall1 / 1000.0
    return round_up(seismic.c0 * w_per_area / LW_DENOMINATOR, 0)


def _spec_roof_and_wall_insulation(settings, stories):
    seismic = settings.seismic
    roof = ROOF_UNIT_LOADS_N_M2[seismic.roof]
    solar = _solar_unit_load(seismic, stories)
    ceiling = _insulation_unit_load(seismic.ceiling_insulation, CEILING_INSULATION_DEFAULT_N_M2)
    wall_ins = _insulation_unit_load(seismic.wall_insulation, WALL_INSULATION_DEFAULT_N_M2)
    return roof + solar + ceiling, wall_ins


def _solar_unit_load(seismic, stories) -> float:
    if seismic.solar.mode == "none":
        return 0.0
    if seismic.solar.mode == "standard":
        return SOLAR_STANDARD_N_M2
    return seismic.solar.mass_kg / max(s.floor_area_m2 for s in stories) * GRAVITY


def _wall_area_factor(story_height_m: float, opening: bool) -> float:
    perimeter_area = (REF_PLAN_SHORT_M * story_height_m * 2.0 + REF_PLAN_LONG_M * story_height_m * 2.0)
    ratio = OPENING_RATIO if opening else (1.0 - OPENING_RATIO)
    return perimeter_area * ratio / (REF_PLAN_SHORT_M * REF_PLAN_LONG_M)


def _insulation_unit_load(ins, default_value):
    if ins.mode == "default":
        return default_value
    total = sum(l.density_kg_m3 * l.thickness_mm * GRAVITY / 1000.0 for l in ins.layers)
    return round_up(total, -1)


def _wall_floor_load(seismic, story_height_m, wall_ins_unit):
    """Story wall load per floor area of that story (N/m2) and its components."""
    exterior = round_up(
        EXTERIOR_WALL_UNIT_LOADS_N_M2[seismic.exterior_wall] * _wall_area_factor(story_height_m, False), -1
    )
    interior = INTERIOR_WALL_N_M2_PER_2_8M * story_height_m / 2.8
    insulation = round_up(wall_ins_unit * _wall_area_factor(story_height_m, False), -1)
    opening = round_up(OPENING_N_M2 * _wall_area_factor(story_height_m, True), -1)
    return exterior + interior + insulation + opening, (exterior, interior, insulation, opening)


def _spec_weights(settings, stories):
    seismic = settings.seismic
    roof = ROOF_UNIT_LOADS_N_M2[seismic.roof]
    solar = _solar_unit_load(seismic, stories)
    ceiling = _insulation_unit_load(seismic.ceiling_insulation, CEILING_INSULATION_DEFAULT_N_M2)
    wall_ins = _insulation_unit_load(seismic.wall_insulation, WALL_INSULATION_DEFAULT_N_M2)
    roof_total = roof + solar + ceiling

    items = [
        SeismicLoadItem("roof", "屋根（" + ROOF_LABELS_JA[seismic.roof] + "）", roof, "屋根面積当たり"),
        SeismicLoadItem("solar", "太陽光発電設備等", solar, _solar_basis(seismic.solar)),
        SeismicLoadItem("ceiling_insulation", "天井断熱材", ceiling, _insulation_basis(seismic.ceiling_insulation)),
        SeismicLoadItem(
            "exterior_wall", "外壁（" + EXTERIOR_WALL_LABELS_JA[seismic.exterior_wall] + "）",
            EXTERIOR_WALL_UNIT_LOADS_N_M2[seismic.exterior_wall], "外壁面積当たり",
        ),
        SeismicLoadItem("wall_insulation", "外壁断熱材", wall_ins,
                        "外壁面積当たり・" + _insulation_basis(seismic.wall_insulation)),
        SeismicLoadItem("opening", "開口部（トリプルガラス）", OPENING_N_M2, "開口部面積当たり（開口率9%）"),
        SeismicLoadItem("interior_wall", "内壁（せっこうボード）", INTERIOR_WALL_N_M2_PER_2_8M, "床面積当たり（階高2.8m時）"),
        SeismicLoadItem("floor", "床", FLOOR_N_M2, "床面積当たり"),
        SeismicLoadItem("live", "積載荷重（地震力算定用）", LIVE_LOAD_SEISMIC_N_M2, "床面積当たり"),
    ]

    if len(stories) == 1:
        s1 = stories[0]
        wall1, parts1 = _wall_floor_load(seismic, s1.height_m, wall_ins)
        items.append(_converted_wall_item(s1.name, wall1, parts1))
        w1_per_area = roof_total / 1000.0 + 0.5 * wall1 / 1000.0
        return tuple(items), [w1_per_area * s1.floor_area_m2]

    s1, s2 = stories[0], stories[1]
    af1, af2 = s1.floor_area_m2, s2.floor_area_m2
    r = af2 / af1
    wall2, parts2 = _wall_floor_load(seismic, s2.height_m, wall_ins)
    wall1, parts1 = _wall_floor_load(seismic, s1.height_m, wall_ins)
    items.append(_converted_wall_item(s2.name, wall2, parts2))
    items.append(_converted_wall_item(s1.name, wall1, parts1))

    # Loads per 1F floor area (kN/m2), as in the tool.
    g_roof2 = roof_total * r / 1000.0
    g_wall2 = wall2 * r / 1000.0
    g_floor2 = (FLOOR_N_M2 + LIVE_LOAD_SEISMIC_N_M2) * r / 1000.0
    g_wall1 = wall1 / 1000.0
    g_lean_to = (1.0 - r) * roof_total / 1000.0 if r < 1.0 else 0.0
    w2 = g_roof2 + 0.5 * g_wall2
    w1 = g_roof2 + g_wall2 + g_floor2 + 0.5 * g_wall1 + g_lean_to
    return tuple(items), [w1 * af1, w2 * af1]


def _converted_wall_item(story, total, parts):
    exterior, interior, insulation, opening = parts
    return SeismicLoadItem(
        "story_wall_" + story,
        story + "階 壁荷重（床面積換算）",
        total,
        "外壁{0:.0f}+内壁{1:.1f}+断熱{2:.0f}+開口{3:.0f}".format(exterior, interior, insulation, opening),
    )


def _solar_basis(solar):
    if solar.mode == "none":
        return "なし"
    if solar.mode == "standard":
        return "あり（260）"
    return "あり（{0:g} kg を最大床面積で均し）".format(solar.mass_kg)


def _insulation_basis(ins):
    if ins.mode == "default":
        return "初期値"
    return "任意入力（" + " + ".join(
        "{0:g}kg/m3×{1:g}mm".format(l.density_kg_m3, l.thickness_mm) for l in ins.layers
    ) + "）"


# ---------------------------------------------------------------------------
# Existing walls


def _story_for_z(z, stories) -> Optional[str]:
    for st in stories:
        if abs(z - st.elevation) <= STORY_Z_TOLERANCE_M:
            return st.name
    for st in stories:
        if st.elevation - STORY_Z_TOLERANCE_M <= z < st.elevation + st.height_m - STORY_Z_TOLERANCE_M:
            return st.name
    return None


def brace_height_reduction(length_m: float, height_m: Optional[float]) -> float:
    """αh = 3.5 Ld / H0 (≤ 1.0) for braced frames taller than 3.2 m."""
    if height_m is None or height_m <= BRACE_HEIGHT_LIMIT_M:
        return 1.0
    return min(1.0, 3.5 * length_m / height_m)


def _collect_rated_walls(mdl, settings, stories, warnings) -> List[WallEntry]:
    overrides = {w.wwll_id: w for w in settings.walls}
    story_names = set(s.name for s in stories)
    nodes_by_id = getattr(mdl, "nodes_by_id", {}) or {}
    known_ids = set()
    raw = []
    for w in getattr(mdl, "wwalls", []):
        known_ids.add(w.id)
        ov = overrides.get(w.id)
        if ov is not None and ov.exclude:
            continue
        node_ids = [n for n in (w.n1, w.n2, w.n3, w.n4) if n is not None]
        nodes = [nodes_by_id[n] for n in node_ids if n in nodes_by_id]
        x_c = y_c = None
        end_a = end_b = None
        story = ov.story if ov is not None and ov.story else None
        if len(nodes) == 4:
            z_min = min(n.z for n in nodes)
            bottom = [n for n in nodes if n.z <= z_min + 1.0e-6]
            x_c = sum(n.x for n in bottom) / len(bottom)
            y_c = sum(n.y for n in bottom) / len(bottom)
            # The parser normalizes N1, N2 to the bottom line and N3 above N2 (single brace N1 -> N3).
            n1, n2 = nodes_by_id[w.n1], nodes_by_id[w.n2]
            end_a, end_b = (n1.x, n1.y), (n2.x, n2.y)
            if story is None:
                story = _story_for_z(z_min, stories)
        if story is None:
            warnings.append("WWLL {0} ({1}): 階を特定できないため壁量に算入しません。".format(w.id, w.name))
            continue
        if story not in story_names:
            warnings.append("WWLL {0} ({1}): 階 {2} は壁量計算の対象外です。".format(w.id, w.name, story))
            continue
        length = w.length if w.length is not None else w.length_input
        height = w.height if w.height is not None else w.height_input
        if length is None:
            warnings.append("WWLL {0} ({1}): 長さが不明なため壁量に算入しません。".format(w.id, w.name))
            continue
        kind = ov.kind if ov is not None else "other"
        m_input = ov.multiplier if ov is not None and ov.multiplier is not None else w.multiplier
        alpha_h = brace_height_reduction(length, height) if kind == "brace" else 1.0
        if kind == "other" and height is not None and height > BRACE_HEIGHT_LIMIT_M:
            warnings.append(
                "WWLL {0} ({1}): 高さ {2:.3f} m > 3.2 m。筋かいの場合は walls[].kind=\"brace\" を指定して αh 低減を適用してください。".format(
                    w.id, w.name, height)
            )
        brace_section = brace_layout = ""
        brace_top = None
        if kind == "brace":
            brace_section = ov.brace_section
            brace_layout = ov.brace_layout or ("x" if str(w.brace_layout).upper() == "X" else "single")
            if brace_layout == "single":
                brace_top = end_b
        raw.append(dict(
            ref=str(w.id), name=w.name, story=story, direction=w.direction.lower(), kind=kind,
            length=length, height=height, m_input=m_input, alpha_h=alpha_h,
            m_reduced=m_input * alpha_h, x=x_c, y=y_c, notes=ov.notes if ov is not None else "",
            end_a=end_a, end_b=end_b, brace_section=brace_section, brace_layout=brace_layout,
            brace_top=brace_top,
        ))
    for wid in overrides:
        if wid not in known_ids:
            warnings.append("wall_quantity.walls: WWLL {0} はモデルに存在しません。".format(wid))

    # 倍率上限 7.0: walls sharing the same frame (same story, direction and position) are summed.
    groups: Dict[tuple, List[dict]] = {}
    for item in raw:
        if item["x"] is None:
            key = ("solo", item["ref"])
        else:
            key = (
                item["story"], item["direction"],
                round(item["x"] / SAME_FRAME_TOLERANCE_M), round(item["y"] / SAME_FRAME_TOLERANCE_M),
                round(item["length"] / SAME_FRAME_TOLERANCE_M),
            )
        item["group"] = key
        groups.setdefault(key, []).append(item)

    out = []
    for item in raw:
        members = groups[item["group"]]
        total = sum(m["m_reduced"] for m in members)
        scale = 1.0
        capped = False
        if total > DEFAULT_MULTIPLIER_CAP + 1.0e-12:
            scale = DEFAULT_MULTIPLIER_CAP / total
            capped = True
            if item is members[0]:
                warnings.append(
                    "WWLL {0}: 同一軸組の壁倍率の合計 {1:.2f} が 7.0 を超えるため 7.0 に調整しました。".format(
                        ", ".join(m["ref"] for m in members), total)
                )
        m_eff = item["m_reduced"] * scale
        out.append(WallEntry(
            source="WWLL",
            ref=item["ref"],
            name=item["name"],
            story=item["story"],
            direction=item["direction"],
            kind=item["kind"],
            length_m=item["length"],
            height_m=item["height"],
            multiplier_input=item["m_input"],
            alpha_h=item["alpha_h"],
            multiplier=m_eff,
            capped=capped,
            amount_cm=m_eff * item["length"] * 100.0,
            x_center=item["x"],
            y_center=item["y"],
            notes=item["notes"],
            multiplier_actual=item["m_reduced"],
            end_a=item["end_a"],
            end_b=item["end_b"],
            brace_section=item["brace_section"],
            brace_layout=item["brace_layout"],
            brace_top_end=item["brace_top"],
        ))
    return out


def quasi_wall_multiplier(q) -> float:
    ratio = q.material_height_m / q.clear_height_m
    if q.material == "panel":
        return q.base_multiplier * 0.6 * ratio
    return 0.5 * ratio


def _collect_quasi_walls(settings, stories, warnings) -> List[WallEntry]:
    story_names = set(s.name for s in stories)
    out = []
    for q in settings.quasi_walls:
        if q.story not in story_names:
            warnings.append("準耐力壁等 {0}: 階 {1} は壁量計算の対象外です。".format(q.name, q.story))
            continue
        if q.type == "quasi":
            if q.length_m < 0.9 - 1.0e-9:
                warnings.append("準耐力壁 {0}: 幅 {1:.2f} m < 0.90 m".format(q.name, q.length_m))
            if q.material_height_m < 0.8 * q.clear_height_m - 1.0e-9:
                warnings.append("準耐力壁 {0}: 材の高さが横架材間内法寸法の80%未満です。".format(q.name))
        else:
            if q.length_m < 0.9 - 1.0e-9 or q.length_m > 2.0 + 1.0e-9:
                warnings.append("垂れ壁・腰壁 {0}: 幅 {1:.2f} m が 0.90〜2.00 m の範囲外です。".format(q.name, q.length_m))
        m = quasi_wall_multiplier(q)
        end_a = end_b = None
        if q.x is not None and q.y is not None:
            half = 0.5 * q.length_m
            if q.direction == "x":
                end_a, end_b = (q.x - half, q.y), (q.x + half, q.y)
            else:
                end_a, end_b = (q.x, q.y - half), (q.x, q.y + half)
        out.append(WallEntry(
            source="QUASI",
            ref=q.name,
            name=q.name,
            story=q.story,
            direction=q.direction,
            kind=q.type,
            length_m=q.length_m,
            height_m=q.clear_height_m,
            multiplier_input=m,
            alpha_h=1.0,
            multiplier=m,
            capped=False,
            amount_cm=m * q.length_m * 100.0,
            x_center=q.x,
            y_center=q.y,
            notes=q.notes,
            multiplier_actual=m,
            end_a=end_a,
            end_b=end_b,
        ))
    return out


# ---------------------------------------------------------------------------
# Checks


def _check_stories(settings, stories, seismic, walls, warnings):
    coef = settings.wind.coefficient_cm_m2
    demand_by_story = {d.story: d for d in seismic.stories}
    rows = []
    for st in stories:
        demand = demand_by_story[st.name]
        for direction in ("x", "y"):
            wind_area = st.wind_area_x_m2 if direction == "x" else st.wind_area_y_m2
            if wind_area <= 0.0:
                warnings.append("{0}階 {1}方向: 見付面積が未入力です（風圧力の必要壁量 0）。".format(
                    st.name, direction.upper()))
            wind_req = wind_area * coef
            seis_req = demand.required_cm
            required = max(seis_req, wind_req)
            governing = "seismic" if seis_req >= wind_req else "wind"
            bearing = sum(w.amount_cm for w in walls if w.source == "WWLL" and w.story == st.name and w.direction == direction)
            quasi = sum(w.amount_cm for w in walls if w.source == "QUASI" and w.story == st.name and w.direction == direction)
            rows.append(dict(
                story=st.name, direction=direction, floor_area=st.floor_area_m2, lw=demand.lw_cm_m2,
                seis_req=seis_req, wind_area=wind_area, wind_req=wind_req, required=required,
                governing=governing, bearing=bearing, quasi=quasi,
            ))

    exceeds_any = any(r["quasi"] > 0.5 * r["required"] + 1.0e-9 for r in rows)
    if exceeds_any and not settings.quasi_over_half_verified:
        warnings.append(
            "準耐力壁等の壁量が必要壁量の1/2を超える階・方向があります。柱の折損等の脆性的な破壊が生じないことの確認が"
            "ないため、算入量を必要壁量の1/2までとしました（quasi_over_half_verified）。"
        )
    out = []
    for r in rows:
        half = 0.5 * r["required"]
        exceeds = r["quasi"] > half + 1.0e-9
        counted = r["quasi"]
        if exceeds and not settings.quasi_over_half_verified:
            counted = half
        existing = r["bearing"] + counted
        ratio = existing / r["required"] if r["required"] > 0.0 else float("inf")
        out.append(StoryDirectionCheck(
            story=r["story"],
            direction=r["direction"],
            floor_area_m2=r["floor_area"],
            lw_cm_m2=r["lw"],
            seismic_required_cm=r["seis_req"],
            wind_area_m2=r["wind_area"],
            wind_coefficient_cm_m2=coef,
            wind_required_cm=r["wind_req"],
            required_cm=r["required"],
            governing=r["governing"],
            bearing_cm=r["bearing"],
            quasi_raw_cm=r["quasi"],
            quasi_counted_cm=counted,
            quasi_exceeds_half=exceeds,
            existing_cm=existing,
            ratio=ratio,
            status="OK" if existing >= r["required"] - 1.0e-9 else "NG",
        ))
    return out, exceeds_any


def _applicability(stories, seismic):
    total_area = sum(s.floor_area_m2 for s in stories)
    rows = [
        {
            "item": "階数", "value": "{0}".format(len(stories)), "limit": "2以下",
            "status": "OK" if len(stories) <= APPLICABILITY_MAX_STORIES else "NG",
        },
        {
            "item": "延べ面積", "value": "{0:.2f} m2".format(total_area), "limit": "300 m2以下",
            "status": "OK" if total_area <= APPLICABILITY_MAX_TOTAL_FLOOR_AREA_M2 + 1.0e-9 else "NG",
        },
        {
            "item": "高さ", "value": "{0:.3f} m".format(seismic.building_height_m), "limit": "16 m以下",
            "status": "OK" if seismic.building_height_m <= APPLICABILITY_MAX_HEIGHT_M + 1.0e-9 else "NG",
        },
    ]
    return rows


# ---------------------------------------------------------------------------
# Helpers


def round_up(value: float, digits: int) -> float:
    """Excel ROUNDUP (away from zero) with a guard against float noise."""
    factor = 10.0 ** digits
    scaled = round(value * factor, 9)
    if scaled >= 0.0:
        return math.ceil(scaled) / factor
    return -math.ceil(-scaled) / factor
