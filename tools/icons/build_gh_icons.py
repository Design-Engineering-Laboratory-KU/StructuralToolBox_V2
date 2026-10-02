"""Build the 24x24 Grasshopper component icons.

Icons follow the 2021 hand-drawn StructuralToolBox set kept in
``grasshopper/gha/Resources/Icons-original``: black outlines over a single light
blue accent, transparent background for components, dark hexagon for parameter
containers. Icons that already exist there are copied verbatim; the rest are
drawn here in the same palette and stroke weight.

Run from the repository root:

    python tools/icons/build_gh_icons.py
"""

import math
import os

from PIL import Image, ImageChops, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "grasshopper", "gha", "Resources", "Icons-original")
DST = os.path.join(ROOT, "grasshopper", "gha", "Resources", "Icons")

N = 24  # final icon size in pixels
S = 8  # supersampling factor used while drawing

BLACK = (0, 0, 0, 255)
BLUE = (135, 211, 223, 255)
CLEAR = (0, 0, 0, 0)

# Reused verbatim from the 2021 set.
COPIES = {
    "Analyze": "icons_C_Sol_LS",
    "Material": "icons_C_Mat",
    "Section": "icons_C_Sec_I",
    "Element": "icons_C_Elem1D",
    "Joint": "icons_C_ElemHinge",
    "Support": "icons_C_Sup",
    "PointLoad": "icons_C_Load_P",
    "Assemble": "icons_C_Mdl",
    "Forces": "icons_C_ElemForces",
    "Reactions": "icons_C_Reaction",
    "DeformedShape": "icons_C_Def",
    "Stress": "icons_C_Sol_Util",
    "LoadContainer": "icons_P_Load_P",
    "MaterialContainer": "icons_P_Mat",
    "SectionContainer": "icons_P_Sec",
    "ModelContainer": "icons_P_Mdl",
    "ElementContainer": "icons_P_Elem1D",
    "SupportContainer": "icons_P_Sup",
}

# Reused glyph plus a corner badge.
BADGED = {
    "AnalyzeFromFile": ("icons_C_Sol_LS", "file"),
    "AssemblyFromFile": ("icons_C_Mdl", "file"),
    "DatBeams": ("icons_C_Elem1D", "file"),
    "ViewSupport": ("icons_C_Sup", "view"),
    "ViewLoad": ("icons_C_Load_P", "view"),
}


def canvas():
    return Image.new("RGBA", (N * S, N * S), CLEAR)


def sc(points):
    return [(x * S, y * S) for x, y in points]


def w(units):
    return max(1, int(round(units * S)))


def stroke(d, points, width=1.5, color=BLACK, close=False):
    pts = list(points) + ([points[0]] if close else [])
    d.line(sc(pts), fill=color, width=w(width), joint="curve")


def shape(d, points, fill=BLUE, width=1.5):
    d.polygon(sc(points), fill=fill)
    stroke(d, points, width=width, close=True)


def disc(d, cx, cy, r, fill=BLUE, width=1.5):
    d.ellipse(sc([(cx - r, cy - r), (cx + r, cy + r)]), fill=fill, outline=BLACK, width=w(width))


def arrow(d, p0, p1, width=1.4, head=3.4, spread=2.8, color=BLACK):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    bx, by = x1 - ux * head, y1 - uy * head
    d.line(sc([(x0, y0), (bx, by)]), fill=color, width=w(width))
    px, py = -uy, ux
    d.polygon(
        sc([(x1, y1),
            (bx + px * spread / 2.0, by + py * spread / 2.0),
            (bx - px * spread / 2.0, by - py * spread / 2.0)]),
        fill=color,
    )


def finish(img):
    return img.resize((N, N), Image.LANCZOS)


def load_original(name):
    src = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    return src.resize((N * S, N * S), Image.NEAREST)


# --- badges ---------------------------------------------------------------

FILE_PAGE = [(12.4, 10.8), (18.9, 10.8), (22.6, 14.3), (22.6, 22.6), (12.4, 22.6)]
FILE_FOLD = [(18.9, 10.8), (18.9, 14.3), (22.6, 14.3)]


