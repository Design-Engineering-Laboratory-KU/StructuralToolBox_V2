"""Bearing pressure and overturning checks of a mat foundation.

The upper structure is analysed on pinned or fixed supports; this module takes
its support reactions. Each reaction is shared among the panels touching the
support in proportion to panel area, and the foundation's own weight is spread
uniformly over the mat. Forces are in kN and lengths in m.

Overturning is taken at the foundation bottom: the moment of the applied
horizontal loads about the support level, plus the base shear times the height
of the foundation below it.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from stb_checks.wood import _load_case_durations
from stb_loads.equilibrium import _load_matrix_kN
from stb_checks.wood_standard import LONG_TERM, LONG_TERM_SNOW, SHORT_TERM, SHORT_TERM_SNOW

TOLERANCE = 1.0e-3
KILO = 1.0e-3
LOAD_DOFS = 6
MIN_HORIZONTAL_KN = 0.01
SLENDERNESS_LIMIT = 2.5
LONG_BEARING_LIMIT = 30.0

LONG_CASES = (LONG_TERM, LONG_TERM_SNOW)
SHORT_CASES = (SHORT_TERM_SNOW, SHORT_TERM)
_MM = 1.0e-3


@dataclass(frozen=True)
class PanelGeometry:
    slab: str
    x_names: Tuple[str, str]
    y_names: Tuple[str, str]
    x0: float
    x1: float
    y0: float
    y1: float

    @property
    def area(self):
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    @property
    def center(self):
        return (self.x0 + self.x1) / 2.0, (self.y0 + self.y1) / 2.0

    def contains(self, x, y):
        return (
            self.x0 - TOLERANCE <= x <= self.x1 + TOLERANCE
            and self.y0 - TOLERANCE <= y <= self.y1 + TOLERANCE
        )


@dataclass(frozen=True)
class FoundationPanelCheck:
    panel: PanelGeometry
    long_pressure: float
    average_long_pressure: float
    short_pressure: float
    allowable_long: float
    allowable_short: float
    long_ratio: float
    short_ratio: float
    long_load_case: Optional[int]
    short_load_case: Optional[int]
    status: str


@dataclass(frozen=True)
class OverturningCheck:
    direction: str
    level_moment: float
    base_shear: float
    moment: float
    weight: float
    arm: float
    resisting_moment: float
    load_case: int
    status: str
    compression_at_high_side: bool = True


@dataclass(frozen=True)
class ShortPressureCheck:
    direction: str
    sigma0: float
    sigma_b: float
    alpha_e: Optional[float]
    pressure: float
    allowable: float
    ratio: float
    status: str


@dataclass(frozen=True)
class SlendernessCheck:
    direction: str
    height: float
    width: float
    ratio: float
    status: str


@dataclass(frozen=True)
class FoundationSummary:
    level_z: float
    total_area: float
    foundation_weight: float
    uniform_pressure: float
    panels: Tuple[FoundationPanelCheck, ...]
    overturning: Tuple[OverturningCheck, ...]
    slenderness: Tuple[SlendernessCheck, ...]
    short_pressure_check_omitted: bool
    max_ratio: float
    status: str
    warnings: Tuple[str, ...]
    short_pressure: Tuple[ShortPressureCheck, ...] = ()


def _coordinate(named, name, axis):
    for coordinate, label in named:
        if label == name:
            return coordinate
    raise ValueError("foundation refers to an unknown {0} grid: {1}".format(axis, name))


def panel_geometries(settings, naming):
    out = []
    for panel in settings.panels:
        xs = sorted((_coordinate(naming.x_grids, panel.x[0], "X"), _coordinate(naming.x_grids, panel.x[1], "X")))
        ys = sorted((_coordinate(naming.y_grids, panel.y[0], "Y"), _coordinate(naming.y_grids, panel.y[1], "Y")))
        geometry = PanelGeometry(panel.slab, tuple(panel.x), tuple(panel.y), xs[0], xs[1], ys[0], ys[1])
        if geometry.area <= TOLERANCE * TOLERANCE:
            raise ValueError("foundation panel has no area: {0}, {1}".format(panel.x, panel.y))
        out.append(geometry)
    return out


def _beam_line_length(line, naming):
    x_named = {name: c for c, name in naming.x_grids}
    y_named = {name: c for c, name in naming.y_grids}
    if line.frame in y_named:
        span = line.span
        if span[0] not in x_named or span[1] not in x_named:
            raise ValueError("foundation beam line has an unknown span on {0}: {1}".format(line.frame, span))
        return abs(x_named[span[1]] - x_named[span[0]])
    if line.frame in x_named:
        span = line.span
        if span[0] not in y_named or span[1] not in y_named:
            raise ValueError("foundation beam line has an unknown span on {0}: {1}".format(line.frame, span))
        return abs(y_named[span[1]] - y_named[span[0]])
    raise ValueError("foundation beam line refers to an unknown grid: " + line.frame)


def foundation_weight(settings, panels, naming):
    """Weight of the mat, finishes and beam webs above the mat (kN)."""

    gamma = settings.concrete.unit_weight
    slabs = {s.name: s for s in settings.slab_types}
    total = sum((slabs[p.slab].thickness * _MM * gamma + settings.extra_load) * p.area for p in panels)
    beams = {b.name: b for b in settings.beam_types}
    thinnest = min(s.thickness for s in settings.slab_types)
    for line in settings.beam_lines:
        beam = beams[line.beam]
        web = max(beam.d - thinnest, 0.0) * _MM
        total += beam.b * _MM * web * gamma * _beam_line_length(line, naming)
    return total


def _level_supports(mdl, settings, naming, warnings):
    if not mdl.cons:
        raise ValueError("foundation check needs supports in the model.")
    if settings.level:
        z = _coordinate(naming.levels, settings.level, "level")
    else:
        z = min(c.nd.z for c in mdl.cons)
    supports = [c.nd for c in mdl.cons if abs(c.nd.z - z) <= TOLERANCE]
    if len(supports) != len(mdl.cons):
        warnings.append("Some supports are not at the foundation level and were ignored.")
    return z, supports


def _load_cases(mdl, project):
    requested = project.design_checks.wood.load_cases
    available = tuple(mdl.lcs)
    return tuple(lc for lc in requested if lc in available) or available


def _shares(supports, panels, warnings):
    """Per support, the (panel index, fraction) pairs its reaction goes to."""

    shares = {}
    outside = []
    for node in supports:
        touching = [i for i, p in enumerate(panels) if p.contains(node.x, node.y)]
        if not touching:
            outside.append(node.id)
            continue
        total = sum(panels[i].area for i in touching)
        shares[id(node)] = [(i, panels[i].area / total) for i in touching]
    if outside:
        warnings.append(
            "Supports outside every foundation panel were not counted in panel pressures: nodes "
            + ", ".join(str(n) for n in outside)
        )
    return shares


def _reactions(node, clc):
    return [float(node.reacts[clc, i]) * KILO for i in range(6)]


def _vertical_sum(supports, clc):
    return sum(_reactions(n, clc)[2] for n in supports if n.reacts is not None)


def _reference_case(supports, cases, durations, indices):
    long_cases = [lc for lc in cases if durations[lc] == LONG_TERM] or [lc for lc in cases if durations[lc] == LONG_TERM_SNOW]
    if not long_cases:
        return None
    return max(long_cases, key=lambda lc: _vertical_sum(supports, indices[lc]))


def _gravity_center(supports, reference_clc, panels, q0):
    weight = x_moment = y_moment = 0.0
    for node in supports:
        if node.reacts is None:
            continue
        rz = _reactions(node, reference_clc)[2]
        weight += rz
        x_moment += rz * node.x
        y_moment += rz * node.y
    for panel in panels:
        load = q0 * panel.area
        x, y = panel.center
        weight += load
        x_moment += load * x
        y_moment += load * y
    return weight, x_moment / weight, y_moment / weight


def _lateral_state(mdl, loads, clc, z_base):
    """(direction, moment about the support level, signed base shear) from applied loads."""

    fx = fy = about_y = about_x = 0.0
    for node in mdl.nds:
        px = float(loads[node.cid * LOAD_DOFS + 0, clc])
        py = float(loads[node.cid * LOAD_DOFS + 1, clc])
        arm = node.z - z_base
        fx += px
        fy += py
        about_y += px * arm
        about_x += py * arm
    if max(abs(fx), abs(fy)) < MIN_HORIZONTAL_KN:
        return None
    if abs(fx) >= abs(fy):
        return "X", abs(about_y), fx
    return "Y", abs(about_x), fy


def base_moment(level_moment, base_shear, first_floor_height, embedment_depth):
    """Overturning moment at the foundation bottom; the heights are in m."""

    return level_moment + abs(base_shear) * (first_floor_height + embedment_depth)


def _overturning(mdl, z, supports, cases, durations, indices, panels, q0, settings, warnings):
    reference = _reference_case(supports, cases, durations, indices)
    if reference is None:
        warnings.append("No long-term load case; overturning was not checked.")
        return ()
    weight, xg, yg = _gravity_center(supports, indices[reference], panels, q0)
    low_arm = {"X": xg - min(p.x0 for p in panels), "Y": yg - min(p.y0 for p in panels)}
    high_arm = {"X": max(p.x1 for p in panels) - xg, "Y": max(p.y1 for p in panels) - yg}
    alpha = settings.first_floor_height * _MM
    beta = settings.embedment_depth * _MM
    loads, _ndof = _load_matrix_kN(mdl)

    worst = {}
    for lc in cases:
        if durations[lc] not in SHORT_CASES:
            continue
        state = _lateral_state(mdl, loads, indices[lc], z)
        if state is None:
            continue
        direction, level_moment, shear = state
        # A force towards +X pushes the +X edge into the ground.
        high_side = shear > 0.0
        arm = high_arm[direction] if high_side else low_arm[direction]
        moment = base_moment(level_moment, shear, alpha, beta)
        resisting = weight * arm
        utilization = moment / resisting if resisting > 0.0 else float("inf")
        if direction not in worst or utilization > worst[direction][0]:
            worst[direction] = (
                utilization,
                OverturningCheck(
                    direction, level_moment, abs(shear), moment, weight, arm, resisting, lc,
                    "OK" if moment < resisting else "NG", high_side,
                ),
            )
    return tuple(worst[d][1] for d in ("X", "Y") if d in worst)


def _strips(panels, direction, high_side):
    """(start, end, width) of each panel, measured from the compression edge."""

    strips = []
    for p in panels:
        low, high, width = (p.x0, p.x1, p.y1 - p.y0) if direction == "X" else (p.y0, p.y1, p.x1 - p.x0)
        strips.append((low, high, width))
    if high_side:
        edge = max(s[1] for s in strips)
        return [(edge - high, edge - low, width) for low, high, width in strips]
    edge = min(s[0] for s in strips)
    return [(low - edge, high - edge, width) for low, high, width in strips]


def _section(strips: List[tuple]):
    """Area, distance of the centroid from the compression edge, and second moment."""

    area = sum((b - a) * w for a, b, w in strips)
    centroid = sum((b - a) * w * (a + b) / 2.0 for a, b, w in strips) / area
    inertia = sum(w * (b - a) ** 3 / 12.0 + (b - a) * w * ((a + b) / 2.0 - centroid) ** 2 for a, b, w in strips)
    return area, centroid, inertia


def neutral_axis(strips, eccentricity, g, tolerance=1.0e-6, iterations=200):
    """Solve xn = In/Sn - e + g by iteration; return (xn, Sn)."""

    depth = max(b for _a, b, _w in strips)
    xn = depth
    sn = 0.0
    for _ in range(iterations):
        sn = inertia = 0.0
        for a, b, w in strips:
            upper = min(b, xn)
            if upper <= a:
                continue
            sn += w * ((xn - a) ** 2 - (xn - upper) ** 2) / 2.0
            inertia += w * ((xn - a) ** 3 - (xn - upper) ** 3) / 3.0
        if sn <= 0.0:
            return None, 0.0
        updated = min(inertia / sn - eccentricity + g, depth)
        if updated <= 0.0:
            return None, 0.0
        if abs(updated - xn) < tolerance:
            return updated, sn
        xn = updated
    return xn, sn


def short_pressure_check(panels, check, allowable):
    """Short-term pressure from overturning; no tension is assumed in the soil."""

    strips = _strips(panels, check.direction, check.compression_at_high_side)
    area, centroid, inertia = _section(strips)
    sigma0 = check.weight / area
    sigma_b = check.moment / (inertia / centroid)
    alpha_e = None
    if sigma0 > sigma_b:
        pressure = sigma0 + sigma_b
    else:
        xn, sn = neutral_axis(strips, check.moment / check.weight, check.arm)
        if xn is None:
            return ShortPressureCheck(check.direction, sigma0, sigma_b, None, float("inf"), allowable, float("inf"), "NG")
        alpha_e = xn * area / sn
        pressure = alpha_e * sigma0
    ratio = pressure / allowable
    return ShortPressureCheck(check.direction, sigma0, sigma_b, alpha_e, pressure, allowable, ratio, "OK" if ratio <= 1.0 else "NG")


def _slenderness(mdl, z, panels):
    height = max(n.z for n in mdl.nds) - z
    widths = (
        ("X", max(p.x1 for p in panels) - min(p.x0 for p in panels)),
        ("Y", max(p.y1 for p in panels) - min(p.y0 for p in panels)),
    )
    return tuple(
        SlendernessCheck(direction, height, width, height / width, "OK" if height / width <= SLENDERNESS_LIMIT else "NG")
        for direction, width in widths
    )


def _worst_pressure(panel_index, panels, cases, durations, indices, supports, shares, q0, group):
    best = None
    best_case = None
    for lc in cases:
        if durations[lc] not in group:
            continue
        load = 0.0
        for node in supports:
            if node.reacts is None or id(node) not in shares:
                continue
            for index, fraction in shares[id(node)]:
                if index == panel_index:
                    load += _reactions(node, indices[lc])[2] * fraction
        pressure = load / panels[panel_index].area + q0
        if best is None or pressure > best:
            best, best_case = pressure, lc
    return best, best_case


def build_foundation_check(mdl, project, naming) -> Optional[FoundationSummary]:
    settings = project.foundation
    if settings.is_default:
        return None

    warnings = []
    panels = panel_geometries(settings, naming)
    z, supports = _level_supports(mdl, settings, naming, warnings)
    cases = _load_cases(mdl, project)
    durations = _load_case_durations(project, cases, warnings)
    indices = {lc: i for i, lc in enumerate(mdl.lcs)}

    total_area = sum(p.area for p in panels)
    weight = foundation_weight(settings, panels, naming)
    q0 = weight / total_area
    shares = _shares(supports, panels, warnings)

    long_vertical = [_vertical_sum(supports, indices[lc]) for lc in cases if durations[lc] in LONG_CASES]
    average = (max(long_vertical) + weight) / total_area if long_vertical else q0

    soil = settings.soil
    panel_checks = []
    for index, panel in enumerate(panels):
        long_pressure, long_case = _worst_pressure(index, panels, cases, durations, indices, supports, shares, q0, LONG_CASES)
        short_pressure, short_case = _worst_pressure(index, panels, cases, durations, indices, supports, shares, q0, SHORT_CASES)
        long_value = long_pressure if long_pressure is not None else q0
        short_value = short_pressure if short_pressure is not None else 0.0
        long_ratio = max(long_value, average) / soil.bearing_long
        short_ratio = short_value / soil.bearing_short
        panel_checks.append(FoundationPanelCheck(
            panel=panel,
            long_pressure=long_value,
            average_long_pressure=average,
            short_pressure=short_value,
            allowable_long=soil.bearing_long,
            allowable_short=soil.bearing_short,
            long_ratio=long_ratio,
            short_ratio=short_ratio,
            long_load_case=long_case,
            short_load_case=short_case,
            status="OK" if max(long_ratio, short_ratio) <= 1.0 else "NG",
        ))

    if settings.first_floor_height == 0.0 and settings.embedment_depth == 0.0:
        warnings.append("foundation.first_floor_height and embedment_depth are 0; overturning excludes the foundation depth.")
    overturning = _overturning(mdl, z, supports, cases, durations, indices, panels, q0, settings, warnings)
    slenderness = _slenderness(mdl, z, panels)
    required = {s.direction for s in slenderness if s.status == "NG"} if soil.bearing_long < LONG_BEARING_LIMIT else set()
    short_pressure = tuple(
        short_pressure_check(panels, o, soil.bearing_short) for o in overturning if o.direction in required
    )
    omitted = not required

    ratios = [max(c.long_ratio, c.short_ratio) for c in panel_checks]
    ratios += [o.moment / o.resisting_moment for o in overturning if o.resisting_moment > 0.0]
    ratios += [c.ratio for c in short_pressure]
    statuses = [c.status for c in panel_checks] + [o.status for o in overturning] + [c.status for c in short_pressure]
    if "NG" in statuses:
        status = "NG"
    elif any("Supports outside" in w for w in warnings):
        status = "WARN"
    else:
        status = "OK"
    return FoundationSummary(
        level_z=z,
        total_area=total_area,
        foundation_weight=weight,
        uniform_pressure=q0,
        panels=tuple(panel_checks),
        overturning=overturning,
        slenderness=slenderness,
        short_pressure_check_omitted=omitted,
        short_pressure=short_pressure,
        max_ratio=max(ratios + [0.0]),
        status=status,
        warnings=tuple(warnings),
    )
