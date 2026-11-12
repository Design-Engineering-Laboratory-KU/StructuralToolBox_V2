"""Plan and elevation drawings, and the result overlays drawn on them."""

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from reportlab.lib import colors

from stb_reports.calc_book.common import fmt
from stb_reports.calc_book.context import KIND_BEAM, KIND_COLUMN, LEVEL_TOLERANCE
from stb_reports.calc_book.document import Figure, Heading
from stb_reports.calc_book.render_pdf import FONT

FIGURE_HEIGHT = 330.0
MARGIN_LEFT = 58.0
MARGIN_RIGHT = 22.0
MARGIN_TOP = 16.0
MARGIN_BOTTOM = 34.0
MAX_DIAGRAM_OFFSET = 26.0
MAX_DEFORMATION_OFFSET = 22.0
DIAGRAM_SAMPLES = 10
SMALL_VALUE = 0.005
LABEL_SIZE = 4.6

COLOR_RESULT = colors.Color(0.82, 0.08, 0.08)
COLOR_GRID = colors.Color(0.55, 0.55, 0.55)
COLOR_MINOR = colors.Color(0.7, 0.7, 0.7)
COLOR_MEMBER = colors.black


@dataclass(frozen=True)
class ViewAxes:
    """Maps a global (x, y, z) point to drawing coordinates (u, v)."""

    u_index: int
    v_index: int
    normal: Tuple[float, float, float]
    u_names: Tuple[Tuple[float, str], ...]
    v_names: Tuple[Tuple[float, str], ...]

    def project(self, point):
        return point[self.u_index], point[self.v_index]


@dataclass(frozen=True)
class View:
    title: str
    axes: ViewAxes
    members: Tuple
    auxiliary: Tuple
    nodes: Tuple


def _xyz(node):
    return node.x, node.y, node.z


class _Transform:
    def __init__(self, view, width, height):
        points = [view.axes.project(_xyz(n)) for n in view.nodes]
        us =[p[0] for p in points] or [0.0]
        vs = [p[1] for p in points] or [0.0]
        self.u_min, self.u_max = min(us), max(us)
        self.v_min, self.v_max = min(vs), max(vs)
        span_u = max(self.u_max - self.u_min, 1.0e-6)
        span_v = max(self.v_max - self.v_min, 1.0e-6)
        area_w = width - MARGIN_LEFT - MARGIN_RIGHT
        area_h = height - MARGIN_TOP - MARGIN_BOTTOM
        self.scale = min(area_w / span_u, area_h / span_v)
        self.x0 = MARGIN_LEFT + (area_w - span_u * self.scale) / 2.0
        self.y0 = MARGIN_BOTTOM + (area_h - span_v * self.scale) / 2.0

    def point(self, u, v):
        return self.x0 + (u - self.u_min) * self.scale, self.y0 + (v - self.v_min) * self.scale


def _in_range(coordinate, low, high):
    return low - LEVEL_TOLERANCE <= coordinate <= high + LEVEL_TOLERANCE


def _draw_base(c, view, t, width, height):
    axes = view.axes
    c.setLineWidth(0.3)
    c.setDash(2, 2)
    c.setStrokeColor(COLOR_GRID)
    top = height - MARGIN_TOP
    u_named = [(u, name) for u, name in axes.u_names if _in_range(u, t.u_min, t.u_max)]
    v_named = [(v, name) for v, name in axes.v_names if _in_range(v, t.v_min, t.v_max)]
    for u, _name in u_named:
        x, _ = t.point(u, t.v_min)
        c.line(x, MARGIN_BOTTOM - 4.0, x, top)
    for v, _name in v_named:
        _, y = t.point(t.u_min, v)
        c.line(MARGIN_LEFT - 6.0, y, width - MARGIN_RIGHT, y)
    c.setDash()
    c.setStrokeColor(COLOR_MEMBER)
    c.setFillColor(COLOR_MEMBER)

    c.setFont(FONT, 6.0)
    for u, name in u_named:
        x, _ = t.point(u, t.v_min)
        c.drawCentredString(x, MARGIN_BOTTOM - 22.0, name)
    for v, name in v_named:
        _, y = t.point(t.u_min, v)
        c.drawRightString(MARGIN_LEFT - 22.0, y - 2.0, name)

    c.setFont(FONT, 4.8)
    for (u0, _a), (u1, _b) in zip(u_named, u_named[1:]):
        x0, _ = t.point(u0, t.v_min)
        x1, _ = t.point(u1, t.v_min)
        c.drawCentredString((x0 + x1) / 2.0, MARGIN_BOTTOM - 13.0, fmt((u1 - u0) * 1000.0, 0))
    for (v0, _a), (v1, _b) in zip(v_named, v_named[1:]):
        _, y0 = t.point(t.u_min, v0)
        _, y1 = t.point(t.u_min, v1)
        c.drawRightString(MARGIN_LEFT - 8.0, (y0 + y1) / 2.0 - 2.0, fmt((v1 - v0) * 1000.0, 0))