def file_badge(d):
    d.polygon(sc(FILE_PAGE), fill=BLUE)
    stroke(d, FILE_PAGE, width=1.4, close=True)
    stroke(d, FILE_FOLD, width=1.2)
    stroke(d, [(14.6, 17.4), (20.4, 17.4)], width=1.1)
    stroke(d, [(14.6, 20.1), (20.4, 20.1)], width=1.1)


def view_badge(d):
    disc(d, 17.0, 16.0, 4.3, width=1.4)
    stroke(d, [(20.2, 19.2), (23.0, 22.2)], width=2.0)


BADGE_SILHOUETTE = {
    "file": FILE_PAGE,
    "view": None,  # handled as a circle below
}


def badge_halo(kind):
    mask = Image.new("L", (N * S, N * S), 0)
    d = ImageDraw.Draw(mask)
    if kind == "file":
        d.polygon(sc(FILE_PAGE), fill=255)
        d.line(sc(FILE_PAGE + [FILE_PAGE[0]]), fill=255, width=w(3.4), joint="curve")
    else:
        d.ellipse(sc([(17.0 - 6.0, 16.0 - 6.0), (17.0 + 6.0, 16.0 + 6.0)]), fill=255)
        d.line(sc([(20.2, 19.2), (23.0, 22.2)]), fill=255, width=w(5.0))
    return mask


def with_badge(base, kind):
    halo = badge_halo(kind)
    alpha = ImageChops.multiply(base.split()[3], ImageChops.invert(halo))
    base.putalpha(alpha)

    badge = canvas()
    d = ImageDraw.Draw(badge)
    (file_badge if kind == "file" else view_badge)(d)
    base.alpha_composite(badge)
    return base


# --- newly drawn icons ----------------------------------------------------


def line_load():
    img = canvas()
    d = ImageDraw.Draw(img)
    shape(d, [(2.4, 16.6), (21.6, 16.6), (21.6, 20.4), (2.4, 20.4)])
    stroke(d, [(3.0, 3.6), (21.0, 3.6)], width=1.6)
    for x in (5.6, 12.0, 18.4):
        arrow(d, (x, 3.6), (x, 14.8), width=1.5, head=3.6, spread=3.4)
    return img


def area_load():
    img = canvas()
    d = ImageDraw.Draw(img)
    shape(d, [(3.0, 15.5), (14.0, 12.0), (21.0, 16.5), (10.0, 20.0)], width=1.4)
    for x, y in ((7.0, 14.2), (12.0, 12.8), (17.0, 14.1)):
        arrow(d, (x, 2.6), (x, y), width=1.2, head=3.0, spread=2.5)
    return img


def gravity_load():
    img = canvas()
    d = ImageDraw.Draw(img)
    disc(d, 12.0, 6.6, 5.2, width=1.8)
    arrow(d, (12.0, 12.8), (12.0, 22.4), width=2.4, head=5.0, spread=5.4)
    return img


def load_combination():
    img = canvas()
    d = ImageDraw.Draw(img)
    stroke(d, [(12.4, 4.4), (4.2, 4.4), (9.4, 12.0), (4.2, 19.6), (12.4, 19.6)], width=1.9)
    shape(d, [(15.4, 6.4), (22.2, 6.4), (22.2, 9.6), (15.4, 9.6)], width=1.2)
    shape(d, [(15.4, 14.4), (22.2, 14.4), (22.2, 17.6), (15.4, 17.6)], width=1.2)
    return img


def area_tributary():
    img = canvas()
    d = ImageDraw.Draw(img)
    # The trapezoidal line load that a tributary area produces on one member.
    shape(d, [(2.6, 16.4), (7.8, 5.2), (16.2, 5.2), (21.4, 16.4)], width=1.4)
    shape(d, [(2.4, 17.6), (21.6, 17.6), (21.6, 21.0), (2.4, 21.0)], width=1.5)
    return img


