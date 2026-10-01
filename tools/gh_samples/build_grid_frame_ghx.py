"""Write grasshopper/samples/building_grid_frame.ghx.

A parametric version of data/building_2f_x1y2.dat: span counts, span lengths and
story heights are sliders feeding STb Grid Frame, and the rest of the definition
assigns materials, sections, supports and loads, analyzes the model and previews
the results.

Run from the repository root:

    python tools/gh_samples/build_grid_frame_ghx.py
"""

import os
import uuid
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "grasshopper", "samples", "building_grid_frame.ghx")

STB_LIB = "984f5847-93df-4f6f-8da7-645af10d7394"
GH_VERSION = "8.35.26251.13001"

GUID = {
    "slider": "57da07bd-ecab-415d-9d86-af36d7073abc",
    "panel": "59e0b89a-e487-49f8-bab8-b5bab16be14c",
    "toggle": "2e78987b-9dfb-42a2-8b76-3923ac8bd91a",
    "grid": "6f3d2b81-4c9e-4a57-b0e2-8d1c5a7f9e36",
    "mat": "2c6d678d-92f9-4ee5-a171-e95d64b1411b",
    "sect": "fd94f3c4-1574-45dc-bd80-6635f18517dd",
    "elem": "e9ac94fe-4ee4-4d15-b16b-7881e3b1f622",
    "support": "54816191-f022-43a1-b094-9bb5cf4bc371",
    "aload": "79badf8b-9c6c-47d7-bef5-ab1f729b89fb",
    "gload": "3c6f0a52-7d1e-4b8a-9f35-2e8d41c7b906",
    "assemble": "ce8a157a-b1b7-4d92-918f-e6ce2294af1c",
    "analyze": "04bd3b60-c622-46f8-8156-afd1f6db5cf5",
    "deformed": "da5d7290-dd2e-4e49-a21a-db2420f7f59a",
    "stress": "2e602955-531a-4bc3-b6a4-a9b7a2e517ad",
    "fdiagram": "7a7f6f8c-62a2-4e07-9ef3-0b1c8d6e4f51",
    "viewsup": "f7a8b9c0-1234-4456-0789-abcdef012345",
    "cases": "b1a8e2f4-5c91-4d0a-9b6e-3f2c8d1a4e70",
}

ROW = 20.0
COMPONENT_WIDTH = 150.0


def new_id():
    return str(uuid.uuid4())


# --- low-level chunk writers --------------------------------------------

def item(parent, name, type_name, code, value=None, index=None):
    el = ET.SubElement(parent, "item", {"name": name})
    if index is not None:
        el.set("index", str(index))
    el.set("type_name", type_name)
    el.set("type_code", str(code))
    if isinstance(value, dict):
        for key, val in value.items():
            ET.SubElement(el, key).text = str(val)
    elif value is not None:
        el.text = value
    return el


def s(parent, name, value):
    return item(parent, name, "gh_string", 10, value)


def b(parent, name, value):
    return item(parent, name, "gh_bool", 1, "true" if value else "false")


def i32(parent, name, value):
    return item(parent, name, "gh_int32", 3, str(value))


def dbl(parent, name, value):
    return item(parent, name, "gh_double", 6, repr(float(value)))


def g(parent, name, value, index=None):
    return item(parent, name, "gh_guid", 9, value, index)


def chunk(parent, name, index=None):
    el = ET.SubElement(parent, "chunk", {"name": name})
    if index is not None:
        el.set("index", str(index))
    return el


def items_of(el):
    found = el.find("items")
    return found if found is not None else ET.SubElement(el, "items")


def chunks_of(el):
    found = el.find("chunks")
    return found if found is not None else ET.SubElement(el, "chunks")


def finalize_counts(el):
    for child in el.iter():
        if child.tag in ("items", "chunks"):
            child.set("count", str(len(child)))


def rect(parent, x, y, w, h):
    item(parent, "Bounds", "gh_drawing_rectanglef", 35, {"X": x, "Y": y, "W": w, "H": h})


def point(parent, name, x, y):
    item(parent, name, "gh_drawing_pointf", 31, {"X": x, "Y": y})


