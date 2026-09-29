"""Aligned .dat section headers shared by templates, export, and file fixups."""

from __future__ import annotations

import re


def _field(fmt: str, value) -> str:
    if value == "" or value is None:
        if fmt.startswith(">"):
            return " " * int(fmt[1:])
        return ""
    return ("{0:" + fmt + "}").format(value)


COMMENT_PREFIX = "# "


def record_line(tag: str, fmts: list[str], values: list) -> str:
    parts = [tag] + [_field(f, v) for f, v in zip(fmts, values)]
    return ", ".join(parts)


def _comment_fmts(fmts: list[str]) -> list[str]:
    """Shrink first field width so column-2+ commas align with data rows under '# '."""
    if not fmts:
        return fmts
    width = int(fmts[0][1:])
    return [">" + str(max(width - len(COMMENT_PREFIX), 1))] + fmts[1:]


def header_line(tag: str, fmts: list[str], names: list[str]) -> str:
    return COMMENT_PREFIX + record_line(tag, _comment_fmts(fmts), names)


def unit_line(tag: str, fmts: list[str], units: list[str]) -> str:
    blank_tag = " " * len(tag)
    return COMMENT_PREFIX + record_line(blank_tag, _comment_fmts(fmts), units)


def comment_data_line(tag: str, fmts: list[str], values: list) -> str:
    """Commented example row: same comma layout as a live data row."""
    return COMMENT_PREFIX + record_line(tag, fmts, values)


# --- per-record column format specs (must match Output*Info writers) ---

MATE_FMTS = [">6", ">10", ">8", ">8", ">8", ">8", ">8"]
MATE_NAMES = ["ID", "NAME", "E", "G", "Gamma", "Alpha", "Fy"]
MATE_UNITS = ["", "", "N/mm2", "N/mm2", "kN/m3", "-", "N/mm2"]

DMAT_FMTS = [">6", ">10", ">10", ">10", ">10", ">8", ">8", ">8"]
DMAT_NAMES = ["ID", "NAME", "Ex", "Ey", "Gxy", "Nuxy", "Gamma", "Alpha"]
DMAT_UNITS = ["", "", "N/mm2", "N/mm2", "N/mm2", "-", "kN/m3", "-"]

SECT_FMTS = [">6", ">10", ">6", ">6", ">8", ">8", ">8", ">8"]
SECT_NAMES = ["ID", "NAME", "MAT", "TYPE", "DIM1", "DIM2", "DIM3", "DIM4"]
SECT_UNITS = ["", "", "", "", "mm", "mm", "mm", "mm"]

NODE_FMTS = [">6", ">9", ">9", ">9"]
NODE_NAMES = ["ID", "X", "Y", "Z"]
NODE_UNITS = ["", "m", "m", "m"]

ELEM_FMTS = [">6", ">6", ">6", ">6", ">8"]
ELEM_NAMES = ["ID", "Ni", "Nj", "SEC", "Beta"]
ELEM_UNITS = ["", "", "", "", "deg"]

DIAP_FMTS = [">6", ">10", ">4", ">4", ">8", ">8", ">8", ">12", ">8"]
DIAP_NAMES = ["ID", "NAME", "TYPE", "SRC", "MAGID", "T", "THETA", "RA", "HMAX"]
DIAP_UNITS = ["", "", "", "", "", "mm", "deg", "rad", "mm"]

DMEM_FMTS = [">6", ">6", ">6", ">6", ">6"]
DMEM_NAMES = ["ID", "DIAP", "N1", "N2", "N3"]
DMEM_UNITS = ["", "", "", "", ""]

DCON_FMTS = [">6", ">4", ">6", ">4", ">8", ">8"]
DCON_NAMES = ["DIAP", "TRGT", "ID", "CONN", "TOL", "SPACING"]
DCON_UNITS = ["", "", "", "", "m", "m"]

