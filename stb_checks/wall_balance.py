"""壁配置のバランス（四分割法）— 昭56建告第1100号第4 (2025年改正).

For each story and direction the plan is cut into quarters perpendicular to the
walls being checked. In each 側端部分 (outer quarter strip):

    必要壁量 = 側端部分の床面積 × 床面積に乗ずる数値 (地震力)
    存在壁量 = Σ(壁倍率 × 長さ) of the walls inside the strip (on the 1/4 line included)
    壁量充足率 = 存在壁量 / 必要壁量

The story/direction passes when both 充足率 > 1.0, or 壁率比 (small/large) ≥ 0.5.

1F strips of a two-story building use the 2階建ての1階 value when any part of
the 2nd floor is above the strip, otherwise the 平屋 value (審査マニュアル 図3-18).
準耐力壁等 are only included when they exceed 1/2 of the required quantity
(補足資料 p.6). When a frame exceeds the 7.0 multiplier cap the check is made both
with the capped multipliers and with the actual (実態) multipliers.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from shapely.geometry import MultiPoint, Polygon, box
from shapely.ops import unary_union


LINE_TOLERANCE_M = 0.005
AREA_TOLERANCE_M2 = 1.0e-6

SIDE_LABELS = {"x": ("下", "上"), "y": ("左", "右")}


@dataclass(frozen=True)
class StripResult:
    side: str                      # 下/上 (X direction) or 左/右 (Y direction)
    band: Tuple[float, float]      # coordinate range of the strip (y for X walls, x for Y walls)
    area_m2: float
    lw_cm_m2: float
    lw_basis: str                  # "2階建ての1階" / "平屋" / "2階建ての2階" / "平屋建て"
    required_cm: float
    existing_cm: float
    existing_actual_cm: float
    fill_ratio: float
    fill_ratio_actual: float
    wall_refs: Tuple[str, ...]


@dataclass(frozen=True)
class BalanceCheck:
    story: str
    direction: str
    strips: Tuple[StripResult, StripResult]
    wall_ratio: float
    status_capped: str
    wall_ratio_actual: float
    status_actual: str
    actual_checked: bool           # True when some frame exceeded the 7.0 cap
    status: str


@dataclass(frozen=True)
class WallBalanceSummary:
    checks: Tuple[BalanceCheck, ...]
    includes_quasi_walls: bool
    status: str


def compute_wall_balance(settings, stories, seismic, walls, quasi_exceeds_half, warnings) -> Optional[WallBalanceSummary]:
    plans = {}
    for st in stories:
        plan = _story_plan(st, walls, warnings)
        if plan is not None:
            plans[st.name] = plan
    if not plans:
        warnings.append("四分割法: 平面形状（plan_polygons）も壁の位置もないため検討できません。")
        return None

    demand = {d.story: d for d in seismic.stories}
    two_story = len(stories) == 2
    upper_plan = plans.get(stories[1].name) if two_story else None
    use_quasi = quasi_exceeds_half
    candidates = [w for w in walls if w.source == "WWLL" or use_quasi]
    if use_quasi:
        for w in walls:
            if w.source == "QUASI" and w.x_center is None:
                warnings.append("四分割法: 準耐力壁等 {0} に位置（x, y）がないため算入しません。".format(w.ref))
    actual_needed = any(w.capped for w in candidates)

    checks = []
    for idx, st in enumerate(stories):
        plan = plans.get(st.name)
        if plan is None:
            continue
        for direction in ("x", "y"):
            strips = []
            minx, miny, maxx, maxy = plan.bounds
            lo, hi = (miny, maxy) if direction == "x" else (minx, maxx)
            quarter = (hi - lo) / 4.0
            for side, band in zip(SIDE_LABELS[direction], ((lo, lo + quarter), (hi - quarter, hi))):
                strip_geom = _band_box(plan, direction, band)
                strip = plan.intersection(strip_geom)
                area = strip.area
                lw, basis = _strip_lw(idx, two_story, st, demand, seismic, upper_plan, strip_geom, warnings)
                required = area * lw
                members = [
                    w for w in candidates
                    if w.story == st.name and w.direction == direction and w.x_center is not None
                    and _in_band(w, direction, band)
                ]
                existing = sum(w.amount_cm for w in members)
                existing_actual = sum(w.actual_multiplier * w.length_m * 100.0 for w in members)
                strips.append(StripResult(
                    side=side,
                    band=band,
                    area_m2=area,
                    lw_cm_m2=lw,
                    lw_basis=basis,
                    required_cm=required,
                    existing_cm=existing,
                    existing_actual_cm=existing_actual,
                    fill_ratio=_ratio(existing, required),
                    fill_ratio_actual=_ratio(existing_actual, required),
                    wall_refs=tuple(w.ref for w in members),
                ))
            ratio, status_c = _judge(strips[0].fill_ratio, strips[1].fill_ratio)
            ratio_a, status_a = _judge(strips[0].fill_ratio_actual, strips[1].fill_ratio_actual)
            if not actual_needed:
                ratio_a, status_a = ratio, status_c
            checks.append(BalanceCheck(
                story=st.name,
                direction=direction,
                strips=(strips[0], strips[1]),
                wall_ratio=ratio,
                status_capped=status_c,
                wall_ratio_actual=ratio_a,
                status_actual=status_a,
                actual_checked=actual_needed,
                status="OK" if status_c == "OK" and status_a == "OK" else "NG",
            ))

    status = "OK" if checks and all(c.status == "OK" for c in checks) else "NG"
    return WallBalanceSummary(checks=tuple(checks), includes_quasi_walls=use_quasi, status=status)


def _story_plan(st, walls, warnings):
    if st.plan_polygons:
        polys = [Polygon(p) for p in st.plan_polygons]
        for i, p in enumerate(polys):
            if not p.is_valid or p.area <= AREA_TOLERANCE_M2:
                raise ValueError("wall_quantity.stories[{0}].plan_polygons[{1}] is not a valid polygon".format(st.name, i))
        plan = unary_union(polys)
        if abs(plan.area - st.floor_area_m2) > max(0.01 * st.floor_area_m2, 0.01):
            warnings.append(
                "{0}階: plan_polygons の面積 {1:.2f} m2 と floor_area_m2 {2:.2f} m2 が一致しません。".format(
                    st.name, plan.area, st.floor_area_m2)
            )
        return plan
    points = []
    for w in walls:
        if w.story == st.name and w.end_a is not None:
            points.extend([w.end_a, w.end_b])
    if len(points) < 3:
        return None
    hull = MultiPoint(points).envelope
    if hull.area <= AREA_TOLERANCE_M2:
        return None
    warnings.append(
        "{0}階: plan_polygons が未入力のため、壁端点の外接矩形（{1:.2f} m2）を平面形状として四分割法を行いました。".format(
            st.name, hull.area)
    )
    return hull


def _band_box(plan, direction, band):
    minx, miny, maxx, maxy = plan.bounds
    pad = 1.0
    if direction == "x":
        return box(minx - pad, band[0], maxx + pad, band[1])
    return box(band[0], miny - pad, band[1], maxy + pad)


def _strip_lw(idx, two_story, st, demand, seismic, upper_plan, strip_geom, warnings):
    lw = demand[st.name].lw_cm_m2
    if not two_story:
        return lw, "平屋建て"
    if idx == 1:
        return lw, "2階建ての2階"
    if upper_plan is not None and upper_plan.intersection(strip_geom).area > AREA_TOLERANCE_M2:
        return lw, "2階建ての1階"
    if upper_plan is None:
        warnings.append("四分割法: 2階の plan_polygons がないため、1階の側端部分はすべて2階建ての1階の数値で検討しました。")
        return lw, "2階建ての1階"
    if seismic.single_story_lw_cm_m2 is None:
        warnings.append(
            "四分割法: 2階のかからない1階側端部分がありますが、平屋の数値がないため2階建ての1階の数値で検討しました"
            "（seismic.single_story_lw_cm_m2）。"
        )
        return lw, "2階建ての1階"
    return seismic.single_story_lw_cm_m2, "平屋"


def _in_band(wall, direction, band):
    coord = wall.y_center if direction == "x" else wall.x_center
    return band[0] - LINE_TOLERANCE_M <= coord <= band[1] + LINE_TOLERANCE_M


def _ratio(existing, required):
    if required <= 0.0:
        return float("inf")
    return existing / required


def _judge(r1, r2):
    small, large = min(r1, r2), max(r1, r2)
    if large == float("inf"):
        wall_ratio = 1.0 if small == float("inf") else 0.0
    elif large <= 0.0:
        wall_ratio = 0.0
    else:
        wall_ratio = small / large
    ok = (r1 > 1.0 and r2 > 1.0) or wall_ratio >= 0.5 - 1.0e-12
    return wall_ratio, "OK" if ok else "NG"