def persistent(parent, kind, value):
    data = chunk(chunks_of(parent), "PersistentData")
    i32(items_of(data), "Count", 1)
    branch = chunk(chunks_of(data), "Branch", 0)
    i32(items_of(branch), "Count", 1)
    s(items_of(branch), "Path", "{0}")
    entry = items_of(chunk(chunks_of(branch), "Item", 0))
    if kind == "str":
        b(entry, "null_string", False)
        s(entry, "string", value)
    elif kind == "int":
        i32(entry, "number", value)
    elif kind == "num":
        dbl(entry, "number", value)
    elif kind == "bool":
        b(entry, "boolean", value)
    elif kind == "vec":
        item(entry, "vector", "gh_point3d", 51, {"X": value[0], "Y": value[1], "Z": value[2]})


# --- document model ------------------------------------------------------

class Param(object):
    def __init__(self, name, nick, default=None, kind=None, flatten=False, optional=False):
        self.name = name
        self.nick = nick
        self.default = default
        self.kind = kind
        self.flatten = flatten
        self.optional = optional
        self.id = new_id()
        self.sources = []


class Obj(object):
    def __init__(self, doc, x, y):
        self.doc = doc
        self.x = x
        self.y = y
        self.id = new_id()
        doc.objects.append(self)


class Component(Obj):
    def __init__(self, doc, key, name, nick, x, y, inputs, outputs, extra=None, hidden=False):
        Obj.__init__(self, doc, x, y)
        self.key = key
        self.name = name
        self.nick = nick
        self.inputs = [Param(*p) if isinstance(p, tuple) else p for p in inputs]
        self.outputs = [Param(n, k) for n, k in outputs]
        self.extra = extra or []
        self.hidden = hidden

    def i(self, name):
        return next(p for p in self.inputs if p.name == name)

    def o(self, name):
        return next(p for p in self.outputs if p.name == name)

    def write(self, parent):
        obj = chunk(parent, "Object")
        head = items_of(obj)
        g(head, "GUID", GUID[self.key])
        g(head, "Lib", STB_LIB)
        s(head, "Name", self.name)

        container = chunk(chunks_of(obj), "Container")
        c_items = items_of(container)
        s(c_items, "Description", self.name)
        if self.hidden:
            b(c_items, "Hidden", True)
        g(c_items, "InstanceGuid", self.id)
        s(c_items, "Name", self.name)
        s(c_items, "NickName", self.nick)
        for kind, name, value in self.extra:
            {"int": i32, "num": dbl, "bool": b}[kind](c_items, name, value)

        rows = max(len(self.inputs), len(self.outputs), 1)
        height = rows * ROW + 4
        left, top = self.x, self.y
        attrs = items_of(chunk(chunks_of(container), "Attributes"))
        rect(attrs, left, top, COMPONENT_WIDTH, height)
        point(attrs, "Pivot", left + COMPONENT_WIDTH / 2, top + height / 2)

        for side, params in (("param_input", self.inputs), ("param_output", self.outputs)):
            px = left + 2 if side == "param_input" else left + COMPONENT_WIDTH - 52
            step = height / max(len(params), 1)
            for index, param in enumerate(params):
                pc = chunk(chunks_of(container), side, index)
                p_items = items_of(pc)
                s(p_items, "Description", param.name)
                g(p_items, "InstanceGuid", param.id)
                if param.flatten:
                    i32(p_items, "Mapping", 1)
                s(p_items, "Name", param.name)
                s(p_items, "NickName", param.nick)
                b(p_items, "Optional", param.optional)
                for k, source in enumerate(param.sources):
                    g(p_items, "Source", source, index=k)
                i32(p_items, "SourceCount", len(param.sources))
                py = top + 2 + index * step
                pa = items_of(chunk(chunks_of(pc), "Attributes"))
                rect(pa, px, py, 50, step)
                point(pa, "Pivot", px + 25, py + step / 2)
                if param.kind and not param.sources:
                    persistent(pc, param.kind, param.default)


class Slider(Obj):
    def __init__(self, doc, nick, x, y, value, lo, hi, integer=False, digits=1):
        Obj.__init__(self, doc, x, y)
        self.nick, self.value, self.lo, self.hi = nick, value, lo, hi
        self.integer, self.digits = integer, digits

    @property
    def out(self):
        return self.id

    def write(self, parent):
        obj = chunk(parent, "Object")
        g(items_of(obj), "GUID", GUID["slider"])
        s(items_of(obj), "Name", "Number Slider")
        container = chunk(chunks_of(obj), "Container")
        c = items_of(container)
        s(c, "Description", "Numeric slider for single values")
        g(c, "InstanceGuid", self.id)
        s(c, "Name", "Number Slider")
        s(c, "NickName", self.nick)
        b(c, "Optional", False)
        i32(c, "SourceCount", 0)
        attrs = items_of(chunk(chunks_of(container), "Attributes"))
        rect(attrs, self.x, self.y, 220, 20)
        point(attrs, "Pivot", self.x, self.y)
        sl = items_of(chunk(chunks_of(container), "Slider"))
        i32(sl, "Digits", 0 if self.integer else self.digits)
        i32(sl, "GripDisplay", 1)
        i32(sl, "Interval", 1 if self.integer else 0)
        dbl(sl, "Max", self.hi)
        dbl(sl, "Min", self.lo)
        i32(sl, "SnapCount", 0)
        dbl(sl, "Value", self.value)