DLOD_AREA_FMTS = [">6", ">4", ">4", ">10", ">10"]
DLOD_LINE_FMTS = [">6", ">4", ">4", ">6", ">6", ">10", ">10"]
DLOD_MBTR_FMTS = [">6", ">4", ">4", ">6", ">10", ">10"]
DLOD_MASS_FMTS = [">6", ">4", ">4", ">10", ">10", ">10"]
DLOD_WGHT_FMTS = DLOD_MASS_FMTS
DLOD_AREA_NAMES = ["DIAP", "LC", "TYPE", "PX", "PY"]
DLOD_AREA_UNITS = ["", "", "", "kN/m2", "kN/m2"]

WWLL_FMTS = [">6", ">10", ">4", ">8", ">8", ">8", ">4", ">14", ">6", ">6", ">6", ">6", ">6", ">4"]
WWLL_NAMES = ["ID", "NAME", "MODEL", "M", "L", "H", "DIR", "RA", "N1", "N2", "N3", "N4", "DIAP", "LAYO"]
WWLL_UNITS = ["", "", "", "-", "m", "m", "", "rad", "", "", "", "", "", ""]

EJNT_FMTS = [">6", ">10", ">10", ">10", ">10"]
EJNT_NAMES = ["ELEM", "Ryi", "Rzi", "Ryj", "Rzj"]
EJNT_UNITS = ["", "kNm/rad", "kNm/rad", "kNm/rad", "kNm/rad"]

CONS_FMTS = [">6", ">4", ">4", ">4", ">4", ">4", ">4"]
CONS_NAMES = ["NODE", "TX", "TY", "TZ", "RX", "RY", "RZ"]
CONS_UNITS = ["", "", "", "", "", "", ""]

LNME_FMTS = [">6", ">4", ">10"]
LNME_NAMES = ["LC", "TYPE", "LABEL"]
LNME_UNITS = ["", "", ""]

PLOD_FMTS = [">6", ">4", ">8", ">8", ">8", ">8", ">8", ">8"]
PLOD_NAMES = ["NODE", "LC", "PX", "PY", "PZ", "MX", "MY", "MZ"]
PLOD_UNITS = ["", "", "kN", "kN", "kN", "kNm", "kNm", "kNm"]

ELOD_FMTS = [">6", ">4", ">4", ">8", ">8", ">8", ">8", ">8", ">8"]
ELOD_NAMES = ["ELEM", "LC", "EG", "WXi", "WYi", "WZi", "WXj", "WYj", "WZj"]
ELOD_UNITS = ["", "", "", "kN/m", "kN/m", "kN/m", "kN/m", "kN/m", "kN/m"]

ALOD_FMTS = [">6", ">8", ">8", ">8", ">6", ">6", ">6", ">6"]
ALOD_NAMES = ["LC", "PX", "PY", "PZ", "E1", "E2", "E3", "E4"]
ALOD_UNITS = ["", "kN/m2", "kN/m2", "kN/m2", "", "", "", ""]

GLOD_FMTS = [">6", ">10", ">10", ">10"]
GLOD_NAMES = ["LC", "GX", "GY", "GZ"]
GLOD_UNITS = ["", "m/s2", "m/s2", "m/s2"]

AXIS_FMTS = [">6", ">10", ">4", ">6", ">4"]
AXIS_NAMES = ["ID", "NAME", "VH", "NID", "XDIR"]
AXIS_UNITS = ["", "", "", "", ""]

PLOT_FMTS = [">6", ">10", ">6", ">4", ">6", ">6", ">8"]
PLOT_NAMES = ["ID", "NAME", "AXIS", "TYPE", "LC", "SCALE", "DEFFAC"]
PLOT_UNITS = ["", "", "", "", "", "", ""]


def _notes(*lines: str) -> list[str]:
    return ["# " + line if not line.startswith("#") else line for line in lines]


