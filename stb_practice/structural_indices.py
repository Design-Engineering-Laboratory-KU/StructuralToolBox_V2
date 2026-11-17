from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


TOLERANCE = 1.0e-9
DRIFT_ROUTE2_LIMIT = 1.0 / 200.0
ECCENTRICITY_ROUTE_LIMIT = 0.15
RIGIDITY_ROUTE2_LIMIT = 0.6
LATERAL_MEMBER_KINDS = ("lateral_resisting_element", "column", "brace", "wall")
SHEAR_PANEL_ELEM_ID_BASE = 900_000
WALL_ELEMENT_ID_OFFSET = 50_000  # WWLL MODEL=3 rows, kept apart from MODEL=1 panel ids


@dataclass(frozen=True)
class LateralCase:
    axis: str
    load_case: int
    name: str
    sign: int = 1
    source: str = "project"


@dataclass(frozen=True)
class StoryIndex:
    name: str
    elevation: float
    height: float


@dataclass(frozen=True)
class StoryDriftRow:
    story: str
    direction: str
    load_case: int
    element_id: int
    lower_node: int
    upper_node: int
    lower_disp_m: float
    upper_disp_m: float
    drift_m: float
    height_m: float
    drift_angle: float
    inverse_ratio: Optional[float]
    is_story_max: bool = False
    status: str = "OK"


@dataclass(frozen=True)
class MemberStiffnessRow:
    story: str
    element_id: int
    member_class: str
    x: float
    y: float
    qx_x_kN: Optional[float]
    qy_x_kN: Optional[float]
    dx_x_m: Optional[float]
    dy_x_m: Optional[float]
    qx_y_kN: Optional[float]
    qy_y_kN: Optional[float]
    dx_y_m: Optional[float]
    dy_y_m: Optional[float]
    dxx_kN_m: Optional[float]
    dxy_kN_m: Optional[float]
    dyy_kN_m: Optional[float]
    status: str = "OK"


@dataclass(frozen=True)
class EccentricityRow:
    story: str
    xg: Optional[float]
    yg: Optional[float]
    xs: Optional[float]
    ys: Optional[float]
    ex: Optional[float]
    ey: Optional[float]
    kx_kN_m: Optional[float]
    ky_kN_m: Optional[float]
    kr_kN_m: Optional[float]
    rex_m: Optional[float]
    rey_m: Optional[float]
    re_x: Optional[float]
    re_y: Optional[float]
    fe_x: Optional[float]
    fe_y: Optional[float]
    status: str = "OK"


@dataclass(frozen=True)
class RigidityRatioRow:
    story: str
    direction: str
    load_case: int
    height_m: float
    drift_m: Optional[float]
    inverse_ratio: Optional[float]
    mean_inverse_ratio: Optional[float]
    rigidity_ratio: Optional[float]
    fs: Optional[float]
    status: str = "OK"


@dataclass(frozen=True)
class StructuralIndicesResult:
    lateral_cases: Tuple[LateralCase, ...]
    story_drifts: Tuple[StoryDriftRow, ...]
    member_stiffnesses: Tuple[MemberStiffnessRow, ...]
    eccentricities: Tuple[EccentricityRow, ...]
    rigidity_ratios: Tuple[RigidityRatioRow, ...]
    warnings: Tuple[str, ...]
    tables: Dict[str, Tuple[dict, ...]]


