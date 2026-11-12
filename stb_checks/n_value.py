"""柱頭・柱脚の接合方法（N値計算法）— 平12建告第1460号 (2025年改正).

Following the 確認申請・審査マニュアル 第3版 (図3-19, 表3-14〜3-16):

    平屋・2階建ての2階・2階のない1階部分:
        N = A1·B1·H1/2.7 − L
    2階建ての1階で上に2階がある部分:
        N = A1·B1·H1/2.7 + A2·B2·H2/2.7 − L

    A1, A2 : 柱の両側の壁倍率の差（筋かいは表3-14の補正値を加算）
    B1, B2 : 出隅 0.8, その他 0.5
    L      : 平屋等 出隅 0.4 / その他 0.6;  2階建ての1階 出隅 1.0 / その他 1.6
    H1, H2 : 横架材の上端の相互間の垂直距離 (3.2 m以下は 2.7 とする)

N is computed for X and Y and the larger value governs. Walls use the 実態倍率
(after αh, without the 7.0 cap). 準耐力壁等 are treated as multiplier 0 unless
they exceed 1/2 of the required quantity, except frames whose 準耐力壁等 multiplier
exceeds 1.5 (補足資料 p.6 / 審査マニュアル p.101).
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Tuple

from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.geometry import Polygon


POINT_TOLERANCE_M = 0.005
QUASI_N_VALUE_MULTIPLIER_LIMIT = 1.5
REFERENCE_HEIGHT_M = 2.7
HEIGHT_LIMIT_M = 3.2

BRACE_INDEX = {"15x90": 0, "30x90": 1, "45x90": 2, "90x90": 3}
# 表3-14 (柱の片側のみに筋かい: 柱頭側 +, 柱脚側 −; たすき掛け 0)
BRACE_SINGLE = (0.0, 0.5, 0.5, 2.0)
# 両側に筋かい, 両方の筋かいの上端がこの柱に取り付く (Λ). [left][right]
BRACE_BOTH_TOP = (
    (0.0, 0.5, 0.5, 2.0),
    (0.5, 1.0, 1.0, 2.5),
    (0.5, 1.0, 1.0, 2.5),
    (2.0, 2.5, 2.5, 4.0),
)
# 両側に筋かい, 一方は上端・他方は下端がこの柱に取り付く (//). [top brace][bottom brace]
BRACE_TOP_BOTTOM = (
    (0.0, -0.5, -0.5, 2.0),
    (0.5, 0.5, 0.0, 1.5),
    (0.5, 0.5, 0.5, 1.5),
    (2.0, 1.5, 1.5, 2.0),
)

# 表3-16 / 平12建告1460号表3: (記号, N値の上限, 必要耐力 kN)
JOINT_SPECS = (
    ("い", 0.0, 0.0),
    ("ろ", 0.65, 3.4),
    ("は", 1.0, 5.1),
    ("に", 1.4, 7.5),
    ("ほ", 1.6, 8.5),
    ("へ", 1.8, 10.0),
    ("と", 2.8, 15.0),
    ("ち", 3.7, 20.0),
    ("り", 4.7, 25.0),
    ("ぬ", 5.6, 30.0),
)
N_VALUE_KN = 5.3


@dataclass(frozen=True)
class DirectionNValue:
    direction: str
    multiplier_neg: float          # walls on the negative side of the column (along the wall axis)
    multiplier_pos: float
    brace_correction: float
    a1: float
    b1: float
    h1_factor: float
    a2: float
    b2: float
    h2_factor: float
    l: float
    n: float
    wall_refs: Tuple[str, ...]


@dataclass(frozen=True)
class ColumnNValue:
    story: str
    x: float
    y: float
    name: str
    corner: bool
    corner_source: str             # "override" / "plan" / "walls"
    upper_story_above: bool
    formula: str                   # "single" / "lower"
    directions: Tuple[DirectionNValue, ...]
    governing_direction: str
    n: float
    joint: str                     # (い)〜(ぬ), or "要検討" above 5.6
    required_kN: float


@dataclass(frozen=True)
class NValueSummary:
    columns: Tuple[ColumnNValue, ...]
    includes_quasi_walls: bool
    status: str                    # NG when some column needs N > 5.6 (outside 表3-16)


def select_joint(n: float):
    for mark, limit, kn in JOINT_SPECS:
        if n <= limit + 1.0e-9:
            return mark, kn
    return "要検討", N_VALUE_KN * n


def height_factor(height_m: float) -> float:
    h = height_m if height_m > HEIGHT_LIMIT_M + 1.0e-9 else REFERENCE_HEIGHT_M
    return h / REFERENCE_HEIGHT_M


def brace_correction(side_a, side_b) -> float:
    """Correction of 表3-14. Each side is None or (section, orientation) with orientation top/bottom/x."""
    sides = [s for s in (side_a, side_b) if s is not None]
    if not sides:
        return 0.0
    if len(sides) == 1:
        section, orient = sides[0]
        if orient == "x":
            return 0.0
        value = BRACE_SINGLE[BRACE_INDEX[section]]
        return value if orient == "top" else -value
    (sa, oa), (sb, ob) = side_a, side_b
    if oa == "x" and ob == "x":
        return 0.0
    if oa == "x" or ob == "x":
        single_section, single_orient = (sb, ob) if oa == "x" else (sa, oa)
        return BRACE_SINGLE[BRACE_INDEX[single_section]] if single_orient == "top" else 0.0
    if oa == "top" and ob == "top":
        return BRACE_BOTH_TOP[BRACE_INDEX[sa]][BRACE_INDEX[sb]]
    if oa == "bottom" and ob == "bottom":
        return 0.0
    top_section, bottom_section = (sa, sb) if oa == "top" else (sb, sa)
    return BRACE_TOP_BOTTOM[BRACE_INDEX[top_section]][BRACE_INDEX[bottom_section]]


# ---------------------------------------------------------------------------


@dataclass
class _Side:
    multiplier: float = 0.0
    brace: Optional[Tuple[str, str]] = None
    refs: Tuple[str, ...] = ()


@dataclass
class _Column:
    x: float
    y: float
    sides: Dict[Tuple[str, int], _Side]


def compute_n_values(settings, stories, walls, quasi_exceeds_half, warnings) -> Optional[NValueSummary]:
    participating = _participating_walls(walls, quasi_exceeds_half, warnings)
    if not participating:
        warnings.append("N値計算: 位置の分かる耐力壁がないため検討できません。")
        return None

    story_names = [s.name for s in stories]
    columns_by_story = {name: _collect_columns([w for w in participating if w.story == name], warnings)
                        for name in story_names}
    plans = {s.name: _plan(s) for s in stories}
    overrides = {}
    for c in settings.columns:
        overrides.setdefault(c.story, []).append(c)

    results: Dict[str, Dict[tuple, ColumnNValue]] = {}
    # Upper (or only) story first, so 1F columns can reference A2.
    for idx in reversed(range(len(stories))):
        st = stories[idx]
        is_lower = len(stories) == 2 and idx == 0
        upper = stories[1] if is_lower else None
        out = {}
        story_cols = dict(columns_by_story[st.name])
        if is_lower:
            # 1F columns below 2F wall-end columns carry A2 even without 1F walls.
            for ukey, ucol in results[upper.name].items():
                if ukey not in story_cols and _near_column(story_cols, ucol) is None:
                    story_cols[ukey] = _Column(x=ucol.x, y=ucol.y, sides={})
        for key, col in story_cols.items():
            corner, corner_src, name = _corner(st.name, col, plans[st.name], overrides)
            above = False
            upper_col = None
            if is_lower:
                upper_col = results[upper.name].get(key) or _near(results[upper.name], col)
                if plans[upper.name] is not None:
                    above = plans[upper.name].buffer(POINT_TOLERANCE_M).covers(Point(col.x, col.y))
                else:
                    above = upper_col is not None
            dirs = []
            for direction in ("x", "y"):
                neg = col.sides.get((direction, -1), _Side())
                pos = col.sides.get((direction, 1), _Side())
                upper_dir = []
                if is_lower and above and upper_col is not None:
                    upper_dir = [d for d in upper_col.directions if d.direction == direction]
                if not neg.refs and not pos.refs and not upper_dir:
                    continue
                corr = brace_correction(neg.brace, pos.brace)
                a1 = abs(pos.multiplier - neg.multiplier) + corr
                b1 = 0.8 if corner else 0.5
                h1 = height_factor(st.height_m)
                a2 = b2 = 0.0
                h2 = 0.0
                if is_lower and above:
                    l_value = 1.0 if corner else 1.6
                    if upper_col is not None:
                        if upper_dir:
                            a2 = upper_dir[0].a1
                        b2 = 0.8 if upper_col.corner else 0.5
                    h2 = height_factor(upper.height_m)
                else:
                    l_value = 0.4 if corner else 0.6
                n = a1 * b1 * h1 + a2 * b2 * h2 - l_value
                dirs.append(DirectionNValue(
                    direction=direction,
                    multiplier_neg=neg.multiplier,
                    multiplier_pos=pos.multiplier,
                    brace_correction=corr,
                    a1=a1, b1=b1, h1_factor=h1,
                    a2=a2, b2=b2, h2_factor=h2,
                    l=l_value,
                    n=n,
                    wall_refs=tuple(sorted(set(neg.refs + pos.refs))),
                ))
            if not dirs:
                continue
            governing = max(dirs, key=lambda d: d.n)
            joint, kn = select_joint(governing.n)
            out[key] = ColumnNValue(
                story=st.name, x=col.x, y=col.y, name=name,
                corner=corner, corner_source=corner_src,
                upper_story_above=above,
                formula="lower" if is_lower and above else "single",
                directions=tuple(dirs),
                governing_direction=governing.direction,
                n=governing.n,
                joint=joint,
                required_kN=kn,
            )
        results[st.name] = out

    columns = []
    for st in stories:
        columns.extend(sorted(results[st.name].values(), key=lambda c: (c.y, c.x)))
    status = "OK" if all(c.joint != "要検討" for c in columns) else "NG"
    for c in columns:
        if c.joint == "要検討":
            warnings.append("N値計算: {0}階 ({1:.3f}, {2:.3f}) の N={3:.2f} は表3-16の範囲外です（必要耐力 {4:.1f} kN）。".format(
                c.story, c.x, c.y, c.n, c.required_kN))
    return NValueSummary(columns=tuple(columns), includes_quasi_walls=quasi_exceeds_half, status=status)


def _participating_walls(walls, quasi_exceeds_half, warnings):
    out = []
    quasi_frames: Dict[tuple, List] = {}
    for w in walls:
        if w.end_a is None:
            if w.source == "WWLL":
                warnings.append("N値計算: WWLL {0} に節点位置がないため算入しません。".format(w.ref))
            continue
        if w.source == "WWLL":
            out.append(w)
        else:
            quasi_frames.setdefault(_frame_key(w), []).append(w)
    for members in quasi_frames.values():
        total = sum(m.actual_multiplier for m in members)
        if quasi_exceeds_half or total > QUASI_N_VALUE_MULTIPLIER_LIMIT + 1.0e-9:
            out.extend(members)
    if not quasi_exceeds_half:
        for w in walls:
            if w.source == "QUASI" and w.end_a is None and w.multiplier > QUASI_N_VALUE_MULTIPLIER_LIMIT:
                warnings.append("N値計算: 準耐力壁等 {0}（倍率1.5超）に位置がないため算入できません。".format(w.ref))
    return out


def _frame_key(w):
    return (w.story, w.direction, _round(w.end_a), _round(w.end_b))


def _round(p):
    return (round(p[0] / POINT_TOLERANCE_M), round(p[1] / POINT_TOLERANCE_M))


def _collect_columns(walls, warnings) -> Dict[tuple, _Column]:
    cols: Dict[tuple, _Column] = {}
    for w in walls:
        axis = 0 if w.direction == "x" else 1
        for end, other in ((w.end_a, w.end_b), (w.end_b, w.end_a)):
            key = _round(end)
            col = cols.get(key)
            if col is None:
                col = cols[key] = _Column(x=end[0], y=end[1], sides={})
            sign = 1 if other[axis] > end[axis] else -1
            side = col.sides.setdefault((w.direction, sign), _Side())
            side.multiplier += w.actual_multiplier
            side.refs = side.refs + (w.ref,)
            if w.kind == "brace":
                if not w.brace_section:
                    warnings.append("N値計算: 筋かい WWLL {0} の brace_section が未入力のため補正値を 0 としました。".format(w.ref))
                elif side.brace is None:
                    if w.brace_layout == "x":
                        orient = "x"
                    else:
                        orient = "top" if w.brace_top_end is not None and _round(w.brace_top_end) == key else "bottom"
                    side.brace = (w.brace_section, orient)
    return cols


def _plan(st):
    if not st.plan_polygons:
        return None
    return unary_union([Polygon(p) for p in st.plan_polygons])


def _near(columns: Dict[tuple, ColumnNValue], col):
    for c in columns.values():
        if math.hypot(c.x - col.x, c.y - col.y) <= POINT_TOLERANCE_M:
            return c
    return None


def _near_column(columns: Dict[tuple, _Column], col):
    for c in columns.values():
        if math.hypot(c.x - col.x, c.y - col.y) <= POINT_TOLERANCE_M:
            return c
    return None


def _corner(story, col, plan, overrides):
    for ov in overrides.get(story, []):
        if math.hypot(ov.x - col.x, ov.y - col.y) <= POINT_TOLERANCE_M:
            if ov.corner is not None:
                return ov.corner, "override", ov.name
            name = ov.name
            break
    else:
        name = ""
    if plan is not None:
        return _is_convex_vertex(plan, col.x, col.y), "plan", name
    # Fallback: L-shaped junction (walls in both directions, each on one side only).
    one_sided = 0
    for direction in ("x", "y"):
        has_neg = (direction, -1) in col.sides
        has_pos = (direction, 1) in col.sides
        if has_neg != has_pos:
            one_sided += 1
    return one_sided == 2, "walls", name


def _is_convex_vertex(plan, x, y) -> bool:
    geoms = getattr(plan, "geoms", [plan])
    for poly in geoms:
        ring = poly.exterior
        coords = list(ring.coords)[:-1]
        ccw = ring.is_ccw
        n = len(coords)
        for i, (vx, vy) in enumerate(coords):
            if math.hypot(vx - x, vy - y) > POINT_TOLERANCE_M:
                continue
            px, py = coords[i - 1]
            nx, ny = coords[(i + 1) % n]
            cross = (vx - px) * (ny - vy) - (vy - py) * (nx - vx)
            return cross > 0.0 if ccw else cross < 0.0
    return False