SECTION_HEADERS: dict[str, list[str]] = {
    "MATE": [
        "# --- MATERIAL(MATE) ---",
        header_line("MATE", MATE_FMTS, MATE_NAMES),
        unit_line("MATE", MATE_FMTS, MATE_UNITS),
    ],
    "DMAT": [
        "# --- DIAPHRAGM MATERIAL(DMAT) ---",
        header_line("DMAT", DMAT_FMTS, DMAT_NAMES),
        unit_line("DMAT", DMAT_FMTS, DMAT_UNITS),
    ],
    "SECT": [
        "# --- SECTION(SECT) ---",
        header_line("SECT", SECT_FMTS, SECT_NAMES),
        unit_line("SECT", SECT_FMTS, SECT_UNITS),
        *_notes(
            "#   TYPE: 0=RECT  1=CIRC  2=I  3=CHS  4=RHS",
            "#   DIM3,DIM4: optional; omit for types with fewer dimensions",
        ),
    ],
    "NODE": [
        "# --- NODE ---",
        header_line("NODE", NODE_FMTS, NODE_NAMES),
        unit_line("NODE", NODE_FMTS, NODE_UNITS),
    ],
    "ELEM": [
        "# --- ELEMENT(ELEM) ---",
        header_line("ELEM", ELEM_FMTS, ELEM_NAMES),
        unit_line("ELEM", ELEM_FMTS, ELEM_UNITS),
    ],
    "DIAP": [
        "# --- DIAPHRAGM REGION(DIAP) ---",
        header_line("DIAP", DIAP_FMTS, DIAP_NAMES),
        unit_line("DIAP", DIAP_FMTS, DIAP_UNITS),
        *_notes(
            "#   TYPE: 0=RIGID  1=SEMI  2=FLEX",
            "#   SRC:  0=DMAT  1=TIMBER_FLOOR  2=TIMBER_ROOF",
            "#   MAGID: SRC=0 -> DMAT ID; SRC=1/2 -> floor/roof multiplier",
            "#   RA,HMAX: optional (blank allowed)",
            "#   HMAX: metadata only in current solver",
        ),
    ],
    "DREG": [
        "# --- DIAPHRAGM OUTER POLYGON(DREG) ---",
        header_line("DREG", [">6"] + [">6"] * 3, ["DIAP", "N1", "N2", "N3"]),
        *_notes(
            "#   N4,N5,...: more corner node IDs as needed",
            "#   Optional when DMEM is supplied; derived from DMEM if omitted",
        ),
    ],
    "DOPN": [
        "# --- DIAPHRAGM OPENING(DOPN) ---",
        header_line("DOPN", [">6"] + [">6"] * 3, ["DIAP", "N1", "N2", "N3"]),
        *_notes(
            "#   N4,N5,...: opening polygon node IDs",
            "#   Parsed only; openings are not applied in current solver",
        ),
    ],
    "DMEM": [
        "# --- DIAPHRAGM MEMBRANE ELEMENT(DMEM) ---",
        header_line("DMEM", DMEM_FMTS, DMEM_NAMES),
    ],
    "DCON": [
        "# --- DIAPHRAGM CONNECTION(DCON) ---",
        header_line("DCON", DCON_FMTS, DCON_NAMES),
        unit_line("DCON", DCON_FMTS, DCON_UNITS),
        *_notes(
            "#   TRGT: 0=AUTO  1=ELEM  2=NODE",
            "#   ID: target element/node ID (blank when TRGT=0)",
            "#   CONN: 0=RIGID in-plane  1=OPEN/disconnected",
            "#   SPACING: optional metadata (blank allowed; not used by current solver)",
        ),
    ],
    "DLOD": [
        "# --- DIAPHRAGM LOAD(DLOD) ---",
        header_line("DLOD", DLOD_AREA_FMTS, DLOD_AREA_NAMES),
        unit_line("DLOD", DLOD_AREA_FMTS, DLOD_AREA_UNITS),
        *_notes(
            "#   TYPE: 0=AREA(PX,PY)  1=LINE(N1,N2,PX,PY)  2=MBTR(ELEM,PX,PY)",
            "#         3=MASS(MASS,AX,AY)  4=WGHT(WGHT,AX,AY)",
            "#   MBTR: member-transfer metadata",
            "#   AX,AY: seismic acceleration coefficients for MASS/WGHT",
        ),
    ],
    "WWLL": [
        "# --- WOOD RATED WALL(WWLL) ---",
        header_line("WWLL", WWLL_FMTS, WWLL_NAMES),
        unit_line("WWLL", WWLL_FMTS, WWLL_UNITS),
        *_notes(
            "#   MODEL: 0=equivalent brace  1=shear panel  2=membrane(reserved)",
            "#   DIR: 0=X  1=Y",
            "#   N1..N4: corner nodes (bottom line N1-N2, top line N3-N4)",
            "#   DIAP: diaphragm ID for in-plane MPC tie (blank=none)",
            "#   LAYO: 0=single brace  1=X-brace pair (default)",
        ),
    ],
    "EJNT": [
        "# --- ELEMENT JOINT(EJNT) ---",
        header_line("EJNT", EJNT_FMTS, EJNT_NAMES),
        unit_line("EJNT", EJNT_FMTS, EJNT_UNITS),
        *_notes("#   blank field = default rigid offset"),
    ],
    "CONS": [
        "# --- CONSTRAINT(CONS) ---",
        header_line("CONS", CONS_FMTS, CONS_NAMES),
        *_notes("#   TX..RZ: 0=FREE  1=FIXED"),
    ],
    "LNME": [
        "# --- LOAD NAME(LNME) ---",
        header_line("LNME", LNME_FMTS, LNME_NAMES),
        *_notes(
            "#   TYPE: 1=DL  2=LL  3=LL(E)  4=S  5=W  6=E  7=CUSTOM",
            "#   LABEL: optional for TYPE 1-6; required for TYPE 7",
            "#   Wi for Ai distribution uses TYPE 1 + TYPE 3",
        ),
    ],
    "LCMB": [
        "# --- LOAD COMBINATION(LCMB) ---",
        header_line("LCMB", [">6", ">10", ">6", ">6"], ["LC", "NAME", "FC1", "LC1"]),
        *_notes("#   FC2,LC2,...: repeat factor/LC pairs"),
    ],
    "PLOD": [
        "# --- POINT LOAD(PLOD) ---",
        header_line("PLOD", PLOD_FMTS, PLOD_NAMES),
        unit_line("PLOD", PLOD_FMTS, PLOD_UNITS),
    ],
    "ELOD": [
        "# --- ELEMENT LOAD(ELOD) ---",
        header_line("ELOD", ELOD_FMTS, ELOD_NAMES),
        unit_line("ELOD", ELOD_FMTS, ELOD_UNITS),
        *_notes("#   EG: 0=element local axes  1=global axes"),
    ],
    "ALOD": [
        "# --- AREA LOAD(ALOD) ---",
        header_line("ALOD", ALOD_FMTS, ALOD_NAMES),
        unit_line("ALOD", ALOD_FMTS, ALOD_UNITS),
        *_notes("#   E4: optional for triangular panels"),
    ],
    "GLOD": [
        "# --- GRAVITY LOAD(GLOD) ---",
        header_line("GLOD", GLOD_FMTS, GLOD_NAMES),
        unit_line("GLOD", GLOD_FMTS, GLOD_UNITS),
    ],
    "AXIS": [
        "# --- AXIS (AXIS) ---",
        header_line("AXIS", AXIS_FMTS, AXIS_NAMES),
        *_notes(
            "#   VH: 0=vertical plane  1=horizontal",
            "#   XDIR: 0=global X  1=global Y (vertical plane only)",
        ),
    ],
    "PLOT": [
        "# --- PLOT (PLOT) ---",
        header_line("PLOT", PLOT_FMTS, PLOT_NAMES),
        *_notes("#   TYPE: 0=MODEL  1=LOAD  2=FORCE  3=UTIL"),
    ],
}