def build_structural_indices(mdl, project) -> StructuralIndicesResult:
    warnings: List[str] = []
    stories = _story_indices(project)
    if not stories:
        warnings.append("No stories are defined in project.json.")

    lateral_cases = _lateral_cases(mdl, project, warnings)
    vertical_members = _vertical_lateral_members(mdl, project, stories, warnings)

    drift_rows = _build_story_drift_rows(mdl, stories, vertical_members, lateral_cases)
    stiffness_rows = _build_member_stiffness_rows(mdl, stories, vertical_members, lateral_cases)
    stiffness_rows.extend(_build_shear_panel_stiffness_rows(mdl, stories))
    eccentricity_rows = _build_eccentricity_rows(mdl, project, stories, stiffness_rows)
    rigidity_rows = _build_rigidity_ratio_rows(project, stories, drift_rows, lateral_cases)

    _append_limit_warnings(project, drift_rows, eccentricity_rows, rigidity_rows, warnings)
    if not vertical_members and not _rated_wall_panels(mdl):
        warnings.append("No vertical lateral members were available for structural indices.")
    if not lateral_cases:
        warnings.append("No X/Y lateral load cases were available for structural indices.")

    tables = {
        "lateral_cases": tuple(_lateral_case_to_dict(c) for c in lateral_cases),
        "story_drifts": tuple(_story_drift_to_dict(r) for r in drift_rows),
        "member_stiffnesses": tuple(_member_stiffness_to_dict(r) for r in stiffness_rows),
        "eccentricities": tuple(_eccentricity_to_dict(r) for r in eccentricity_rows),
        "rigidity_ratios": tuple(_rigidity_ratio_to_dict(r) for r in rigidity_rows),
    }

    return StructuralIndicesResult(
        lateral_cases=tuple(lateral_cases),
        story_drifts=tuple(drift_rows),
        member_stiffnesses=tuple(stiffness_rows),
        eccentricities=tuple(eccentricity_rows),
        rigidity_ratios=tuple(rigidity_rows),
        warnings=tuple(dict.fromkeys(warnings)),
        tables=tables,
    )


def _story_indices(project) -> List[StoryIndex]:
    stories = []
    for s in sorted(getattr(project, "stories", ()), key=lambda x: (x.elevation, x.name)):
        stories.append(StoryIndex(name=s.name, elevation=float(s.elevation), height=float(s.height)))
    return stories


def _lateral_cases(mdl, project, warnings: List[str]) -> List[LateralCase]:
    cases: List[LateralCase] = []
    seen = set()
    for d in getattr(getattr(project, "load_conditions", None), "seismic", ()).directions:
        axis = str(d.axis).lower()
        if axis not in ("x", "y"):
            continue
        if not _has_lc(mdl, d.load_case):
            warnings.append("Seismic direction {0} references missing LC {1}.".format(d.name, d.load_case))
            continue
        key = (axis, int(d.load_case))
        if key in seen:
            continue
        seen.add(key)
        cases.append(LateralCase(axis=axis, load_case=int(d.load_case), name=d.name, sign=int(d.sign), source="project"))

    if cases:
        return cases

    inferred = _infer_lateral_cases_from_dlod(mdl)
    if inferred:
        warnings.append("No seismic directions were defined; lateral cases were inferred from DLOD/LNME.")
    return inferred


def _infer_lateral_cases_from_dlod(mdl) -> List[LateralCase]:
    candidates: Dict[str, Dict[int, float]] = {"x": {}, "y": {}}
    for dl in getattr(mdl, "dloads", []) or []:
        if getattr(dl, "load_type", "") != "AREA":
            continue
        lc = int(getattr(dl, "lc", getattr(dl, "clc", -1)))
        if lc < 0 or not _has_lc(mdl, lc):
            continue
        px = abs(float(getattr(dl, "px", 0.0)))
        py = abs(float(getattr(dl, "py", 0.0)))
        if px > TOLERANCE:
            candidates["x"][lc] = candidates["x"].get(lc, 0.0) + px
        if py > TOLERANCE:
            candidates["y"][lc] = candidates["y"].get(lc, 0.0) + py

    out = []
    for axis in ("x", "y"):
        if not candidates[axis]:
            continue
        lc = max(candidates[axis], key=lambda k: candidates[axis][k])
        out.append(LateralCase(axis=axis, load_case=lc, name=_lc_label(mdl, lc) or axis.upper(), source="inferred_dlod"))
    return out


