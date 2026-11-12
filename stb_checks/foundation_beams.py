"""Foundation beams of a mat foundation: loads, grillage analysis and RC checks.

Long-term and snow cases: the ground reaction under each mat panel acts upward
on its edge beams (45-degree tributary areas), with the beams pinned at the
columns. Horizontal cases: the changes in column reactions act on the same
beams resting on a soil spring. Both models are solved with the frame solver.

Forces are in kN and lengths in m unless a name says otherwise.
"""

import contextlib
from dataclasses import dataclass
import io
import math
import re
from typing import Dict, List, Optional, Tuple

from stb_checks import foundation as fd
from stb_checks.wood import _load_case_durations
from stb_checks.wood_standard import LONG_TERM, LONG_TERM_SNOW, SHORT_TERM, SHORT_TERM_SNOW

MODULAR_RATIO = 15.0
DEFAULT_SOIL_SPRING = 5000.0  # kN/m2 per unit beam length, when the soil has no value
NO_SLAB_SOIL_SPRING = 1.0
STANDARD_UNIT_WEIGHT = 23.0
MIN_SHEAR_REINFORCEMENT = 0.002
MAX_SHEAR_REINFORCEMENT = 0.006
SHEAR_INCREASE = 1.5
SUBDIVISIONS = 4
COMBINED_CASE_SHARE = 0.5
MM = 1.0e-3
TOL = 1.0e-4

BAR_AREAS = {10: 71.33, 13: 126.7, 16: 198.6, 19: 286.5, 22: 387.1, 25: 506.7, 29: 642.4, 32: 794.2}
LOCATIONS = ("左端", "中央", "右端")


def main_bar_allowable(grade, diameter):
    """(long-term, short-term) tensile allowable stress of main bars, N/mm2."""

    if grade == "SD295":
        return 195.0, 295.0
    if grade == "SD345":
        return (195.0 if diameter >= 29 else 215.0), 345.0
    raise ValueError("Unsupported reinforcing bar grade: " + grade)


def stirrup_allowable(grade):
    """(long-term, short-term) allowable stress of shear reinforcement, N/mm2."""

    if grade == "SD295":
        return 195.0, 295.0
    if grade == "SD345":
        return 195.0, 345.0
    raise ValueError("Unsupported reinforcing bar grade: " + grade)


def concrete_allowable(fc):
    """Long-term (compression, shear) allowable stress of concrete, N/mm2."""

    return fc / 3.0, min(fc / 30.0, 0.49 + fc / 100.0)


def concrete_young(fc):
    """Young's modulus (N/mm2) for normal-weight concrete."""

    return 33500.0 * (STANDARD_UNIT_WEIGHT / 24.0) ** 2 * (fc / 60.0) ** (1.0 / 3.0)


def parse_bars(text):
    """(count, area of one bar) from a notation such as 2-D19."""

    match = re.match(r"^(\d+)-D(\d+)", text)
    return int(match.group(1)), int(match.group(2))


def bar_area(diameter):
    if diameter not in BAR_AREAS:
        raise ValueError("Unsupported bar diameter: D" + str(diameter))
    return BAR_AREAS[diameter]


def stirrup_ratio(text, width):
    count, diameter = parse_bars(text)
    spacing = float(text.split("@")[1])
    return count * bar_area(diameter) / (width * spacing)


def allowable_moment(width, depth, dt, tension_area, compression_area, fc, ft):
    """Allowable bending moment (kN*m) of a doubly reinforced section."""

    d = depth - dt
    a = width / 2.0
    b = MODULAR_RATIO * (compression_area + tension_area)
    c = -MODULAR_RATIO * (compression_area * dt + tension_area * d)
    xn = (-b + math.sqrt(b * b - 4.0 * a * c)) / (2.0 * a)
    inertia = (
        width * xn ** 3 / 3.0
        + MODULAR_RATIO * compression_area * (xn - dt) ** 2
        + MODULAR_RATIO * tension_area * (d - xn) ** 2
    )
    by_steel = ft / MODULAR_RATIO * inertia / (d - xn)
    by_concrete = fc * inertia / xn
    return min(by_steel, by_concrete) * 1.0e-6