def example_line(key: str) -> str:
    examples = {
        "MATE": record_line("MATE", MATE_FMTS, [0, "STEEL", 205000, 79000, 78.5, 1.2e-5, 235]),
        "DMAT": record_line("DMAT", DMAT_FMTS, [0, "SLAB01", 25500, 25500, 10625.0, 0.20, 0.0, 0.0]),
        "SECT": record_line("SECT", SECT_FMTS[:6], [0, "RECT", 0, 0, 200.0, 300.0]),
        "NODE": record_line("NODE", NODE_FMTS, [0, 0.0, 0.0, 0.0]),
        "ELEM": record_line("ELEM", ELEM_FMTS, [0, 0, 1, 0, 0.0]),
        "DIAP": record_line("DIAP", DIAP_FMTS, [10, "2F_MAIN", 1, 1, 2.0, 1000.0, 0.0, 0.006667, 1820.0]),
        "DREG": record_line("DREG", [">6", ">6", ">6", ">6"], [1, 0, 1, 2]),
        "DOPN": record_line("DOPN", [">6", ">6", ">6", ">6"], [1, 4, 5, 6]),
        "DMEM": record_line("DMEM", DMEM_FMTS, [1, 1, 0, 1, 2]),
        "DCON": record_line("DCON", DCON_FMTS, [1, 1, 0, 0, 0.01, ""]),
        "DLOD": record_line("DLOD", DLOD_AREA_FMTS, [1, 1, 0, 1.0, 0.0]),
        "WWLL": record_line("WWLL", WWLL_FMTS, [1, "W1_X", 0, 2.0, 1.82, 2.73, 0, 0.0083333333, 11, 12, 22, 21, 10, 1]),
        "EJNT": record_line("EJNT", EJNT_FMTS, [0, 0.0, "", "", 0.0]),
        "CONS": record_line("CONS", CONS_FMTS, [0, 1, 1, 1, 1, 1, 1]),
        "LNME": record_line("LNME", [">6", ">4"], [1, 1]),
        "LCMB": record_line("LCMB", [">6", ">10", ">6", ">6", ">6", ">6"], [2, "EX(+)", 2.0, 0, 1.0, 1]),
        "PLOD": record_line("PLOD", PLOD_FMTS, [1, 0, 0.0, 0.0, -5.0, 0.0, 0.0, 0.0]),
        "ELOD": record_line("ELOD", ELOD_FMTS, [0, 0, 0, 0.0, 0.0, -10.0, 0.0, 0.0, -10.0]),
        "ALOD": record_line("ALOD", ALOD_FMTS, [0, 0.0, 0.0, -5.0, 0, 1, 2, 3]),
        "GLOD": record_line("GLOD", GLOD_FMTS, [0, 0.0, 0.0, -9.80665]),
        "AXIS": record_line("AXIS", AXIS_FMTS, [0, "A1", 0, 0, 0]),
        "PLOT": record_line("PLOT", PLOT_FMTS, [0, "MDL1", 0, 0, 0, 50, 50.0]),
    }
    return examples[key]