class Toggle(Obj):
    def __init__(self, doc, nick, x, y, value):
        Obj.__init__(self, doc, x, y)
        self.nick, self.value = nick, value

    def write(self, parent):
        obj = chunk(parent, "Object")
        g(items_of(obj), "GUID", GUID["toggle"])
        s(items_of(obj), "Name", "Boolean Toggle")
        container = chunk(chunks_of(obj), "Container")
        c = items_of(container)
        s(c, "Description", "Boolean (true/false) toggle")
        g(c, "InstanceGuid", self.id)
        s(c, "Name", "Boolean Toggle")
        s(c, "NickName", self.nick)
        b(c, "Optional", False)
        i32(c, "SourceCount", 0)
        b(c, "ToggleValue", self.value)
        rect(items_of(chunk(chunks_of(container), "Attributes")), self.x, self.y, 110, 22)


class Note(Obj):
    def __init__(self, doc, text, x, y, w, h, colour="255;255;250;90"):
        Obj.__init__(self, doc, x, y)
        self.text, self.w, self.h, self.colour = text, w, h, colour

    def write(self, parent):
        obj = chunk(parent, "Object")
        g(items_of(obj), "GUID", GUID["panel"])
        s(items_of(obj), "Name", "Panel")
        container = chunk(chunks_of(obj), "Container")
        c = items_of(container)
        s(c, "Description", "A panel for custom notes and text values")
        g(c, "InstanceGuid", self.id)
        s(c, "Name", "Panel")
        s(c, "NickName", "")
        b(c, "Optional", False)
        dbl(c, "ScrollRatio", 0)
        i32(c, "SourceCount", 0)
        s(c, "UserText", self.text)
        attrs = items_of(chunk(chunks_of(container), "Attributes"))
        rect(attrs, self.x, self.y, self.w, self.h)
        i32(attrs, "MarginLeft", 0)
        i32(attrs, "MarginRight", 0)
        i32(attrs, "MarginTop", 0)
        point(attrs, "Pivot", self.x, self.y)
        props = items_of(chunk(chunks_of(container), "PanelProperties"))
        item(props, "Colour", "gh_drawing_color", 36, {"ARGB": self.colour})
        b(props, "DrawIndices", False)
        b(props, "DrawPaths", False)
        b(props, "Multiline", True)
        b(props, "SpecialCodes", False)
        b(props, "Stream", False)
        b(props, "Wrap", True)


class Doc(object):
    def __init__(self):
        self.objects = []


def wire(target, *sources):
    for source in sources:
        target.sources.append(source.id if isinstance(source, (Param, Obj)) else source)


# --- component factories -------------------------------------------------

def material(doc, x, y, name, e, gmod, gamma, alpha, fy):
    return Component(doc, "mat", "STb Mat", name, x, y, [
        Param("Name", "Name", name, "str"),
        Param("E", "E", e, "num"),
        Param("G", "G", gmod, "num"),
        Param("Gamma", "Gamma", gamma, "num"),
        Param("Alpha", "Alpha", alpha, "num"),
        Param("Fy", "Fy", fy, "num"),
    ], [("STb Mat", "Mat")])


SECTION_DIMS = {0: ("B", "H"), 2: ("H", "B", "tw", "tf"), 4: ("H", "B", "tw", "tf")}


def section(doc, x, y, name, mat, sect_type, dims):
    inputs = [Param("Name", "Name", name, "str"), Param("STb Mat", "Mat")]
    for dim_name, value in zip(SECTION_DIMS[sect_type], dims):
        inputs.append(Param(dim_name, dim_name, value, "num"))
    comp = Component(doc, "sect", "STb Section", name, x, y, inputs, [("STb Section", "Sec")],
                     extra=[("int", "SectionType", sect_type)])
    wire(comp.i("STb Mat"), mat.o("STb Mat"))
    return comp