def shear_span_factor(moment, shear, d_m):
    """Shear-span factor alpha, limited to 1..2; moment in kN*m, shear in kN."""

    if abs(shear) < 1.0e-9:
        return 2.0
    return min(max(4.0 / (abs(moment) / (abs(shear) * d_m) + 1.0), 1.0), 2.0)


def allowable_shear(width, j, alpha, fs, wft, pw):
    """Allowable shear force (kN)."""

    effective = max(min(pw, MAX_SHEAR_REINFORCEMENT) - MIN_SHEAR_REINFORCEMENT, 0.0)
    return width * j * (alpha * fs + 0.5 * wft * effective) * 1.0e-3


@dataclass(frozen=True)
class _Span:
    beam: str
    frame: str
    names: Tuple[str, str]
    axis: str
    line_coordinate: float
    start: float
    end: float


@dataclass(frozen=True)
class _Member:
    element_id: int
    span: int
    start: float
    end: float
    n0: int
    n1: int


@dataclass(frozen=True)
class BeamSectionForces:
    location: str
    long_moment: float
    long_shear: float
    long_case: Optional[int]
    short_top: float
    short_bottom: float
    design_shear: float
    top_case: Optional[int]
    bottom_case: Optional[int]
    shear_case: Optional[int]
    alpha_long: float
    alpha_short: float
    allowable_long_shear: float
    allowable_short_shear: float
    long_moment_ratio: float
    top_ratio: float
    bottom_ratio: float
    long_shear_ratio: float
    short_shear_ratio: float
    ratio: float


@dataclass(frozen=True)
class FoundationBeamCheck:
    beam: str
    frame: str
    span: Tuple[str, str]
    length: float
    width: float
    depth: float
    top: str
    bottom: str
    stirrup: str
    allowable_long: float
    allowable_short_top: float
    allowable_short_bottom: float
    pw: float
    sections: Tuple[BeamSectionForces, ...]
    max_ratio: float
    status: str


@dataclass(frozen=True)
class FoundationBeamSummary:
    checks: Tuple[FoundationBeamCheck, ...]
    max_ratio: float
    status: str
    warnings: Tuple[str, ...]


def _grid_maps(naming):
    return {name: c for c, name in naming.x_grids}, {name: c for c, name in naming.y_grids}