RECORD_FMTS: dict[str, list[str]] = {
    "MATE": MATE_FMTS,
    "DMAT": DMAT_FMTS,
    "SECT": SECT_FMTS,
    "NODE": NODE_FMTS,
    "ELEM": ELEM_FMTS,
    "DIAP": DIAP_FMTS,
    "DMEM": DMEM_FMTS,
    "DCON": DCON_FMTS,
    "WWLL": WWLL_FMTS,
    "EJNT": EJNT_FMTS,
    "CONS": CONS_FMTS,
    "LNME": LNME_FMTS,
    "PLOD": PLOD_FMTS,
    "ELOD": ELOD_FMTS,
    "ALOD": ALOD_FMTS,
    "GLOD": GLOD_FMTS,
    "AXIS": AXIS_FMTS,
    "PLOT": PLOT_FMTS,
}

DLOD_TYPE_FMTS = {
    0: DLOD_AREA_FMTS,
    1: DLOD_LINE_FMTS,
    2: DLOD_MBTR_FMTS,
    3: DLOD_MASS_FMTS,
    4: DLOD_WGHT_FMTS,
}


def parse_field(raw: str):
    s = raw.strip()
    if s == "":
        return ""
    try:
        if any(c in s for c in ".eE"):
            return float(s)
        return int(s)
    except ValueError:
        return s