def element(doc, x, y, name, sect, lines):
    comp = Component(doc, "elem", "STb Element", name, x, y, [
        Param("Name", "Name", name, "str"),
        Param("Line", "L"),
        Param("STb Section", "Sec"),
        Param("Beta", "Beta", 0.0, "num"),
    ], [("STb Element", "Elem")], hidden=True)
    wire(comp.i("Line"), *lines)
    wire(comp.i("STb Section"), sect.o("STb Section"))
    return comp


def area_load(doc, x, y, nick, elements, lc, pressure):
    comp = Component(doc, "aload", "STb Load", nick, x, y, [
        Param("STb Boundary Elements", "Elem"),
        Param("LC", "LC", lc, "int"),
        Param("Pressure", "P", pressure, "vec"),
    ], [("STb Load", "Ld")])
    wire(comp.i("STb Boundary Elements"), elements.o("STb Element"))
    return comp


# --- the definition ------------------------------------------------------

def build():
    doc = Doc()
    col = [0, 300, 560, 820, 1080, 1340, 1600, 1880]

    Note(doc,
         "STB sample: parametric 2-story steel frame (based on data/building_2f_x1y2.dat)\n"
         "\n"
         "- X Span / X Count: bay length and number of bays along X\n"
         "- Y Span 1, Y Span 2: bay lengths along Y. Y Count > 0 repeats them (9.0, 3.2, 9.0, ...)\n"
         "- Story H1, H2: story heights. Stories > 0 repeats them\n"
         "- Loads: floor 10 kN/m2 (LC0, base level included), wall 2 kN/m2 on Y faces (LC1), self weight (LC0)\n"
         "- Turn 'Run' on to analyze. 'LC' picks the load case for the result previews.",
         col[0] - 20, -230, 560, 150)

    sx = Slider(doc, "X Span [m]", col[0], 0, 5.5, 3.0, 12.0, digits=1)
    snx = Slider(doc, "X Count", col[0], 30, 1, 1, 8, integer=True)
    sy1 = Slider(doc, "Y Span 1 [m]", col[0], 80, 9.0, 3.0, 12.0, digits=1)
    sy2 = Slider(doc, "Y Span 2 [m]", col[0], 110, 3.2, 2.0, 12.0, digits=1)
    sny = Slider(doc, "Y Count (0 = as listed)", col[0], 140, 0, 0, 8, integer=True)
    sh1 = Slider(doc, "Story H1 [m]", col[0], 190, 3.8, 2.5, 6.0, digits=2)
    sh2 = Slider(doc, "Story H2 [m]", col[0], 220, 3.5, 2.5, 6.0, digits=2)
    snz = Slider(doc, "Stories (0 = as listed)", col[0], 250, 0, 0, 6, integer=True)

    grid = Component(doc, "grid", "STb Grid Frame", "STb Grid", col[1], 20, [
        Param("X Spans", "X"), Param("X Count", "Nx"),
        Param("Y Spans", "Y"), Param("Y Count", "Ny"),
        Param("Story Heights", "H"), Param("Stories", "Nz"),
    ], [
        ("Nodes", "Pt"), ("Columns", "C"), ("X Beams", "Bx"), ("Y Beams", "By"),
        ("X Foundation", "Fx"), ("Y Foundation", "Fy"), ("Supports", "S"),
        ("Floor Panels", "Pf"), ("Wall Panels", "Pw"),
    ])
    wire(grid.i("X Spans"), sx)
    wire(grid.i("X Count"), snx)
    wire(grid.i("Y Spans"), sy1, sy2)
    wire(grid.i("Y Count"), sny)
    wire(grid.i("Story Heights"), sh1, sh2)
    wire(grid.i("Stories"), snz)

    sn400 = material(doc, col[1], 300, "SN400B", 205000, 79000, 78.5, 1.2e-05, 235)
    bcr295 = material(doc, col[1], 450, "BCR295", 205000, 79000, 78.5, 1.2e-05, 295)
    fc24 = material(doc, col[1], 600, "FC24", 25500, 10600, 24.0, 1e-05, 24)

    c1 = section(doc, col[2], 300, "C1", bcr295, 4, (350.0, 350.0, 19.0, 19.0))
    g1 = section(doc, col[2], 450, "G1", sn400, 2, (500.0, 200.0, 12.0, 19.0))
    fg1 = section(doc, col[2], 600, "FG1", fc24, 0, (500.0, 1200.0))

    columns = element(doc, col[3], 0, "C1", c1, [grid.o("Columns")])
    beams = element(doc, col[3], 110, "G1", g1, [grid.o("X Beams"), grid.o("Y Beams")])
    found = element(doc, col[3], 220, "FG1", fg1, [grid.o("X Foundation"), grid.o("Y Foundation")])
    floor_panels = element(doc, col[3], 360, "floor panel", g1, [grid.o("Floor Panels")])
    wall_panels = element(doc, col[3], 470, "wall panel", g1, [grid.o("Wall Panels")])

    support = Component(doc, "support", "STb Support", "STb Sup", col[3], 600,
                        [Param("Point", "P")], [("STb Support", "Sup")])
    wire(support.i("Point"), grid.o("Supports"))

    floor_load = area_load(doc, col[4], 360, "Floor 10kN/m2", floor_panels, 0, (0.0, 0.0, -10.0))
    wall_load = area_load(doc, col[4], 470, "Wall 2kN/m2", wall_panels, 1, (0.0, -2.0, 0.0))
    gravity = Component(doc, "gload", "STb Gravity Load", "Self weight", col[4], 580, [
        Param("LC", "LC", 0, "int"),
        Param("Acceleration", "G", (0.0, 0.0, -9.80665), "vec"),
    ], [("STb Load", "Ld")])

    assemble = Component(doc, "assemble", "STB Assemble Model", "STb Model", col[5], 200, [
        Param("STb Element", "Elem", flatten=True),
        Param("STb Load", "Ld", flatten=True, optional=True),
        Param("STb Support", "Sup", flatten=True, optional=True),
        Param("DAT", "DAT", "", "str"),
        Param("Write", "Write", False, "bool"),
        Param("Results", "R", optional=True),
    ], [("Text", "Text"), ("DAT", "DAT"), ("STb Model", "STb Model")])
    wire(assemble.i("STb Element"), columns.o("STb Element"), beams.o("STb Element"), found.o("STb Element"))
    wire(assemble.i("STb Load"), floor_load.o("STb Load"), wall_load.o("STb Load"), gravity.o("STb Load"))
    wire(assemble.i("STb Support"), support.o("STb Support"))

    run = Toggle(doc, "Run", col[5], 380, False)
    analyze = Component(doc, "analyze", "STb Analyze", "STb Analyze", col[6], 200, [
        Param("STb Model", "STb Model"),
        Param("Python Exe", "Py", "", "str"),
        Param("Repo Root", "Root", "", "str", optional=True),
        Param("Run", "Run"),
        Param("Out Path", "Out", "", "str"),
        Param("Load Case", "LC", -1, "int"),
    ], [
        ("Success", "S"), ("Exit Code", "Code"), ("Out Path", "Out"), ("Stdout", "Stdout"),
        ("Stderr", "Stderr"), ("Summary", "Summary"), ("Results", "R"), ("STb Model", "STb Model"),
    ])
    wire(analyze.i("STb Model"), assemble.o("STb Model"))
    wire(analyze.i("Run"), run)

    lc = Slider(doc, "LC", col[6], 420, 0, 0, 1, integer=True)
    model = analyze.o("STb Model")

    deformed = Component(doc, "deformed", "STB Deformed Shape", "STB Def", col[7], 0, [
        Param("STb Model", "STb Model"),
        Param("Load Case", "LC"),
        Param("Legend", "Legend", True, "bool"),
    ], [("Initial Points", "Pi"), ("Deformed Points", "Pd"), ("Deformed Lines", "Ld"), ("Node IDs", "N"),
        ("Deformed Curves", "Cd")],
        extra=[("num", "Scale", 200.0), ("num", "ScaleMinimum", 0.0), ("num", "ScaleMaximum", 1000.0)])
    stress = Component(doc, "stress", "STB Stress", "STB Stress", col[7], 140, [
        Param("STb Model", "STb Model"),
        Param("Load Case", "LC"),
        Param("Divisions", "D", 12, "int"),
        Param("Maximum", "Max", 0.0, "num"),
        Param("Legend", "Legend", False, "bool"),
    ], [("Segments", "L"), ("Stress", "S"), ("Colors", "C")],
        extra=[("int", "StressMode", 0)], hidden=True)
    fdiagram = Component(doc, "fdiagram", "STB Force Diagram", "STB FDiagram", col[7], 290, [
        Param("STb Model", "STb Model"),
        Param("Load Case", "LC"),
        Param("Divisions", "D", 8, "int"),
        Param("Values", "V", False, "bool"),
        Param("Legend", "Legend", False, "bool"),
    ], [("Diagram", "D"), ("Values", "V"), ("Element IDs", "E")],
        extra=[("int", "ComponentIndex", 5), ("num", "DiagramScale", 0.01)], hidden=True)
    viewsup = Component(doc, "viewsup", "View Support Condition", "View Sup", col[7], 440, [
        Param("STb Model", "STb Model"),
        Param("Size", "S", 0.35, "num"),
    ], [("Points", "P"), ("Symbols", "B"), ("Conditions", "C")])
    cases = Component(doc, "cases", "STB Load Cases", "STB LC", col[7], 540, [
        Param("Results", "R"),
    ], [("Load Cases", "LC")])

    for comp in (deformed, stress, fdiagram):
        wire(comp.i("STb Model"), model)
        wire(comp.i("Load Case"), lc)
    wire(viewsup.i("STb Model"), assemble.o("STb Model"))
    wire(cases.i("Results"), analyze.o("Results"))

    Note(doc,
         "Previews: Deformed Shape is on. Stress and Force Diagram are hidden;\n"
         "enable their preview (and Legend) to compare. Only one legend at a time reads well.",
         col[7] - 20, -110, 330, 60, colour="255;210;235;245")
    return doc