class _Grillage:
    """Beam spans, their refined nodes and the generated solver input."""

    def __init__(self, settings, naming, panels, supports, warnings):
        self.settings = settings
        self.naming = naming
        self.panels = panels
        self.warnings = warnings
        self.x_names, self.y_names = _grid_maps(naming)
        self.lines = [self._line(line) for line in settings.beam_lines]
        self.supports = supports
        self.spans: List[_Span] = []
        self.members: List[_Member] = []
        self.nodes: Dict[Tuple[float, float], int] = {}
        self._build()

    def _line(self, line):
        if line.frame in self.y_names and line.span[0] in self.x_names and line.span[1] in self.x_names:
            low, high = sorted((self.x_names[line.span[0]], self.x_names[line.span[1]]))
            return line, "x", self.y_names[line.frame], low, high
        if line.frame in self.x_names and line.span[0] in self.y_names and line.span[1] in self.y_names:
            low, high = sorted((self.y_names[line.span[0]], self.y_names[line.span[1]]))
            return line, "y", self.x_names[line.frame], low, high
        raise ValueError("foundation beam line refers to an unknown grid: {0}, {1}".format(line.frame, line.span))

    @staticmethod
    def point(axis, coordinate, station):
        return (station, coordinate) if axis == "x" else (coordinate, station)

    def _on_line(self, axis, coordinate, low, high, x, y):
        along, across = (x, y) if axis == "x" else (y, x)
        return abs(across - coordinate) <= TOL and low - TOL <= along <= high + TOL

    def _stations(self, axis, coordinate, low, high):
        """Span boundaries: line ends, supports on the line and crossing beam lines."""

        stations = {low, high}
        for node in self.supports:
            if self._on_line(axis, coordinate, low, high, node.x, node.y):
                stations.add(node.x if axis == "x" else node.y)
        for _other, other_axis, other_coordinate, other_low, other_high in self.lines:
            if other_axis != axis and low - TOL <= other_coordinate <= high + TOL and other_low - TOL <= coordinate <= other_high + TOL:
                stations.add(other_coordinate)
        return sorted(stations)

    def _edges(self, axis, coordinate):
        """(start, end, half-width of the tributary area) of panel edges on this line."""

        edges = []
        for panel in self.panels:
            half = min(panel.x1 - panel.x0, panel.y1 - panel.y0) / 2.0
            if axis == "x" and any(abs(coordinate - y) <= TOL for y in (panel.y0, panel.y1)):
                edges.append((panel, panel.x0, panel.x1, half))
            if axis == "y" and any(abs(coordinate - x) <= TOL for x in (panel.x0, panel.x1)):
                edges.append((panel, panel.y0, panel.y1, half))
        return edges

    def _node(self, axis, coordinate, station):
        key = tuple(round(v, 5) for v in self.point(axis, coordinate, station))
        if key not in self.nodes:
            self.nodes[key] = len(self.nodes) + 1
        return self.nodes[key]

    def _build(self):
        element = 0
        for line, axis, coordinate, low, high in self.lines:
            stations = self._stations(axis, coordinate, low, high)
            edges = self._edges(axis, coordinate)
            breaks = set()
            for _panel, start, end, half in edges:
                breaks.update((start, start + half, end - half, end))
            names = self.naming.x if axis == "x" else self.naming.y
            for a, b in zip(stations, stations[1:]):
                points = {a, b, (a + b) / 2.0}
                points.update(a + (b - a) * i / SUBDIVISIONS for i in range(1, SUBDIVISIONS))
                points.update(v for v in breaks if a + TOL < v < b - TOL)
                ordered = self._dedupe(sorted(points))
                span = len(self.spans)
                self.spans.append(_Span(line.beam, line.frame, (names(a), names(b)), axis, coordinate, a, b))
                for start, end in zip(ordered, ordered[1:]):
                    element += 1
                    self.members.append(_Member(
                        element, span, start, end,
                        self._node(axis, coordinate, start),
                        self._node(axis, coordinate, end),
                    ))

    @staticmethod
    def _dedupe(values):
        out = []
        for value in values:
            if not out or value - out[-1] > TOL:
                out.append(value)
        return out

    def intensity(self, span, station, pressures):
        """Upward line load (kN/m) at a station from the panels along this line."""

        total = 0.0
        for (panel, start, end, half), pressure in pressures[self._line_key(span)]:
            if start - TOL <= station <= end + TOL:
                total += pressure * min(station - start, end - station, half)
        return total

    @staticmethod
    def _line_key(span):
        return span.axis, round(span.line_coordinate, 5)

    def pressures_by_line(self, panel_pressure):
        out = {}
        for span in self.spans:
            key = self._line_key(span)
            if key in out:
                continue
            out[key] = []
            for edge in self._edges(span.axis, span.line_coordinate):
                out[key].append((edge, panel_pressure[id(edge[0])]))
        return out

    def beam_on_slab(self, span, member):
        middle = (member.start + member.end) / 2.0
        return any(start - TOL <= middle <= end + TOL for _p, start, end, _h in self._edges(span.axis, span.line_coordinate))

    def uncovered_panel_edges(self):
        missing = 0
        for panel in self.panels:
            for axis, coordinate, low, high in (
                ("x", panel.y0, panel.x0, panel.x1), ("x", panel.y1, panel.x0, panel.x1),
                ("y", panel.x0, panel.y0, panel.y1), ("y", panel.x1, panel.y0, panel.y1),
            ):
                middle = (low + high) / 2.0
                if not any(
                    other_axis == axis and abs(other_coordinate - coordinate) <= TOL and other_low - TOL <= middle <= other_high + TOL
                    for _l, other_axis, other_coordinate, other_low, other_high in self.lines
                ):
                    missing += 1
        return missing

    def _section_lines(self):
        lines = []
        for i, beam in enumerate(self.settings.beam_types):
            lines.append("SECT, {0}, {1}, 1, 0, {2}, {3}".format(i + 1, beam.name, beam.b, beam.d))
        return lines

    def base_lines(self, young):
        lines = ["MATE, 1, FG, {0}, {1}, 0.0, 1e-05, 0".format(young, young / 2.4)]
        lines.extend(self._section_lines())
        for (x, y), node in self.nodes.items():
            lines.append("NODE, {0}, {1}, {2}, 0.0".format(node, x, y))
        beams = {b.name: i + 1 for i, b in enumerate(self.settings.beam_types)}
        for member in self.members:
            span = self.spans[member.span]
            lines.append("ELEM, {0}, {1}, {2}, {3}, 0.0".format(member.element_id, member.n0, member.n1, beams[span.beam]))
        return lines

    def constraint_lines(self, pinned):
        """Supports: plan movement is fixed; vertical restraint only where pinned."""

        spin = self._spin_fixed_nodes()
        lines = []
        for (x, y), node in self.nodes.items():
            vertical = 1 if node in pinned else 0
            rx, ry = spin.get(node, (0, 0))
            lines.append("CONS, {0}, 1, 1, {1}, {2}, {3}, 1".format(node, vertical, rx, ry))
        return lines

    def _spin_fixed_nodes(self):
        """Lines with no crossing beam would spin freely about their own axis."""

        crossing_nodes = {}
        for member in self.members:
            span = self.spans[member.span]
            for node in (member.n0, member.n1):
                crossing_nodes.setdefault(node, set()).add(span.axis)
        fixed = {}
        done = set()
        for member in self.members:
            span = self.spans[member.span]
            key = self._line_key(span)
            if key in done:
                continue
            nodes = [n for m in self.members if self._line_key(self.spans[m.span]) == key for n in (m.n0, m.n1)]
            if not any(len(crossing_nodes[n]) > 1 for n in nodes):
                done.add(key)
                fixed[member.n0] = (1, 0) if span.axis == "x" else (0, 1)
        return fixed


