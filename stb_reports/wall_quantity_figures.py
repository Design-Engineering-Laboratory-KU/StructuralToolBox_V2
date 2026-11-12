"""SVG plan figures for the wall-quantity report (耐力壁配置図・四分割線, 柱接合部図)."""

import html
from typing import List, Optional, Tuple

WIDTH_PX = 680.0
MARGIN_PX = 56.0
COLOR_X = "#1f6feb"      # X方向の壁
COLOR_Y = "#d1242f"      # Y方向の壁
COLOR_QUASI = "#8c959f"
COLOR_OUTLINE = "#24292f"
COLOR_GRID = "#afb8c1"
COLOR_TEXT = "#24292f"
JOINT_COLORS = {
    "い": "#8c959f", "ろ": "#8c959f",
    "は": "#1f6feb", "に": "#1f6feb", "ほ": "#1f6feb",
    "へ": "#bf8700", "と": "#bf8700", "ち": "#d1242f", "り": "#d1242f", "ぬ": "#d1242f",
    "要検討": "#d1242f",
}


class _Frame:
    def __init__(self, bounds):
        minx, miny, maxx, maxy = bounds
        span_x = max(maxx - minx, 1.0)
        span_y = max(maxy - miny, 1.0)
        self.scale = (WIDTH_PX - 2 * MARGIN_PX) / span_x
        self.minx, self.maxy = minx, maxy
        self.width = WIDTH_PX
        self.height = span_y * self.scale + 2 * MARGIN_PX

    def pt(self, x, y):
        return (MARGIN_PX + (x - self.minx) * self.scale, MARGIN_PX + (self.maxy - y) * self.scale)


def _story_polygons(project, story) -> Tuple[Tuple[Tuple[float, float], ...], ...]:
    for st in project.wall_quantity.stories:
        if st.story == story:
            return st.plan_polygons
    return ()


def _bounds(project, summary, story):
    xs, ys = [], []
    for st in project.wall_quantity.stories:
        for poly in st.plan_polygons:
            xs.extend(p[0] for p in poly)
            ys.extend(p[1] for p in poly)
    for w in summary.walls:
        if w.end_a is not None:
            xs.extend([w.end_a[0], w.end_b[0]])
            ys.extend([w.end_a[1], w.end_b[1]])
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _poly_path(frame, poly):
    pts = [frame.pt(x, y) for x, y in poly]
    return "M" + " L".join("{0:.1f},{1:.1f}".format(px, py) for px, py in pts) + " Z"


def _text(x, y, s, size=11, anchor="middle", color=COLOR_TEXT, weight="normal"):
    return ('<text x="{0:.1f}" y="{1:.1f}" font-size="{2}" text-anchor="{3}" fill="{4}" font-weight="{5}">{6}</text>'
            .format(x, y, size, anchor, color, weight, html.escape(s)))


def _base(project, summary, story, frame) -> List[str]:
    out = []
    # grid lines
    for g in project.grids:
        if g.direction == "x":
            x0, y0 = frame.pt(g.coordinate, frame.maxy)
            out.append('<line x1="{0:.1f}" y1="{1:.1f}" x2="{0:.1f}" y2="{2:.1f}" stroke="{3}" stroke-width="0.8" stroke-dasharray="6 3 1 3"/>'
                       .format(x0, MARGIN_PX - 18, frame.height - MARGIN_PX + 18, COLOR_GRID))
            out.append(_text(x0, frame.height - MARGIN_PX + 32, g.name, 10, color="#57606a"))
        else:
            _x, y0 = frame.pt(frame.minx, g.coordinate)
            out.append('<line x1="{0:.1f}" y1="{1:.1f}" x2="{2:.1f}" y2="{1:.1f}" stroke="{3}" stroke-width="0.8" stroke-dasharray="6 3 1 3"/>'
                       .format(MARGIN_PX - 18, y0, frame.width - MARGIN_PX + 18, COLOR_GRID))
            out.append(_text(MARGIN_PX - 24, y0 + 4, g.name, 10, anchor="end", color="#57606a"))
    # outlines: this story solid; the story above dashed (on 1F of a two-story building)
    for poly in _story_polygons(project, story):
        out.append('<path d="{0}" fill="#f6f8fa" stroke="{1}" stroke-width="1.4"/>'.format(_poly_path(frame, poly), COLOR_OUTLINE))
    names = [d.story for d in summary.seismic.stories]
    if len(names) == 2 and story == names[0]:
        for poly in _story_polygons(project, names[1]):
            out.append('<path d="{0}" fill="none" stroke="{1}" stroke-width="1" stroke-dasharray="5 4"/>'.format(
                _poly_path(frame, poly), "#57606a"))
    return out


def _wall_lines(frame, walls, thin=False) -> List[str]:
    out = []
    for w in walls:
        if w.end_a is None:
            continue
        (x1, y1), (x2, y2) = frame.pt(*w.end_a), frame.pt(*w.end_b)
        if w.source == "QUASI":
            color, dash = COLOR_QUASI, ' stroke-dasharray="4 3"'
        else:
            color, dash = (COLOR_X if w.direction == "x" else COLOR_Y), ""
        if thin:
            color = "#6e7781"
        out.append('<line x1="{0:.1f}" y1="{1:.1f}" x2="{2:.1f}" y2="{3:.1f}" stroke="{4}" stroke-width="{5}" stroke-linecap="butt"{6}/>'
                   .format(x1, y1, x2, y2, color, 2.0 if thin else 5.0, dash))
        if not thin:
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            label = "{0:g}".format(round(w.multiplier, 2))
            if w.direction == "x":
                out.append(_text(mx, my - 7, label, 9, color=color))
            else:
                out.append(_text(mx + 7, my + 3, label, 9, anchor="start", color=color))
    return out