def _has_lc(mdl, lc: int) -> bool:
    return int(lc) in [int(x) for x in (getattr(mdl, "lcs", None) or [])]


def _lc_index(mdl, lc: int) -> Optional[int]:
    for i, item in enumerate(getattr(mdl, "lcs", None) or []):
        if int(item) == int(lc):
            return i
    return None


def _lc_label(mdl, lc: int) -> str:
    for item in getattr(mdl, "lcases", []) or []:
        if int(getattr(item, "lc", -1)) == int(lc):
            return str(getattr(item, "label", "") or getattr(item, "lname", "") or "")
    return ""


def _vertical_lateral_members(mdl, project, stories: Sequence[StoryIndex], warnings: List[str]):
    class_by_element_id = {}
    for mc in getattr(project, "member_classes", ()) or ():
        if str(mc.kind) not in LATERAL_MEMBER_KINDS:
            continue
        for eid in mc.element_ids:
            class_by_element_id[int(eid)] = mc

    if not class_by_element_id:
        # Wall columns generated for WWLL MODEL=3 are counted through the wall itself.
        wall_columns = {id(we.column) for we in getattr(mdl, "wwelems", []) or []}
        for e in getattr(mdl, "elms", []) or []:
            if _is_vertical_member(e) and id(e) not in wall_columns:
                class_by_element_id[int(e.id)] = None
        if class_by_element_id:
            warnings.append("No lateral member classes were defined; vertical members were used as lateral members.")

    members = []
    for eid, mc in sorted(class_by_element_id.items()):
        e = mdl.FindElemFromEid(eid)
        if e == -1:
            warnings.append("Lateral member class references missing element {0}.".format(eid))
            continue
        if not _is_vertical_member(e):
            continue
        story = str(getattr(mc, "story", "") or "") if mc is not None else _story_for_member(e, stories)
        if not story:
            story = _story_for_member(e, stories)
        members.append((e, mc, story))
    return members


def _is_vertical_member(e) -> bool:
    dx = float(e.n1.x - e.n0.x)
    dy = float(e.n1.y - e.n0.y)
    dz = float(e.n1.z - e.n0.z)
    return abs(dz) > math.hypot(dx, dy)


def _story_for_z_midpoint(z_mid: float, stories: Sequence[StoryIndex]) -> str:
    last = len(stories) - 1
    for i, s in enumerate(stories):
        lo = s.elevation - TOLERANCE
        top = s.elevation + s.height
        hi = top + TOLERANCE if i == last else top - TOLERANCE
        if lo <= z_mid <= hi:
            return s.name
    return ""


def _story_for_member(e, stories: Sequence[StoryIndex]) -> str:
    mid = 0.5 * (float(e.n0.z) + float(e.n1.z))
    return _story_for_z_midpoint(mid, stories)


def _story_by_name(stories: Sequence[StoryIndex], name: str) -> Optional[StoryIndex]:
    for s in stories:
        if s.name == name:
            return s
    return None


def _node_disp(node, mdl, lc: int, axis: str) -> Optional[float]:
    idx = _lc_index(mdl, lc)
    if idx is None or getattr(node, "disps", None) is None:
        return None
    row = 0 if axis == "x" else 1
    return float(node.disps[row, idx])


def _member_delta(e, mdl, lc: int) -> Optional[Tuple[float, float]]:
    idx = _lc_index(mdl, lc)
    if idx is None or getattr(e.n0, "disps", None) is None or getattr(e.n1, "disps", None) is None:
        return None
    lower, upper = _lower_upper_nodes(e)
    dx = float(upper.disps[0, idx] - lower.disps[0, idx])
    dy = float(upper.disps[1, idx] - lower.disps[1, idx])
    return dx, dy


def _lower_upper_nodes(e):
    return (e.n0, e.n1) if e.n0.z <= e.n1.z else (e.n1, e.n0)