def _solve(lines):
    from stb_engine import parse_input, solve_model

    mdl = parse_input(lines)
    with contextlib.redirect_stdout(io.StringIO()):
        solve_model(mdl)
    return mdl


def _panel_pressures(panels, supports, shares, clc):
    """Ground pressure (kN/m2) under each panel from the column reactions alone."""

    loads = {id(p): 0.0 for p in panels}
    index = {i: p for i, p in enumerate(panels)}
    for node in supports:
        if node.reacts is None or id(node) not in shares:
            continue
        rz = float(node.reacts[clc, 2]) * fd.KILO
        for i, fraction in shares[id(node)]:
            loads[id(index[i])] += rz * fraction
    return {id(p): loads[id(p)] / p.area for p in panels}


def _pinned_nodes(grillage, supports):
    pinned = set()
    off_line = 0
    for node in supports:
        key = (round(node.x, 5), round(node.y, 5))
        if key in grillage.nodes:
            pinned.add(grillage.nodes[key])
        else:
            off_line += 1
    if off_line:
        grillage.warnings.append("{0} support(s) are not on a foundation beam line and were ignored.".format(off_line))
    return pinned


def _gravity_model(grillage, young, pinned, cases, panels, supports, shares, indices):
    """Beams pinned at the columns under the upward ground reaction."""

    lines = grillage.base_lines(young)
    lines.extend(grillage.constraint_lines(pinned))
    for lc in cases:
        pressures = grillage.pressures_by_line(_panel_pressures(panels, supports, shares, indices[lc]))
        for member in grillage.members:
            span = grillage.spans[member.span]
            wi = grillage.intensity(span, member.start, pressures)
            wj = grillage.intensity(span, member.end, pressures)
            lines.append("ELOD, {0}, {1}, 1, 0.0, 0.0, {2}, 0.0, 0.0, {3}".format(member.element_id, lc, wi, wj))
    return _solve(lines)