def render_wall_plan_svg(project, summary, story) -> Optional[str]:
    bounds = _bounds(project, summary, story)
    if bounds is None:
        return None
    frame = _Frame(bounds)
    parts = _base(project, summary, story, frame)
    # quarter lines from the 四分割法 result
    if summary.balance is not None:
        for c in summary.balance.checks:
            if c.story != story:
                continue
            color = COLOR_X if c.direction == "x" else COLOR_Y
            for strip, inner in ((c.strips[0], c.strips[0].band[1]), (c.strips[1], c.strips[1].band[0])):
                if c.direction == "x":
                    _x0, py = frame.pt(frame.minx, inner)
                    parts.append('<line x1="{0:.1f}" y1="{1:.1f}" x2="{2:.1f}" y2="{1:.1f}" stroke="{3}" stroke-width="1" stroke-dasharray="3 3" opacity="0.8"/>'
                                 .format(MARGIN_PX - 6, py, frame.width - MARGIN_PX + 6, color))
                    parts.append(_text(frame.width - MARGIN_PX + 10, py + 4, "1/4 ({0})".format(strip.side), 9,
                                       anchor="start", color=color))
                else:
                    px, _y0 = frame.pt(inner, frame.maxy)
                    parts.append('<line x1="{0:.1f}" y1="{1:.1f}" x2="{0:.1f}" y2="{2:.1f}" stroke="{3}" stroke-width="1" stroke-dasharray="3 3" opacity="0.8"/>'
                                 .format(px, MARGIN_PX - 6, frame.height - MARGIN_PX + 6, color))
                    parts.append(_text(px, MARGIN_PX - 10, "1/4 ({0})".format(strip.side), 9, color=color))
    walls = [w for w in summary.walls if w.story == story]
    parts.extend(_wall_lines(frame, walls))
    # column marks at wall ends
    seen = set()
    for w in walls:
        if w.end_a is None or w.source != "WWLL":
            continue
        for p in (w.end_a, w.end_b):
            key = (round(p[0], 3), round(p[1], 3))
            if key in seen:
                continue
            seen.add(key)
            px, py = frame.pt(*p)
            parts.append('<rect x="{0:.1f}" y="{1:.1f}" width="6" height="6" fill="#fff" stroke="{2}" stroke-width="1"/>'
                         .format(px - 3, py - 3, COLOR_OUTLINE))
    parts.extend(_legend(frame, [
        (COLOR_X, "", "X方向 耐力壁（数値は採用倍率）"),
        (COLOR_Y, "", "Y方向 耐力壁"),
        (COLOR_QUASI, "4 3", "準耐力壁等"),
    ]))
    return _svg(frame, parts, "{0}階 耐力壁配置図".format(story))


def render_n_value_plan_svg(project, summary, story) -> Optional[str]:
    if summary.n_values is None:
        return None
    bounds = _bounds(project, summary, story)
    if bounds is None:
        return None
    frame = _Frame(bounds)
    parts = _base(project, summary, story, frame)
    parts.extend(_wall_lines(frame, [w for w in summary.walls if w.story == story], thin=True))
    for c in summary.n_values.columns:
        if c.story != story:
            continue
        px, py = frame.pt(c.x, c.y)
        color = JOINT_COLORS.get(c.joint, COLOR_TEXT)
        fill = color if c.corner else "#fff"
        parts.append('<circle cx="{0:.1f}" cy="{1:.1f}" r="5" fill="{2}" stroke="{3}" stroke-width="1.5"/>'.format(
            px, py, fill, color))
        label = c.joint if c.joint == "要検討" else "({0})".format(c.joint)
        parts.append(_text(px + 7, py - 6, label, 10, anchor="start", color=color, weight="bold"))
        parts.append(_text(px + 7, py + 12, "N={0:.2f}".format(c.n), 8, anchor="start", color="#57606a"))
    parts.extend(_legend(frame, [
        (JOINT_COLORS["ろ"], "", "（い）（ろ）"),
        (JOINT_COLORS["は"], "", "（は）〜（ほ）"),
        (JOINT_COLORS["と"], "", "（へ）（と） 引き寄せ金物"),
        (JOINT_COLORS["ち"], "", "（ち）以上"),
    ], note="● 塗りつぶし = 出隅の柱"))
    return _svg(frame, parts, "{0}階 柱頭・柱脚の接合部".format(story))


def _legend(frame, items, note=""):
    out = []
    y = frame.height + 10
    x = MARGIN_PX
    for color, dash, label in items:
        dash_attr = ' stroke-dasharray="{0}"'.format(dash) if dash else ""
        out.append('<line x1="{0:.1f}" y1="{1:.1f}" x2="{2:.1f}" y2="{1:.1f}" stroke="{3}" stroke-width="4"{4}/>'.format(
            x, y - 4, x + 18, color, dash_attr))
        out.append(_text(x + 24, y, label, 9, anchor="start"))
        x += 24 + 10.5 * len(label) + 18
    if note:
        out.append(_text(x, y, note, 9, anchor="start", color="#57606a"))
    return out


def _svg(frame, parts, title):
    height = frame.height + 20
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {0:.0f} {1:.0f}" width="{0:.0f}" height="{1:.0f}" '
            'role="img" aria-label="{2}" font-family="sans-serif">'
            '<rect width="100%" height="100%" fill="#fff"/>{3}</svg>').format(
        frame.width, height, html.escape(title), "".join(parts))