def _build_story_drift_rows(mdl, stories, members, lateral_cases) -> List[StoryDriftRow]:
    rows: List[StoryDriftRow] = []
    for case in lateral_cases:
        for e, _mc, story_name in members:
            story = _story_by_name(stories, story_name)
            if story is None or story.height <= TOLERANCE:
                continue
            lower, upper = _lower_upper_nodes(e)
            d0 = _node_disp(lower, mdl, case.load_case, case.axis)
            d1 = _node_disp(upper, mdl, case.load_case, case.axis)
            if d0 is None or d1 is None:
                continue
            drift = d1 - d0
            angle = abs(drift) / story.height
            rows.append(StoryDriftRow(
                story=story.name,
                direction=case.axis,
                load_case=case.load_case,
                element_id=int(e.id),
                lower_node=int(lower.id),
                upper_node=int(upper.id),
                lower_disp_m=d0,
                upper_disp_m=d1,
                drift_m=drift,
                height_m=story.height,
                drift_angle=angle,
                inverse_ratio=(1.0 / angle if angle > TOLERANCE else None),
            ))

    max_keys = {}
    for i, row in enumerate(rows):
        key = (row.story, row.direction, row.load_case)
        cur = max_keys.get(key)
        if cur is None or row.drift_angle > rows[cur].drift_angle:
            max_keys[key] = i
    marked = []
    for i, row in enumerate(rows):
        marked.append(StoryDriftRow(**{**row.__dict__, "is_story_max": i in set(max_keys.values())}))
    return marked


def _build_member_stiffness_rows(mdl, stories, members, lateral_cases) -> List[MemberStiffnessRow]:
    x_case = next((c for c in lateral_cases if c.axis == "x"), None)
    y_case = next((c for c in lateral_cases if c.axis == "y"), None)
    rows = []
    for e, mc, story_name in members:
        qx_x = qy_x = dx_x = dy_x = qx_y = qy_y = dx_y = dy_y = None
        if x_case is not None:
            q = _member_global_shear(e, mdl, x_case.load_case)
            d = _member_delta(e, mdl, x_case.load_case)
            if q is not None:
                qx_x, qy_x = q[0] * 1.0e-3, q[1] * 1.0e-3
            if d is not None:
                dx_x, dy_x = d
        if y_case is not None:
            q = _member_global_shear(e, mdl, y_case.load_case)
            d = _member_delta(e, mdl, y_case.load_case)
            if q is not None:
                qx_y, qy_y = q[0] * 1.0e-3, q[1] * 1.0e-3
            if d is not None:
                dx_y, dy_y = d
        dxx, dxy, dyy, status = _stiffness_components(qx_x, qy_x, dx_x, dy_x, qx_y, qy_y, dx_y, dy_y)
        x, y = _element_xy(e)
        rows.append(MemberStiffnessRow(
            story=story_name or _story_for_member(e, stories),
            element_id=int(e.id),
            member_class=(mc.name if mc is not None else ""),
            x=x,
            y=y,
            qx_x_kN=qx_x,
            qy_x_kN=qy_x,
            dx_x_m=dx_x,
            dy_x_m=dy_x,
            qx_y_kN=qx_y,
            qy_y_kN=qy_y,
            dx_y_m=dx_y,
            dy_y_m=dy_y,
            dxx_kN_m=dxx,
            dxy_kN_m=dxy,
            dyy_kN_m=dyy,
            status=status,
        ))
    return rows