def _spring_stiffness(grillage, modulus):
    """Vertical spring (kN/m) of each node from the beam length it carries."""

    stiffness = {node: 0.0 for node in grillage.nodes.values()}
    for member in grillage.members:
        span = grillage.spans[member.span]
        k = modulus if grillage.beam_on_slab(span, member) else NO_SLAB_SOIL_SPRING
        share = k * (member.end - member.start) / 2.0
        stiffness[member.n0] += share
        stiffness[member.n1] += share
    return stiffness


def _spring_model(grillage, young, modulus, lateral_loads):
    """Beams on soil springs under the change in column reactions."""

    lines = grillage.base_lines(young)
    lines.extend(grillage.constraint_lines(set()))
    stiffness = _spring_stiffness(grillage, modulus)
    next_node = max(grillage.nodes.values()) + 1
    next_element = max(m.element_id for m in grillage.members) + 1
    next_section = len(grillage.settings.beam_types) + 1
    for (x, y), node in grillage.nodes.items():
        area = stiffness[node] * 1.0e3 / (young * 1.0e6)  # EA/L = k with L = 1 m
        side = math.sqrt(area) * 1000.0
        lines.append("SECT, {0}, SP, 1, 0, {1}, {1}".format(next_section, side))
        lines.append("NODE, {0}, {1}, {2}, -1.0".format(next_node, x, y))
        lines.append("ELEM, {0}, {1}, {2}, {3}, 0.0".format(next_element, next_node, node, next_section))
        lines.append("EJNT, {0}, 0, 0, 0, 0".format(next_element))
        lines.append("CONS, {0}, 1, 1, 1, 1, 1, 1".format(next_node))
        next_node += 1
        next_element += 1
        next_section += 1
    for lc, loads in lateral_loads.items():
        for node, force in loads.items():
            lines.append("PLOD, {0}, {1}, 0.0, 0.0, {2}, 0.0, 0.0, 0.0".format(node, lc, force))
    return _solve(lines)


def _span_forces(mdl, members, clc):
    """(moment, shear) at the left end, middle and right end of a span."""

    members = sorted(members, key=lambda m: m.start)
    left = mdl.FindElemFromEid(members[0].element_id)
    right = mdl.FindElemFromEid(members[-1].element_id)
    middle_station = (members[0].start + members[-1].end) / 2.0
    middle_member = min(members, key=lambda m: abs(m.start - middle_station))
    middle = mdl.FindElemFromEid(middle_member.element_id)
    return (
        (float(left.forces[4, clc]) * fd.KILO, float(left.forces[2, clc]) * fd.KILO),
        (float(middle.forces[4, clc]) * fd.KILO, float(middle.forces[2, clc]) * fd.KILO),
        (float(right.forces[10, clc]) * fd.KILO, float(right.forces[8, clc]) * fd.KILO),
    )


def _classify(mdl, cases, durations, indices, z):
    loads, _ndof = fd._load_matrix_kN(mdl)
    horizontal = {lc: fd._lateral_state(mdl, loads, indices[lc], z) is not None for lc in cases}
    return (
        [lc for lc in cases if not horizontal[lc]],
        [lc for lc in cases if horizontal[lc] and durations[lc] in fd.SHORT_CASES],
    )