def displacements():
    img = canvas()
    d = ImageDraw.Draw(img)
    arrow(d, (10.0, 14.0), (10.0, 3.0), width=1.5, head=3.8, spread=3.4)
    arrow(d, (10.0, 14.0), (21.4, 14.0), width=1.5, head=3.8, spread=3.4)
    arrow(d, (10.0, 14.0), (3.0, 21.2), width=1.5, head=3.8, spread=3.4)
    disc(d, 10.0, 14.0, 3.6, width=1.6)
    return img


def force_diagram():
    img = canvas()
    d = ImageDraw.Draw(img)
    left, right, base, depth = 3.2, 20.8, 7.6, 12.2
    span = (right - left) / 2.0
    mid = (left + right) / 2.0
    curve = []
    steps = 40
    for i in range(steps + 1):
        x = left + (right - left) * i / steps
        t = (x - mid) / span
        curve.append((x, base + depth * (1.0 - t * t)))
    d.polygon(sc(curve + [(right, base), (left, base)]), fill=BLUE)
    stroke(d, curve, width=1.3)
    stroke(d, [(2.2, base), (21.8, base)], width=1.8)
    return img


def load_cases():
    img = canvas()
    d = ImageDraw.Draw(img)
    for top in (14.6, 8.6, 2.6):
        shape(d, [(4.0, top + 2.6), (12.0, top), (20.0, top + 2.6), (12.0, top + 5.2)], width=1.3)
    return img


def dat_nodes():
    img = canvas()
    d = ImageDraw.Draw(img)
    stroke(d, [(5.6, 6.2), (14.2, 5.2)], width=1.3)
    stroke(d, [(5.6, 6.2), (6.4, 14.8)], width=1.3)
    for cx, cy in ((5.6, 6.2), (14.2, 5.2), (6.4, 14.8)):
        disc(d, cx, cy, 2.9, width=1.4)
    return img


def grid_frame():
    img = canvas()
    d = ImageDraw.Draw(img)
    xs, ys = (3.0, 12.0, 21.0), (21.0, 12.5, 4.0)
    shape(d, [(xs[0], ys[1]), (xs[1], ys[1]), (xs[1], ys[2]), (xs[0], ys[2])], width=1.6)
    for x in xs:
        stroke(d, [(x, ys[0]), (x, ys[2])], width=1.6)
    for y in ys[1:]:
        stroke(d, [(xs[0], y), (xs[2], y)], width=1.6)
    stroke(d, [(1.6, ys[0]), (22.4, ys[0])], width=2.0)
    return img


DRAWINGS = {
    "GridFrame": grid_frame,
    "LineLoad": line_load,
    "AreaLoad": area_load,
    "GravityLoad": gravity_load,
    "LoadCombination": load_combination,
    "AreaTributary": area_tributary,
    "Displacements": displacements,
    "ForceDiagram": force_diagram,
    "LoadCases": load_cases,
}

BADGED_DRAWINGS = {"DatNodes": (dat_nodes, "file")}


def main():
    if not os.path.isdir(DST):
        os.makedirs(DST)

    written = set()

    for name, source in sorted(COPIES.items()):
        finish(load_original(source)).save(os.path.join(DST, name + ".png"))
        written.add(name)

    for name, (source, kind) in sorted(BADGED.items()):
        finish(with_badge(load_original(source), kind)).save(os.path.join(DST, name + ".png"))
        written.add(name)

    for name, draw in sorted(DRAWINGS.items()):
        finish(draw()).save(os.path.join(DST, name + ".png"))
        written.add(name)

    for name, (draw, kind) in sorted(BADGED_DRAWINGS.items()):
        finish(with_badge(draw(), kind)).save(os.path.join(DST, name + ".png"))
        written.add(name)

    for stale in sorted(os.listdir(DST)):
        if stale.endswith(".png") and stale[:-4] not in written:
            os.remove(os.path.join(DST, stale))
            print("removed stale " + stale)

    print("wrote %d icons to %s" % (len(written), DST))


if __name__ == "__main__":
    main()