def parse_record_line(line: str) -> tuple[str, list] | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    parts = [p.strip() for p in s.split(",")]
    if not parts:
        return None
    tag = parts[0].upper()
    return tag, [parse_field(p) for p in parts[1:]]


def fmts_for_record(tag: str, values: list) -> list[str] | None:
    if tag == "DLOD":
        if len(values) < 3:
            return None
        try:
            type_code = int(values[2]) if values[2] != "" else 0
        except (TypeError, ValueError):
            return None
        fmts = DLOD_TYPE_FMTS.get(type_code)
        if fmts is None or len(fmts) != len(values):
            return None
        return fmts
    if tag in ("DREG", "DOPN"):
        if len(values) < 4:
            return None
        return [">6"] * len(values)
    if tag == "LCMB":
        if len(values) < 4 or (len(values) - 2) % 2:
            return None
        return [">6", ">10"] + [">6"] * (len(values) - 2)
    if tag == "LNME":
        if len(values) < 2:
            return None
        fmts = [">6", ">4"]
        if len(values) >= 3 and values[2] != "":
            fmts.append(">10")
        if len(fmts) != len(values):
            return None
        return fmts
    if tag == "SECT":
        if len(values) < 4 or len(values) > len(SECT_FMTS):
            return None
        return SECT_FMTS[: len(values)]
    if tag == "NODE" and len(values) == 5:
        return NODE_FMTS + [">6"]
    if tag == "DCON" and len(values) == 5:
        return DCON_FMTS[:5]
    fmts = RECORD_FMTS.get(tag)
    if fmts is None or len(fmts) != len(values):
        return None
    return fmts


NAME_ROWS: dict[str, list[str]] = {
    "MATE": MATE_NAMES,
    "DMAT": DMAT_NAMES,
    "SECT": SECT_NAMES,
    "NODE": NODE_NAMES,
    "ELEM": ELEM_NAMES,
    "DIAP": DIAP_NAMES,
    "DMEM": DMEM_NAMES,
    "DCON": DCON_NAMES,
    "WWLL": WWLL_NAMES,
    "EJNT": EJNT_NAMES,
    "CONS": CONS_NAMES,
    "LNME": LNME_NAMES,
    "PLOD": PLOD_NAMES,
    "ELOD": ELOD_NAMES,
    "ALOD": ALOD_NAMES,
    "GLOD": GLOD_NAMES,
    "AXIS": AXIS_NAMES,
    "PLOT": PLOT_NAMES,
}

UNIT_ROWS: dict[str, list[str]] = {
    "MATE": MATE_UNITS,
    "DMAT": DMAT_UNITS,
    "SECT": SECT_UNITS,
    "NODE": NODE_UNITS,
    "ELEM": ELEM_UNITS,
    "DIAP": DIAP_UNITS,
    "DCON": DCON_UNITS,
    "WWLL": WWLL_UNITS,
    "EJNT": EJNT_UNITS,
    "PLOD": PLOD_UNITS,
    "ELOD": ELOD_UNITS,
    "ALOD": ALOD_UNITS,
    "GLOD": GLOD_UNITS,
    "DLOD": DLOD_AREA_UNITS,
}


def is_schema_comment_row(tag: str, values: list) -> bool:
    """True for # TAG, col-name / unit rows copied from section headers."""
    names = NAME_ROWS.get(tag)
    units = UNIT_ROWS.get(tag)
    for ref in (names, units):
        if ref is None or len(ref) != len(values):
            continue
        if all(v == "" or str(v) == str(r) for v, r in zip(values, ref)):
            return True
    non_empty = [v for v in values if v != ""]
    if not non_empty:
        return True
    unitish = {
        "m", "mm", "rad", "deg", "kN/m2", "kN/m", "kNm/rad", "N/mm2", "kN/m3", "-", "kNm", "kN",
    }
    return all(isinstance(v, str) and v in unitish for v in non_empty)