def _lateral_loads(grillage, supports, lateral_cases, indices, reference_clc, warnings):
    """Downward force at each column node from the change in its reaction."""

    base = sum(float(n.reacts[reference_clc, 2]) for n in supports if n.reacts is not None)
    out = {}
    uplift = 0
    for lc in lateral_cases:
        clc = indices[lc]
        total = sum(float(n.reacts[clc, 2]) for n in supports if n.reacts is not None)
        combined = total >= COMBINED_CASE_SHARE * base
        loads = {}
        for node in supports:
            key = (round(node.x, 5), round(node.y, 5))
            if node.reacts is None or key not in grillage.nodes:
                continue
            rz = float(node.reacts[clc, 2]) * fd.KILO
            ref = float(node.reacts[reference_clc, 2]) * fd.KILO
            change = rz - ref if combined else rz
            final = rz if combined else rz + ref
            if final < 0.0:
                uplift += 1
            loads[grillage.nodes[key]] = -change
        out[lc] = loads
    if uplift:
        warnings.append(
            "柱の引抜きが {0} 箇所で生じています。基礎梁の格子梁解析では地盤バネの浮上りを考慮していません。".format(uplift)
        )
    return out


def build_foundation_beam_check(mdl, project, naming, summary) -> Optional[FoundationBeamSummary]:
    settings = project.foundation
    if settings.is_default or not settings.beam_lines:
        return None

    warnings = []
    panels = [check.panel for check in summary.panels]
    z, supports = fd._level_supports(mdl, settings, naming, [])
    cases = fd._load_cases(mdl, project)
    durations = _load_case_durations(project, cases, [])
    indices = {lc: i for i, lc in enumerate(mdl.lcs)}
    shares = fd._shares(supports, panels, [])
    reference = fd._reference_case(supports, cases, durations, indices)
    if reference is None:
        return FoundationBeamSummary((), 0.0, "WARN", ("No long-term load case; foundation beams were not checked.",))

    grillage = _Grillage(settings, naming, panels, supports, warnings)
    missing = grillage.uncovered_panel_edges()
    if missing:
        warnings.append("{0} panel edge(s) have no foundation beam; their ground reaction is not carried.".format(missing))

    young = concrete_young(settings.concrete.fc)
    modulus = settings.soil.young or DEFAULT_SOIL_SPRING
    pinned = _pinned_nodes(grillage, supports)
    gravity_cases, lateral_cases = _classify(mdl, cases, durations, indices, z)
    if reference not in gravity_cases:
        gravity_cases.append(reference)

    gravity = _gravity_model(grillage, young, pinned, gravity_cases, panels, supports, shares, indices)
    gravity_index = {lc: list(gravity.lcs).index(lc) for lc in gravity_cases}
    spring = None
    spring_index = {}
    if lateral_cases:
        loads = _lateral_loads(grillage, supports, lateral_cases, indices, indices[reference], warnings)
        spring = _spring_model(grillage, young, modulus, loads)
        spring_index = {lc: list(spring.lcs).index(lc) for lc in lateral_cases}

    return _check_spans(
        grillage, settings, durations, reference, gravity, gravity_index, gravity_cases, spring, spring_index,
        lateral_cases, warnings,
    )