def _member_global_shear(e, mdl, lc: int) -> Optional[Tuple[float, float]]:
    idx = _lc_index(mdl, lc)
    if idx is None or getattr(e, "forces", None) is None or getattr(e, "tm", None) is None:
        return None
    f = e.forces[:, idx]
    sub_tm = np.array(e.tm[0:3, 0:3], dtype=float)
    gi = sub_tm.T @ np.array([float(f[0]), float(f[1]), float(f[2])])
    gj = sub_tm.T @ np.array([float(f[6]), float(f[7]), float(f[8])])
    out = []
    for comp_i, comp_j in ((gi[0], gj[0]), (gi[1], gj[1])):
        if comp_i == 0.0:
            out.append(float(comp_j))
        elif comp_j == 0.0:
            out.append(float(comp_i))
        elif comp_i * comp_j >= 0.0:
            out.append(float(0.5 * (comp_i + comp_j)))
        else:
            out.append(float(comp_i if abs(comp_i) >= abs(comp_j) else comp_j))
    return out[0], out[1]


def _stiffness_components(qx_x, qy_x, dx_x, dy_x, qx_y, qy_y, dx_y, dy_y):
    dxx = (qx_x / dx_x) if qx_x is not None and dx_x not in (None, 0.0) and abs(dx_x) > TOLERANCE else None
    dyy = (qy_y / dy_y) if qy_y is not None and dy_y not in (None, 0.0) and abs(dy_y) > TOLERANCE else None
    dxy = 0.0
    if None not in (qx_x, qy_x, dx_x, dy_x, qx_y, qy_y, dx_y, dy_y):
        delta = np.array([[dx_x, dx_y], [dy_x, dy_y]], dtype=float)
        force = np.array([[qx_x, qx_y], [qy_x, qy_y]], dtype=float)
        det = float(np.linalg.det(delta))
        scale = max(abs(float(dx_x)), abs(float(dx_y)), abs(float(dy_x)), abs(float(dy_y)), TOLERANCE)
        if abs(det) > TOLERANCE and abs(det) / (scale * scale) > 0.05:
            d = force @ np.linalg.inv(delta)
            dxy = 0.5 * (float(d[0, 1]) + float(d[1, 0]))
            return float(d[0, 0]), dxy, float(d[1, 1]), "OK"

    if dxx is None and dyy is None:
        return None, None, None, "insufficient_data"
    return dxx, dxy, dyy, "diagonal_fallback"


def _element_xy(e) -> Tuple[float, float]:
    return 0.5 * (float(e.n0.x) + float(e.n1.x)), 0.5 * (float(e.n0.y) + float(e.n1.y))


def _shear_panel_xy(panel) -> Tuple[float, float]:
    nodes = panel.nodes()
    if not nodes:
        return 0.0, 0.0
    x = sum(float(n.x) for n in nodes) / len(nodes)
    y = sum(float(n.y) for n in nodes) / len(nodes)
    return x, y


def _story_for_shear_panel(panel, stories: Sequence[StoryIndex]) -> str:
    nodes = panel.nodes()
    if not nodes:
        return ""
    z_mid = sum(float(n.z) for n in nodes) / len(nodes)
    return _story_for_z_midpoint(z_mid, stories)


def _rated_wall_panels(mdl):
    """Shear panels (WWLL MODEL=1) and wall elements (MODEL=3), which share one reporting view."""
    return list(getattr(mdl, "wshears", []) or []) + list(getattr(mdl, "wwelems", []) or [])