def write(doc, path):
    root = ET.Element("Archive", {"name": "Root"})
    top = items_of(root)
    item(top, "ArchiveVersion", "gh_version", 80, {"Major": 0, "Minor": 2, "Revision": 2})

    definition = chunk(chunks_of(root), "Definition")
    item(items_of(definition), "plugin_version", "gh_version", 80, {"Major": 1, "Minor": 0, "Revision": 8})
    parts = chunks_of(definition)

    header = items_of(chunk(parts, "DocumentHeader"))
    g(header, "DocumentID", new_id())
    s(header, "Preview", "Shaded")
    i32(header, "PreviewMeshType", 1)
    item(header, "PreviewNormal", "gh_drawing_color", 36, {"ARGB": "100;150;0;0"})
    item(header, "PreviewSelected", "gh_drawing_color", 36, {"ARGB": "100;0;150;0"})

    props = chunk(parts, "DefinitionProperties")
    p_items = items_of(props)
    item(p_items, "Date", "gh_date", 8, "639178337510151384")
    s(p_items, "Description", "Parametric version of data/building_2f_x1y2.dat")
    b(p_items, "KeepOpen", False)
    s(p_items, "Name", os.path.basename(path))
    i32(items_of(chunk(chunks_of(props), "Revisions")), "RevisionCount", 0)
    projection = items_of(chunk(chunks_of(props), "Projection"))
    item(projection, "Target", "gh_drawing_point", 30, {"X": 60, "Y": 260})
    item(projection, "Zoom", "gh_single", 5, "0.7")
    i32(items_of(chunk(chunks_of(props), "Views")), "ViewCount", 0)

    i32(items_of(chunk(parts, "RcpLayout")), "GroupCount", 0)

    libs = chunk(parts, "GHALibraries")
    i32(items_of(libs), "Count", 2)
    gh = items_of(chunk(chunks_of(libs), "Library", 0))
    s(gh, "Author", "Robert McNeel & Associates")
    g(gh, "Id", "00000000-0000-0000-0000-000000000000")
    s(gh, "Name", "Grasshopper")
    s(gh, "Version", GH_VERSION)
    stb = items_of(chunk(chunks_of(libs), "Library", 1))
    s(stb, "AssemblyFullName", "StbGrasshopper, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null")
    s(stb, "AssemblyVersion", "1.0.0.0")
    s(stb, "Author", "Structural Toolbox")
    g(stb, "Id", STB_LIB)
    s(stb, "Name", "STB Grasshopper")
    s(stb, "Version", "")

    objects = chunk(parts, "DefinitionObjects")
    i32(items_of(objects), "ObjectCount", len(doc.objects))
    holder = chunks_of(objects)
    for index, obj in enumerate(doc.objects):
        obj.write(holder)
        holder[-1].set("index", str(index))

    finalize_counts(root)
    ET.indent(root, space="  ")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(b'<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n')
        handle.write(ET.tostring(root, encoding="utf-8"))
    print("wrote %s (%d objects)" % (path, len(doc.objects)))


if __name__ == "__main__":
    write(build(), OUT)