def _member_endpoints(view, t, e):
    x0, y0 = t.point(*view.axes.project(_xyz(e.n0)))
    x1, y1 = t.point(*view.axes.project(_xyz(e.n1)))
    return x0, y0, x1, y1


def _draw_members(c, view, t, line_width=0.8):
    c.setStrokeColor(COLOR_MINOR)
    c.setLineWidth(0.3)
    for e in view.auxiliary:
        c.line(*_member_endpoints(view, t, e))
    c.setStrokeColor(COLOR_MEMBER)
    c.setLineWidth(line_width)
    for e in view.members:
        c.line(*_member_endpoints(view, t, e))


def _draw_supports(c, view, t):
    c.setLineWidth(0.5)
    for node in view.nodes:
        if node.cons is None:
            continue
        x, y = t.point(*view.axes.project(_xyz(node)))
        path = c.beginPath()
        path.moveTo(x, y)
        path.lineTo(x - 3.5, y - 6.0)
        path.lineTo(x + 3.5, y - 6.0)
        path.close()
        c.drawPath(path, stroke=1, fill=0)


def _member_text(c, view, t, e, text, color=COLOR_MEMBER, size=LABEL_SIZE, offset=2.0, fraction=0.5):
    x0, y0, x1, y1 = _member_endpoints(view, t, e)
    x = x0 + (x1 - x0) * fraction
    y = y0 + (y1 - y0) * fraction
    c.setFillColor(color)
    c.setFont(FONT, size)
    if abs(x1 - x0) >= abs(y1 - y0):
        c.drawCentredString(x, y + offset, text)
    else:
        c.saveState()
        c.translate(x - offset, y)
        c.rotate(90)
        c.drawCentredString(0.0, 0.0, text)
        c.restoreState()
    c.setFillColor(COLOR_MEMBER)


def _is_upward_vertical(e):
    return bool(e.isVxZ) and e.pln.vx.v[2] > 0


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def bending_in_plane(e, clc, normal):
    """Moments at i, mid, j and the global direction of the tension fibre.

    The solver reports moments with a member-orientation dependent sign; this
    converts them to the standard section moment, which is positive when the
    +z fibre (about y) or the -y fibre (about z) is in tension.
    """

    forces = e.forces[:, clc]
    sign = 1.0 if _is_upward_vertical(e) else -1.0
    vy = tuple(float(v) for v in e.pln.vy.v)
    vz = tuple(float(v) for v in e.pln.vz.v)
    if abs(_dot(vy, normal)) >= abs(_dot(vz, normal)):
        return (
            (sign * float(forces[4]), sign * float(forces[12]), sign * float(forces[10])),
            vz,
        )
    return (
        (sign * float(forces[5]), sign * float(forces[13]), sign * float(forces[11])),
        tuple(-v for v in vy),
    )


def _parabola(values, s):
    m0, mc, m1 = values
    return m0 * (1 - s) * (1 - 2 * s) + 4.0 * mc * s * (1 - s) + m1 * s * (2 * s - 1)


def _max_moment(view, clc):
    largest = 0.0
    for e in view.members:
        values, _ = bending_in_plane(e, clc, view.axes.normal)
        largest = max(largest, max(abs(v) for v in values))
    return largest