def _build_shear_panel_stiffness_rows(mdl, stories: Sequence[StoryIndex]) -> List[MemberStiffnessRow]:
    """Rated walls (WWLL MODEL=1 and 3) as directional spring stiffness K at the wall centroid."""
    rows: List[MemberStiffnessRow] = []
    for panel in _rated_wall_panels(mdl):
        story_name = _story_for_shear_panel(panel, stories)
        if not story_name:
            continue
        direction = str(getattr(panel, "direction", "")).upper()
        if direction not in ("X", "Y"):
            continue
        k_kN_m = float(panel.k) / 1000.0
        if k_kN_m <= TOLERANCE:
            continue
        x, y = _shear_panel_xy(panel)
        dxx = k_kN_m if direction == "X" else None
        dyy = k_kN_m if direction == "Y" else None
        wall_id = int(getattr(panel, "wall_id", 0) or 0)
        label = str(getattr(panel, "name", "") or "").strip()
        member_class = "shear_panel"
        if label:
            member_class = "shear_panel ({0})".format(label)
        rows.append(MemberStiffnessRow(
            story=story_name,
            element_id=SHEAR_PANEL_ELEM_ID_BASE + (WALL_ELEMENT_ID_OFFSET if hasattr(panel, "column") else 0) + int(panel.id),
            member_class=member_class,
            x=x,
            y=y,
            qx_x_kN=None,
            qy_x_kN=None,
            dx_x_m=None,
            dy_x_m=None,
            qx_y_kN=None,
            qy_y_kN=None,
            dx_y_m=None,
            dy_y_m=None,
            dxx_kN_m=dxx,
            dxy_kN_m=0.0,
            dyy_kN_m=dyy,
            status="shear_panel",
        ))
    return rows


def _build_eccentricity_rows(mdl, project, stories, stiffness_rows) -> List[EccentricityRow]:
    out = []
    for story in stories:
        rows = [r for r in stiffness_rows if r.story == story.name]
        xg, yg = _center_of_mass_for_story(mdl, project, story)
        valid = [r for r in rows if r.dxx_kN_m is not None or r.dyy_kN_m is not None]
        if not valid:
            out.append(EccentricityRow(story.name, xg, yg, None, None, None, None, None, None, None, None, None, None, None, None, None, "no_stiffness"))
            continue
        kxx = sum(_positive_stiffness(r.dxx_kN_m) for r in valid)
        kxy = sum(abs(float(r.dxy_kN_m or 0.0)) for r in valid)
        kyy = sum(_positive_stiffness(r.dyy_kN_m) for r in valid)
        xs, ys = _directional_rigidity_center(valid)
        status = "OK"
        if xs is None or ys is None:
            out.append(EccentricityRow(story.name, xg, yg, None, None, None, None, kxx, kyy, None, None, None, None, None, None, None, "center_unavailable"))
            continue
        kr = _directional_torsional_stiffness(valid, xs, ys)
        rex = _directional_elastic_radius(valid, "y", "dxx_kN_m", ys)
        rey = _directional_elastic_radius(valid, "x", "dyy_kN_m", xs)
        ex = abs(xs - xg) if xg is not None else None
        ey = abs(ys - yg) if yg is not None else None
        re_x = (ey / rex) if ey is not None and rex and rex > TOLERANCE else None
        re_y = (ex / rey) if ex is not None and rey and rey > TOLERANCE else None
        out.append(EccentricityRow(
            story=story.name,
            xg=xg,
            yg=yg,
            xs=xs,
            ys=ys,
            ex=ex,
            ey=ey,
            kx_kN_m=kxx,
            ky_kN_m=kyy,
            kr_kN_m=kr,
            rex_m=rex,
            rey_m=rey,
            re_x=re_x,
            re_y=re_y,
            fe_x=_fe(re_x),
            fe_y=_fe(re_y),
            status=status,
        ))
    return out


def _center_of_mass_for_story(mdl, project, story: StoryIndex) -> Tuple[Optional[float], Optional[float]]:
    weighted = []
    for entry in getattr(getattr(project, "load_conditions", None), "seismic_masses", ()) or ():
        if getattr(entry, "story", None) != story.name:
            continue
        weight = float(getattr(entry, "weight", None) or 0.0)
        points = _mass_entry_points(mdl, entry, story)
        if not points:
            continue
        if weight <= 0.0:
            weight = 1.0
        for x, y in points:
            weighted.append((x, y, weight / len(points)))
    if not weighted:
        for e in getattr(mdl, "elms", []) or []:
            if _story_for_member(e, [story]) != story.name:
                continue
            w = max(0.0, float(getattr(e, "weight", 0.0)))
            if w <= 0.0:
                continue
            x, y = _element_xy(e)
            weighted.append((x, y, w))
    center = _weighted_center(weighted)
    return center if center != (None, None) else (None, None)