def _check_spans(grillage, settings, durations, reference, gravity, gravity_index, gravity_cases, spring, spring_index, lateral_cases, warnings):
    beams = {b.name: b for b in settings.beam_types}
    fc_long, fs_long = concrete_allowable(settings.concrete.fc)
    by_span = {}
    for member in grillage.members:
        by_span.setdefault(member.span, []).append(member)

    checks = []
    for span_index, span in enumerate(grillage.spans):
        beam = beams[span.beam]
        members = by_span[span_index]
        d = beam.d - beam.dt
        d_m = d * MM
        j = 7.0 / 8.0 * d
        top_count, top_d = parse_bars(beam.top)
        bottom_count, bottom_d = parse_bars(beam.bottom)
        top_area = top_count * bar_area(top_d)
        bottom_area = bottom_count * bar_area(bottom_d)
        ft_top = main_bar_allowable(beam.main_rebar, top_d)
        ft_bottom = main_bar_allowable(beam.main_rebar, bottom_d)
        wft = stirrup_allowable(beam.stirrup_rebar)
        pw = stirrup_ratio(beam.stirrup, beam.b)

        ma_long = min(
            allowable_moment(beam.b, beam.d, beam.dt, bottom_area, top_area, fc_long, ft_bottom[0]),
            allowable_moment(beam.b, beam.d, beam.dt, top_area, bottom_area, fc_long, ft_top[0]),
        )
        ma_short_top = allowable_moment(beam.b, beam.d, beam.dt, top_area, bottom_area, fc_long * 2.0, ft_top[1])
        ma_short_bottom = allowable_moment(beam.b, beam.d, beam.dt, bottom_area, top_area, fc_long * 2.0, ft_bottom[1])

        sections = []
        ref_forces = _span_forces(gravity, members, gravity_index[reference])
        for location, loc in zip(LOCATIONS, range(3)):
            long_m = long_q = 0.0
            long_case = None
            short_top = short_bottom = design = 0.0
            top_case = bottom_case = shear_case = None
            for lc in gravity_cases:
                moment, shear = _span_forces(gravity, members, gravity_index[lc])[loc]
                if durations[lc] in fd.LONG_CASES:
                    if long_case is None or abs(moment) > abs(long_m):
                        long_m, long_q, long_case = moment, shear, lc
                else:
                    if -moment > short_top:
                        short_top, top_case = -moment, lc
                    if moment > short_bottom:
                        short_bottom, bottom_case = moment, lc
                    added = abs(ref_forces[loc][1]) + SHEAR_INCREASE * abs(shear - ref_forces[loc][1])
                    if added > design:
                        design, shear_case = added, lc
            for lc in lateral_cases:
                add_m, add_q = _span_forces(spring, members, spring_index[lc])[loc]
                moment = ref_forces[loc][0] + add_m
                if -moment > short_top:
                    short_top, top_case = -moment, lc
                if moment > short_bottom:
                    short_bottom, bottom_case = moment, lc
                added = abs(ref_forces[loc][1]) + SHEAR_INCREASE * abs(add_q)
                if added > design:
                    design, shear_case = added, lc

            alpha_long = shear_span_factor(long_m, long_q, d_m)
            alpha_short = shear_span_factor(max(short_top, short_bottom), design, d_m)
            qa_long = allowable_shear(beam.b, j, alpha_long, fs_long, wft[0], pw)
            qa_short = allowable_shear(beam.b, j, alpha_short, fs_long * 1.5, wft[1], pw)
            ratios = dict(
                long_moment_ratio=abs(long_m) / ma_long,
                top_ratio=short_top / ma_short_top,
                bottom_ratio=short_bottom / ma_short_bottom,
                long_shear_ratio=abs(long_q) / qa_long,
                short_shear_ratio=design / qa_short,
            )
            sections.append(BeamSectionForces(
                location=location, long_moment=long_m, long_shear=long_q, long_case=long_case,
                short_top=short_top, short_bottom=short_bottom, design_shear=design,
                top_case=top_case, bottom_case=bottom_case, shear_case=shear_case,
                alpha_long=alpha_long, alpha_short=alpha_short,
                allowable_long_shear=qa_long, allowable_short_shear=qa_short,
                ratio=max(ratios.values()),
                **ratios,
            ))
        max_ratio = max(s.ratio for s in sections)
        checks.append(FoundationBeamCheck(
            beam=span.beam, frame=span.frame, span=span.names, length=span.end - span.start,
            width=beam.b, depth=beam.d, top=beam.top, bottom=beam.bottom, stirrup=beam.stirrup,
            allowable_long=ma_long, allowable_short_top=ma_short_top, allowable_short_bottom=ma_short_bottom,
            pw=pw, sections=tuple(sections), max_ratio=max_ratio, status="OK" if max_ratio <= 1.0 else "NG",
        ))
    overall = max([c.max_ratio for c in checks] + [0.0])
    return FoundationBeamSummary(
        checks=tuple(checks),
        max_ratio=overall,
        status="NG" if any(c.status == "NG" for c in checks) else "OK",
        warnings=tuple(warnings),
    )