def _draw_moment_diagram(c, view, t, e, clc, scale):
    values, direction = bending_in_plane(e, clc, view.axes.normal)
    if max(abs(v) for v in values) * scale < 0.05:
        return
    x0, y0, x1, y1 = _member_endpoints(view, t, e)
    du = direction[view.axes.u_index]
    dv = direction[view.axes.v_index]
    path = c.beginPath()
    path.moveTo(x0, y0)
    for i in range(DIAGRAM_SAMPLES + 1):
        s = i / float(DIAGRAM_SAMPLES)
        offset = _parabola(values, s) * scale
        path.lineTo(x0 + (x1 - x0) * s + du * offset, y0 + (y1 - y0) * s + dv * offset)
    path.lineTo(x1, y1)
    c.setStrokeColor(COLOR_RESULT)
    c.setLineWidth(0.5)
    c.drawPath(path, stroke=1, fill=0)
    c.setStrokeColor(COLOR_MEMBER)
    for fraction, value in ((0.12, values[0]), (0.5, values[1]), (0.88, values[2])):
        kn = value * 1.0e-3
        if abs(kn) >= SMALL_VALUE:
            _member_text(c, view, t, e, fmt(abs(kn), 2), COLOR_RESULT, fraction=fraction)


def _draw_axial_labels(c, view, t, e, clc):
    n = float(e.forces[0, clc]) * 1.0e-3
    if abs(n) >= SMALL_VALUE:
        _member_text(c, view, t, e, "N" + fmt(n, 1), COLOR_MEMBER, offset=-5.5)


def _stress_painter(view, clc):
    def paint(c, width, height):
        t = _Transform(view, width, height)
        _draw_base(c, view, t, width, height)
        _draw_members(c, view, t, line_width=0.45)
        _draw_supports(c, view, t)
        largest = _max_moment(view, clc)
        scale = MAX_DIAGRAM_OFFSET / largest if largest > 0.0 else 0.0
        for e in view.members:
            _draw_moment_diagram(c, view, t, e, clc, scale)
            _draw_axial_labels(c, view, t, e, clc)

    return paint


def _model_painter(view, label: Optional[Callable] = None):
    def paint(c, width, height):
        t = _Transform(view, width, height)
        _draw_base(c, view, t, width, height)
        _draw_members(c, view, t)
        _draw_supports(c, view, t)
        if label is not None:
            for e in view.members:
                text = label(e)
                if text:
                    color = COLOR_RESULT if text.endswith("*") else COLOR_MEMBER
                    _member_text(c, view, t, e, text, color)

    return paint


def _max_displacement(view, clc):
    largest = 0.0
    u, v = view.axes.u_index, view.axes.v_index
    for node in view.nodes:
        if node.disps is not None:
            largest = max(largest, abs(float(node.disps[u, clc])), abs(float(node.disps[v, clc])))
    return largest


def _deformation_painter(view, clc):
    def paint(c, width, height):
        t = _Transform(view, width, height)
        _draw_base(c, view, t, width, height)
        _draw_members(c, view, t, line_width=0.3)
        _draw_supports(c, view, t)
        largest = _max_displacement(view, clc)
        if largest <= 0.0:
            return
        scale = MAX_DEFORMATION_OFFSET / largest
        ui, vi = view.axes.u_index, view.axes.v_index

        def moved(node):
            x, y = t.point(*view.axes.project(_xyz(node)))
            return x + float(node.disps[ui, clc]) * scale, y + float(node.disps[vi, clc]) * scale

        c.setStrokeColor(COLOR_RESULT)
        c.setLineWidth(0.7)
        for e in view.members:
            if e.n0.disps is not None and e.n1.disps is not None:
                c.line(*moved(e.n0), *moved(e.n1))
        c.setStrokeColor(COLOR_MEMBER)

    return paint


def _reaction_painter(view, clc):
    def paint(c, width, height):
        t = _Transform(view, width, height)
        _draw_base(c, view, t, width, height)
        _draw_members(c, view, t, line_width=0.4)
        c.setFont(FONT, 4.8)
        for node in view.nodes:
            if node.cons is None or node.reacts is None:
                continue
            x, y = t.point(*view.axes.project(_xyz(node)))
            c.setFillColor(COLOR_RESULT)
            c.circle(x, y, 1.2, stroke=0, fill=1)
            c.drawString(x + 2.5, y + 2.0, fmt(float(node.reacts[clc, 2]) * 1.0e-3, 1))
            c.setFillColor(COLOR_MEMBER)

    return paint