def _mass_entry_points(mdl, entry, story: StoryIndex) -> List[Tuple[float, float]]:
    diap_id = getattr(entry, "application_diaphragm", None)
    if diap_id is not None:
        for d in getattr(mdl, "diaps", []) or []:
            if int(getattr(d, "id", -1)) != int(diap_id):
                continue
            pts = [(float(n.x), float(n.y)) for n in getattr(d, "nodes", []) or []]
            if pts:
                return pts
    pts = []
    z0 = story.elevation - 1.0e-6
    z1 = story.elevation + story.height + 1.0e-6
    for n in getattr(mdl, "nds", []) or []:
        if z0 <= float(n.z) <= z1:
            pts.append((float(n.x), float(n.y)))
    return pts


def _weighted_center(items: Iterable[Tuple[float, float, float]]) -> Tuple[Optional[float], Optional[float]]:
    vals = list(items)
    total = sum(max(0.0, w) for _x, _y, w in vals)
    if total <= TOLERANCE:
        return None, None
    x = sum(x * max(0.0, w) for x, _y, w in vals) / total
    y = sum(y * max(0.0, w) for _x, y, w in vals) / total
    return x, y


def _weighted_center_stiffness(rows: Sequence[MemberStiffnessRow]) -> Tuple[Optional[float], Optional[float]]:
    vals = []
    for r in rows:
        w = abs(float(r.dxx_kN_m or 0.0)) + abs(float(r.dyy_kN_m or 0.0))
        vals.append((r.x, r.y, w))
    return _weighted_center(vals)


def _directional_rigidity_center(rows: Sequence[MemberStiffnessRow]) -> Tuple[Optional[float], Optional[float]]:
    """Rigidity center from directional stiffness weights (Dyy -> Xs, Dxx -> Ys)."""
    x_vals = [
        (r.x, r.y, abs(float(r.dyy_kN_m or 0.0)))
        for r in rows
        if abs(float(r.dyy_kN_m or 0.0)) > TOLERANCE
    ]
    y_vals = [
        (r.x, r.y, abs(float(r.dxx_kN_m or 0.0)))
        for r in rows
        if abs(float(r.dxx_kN_m or 0.0)) > TOLERANCE
    ]
    xs = _weighted_center(x_vals)[0] if x_vals else None
    ys = _weighted_center(y_vals)[1] if y_vals else None
    if xs is None or ys is None:
        return _weighted_center_stiffness(rows)
    return xs, ys


def _positive_stiffness(value: Optional[float]) -> float:
    return max(0.0, float(value or 0.0))


def _directional_elastic_radius(
    rows: Sequence[MemberStiffnessRow],
    coord: str,
    stiff_field: str,
    center: float,
) -> Optional[float]:
    total = 0.0
    inertia = 0.0
    for r in rows:
        stiff = _positive_stiffness(getattr(r, stiff_field))
        if stiff <= TOLERANCE:
            continue
        c = float(getattr(r, coord))
        total += stiff
        inertia += stiff * (c - center) ** 2
    if total <= TOLERANCE:
        return None
    if inertia <= TOLERANCE:
        return 0.0
    return math.sqrt(inertia / total)


def _directional_torsional_stiffness(
    rows: Sequence[MemberStiffnessRow],
    xs: float,
    ys: float,
) -> Optional[float]:
    kr = 0.0
    for r in rows:
        dxx = _positive_stiffness(r.dxx_kN_m)
        dyy = _positive_stiffness(r.dyy_kN_m)
        if dxx > TOLERANCE:
            kr += dxx * (r.y - ys) ** 2
        if dyy > TOLERANCE:
            kr += dyy * (r.x - xs) ** 2
    return kr if kr > TOLERANCE else None


