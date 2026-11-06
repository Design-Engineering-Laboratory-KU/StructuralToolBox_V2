"""柱の小径 — 令第43条第1項・第6項, 平12建告第1349号 (2025年改正).

Implements the three methods of the 日本住宅・木材技術センター 表計算ツール
（在来軸組工法用 ver1.2）, which are based on the buckling formula of the 告示:

2-1 / 2-2  必要小径 de (mm) for a column material (Fc). 2-1 is すぎ無等級 (Fc 17.7);
           2-2 is the material chosen per story. The tool uses the 外周部 column load
           and a load-bearing area Ae = 5 m2::

               U  = sqrt(Wd·Ae / (1.1/3·Fc))                       (short column)
               de = (12 l^2 / 3000 · U^2)^(1/4)          if l/52.7 > U   (λ > 100)
               de = U                                    if l/8.66 < U   (λ ≤ 30)
               de = l/75.05 + sqrt((l/75.05)^2 + U^2/1.3)  otherwise
               de = max(roundup(de), roundup(sqrt(12)·l/150))   (有効細長比 ≤ 150)

2-3        柱の負担可能面積 (m2) for a b x d column (外周部 / 内部)::

               λ = 3.46 l / min(b, d);  η = 1 (λ≤30), 1.3−0.01λ (λ≤100), 3000/λ² (λ>100)
               A = rounddown(1.1/3 · η · Fc · b · d / Wd / 1000, 1)

Wd (kN/m2) is the 固定荷重と積載荷重 per floor area carried by a column (積載 1300
N/m2 for columns, no snow). l = 横架材相互間の垂直距離 = 階高 − 105 mm (平屋・2階)
or − 120 mm (2階建ての1階), as in the tool.
"""

from dataclasses import dataclass
import math
from typing import List, Optional, Tuple

from stb_checks.wall_quantity import (
    FLOOR_N_M2,
    INTERIOR_WALL_N_M2_PER_2_8M,
    _spec_roof_and_wall_insulation,
    _story_for_z,
    _wall_floor_load,
    round_up,
)


DEFAULT_COLUMN_FC = 17.7            # すぎ 無等級材 (method 2-1)
DEFAULT_COLUMN_LABEL = "無等級材 すぎ"
LIVE_LOAD_COLUMN_N_M2 = 1300.0      # 積載（柱算定用）
COLUMN_LOAD_AREA_M2 = 5.0           # Ae used by the tool for 2-1 / 2-2
BEAM_DEPTH_TOP_MM = 105.0           # 平屋・2階建ての2階
BEAM_DEPTH_LOWER_MM = 120.0         # 2階建ての1階
MAX_SLENDERNESS = 150.0
VERTICAL_TOLERANCE_M = 0.001


@dataclass(frozen=True)
class StoryColumnRequirement:
    story: str
    length_mm: float               # l
    outer_load_kN_m2: float        # Wd 外周部の柱
    inner_load_kN_m2: float        # Wd 内部の柱
    material_label: str
    fc_n_mm2: float
    required_mm: float             # de (method 2-2 with the story material; 2-1 when default)
    required_ratio_text: str       # "1/27.1"
    default_required_mm: float     # 2-1: すぎ無等級
    allowable_areas: Tuple[dict, ...]  # 2-3 for 105/120 square columns, outer/inner


@dataclass(frozen=True)
class ModelColumnCheck:
    story: str
    section: str
    b_mm: float
    d_mm: float
    element_ids: Tuple[int, ...]
    required_mm: float
    slenderness: float
    status: str


@dataclass(frozen=True)
class TributaryCheck:
    name: str
    story: str
    location: str
    b_mm: float
    d_mm: float
    area_m2: float
    allowable_m2: Optional[float]  # None when 有効細長比 > 150
    status: str


@dataclass(frozen=True)
class ColumnSizeSummary:
    stories: Tuple[StoryColumnRequirement, ...]
    model_columns: Tuple[ModelColumnCheck, ...]
    tributary_checks: Tuple[TributaryCheck, ...]
    status: str


# ---------------------------------------------------------------------------
# Formulas