# --- views -------------------------------------------------------------------


def _near(a, b):
    return abs(a - b) <= LEVEL_TOLERANCE


def _nodes_of(members):
    seen = {}
    for e in members:
        seen[id(e.n0)] = e.n0
        seen[id(e.n1)] = e.n1
    return tuple(seen.values())


def plan_views(ctx) -> List[View]:
    naming = ctx.naming
    axes = ViewAxes(0, 1, (0.0, 0.0, 1.0), tuple(naming.x_grids), tuple(naming.y_grids))
    out = []
    members = ctx.real_members()
    for z, name in naming.levels:
        level_members = tuple(
            e for e in members if naming.kind(e) == KIND_BEAM and _near(e.n0.z, z)
        )
        nodes = [n for e in members if naming.kind(e) == KIND_COLUMN for n in (e.n0, e.n1) if _near(n.z, z)]
        if level_members or nodes:
            unique = {id(n): n for n in list(_nodes_of(level_members)) + nodes}
            out.append(View(name + "層", axes, level_members, (), tuple(unique.values())))
    return out


def _frame_view(ctx, title, axes, members, auxiliary):
    return View(title, axes, tuple(members), tuple(auxiliary), _nodes_of(list(members) + list(auxiliary)))


def elevation_views(ctx) -> List[View]:
    naming = ctx.naming
    members = ctx.real_members()
    generated = [e for e in ctx.mdl.elms if getattr(e, "auto_generated", False)]
    out = []
    for y, name in naming.y_grids:
        axes = ViewAxes(0, 2, (0.0, 1.0, 0.0), tuple(naming.x_grids), tuple(naming.levels))
        inside = [e for e in members if _near(e.n0.y, y) and _near(e.n1.y, y)]
        if inside:
            aux = [e for e in generated if _near(e.n0.y, y) and _near(e.n1.y, y)]
            out.append(_frame_view(ctx, name + "通り", axes, inside, aux))
    for x, name in naming.x_grids:
        axes = ViewAxes(1, 2, (1.0, 0.0, 0.0), tuple(naming.y_grids), tuple(naming.levels))
        inside = [e for e in members if _near(e.n0.x, x) and _near(e.n1.x, x)]
        if inside:
            aux = [e for e in generated if _near(e.n0.x, x) and _near(e.n1.x, x)]
            out.append(_frame_view(ctx, name + "通り", axes, inside, aux))
    return out


def report_load_cases(ctx):
    requested = tuple(ctx.project.design_checks.wood.load_cases)
    available = tuple(ctx.mdl.lcs)
    chosen = tuple(lc for lc in requested if lc in available)
    return chosen or available


def _section_name(e):
    return e.sec.name


def plan_chapter(ctx):
    blocks = [Heading(2, "1.2 略伏図"), Heading(3, "1.2.1 略伏図")]
    blocks.extend(
        Figure(FIGURE_HEIGHT, _model_painter(v, _section_name), title=v.title) for v in plan_views(ctx)
    )
    return blocks


def elevation_chapter(ctx):
    blocks = [Heading(2, "1.3 略軸組図"), Heading(3, "1.3.1 略軸組図")]
    blocks.extend(
        Figure(FIGURE_HEIGHT, _model_painter(v, _section_name), title=v.title) for v in elevation_views(ctx)
    )
    return blocks


def model_figures(ctx):
    return [Figure(FIGURE_HEIGHT, _model_painter(v), title=v.title) for v in elevation_views(ctx)]


def stress_figures(ctx, lc):
    clc = ctx.lc_index(lc)
    title = ctx.lc_label(lc)
    return [
        Figure(FIGURE_HEIGHT, _stress_painter(v, clc), title=v.title + " " + title, unit="M (kN・m)、N (kN)")
        for v in elevation_views(ctx)
    ]