def _fe(re: Optional[float]) -> Optional[float]:
    if re is None:
        return None
    if re <= 0.15:
        return 1.0
    if re >= 0.3:
        return 1.5
    return 1.0 + 0.5 * (re - 0.15) / 0.15


def _build_rigidity_ratio_rows(project, stories, drift_rows, lateral_cases) -> List[RigidityRatioRow]:
    """Rigidity ratio Rs = ri / ri_mean with ri = h / delta (proxy for story stiffness)."""
    out = []
    for case in lateral_cases:
        maxima = {}
        for row in drift_rows:
            if row.direction != case.axis or row.load_case != case.load_case or not row.is_story_max:
                continue
            maxima[row.story] = abs(row.drift_m)
        rs_values = []
        for story in stories:
            drift = maxima.get(story.name)
            if drift is not None and drift > TOLERANCE:
                rs_values.append(story.height / drift)
        mean_rs = sum(rs_values) / len(rs_values) if rs_values else None
        for story in stories:
            drift = maxima.get(story.name)
            inv = (story.height / drift) if drift is not None and drift > TOLERANCE else None
            ratio = (inv / mean_rs) if inv is not None and mean_rs and mean_rs > TOLERANCE else None
            out.append(RigidityRatioRow(
                story=story.name,
                direction=case.axis,
                load_case=case.load_case,
                height_m=story.height,
                drift_m=drift,
                inverse_ratio=inv,
                mean_inverse_ratio=mean_rs,
                rigidity_ratio=ratio,
                fs=_fs(ratio),
                status=("OK" if ratio is not None else "no_drift"),
            ))
    return out


def _fs(rs: Optional[float]) -> Optional[float]:
    if rs is None:
        return None
    if rs >= 0.6:
        return 1.0
    return 2.0 - rs / 0.6


def _append_limit_warnings(project, drift_rows, eccentricity_rows, rigidity_rows, warnings: List[str]) -> None:
    route = str(getattr(getattr(project, "building", None), "calculation_route", "") or "")
    route_compact = route.replace("－", "-").replace("ー", "-")
    route2 = "2" in route_compact
    route12_or_2 = ("1-2" in route_compact) or route2
    if route2:
        for row in drift_rows:
            if row.is_story_max and row.drift_angle > DRIFT_ROUTE2_LIMIT:
                warnings.append("Story {0} {1} LC{2} drift angle exceeds 1/200.".format(row.story, row.direction.upper(), row.load_case))
        for row in rigidity_rows:
            if row.rigidity_ratio is not None and row.rigidity_ratio < RIGIDITY_ROUTE2_LIMIT:
                warnings.append("Story {0} {1} LC{2} rigidity ratio is below 0.6.".format(row.story, row.direction.upper(), row.load_case))
    if route12_or_2:
        for row in eccentricity_rows:
            if row.re_x is not None and row.re_x > ECCENTRICITY_ROUTE_LIMIT:
                warnings.append("Story {0} Rex exceeds 0.15.".format(row.story))
            if row.re_y is not None and row.re_y > ECCENTRICITY_ROUTE_LIMIT:
                warnings.append("Story {0} Rey exceeds 0.15.".format(row.story))


def _lateral_case_to_dict(c: LateralCase) -> dict:
    return c.__dict__.copy()


def _story_drift_to_dict(r: StoryDriftRow) -> dict:
    return r.__dict__.copy()


def _member_stiffness_to_dict(r: MemberStiffnessRow) -> dict:
    return r.__dict__.copy()


def _eccentricity_to_dict(r: EccentricityRow) -> dict:
    return r.__dict__.copy()


def _rigidity_ratio_to_dict(r: RigidityRatioRow) -> dict:
    d = r.__dict__.copy()
    if r.drift_m is not None and r.height_m and r.height_m > TOLERANCE:
        d["drift_angle"] = abs(float(r.drift_m)) / float(r.height_m)
    else:
        d["drift_angle"] = None
    return d