def required_column_size_mm(wd_kN_m2: float, length_mm: float, fc_n_mm2: float,
                            load_area_m2: float = COLUMN_LOAD_AREA_M2) -> float:
    u = math.sqrt(wd_kN_m2 * load_area_m2 / (1.1 / 3.0 * fc_n_mm2) * 1000.0)
    l = length_mm
    if l / 52.7 > u:
        de = (12.0 * l * l / 3000.0 * u * u) ** 0.25
    elif l / 8.66 < u:
        de = u
    else:
        de = l / 75.05 + math.sqrt((l / 75.05) ** 2 + u * u / 1.3)
    slender = math.sqrt(12.0) * l / MAX_SLENDERNESS
    return max(round_up(de, 0), round_up(slender, 0))


def buckling_factor(slenderness: float) -> float:
    if slenderness <= 30.0:
        return 1.0
    if slenderness > 100.0:
        return 3000.0 / slenderness ** 2
    return 1.3 - 0.01 * slenderness


def allowable_load_area_m2(b_mm: float, d_mm: float, wd_kN_m2: float, length_mm: float,
                           fc_n_mm2: float) -> Optional[float]:
    """2-3 柱の負担可能面積. None when 有効細長比 exceeds 150."""
    small = min(b_mm, d_mm)
    if length_mm / small > 43.3:
        return None
    eta = buckling_factor(3.46 * length_mm / small)
    value = 1.1 / 3.0 * eta * fc_n_mm2 * b_mm * d_mm / wd_kN_m2 / 1000.0
    return math.floor(round(value * 10.0, 9)) / 10.0


def ratio_text(length_mm: float, de_mm: float) -> str:
    return "1/{0:.1f}".format(math.floor(round(length_mm / de_mm * 10.0, 9)) / 10.0)


# ---------------------------------------------------------------------------


def compute_column_size(mdl, settings, stories, warnings) -> Optional[ColumnSizeSummary]:
    cs = settings.column_size
    if not cs.enabled:
        return None
    overrides = {s.story: s for s in cs.stories}
    for name in overrides:
        if name not in [s.name for s in stories]:
            warnings.append("柱の小径: column_size.stories の階 {0} は対象外です。".format(name))
    loads = _column_loads(settings, stories, overrides, warnings)
    if loads is None:
        return None

    reqs = []
    for idx, st in enumerate(stories):
        ov = overrides.get(st.name)
        lower = len(stories) == 2 and idx == 0
        if ov is not None and ov.length_mm is not None:
            length = ov.length_mm
        else:
            length = st.height_m * 1000.0 - (BEAM_DEPTH_LOWER_MM if lower else BEAM_DEPTH_TOP_MM)
        fc, label = _story_material(ov)
        outer, inner = loads[st.name]
        de = required_column_size_mm(outer, length, fc)
        de_default = required_column_size_mm(outer, length, DEFAULT_COLUMN_FC)
        areas = []
        for size in (105.0, 120.0):
            for location, wd in (("outer", outer), ("inner", inner)):
                areas.append({
                    "size_mm": size,
                    "location": location,
                    "allowable_m2": allowable_load_area_m2(size, size, wd, length, fc),
                })
        reqs.append(StoryColumnRequirement(
            story=st.name,
            length_mm=length,
            outer_load_kN_m2=outer,
            inner_load_kN_m2=inner,
            material_label=label,
            fc_n_mm2=fc,
            required_mm=de,
            required_ratio_text=ratio_text(length, de),
            default_required_mm=de_default,
            allowable_areas=tuple(areas),
        ))

    req_by_story = {r.story: r for r in reqs}
    model_checks = _check_model_columns(mdl, stories, req_by_story, warnings) if cs.check_model_columns else []

    tributary = []
    for t in cs.tributary_checks:
        req = req_by_story.get(t.story)
        if req is None:
            warnings.append("柱の小径: tributary_checks の階 {0} は対象外です。".format(t.story))
            continue
        wd = req.outer_load_kN_m2 if t.location == "outer" else req.inner_load_kN_m2
        allowable = allowable_load_area_m2(t.b_mm, t.d_mm, wd, req.length_mm, req.fc_n_mm2)
        status = "OK" if allowable is not None and t.area_m2 <= allowable + 1.0e-9 else "NG"
        tributary.append(TributaryCheck(
            name=t.name, story=t.story, location=t.location, b_mm=t.b_mm, d_mm=t.d_mm,
            area_m2=t.area_m2, allowable_m2=allowable, status=status,
        ))

    statuses = [c.status for c in model_checks] + [t.status for t in tributary]
    status = "OK" if all(s == "OK" for s in statuses) else "NG"
    return ColumnSizeSummary(
        stories=tuple(reqs),
        model_columns=tuple(model_checks),
        tributary_checks=tuple(tributary),
        status=status,
    )