def deformation_figures(ctx, lc):
    clc = ctx.lc_index(lc)
    title = ctx.lc_label(lc)
    figures = []
    for view in elevation_views(ctx):
        largest = _max_displacement(view, clc) * 1000.0
        figures.append(Figure(
            FIGURE_HEIGHT,
            _deformation_painter(view, clc),
            title=view.title + " " + title,
            unit="面内最大変位 " + fmt(largest, 2) + " mm",
        ))
    return figures


def reaction_figure(ctx, lc):
    naming = ctx.naming
    clc = ctx.lc_index(lc)
    supported = [c.nd for c in ctx.mdl.cons]
    if not supported:
        return None
    axes = ViewAxes(0, 1, (0.0, 0.0, 1.0), tuple(naming.x_grids), tuple(naming.y_grids))
    level = min(n.z for n in supported)
    members = tuple(e for e in ctx.real_members() if naming.kind(e) == KIND_BEAM and _near(e.n0.z, level))
    unique = {id(n): n for n in list(_nodes_of(members)) + supported}
    view = View(naming.level(level) + "層", axes, members, (), tuple(unique.values()))
    total = sum(float(n.reacts[clc, 2]) for n in supported if n.reacts is not None) * 1.0e-3
    return Figure(
        FIGURE_HEIGHT,
        _reaction_painter(view, clc),
        title=view.title + " " + ctx.lc_label(lc),
        unit="鉛直反力 (kN)、Σ = " + fmt(total, 1) + " kN",
    )


def foundation_figure(ctx):
    """Plan of the mat panels and foundation beam lines."""

    naming = ctx.naming
    foundation = ctx.foundation
    settings = ctx.project.foundation
    axes = ViewAxes(0, 1, (0.0, 0.0, 1.0), tuple(naming.x_grids), tuple(naming.y_grids))
    supports = [c.nd for c in ctx.mdl.cons]
    panels = [check.panel for check in foundation.panels]

    def corner(x, y):
        return type("Corner", (), {"x": x, "y": y, "z": foundation.level_z, "cons": None})()

    nodes = tuple(corner(x, y) for p in panels for x, y in ((p.x0, p.y0), (p.x1, p.y1))) + tuple(supports)
    view = View(naming.level(foundation.level_z) + "層", axes, (), (), nodes)

    def paint(c, width, height):
        t = _Transform(view, width, height)
        _draw_base(c, view, t, width, height)
        c.setLineWidth(0.5)
        for panel in panels:
            x0, y0 = t.point(panel.x0, panel.y0)
            x1, y1 = t.point(panel.x1, panel.y1)
            c.rect(x0, y0, x1 - x0, y1 - y0, stroke=1, fill=0)
            c.setFont(FONT, 6.0)
            c.drawCentredString((x0 + x1) / 2.0, (y0 + y1) / 2.0 - 2.0, panel.slab)
        x_named = {name: value for value, name in naming.x_grids}
        y_named = {name: value for value, name in naming.y_grids}
        c.setLineWidth(1.6)
        for line in settings.beam_lines:
            if line.frame in y_named:
                a = t.point(x_named[line.span[0]], y_named[line.frame])
                b = t.point(x_named[line.span[1]], y_named[line.frame])
            else:
                a = t.point(x_named[line.frame], y_named[line.span[0]])
                b = t.point(x_named[line.frame], y_named[line.span[1]])
            c.line(a[0], a[1], b[0], b[1])
            c.setFont(FONT, 5.0)
            c.drawCentredString((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0 + 2.5, line.beam)
        c.setFillColor(COLOR_RESULT)
        for node in supports:
            x, y = t.point(node.x, node.y)
            c.circle(x, y, 1.3, stroke=0, fill=1)
        c.setFillColor(COLOR_MEMBER)

    return Figure(FIGURE_HEIGHT, paint, title=view.title)


def ratio_figures(ctx, ratios):
    """Elevations labelled with each member's governing check ratio."""

    def label(e):
        ratio = ratios.get(e.id)
        if ratio is None:
            return ""
        return fmt(ratio, 2) + ("*" if ratio > 1.0 else "")

    return [Figure(FIGURE_HEIGHT, _model_painter(v, label), title=v.title) for v in elevation_views(ctx)]