SECTION_TITLE_RE = re.compile(r"^#\s*---\s*.+---\s*$")


def record_key_from_line(line: str) -> str | None:
    parsed = parse_record_line(line)
    return parsed[0] if parsed else None


def ensure_section_blank_lines(lines: list[str]) -> bool:
    """Insert one blank line after the last data row before the next record type."""
    changed = False
    i = 0
    while i < len(lines):
        key = record_key_from_line(lines[i])
        if key is None:
            i += 1
            continue
        end = i + 1
        while end < len(lines) and record_key_from_line(lines[end]) == key:
            end += 1
        last_data = end - 1
        j = end
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines):
            nxt = lines[j].strip()
            nxt_key = record_key_from_line(lines[j])
            if SECTION_TITLE_RE.match(nxt) or (nxt_key is not None and nxt_key != key):
                if lines[last_data + 1].strip():
                    lines.insert(last_data + 1, "")
                    changed = True
                    end += 1
        i = end
    return changed


def reformat_record_line(line: str) -> str:
    parsed = parse_record_line(line)
    if parsed is None:
        return line.rstrip("\n")
    tag, values = parsed
    fmts = fmts_for_record(tag, values)
    if fmts is None:
        return line.rstrip("\n")
    return record_line(tag, fmts, values)


def prepare_dat_text_for_write(text: str) -> str:
    """Normalize .dat text to LF line endings for safe writes on all platforms."""

    if text is None:
        return "\n"
    lines = text.splitlines()
    if not lines:
        return "\n"
    return "\n".join(lines) + "\n"


def write_dat_text(path: str, text: str) -> None:
    """Write a .dat file using LF endings (avoids Windows text-mode \\r\\n expansion)."""

    normalized = prepare_dat_text_for_write(text)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(normalized)


NEW_MODEL_ORDER_ADVANCED = [
    "MATE", "DMAT", "SECT", "NODE", "ELEM", "DIAP", "DREG", "DOPN", "DMEM", "DCON",
    "DLOD", "WWLL", "EJNT", "CONS", "LNME", "LCMB", "PLOD", "ELOD", "ALOD", "GLOD",
    "AXIS", "PLOT",
]

# Simple GUI: no diaphragm (DMAT/DIAP/DREG/DOPN/DMEM/DCON/DLOD), wood wall (WWLL)
# or CLI plot records.
NEW_MODEL_ORDER_SIMPLE = [
    "MATE", "SECT", "NODE", "ELEM", "EJNT", "CONS", "LNME", "LCMB",
    "PLOD", "ELOD", "ALOD", "GLOD",
]


def _template_examples(key: str, mode: str) -> list[str]:
    if mode == "advanced" and key == "DLOD":
        return [
            example_line("DLOD"),
            record_line("DLOD", DLOD_LINE_FMTS, [1, 1, 1, 0, 1, 5.0, 0.0]),
            record_line("DLOD", DLOD_MBTR_FMTS, [1, 1, 2, 0, 5.0, 0.0]),
            record_line("DLOD", DLOD_MASS_FMTS, [1, 2, 3, 10.0, 0.2, 0.0]),
            record_line("DLOD", DLOD_WGHT_FMTS, [1, 2, 4, 100.0, 0.2, 0.0]),
        ]
    return [example_line(key)]


def new_model_template(mode: str = "advanced") -> str:
    mode = "simple" if mode == "simple" else "advanced"
    lines = [
        "# --- NEW MODEL ---",
        "# Structural Toolbox input file",
        "#",
        "# TYPE OF ANALYSIS: 3D LINEAR STATIC",
        "#",
    ]
    order = NEW_MODEL_ORDER_SIMPLE if mode == "simple" else NEW_MODEL_ORDER_ADVANCED
    for key in order:
        lines.extend(SECTION_HEADERS[key])
        for ex in _template_examples(key, mode):
            lines.append(COMMENT_PREFIX + ex)
        lines.append("#")
    return "\n".join(lines) + "\n"