def _story_material(ov):
    if ov is None:
        return DEFAULT_COLUMN_FC, DEFAULT_COLUMN_LABEL
    if ov.fc_n_mm2 is not None:
        return ov.fc_n_mm2, ov.label or "Fc={0:g}".format(ov.fc_n_mm2)
    if ov.jas:
        from stb_project.column_fc_table import lookup_column_fc

        fc = lookup_column_fc(ov.jas, ov.species, ov.grade)
        label = ov.label or " ".join(v for v in (ov.jas, ov.species, ov.grade) if v)
        return fc, label
    return DEFAULT_COLUMN_FC, ov.label or DEFAULT_COLUMN_LABEL


def _column_loads(settings, stories, overrides, warnings):
    """Wd for 外周部 / 内部 columns per story (kN/m2)."""
    computed = {}
    if settings.seismic.method == "spec":
        seismic = settings.seismic
        roof_total, wall_ins = _spec_roof_and_wall_insulation(settings, stories)
        roof = roof_total / 1000.0
        floor = (FLOOR_N_M2 + LIVE_LOAD_COLUMN_N_M2) / 1000.0

        def wall(h):
            return _wall_floor_load(seismic, h, wall_ins)[0] / 1000.0

        def interior(h):
            return INTERIOR_WALL_N_M2_PER_2_8M * h / 2.8 / 1000.0

        if len(stories) == 1:
            h1 = stories[0].height_m
            computed[stories[0].name] = (roof + 0.5 * wall(h1), roof + 0.5 * interior(h1))
        else:
            h1, h2 = stories[0].height_m, stories[1].height_m
            computed[stories[1].name] = (roof + 0.5 * wall(h2), roof + 0.5 * interior(h2))
            computed[stories[0].name] = (
                roof + wall(h2) + floor + 0.5 * wall(h1),
                roof + interior(h2) + floor + 0.5 * interior(h1),
            )
    out = {}
    for st in stories:
        ov = overrides.get(st.name)
        outer, inner = computed.get(st.name, (None, None))
        if ov is not None and ov.outer_load_kN_m2 is not None:
            outer = ov.outer_load_kN_m2
        if ov is not None and ov.inner_load_kN_m2 is not None:
            inner = ov.inner_load_kN_m2
        if outer is None or inner is None:
            warnings.append(
                "柱の小径: {0}階の柱の負担荷重 Wd が不明です（seismic.method=direct の場合は "
                "column_size.stories[].outer_load_kN_m2 / inner_load_kN_m2 を入力）。".format(st.name)
            )
            return None
        out[st.name] = (outer, inner)
    return out


def _check_model_columns(mdl, stories, req_by_story, warnings) -> List[ModelColumnCheck]:
    groups = {}
    for e in getattr(mdl, "elms", []):
        if getattr(e, "auto_generated", False):
            continue
        n0, n1 = e.n0, e.n1
        if math.hypot(n0.x - n1.x, n0.y - n1.y) > VERTICAL_TOLERANCE_M or abs(n0.z - n1.z) <= VERTICAL_TOLERANCE_M:
            continue
        sec = e.sec
        if sec is None or sec.type != 0:
            continue
        story = _story_for_z(min(n0.z, n1.z), stories)
        if story is None or story not in req_by_story:
            continue
        b, d = sec.dims[0] * 1000.0, sec.dims[1] * 1000.0
        key = (story, sec.name, round(b, 3), round(d, 3))
        groups.setdefault(key, []).append(e.id)
    out = []
    for (story, name, b, d), ids in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        req = req_by_story[story]
        small = min(b, d)
        slender = math.sqrt(12.0) * req.length_mm / small
        status = "OK" if small >= req.required_mm - 1.0e-9 and slender <= MAX_SLENDERNESS + 1.0e-9 else "NG"
        out.append(ModelColumnCheck(
            story=story, section=name, b_mm=b, d_mm=d, element_ids=tuple(sorted(ids)),
            required_mm=req.required_mm, slenderness=slender, status=status,
        ))
    if not out:
        warnings.append("柱の小径: モデルに矩形断面の柱（鉛直部材）が見つかりません。必要小径のみ示します。")
    return out
