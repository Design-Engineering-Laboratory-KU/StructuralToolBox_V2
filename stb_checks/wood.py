from dataclasses import dataclass, replace
import math
from typing import Optional, Tuple

from stb_checks import wood_floors, wood_joints, wood_standard
from stb_checks.wood_standard import WoodStandardElement, element_chord_deflection
from stb_project import ProjectDefinition, WoodAllowableStresses, WoodMemberCondition


CHECKED_MEMBER_KINDS = ("beam", "column", "brace")
DEFAULT_TOLERANCE = 1.0e-9
STRESS_UNIT = 1.0e6  # N/mm2 to N/m2

METHOD_SIMPLIFIED = "simplified"
METHOD_STANDARD = "standard"
STATUS_OK = "OK"
STATUS_NG = "NG"
STATUS_WARN = "WARN"
SIMPLIFIED_METHOD_WARNING = (
    "木造検定は簡易法です。荷重継続期間と座屈を考慮していないため、"
    "design_checks.wood.materials に基準強度を設定してください。"
)


@dataclass(frozen=True)
class WoodCheckDemand:
    load_case: int
    axial: float
    shear_y: float
    shear_z: float
    moment_y: float
    moment_z: float
    deflection: Optional[float]


@dataclass(frozen=True)
class WoodElementCheck:
    element_id: int
    member_class: str
    kind: str
    section: str
    material: str
    governing_load_case: int
    axial_ratio: float
    bending_ratio: float
    shear_ratio: float
    deflection_ratio: Optional[float]
    combined_ratio: float
    status: str
    demand: WoodCheckDemand
    duration: str = ""
    location: str = ""
    messages: Tuple[str, ...] = ()
    standard: Optional[WoodStandardElement] = None


@dataclass(frozen=True)
class WoodCheckTables:
    element_checks: Tuple[dict, ...]
    member_classes: Tuple[dict, ...]
    wall_checks: Tuple[dict, ...]
    standard_sections: Tuple[dict, ...] = ()
    standard_results: Tuple[dict, ...] = ()


@dataclass(frozen=True)
class WoodCheckSummary:
    element_checks: Tuple[WoodElementCheck, ...]
    wall_checks: Tuple["WoodWallCheck", ...]
    warnings: Tuple[str, ...]
    max_ratio: float
    status: str
    tables: WoodCheckTables
    method: str = METHOD_SIMPLIFIED
    joint_checks: Tuple[wood_joints.WoodJointCheck, ...] = ()
    floor_checks: Tuple[wood_floors.WoodFloorCheck, ...] = ()


@dataclass(frozen=True)
class _StandardContext:
    materials: dict
    durations: dict
    free_nodes: frozenset


@dataclass(frozen=True)
class WoodWallCheck:
    wall_id: int
    wall_name: str
    direction: str
    wall_magnification: float
    wall_length: float
    wall_height: float
    allowable_shear_capacity_Qa: float
    analysis_shear_force_Q: float
    utilization_ratio: float
    status: str
    governing_load_case: int


def build_wood_check_summary(mdl, project: ProjectDefinition):
    """Build wood member checks for beams, columns, and braces.

    With design_checks.wood.materials set, members are checked by the standard
    method (load duration, buckling, bearing, deflection). Otherwise the
    simplified MVP check runs and the summary carries a warning saying so.
    Strengths in project JSON are in N/mm2 and converted to internal N/m2.
    """

    warnings = []
    if project.building.structure.lower() != "wood":
        warnings.append("Project building.structure is not wood; wood checks were still evaluated.")

    load_cases = _load_cases_to_check(mdl, project, warnings)
    load_case_indices = {lc: idx for idx, lc in enumerate(mdl.lcs)}
    settings = project.design_checks.wood
    durations = _load_case_durations(project, load_cases, warnings) if settings.materials or settings.joint_assignments else {}
    standard = None
    if settings.materials:
        standard = _standard_context(mdl, project, durations)
    else:
        warnings.append(SIMPLIFIED_METHOD_WARNING)

    checks = []
    for member_class in project.member_classes:
        if member_class.kind not in CHECKED_MEMBER_KINDS:
            continue
        for element_id in member_class.element_ids:
            e = mdl.FindElemFromEid(element_id)
            if e == -1:
                warnings.append(
                    "Member class {0} references missing element {1}.".format(
                        member_class.name,
                        element_id,
                    )
                )
                continue
            if getattr(e, "forces", None) is None:
                warnings.append("Element {0} has no solved forces and was skipped.".format(element_id))
                continue
            if standard is None:
                checks.append(_check_element(e, member_class, load_cases, load_case_indices, project, warnings))
            else:
                checks.append(
                    _check_element_standard(
                        e, member_class, load_cases, load_case_indices, standard, project, warnings
                    )
                )

    wall_checks = _check_wood_rated_walls(mdl, load_cases, load_case_indices, warnings)

    if not checks:
        warnings.append("No beam, column, or brace member classes were available for wood checks.")

    joint_checks = wood_joints.build_joint_checks(
        mdl, project, load_cases, load_case_indices, durations, project.member_classes, warnings
    )
    floor_checks = wood_floors.build_floor_checks(mdl, project, load_cases, load_case_indices, warnings)
    max_ratio = max(
        [c.combined_ratio for c in checks]
        + [wc.utilization_ratio for wc in wall_checks]
        + [j.max_ratio for j in joint_checks]
        + [f.ratio for f in floor_checks]
        + [0.0]
    )
    has_any = bool(checks or wall_checks or floor_checks)
    status = (
        _overall_status(
            [c.status for c in checks]
            + [wc.status for wc in wall_checks]
            + [j.status for j in joint_checks]
            + [f.status for f in floor_checks]
        )
        if has_any
        else STATUS_WARN
    )
    tables = _build_tables(checks, wall_checks, project)
    return WoodCheckSummary(
        element_checks=tuple(checks),
        wall_checks=tuple(wall_checks),
        warnings=tuple(warnings),
        max_ratio=max_ratio,
        status=status,
        tables=tables,
        method=METHOD_SIMPLIFIED if standard is None else METHOD_STANDARD,
        joint_checks=joint_checks,
        floor_checks=floor_checks,
    )


def _overall_status(statuses):
    if STATUS_NG in statuses:
        return STATUS_NG
    if STATUS_WARN in statuses:
        return STATUS_WARN
    return STATUS_OK


def _load_case_durations(project, load_cases, warnings):
    settings = project.design_checks.wood
    explicit = {d.load_case: d.duration for d in settings.load_case_durations}
    combinations = {c.load_case: c.duration for c in project.load_conditions.load_combinations}
    durations = {}
    for lc in load_cases:
        duration = explicit.get(lc, combinations.get(lc))
        if duration is None:
            warnings.append("Load case {0} has no duration; long-term allowables were used.".format(lc))
            duration = wood_standard.LONG_TERM
        durations[lc] = duration
    return durations


def _standard_context(mdl, project, durations):
    settings = project.design_checks.wood
    return _StandardContext(
        materials={m.name: m for m in settings.materials},
        durations=durations,
        free_nodes=_free_end_nodes(mdl),
    )


def _free_end_nodes(mdl):
    """Nodes that belong to exactly one member and have no support."""

    counts = {}
    for e in mdl.elms:
        counts[id(e.n0)] = counts.get(id(e.n0), 0) + 1
        counts[id(e.n1)] = counts.get(id(e.n1), 0) + 1
    supported = {id(c.nd) for c in mdl.cons}
    return frozenset(node for node, count in counts.items() if count == 1 and node not in supported)


def _condition_for(settings, member_class):
    by_class = [c for c in settings.conditions if c.member_class == member_class.name]
    if by_class:
        return by_class[0]
    by_kind = [c for c in settings.conditions if c.kind == member_class.kind]
    if by_kind:
        return by_kind[0]
    return WoodMemberCondition()


def _check_element_standard(e, member_class, load_cases, load_case_indices, context, project, warnings):
    settings = project.design_checks.wood
    material = context.materials.get(e.sec.mat.name)
    if material is None:
        warnings.append(
            "Element {0}: material {1} has no base strengths and was not checked.".format(e.id, e.sec.mat.name)
        )
        return _unchecked_element(e, member_class, load_cases, load_case_indices)
    if not wood_standard.is_supported_section(e.sec):
        warnings.append("Element {0}: only rectangular sections are supported and it was not checked.".format(e.id))
        return _unchecked_element(e, member_class, load_cases, load_case_indices)

    is_cantilever = (id(e.n0) in context.free_nodes) != (id(e.n1) in context.free_nodes)
    result = wood_standard.check_element(
        e,
        material,
        _condition_for(settings, member_class),
        member_class.kind,
        load_cases,
        load_case_indices,
        context.durations,
        is_cantilever=is_cantilever,
        fallback_deflection_ratio=settings.deflection_limit_ratio,
    )
    governing = result.governing
    demand = _demand_for_load_case(e, governing.load_case, load_case_indices[governing.load_case])
    return WoodElementCheck(
        element_id=e.id,
        member_class=member_class.name,
        kind=member_class.kind,
        section=e.sec.name,
        material=e.sec.mat.name,
        governing_load_case=governing.load_case,
        axial_ratio=governing.axial_ratio,
        bending_ratio=governing.bending_ratio,
        shear_ratio=governing.shear_ratio,
        deflection_ratio=governing.deflection_ratio,
        combined_ratio=governing.ratio,
        status=STATUS_OK if governing.ratio <= 1.0 and not result.messages else STATUS_NG,
        demand=replace(demand, deflection=governing.deflection),
        duration=governing.duration,
        location=governing.location,
        messages=result.messages,
        standard=result,
    )


def _unchecked_element(e, member_class, load_cases, load_case_indices):
    load_case = load_cases[0]
    return WoodElementCheck(
        element_id=e.id,
        member_class=member_class.name,
        kind=member_class.kind,
        section=e.sec.name,
        material=e.sec.mat.name,
        governing_load_case=load_case,
        axial_ratio=0.0,
        bending_ratio=0.0,
        shear_ratio=0.0,
        deflection_ratio=None,
        combined_ratio=0.0,
        status=STATUS_WARN,
        demand=_demand_for_load_case(e, load_case, load_case_indices[load_case]),
    )


def summarize_wood_checks(mdl, project: ProjectDefinition):
    return build_wood_check_summary(mdl, project)


def _load_cases_to_check(mdl, project, warnings):
    requested = project.design_checks.wood.load_cases
    available = tuple(mdl.lcs)
    if not requested:
        warnings.append("No wood check load_cases were specified; all analysis load cases were checked.")
        return available

    out = []
    for lc in requested:
        if lc in available:
            out.append(lc)
        else:
            warnings.append("Wood check load case {0} is not in the solved model.".format(lc))
    if not out:
        warnings.append("No requested wood check load cases were available; all analysis load cases were checked.")
        return available
    return tuple(out)


def _check_element(e, member_class, load_cases, load_case_indices, project, warnings):
    best = None
    for lc in load_cases:
        result = _check_element_load_case(e, member_class, lc, load_case_indices, project, warnings)
        if best is None or result.combined_ratio > best.combined_ratio:
            best = result
    return best


def _check_element_load_case(e, member_class, load_case, load_case_indices, project, warnings):
    clc = load_case_indices.get(load_case, 0)
    allowable = _allowable_for_element(e, project, warnings)
    demand = _demand_for_load_case(e, load_case, clc)

    axial_ratio = _axial_ratio(demand.axial, allowable, member_class.kind)
    bending_ratio = _bending_ratio(e, demand, allowable)
    shear_ratio = _shear_ratio(e, demand, allowable)
    deflection_ratio = _deflection_ratio(e, demand.deflection, project)

    if member_class.kind == "brace":
        combined_ratio = axial_ratio
    else:
        combined_ratio = axial_ratio + bending_ratio
    if deflection_ratio is not None:
        combined_ratio = max(combined_ratio, deflection_ratio)
    combined_ratio = max(combined_ratio, shear_ratio)

    return WoodElementCheck(
        element_id=e.id,
        member_class=member_class.name,
        kind=member_class.kind,
        section=e.sec.name,
        material=e.sec.mat.name,
        governing_load_case=load_case,
        axial_ratio=axial_ratio,
        bending_ratio=bending_ratio,
        shear_ratio=shear_ratio,
        deflection_ratio=deflection_ratio,
        combined_ratio=combined_ratio,
        status="OK" if combined_ratio <= 1.0 else "NG",
        demand=demand,
    )


def _demand_for_load_case(e, load_case, clc):
    f = e.forces[:, clc]
    axial = max(abs(float(f[0])), abs(float(f[6])))
    shear_y = max(abs(float(f[1])), abs(float(f[7])))
    shear_z = max(abs(float(f[2])), abs(float(f[8])))
    moment_y = max(abs(float(f[4])), abs(float(f[10])), abs(float(f[12])))
    moment_z = max(abs(float(f[5])), abs(float(f[11])), abs(float(f[13])))
    return WoodCheckDemand(
        load_case=load_case,
        axial=axial,
        shear_y=shear_y,
        shear_z=shear_z,
        moment_y=moment_y,
        moment_z=moment_z,
        deflection=_element_deflection(e, clc),
    )


def _allowable_for_element(e, project, warnings):
    configured = project.design_checks.wood.allowable_stresses
    if _has_all_allowables(configured):
        return _scale_allowables(configured)

    fy = max(0.0, getattr(e.sec.mat, "fy", 0.0))
    if fy <= 0.0:
        warnings.append(
            "Element {0} has no configured wood allowables and material Fy is zero.".format(e.id)
        )
        return WoodAllowableStresses()

    warnings.append(
        "Wood allowables are incomplete; element {0} used material Fy with shear=0.1*Fy.".format(e.id)
    )
    return WoodAllowableStresses(
        bending=fy,
        shear=0.1 * fy,
        compression=fy,
        tension=fy,
    )


def _has_all_allowables(allowable):
    return (
        allowable.bending > 0.0
        and allowable.shear > 0.0
        and allowable.compression > 0.0
        and allowable.tension > 0.0
    )


def _scale_allowables(allowable):
    return WoodAllowableStresses(
        bending=allowable.bending * STRESS_UNIT,
        shear=allowable.shear * STRESS_UNIT,
        compression=allowable.compression * STRESS_UNIT,
        tension=allowable.tension * STRESS_UNIT,
    )


def _axial_ratio(axial, allowable, kind):
    limit = min(_positive_or_inf(allowable.compression), _positive_or_inf(allowable.tension))
    if kind == "brace":
        limit = _positive_or_inf(allowable.tension)
    return _ratio(axial, limit)


def _bending_ratio(e, demand, allowable):
    return _ratio(demand.moment_y / _positive_or_inf(e.sec.Wy), allowable.bending) + _ratio(
        demand.moment_z / _positive_or_inf(e.sec.Wz),
        allowable.bending,
    )


def _shear_ratio(e, demand, allowable):
    shear_y_ratio = _ratio(demand.shear_y / _positive_or_inf(e.sec.Asy), allowable.shear)
    shear_z_ratio = _ratio(demand.shear_z / _positive_or_inf(e.sec.Asz), allowable.shear)
    return max(shear_y_ratio, shear_z_ratio)


def _deflection_ratio(e, deflection, project):
    limit_ratio = project.design_checks.wood.deflection_limit_ratio
    if limit_ratio <= 0.0 or deflection is None:
        return None
    allowable = e.len / limit_ratio
    return _ratio(deflection, allowable)


def _element_deflection(e, clc):
    return element_chord_deflection(e, clc)


def _positive_or_inf(value):
    return value if value > DEFAULT_TOLERANCE else float("inf")


def _ratio(demand, capacity):
    if capacity <= DEFAULT_TOLERANCE or math.isinf(demand):
        return 0.0
    return max(0.0, demand) / capacity


def _build_tables(checks, wall_checks, project):
    checks_by_class = {}
    for check in checks:
        checks_by_class.setdefault(check.member_class, []).append(check)

    return WoodCheckTables(
        element_checks=tuple(_check_to_dict(c) for c in checks),
        member_classes=tuple(
            {
                "name": member_class.name,
                "kind": member_class.kind,
                "checked_count": len(checks_by_class.get(member_class.name, [])),
                "max_ratio": max(
                    [c.combined_ratio for c in checks_by_class.get(member_class.name, [])] + [0.0]
                ),
                "status": _overall_status([c.status for c in checks_by_class.get(member_class.name, [])]),
            }
            for member_class in project.member_classes
            if member_class.kind in CHECKED_MEMBER_KINDS
        ),
        wall_checks=tuple(_wall_check_to_dict(c) for c in wall_checks),
        standard_sections=tuple(_standard_section_to_dict(c) for c in checks if c.standard is not None),
        standard_results=tuple(
            _standard_result_to_dict(c, r) for c in checks if c.standard is not None for r in c.standard.results
        ),
    )


def _standard_section_to_dict(check):
    p = check.standard.properties
    return {
        "element_id": check.element_id,
        "member_class": check.member_class,
        "kind": check.kind,
        "section": check.section,
        "material": check.material,
        "area_e_100mm2": p.area * 1.0e4,
        "z_y_e_1000mm3": p.section_modulus_y * 1.0e6,
        "z_z_e_1000mm3": p.section_modulus_z * 1.0e6,
        "radius_min_mm": min(p.radius_y, p.radius_z) * 1.0e3,
        "lk_y_mm": p.buckling_length_y * 1.0e3,
        "lk_z_mm": p.buckling_length_z * 1.0e3,
        "slenderness": p.slenderness,
        "eta": p.eta,
        "ck": p.lateral_ck,
        "cs": p.lateral_cs,
        "cb": p.lateral_cb if p.lateral_cs is not None else None,
        "le_mm": p.lateral_length * 1.0e3 if p.lateral_length is not None else None,
        "messages": ", ".join(check.messages),
    }


def _standard_result_to_dict(check, r):
    return {
        "element_id": check.element_id,
        "duration": wood_standard.DURATION_LABELS[r.duration],
        "load_case": r.load_case,
        "location": wood_standard.location_label(r.location),
        "axial_kn": r.axial * 1.0e-3,
        "moment_y_knm": r.moment_y * 1.0e-3,
        "moment_z_knm": r.moment_z * 1.0e-3,
        "shear_kn": r.shear * 1.0e-3,
        "fc": r.allowable_compression / STRESS_UNIT,
        "ft": r.allowable_tension / STRESS_UNIT,
        "fb_y": r.allowable_bending_y / STRESS_UNIT,
        "fb_z": r.allowable_bending_z / STRESS_UNIT,
        "fs": r.allowable_shear / STRESS_UNIT,
        "sigma_n": r.sigma_n / STRESS_UNIT,
        "sigma_by": r.sigma_by / STRESS_UNIT,
        "sigma_bz": r.sigma_bz / STRESS_UNIT,
        "tau": r.tau / STRESS_UNIT,
        "sigma_cv": r.sigma_cv / STRESS_UNIT,
        "stress_ratio": r.combined_stress_ratio,
        "shear_ratio": r.shear_ratio,
        "bearing_ratio": r.bearing_ratio,
        "deflection_mm": r.deflection * 1.0e3 if r.deflection is not None else None,
        "deflection_ratio": r.deflection_ratio,
        "ratio": r.ratio,
    }


def _check_to_dict(check):
    return {
        "element_id": check.element_id,
        "member_class": check.member_class,
        "kind": check.kind,
        "section": check.section,
        "material": check.material,
        "governing_load_case": check.governing_load_case,
        "axial_ratio": check.axial_ratio,
        "bending_ratio": check.bending_ratio,
        "shear_ratio": check.shear_ratio,
        "deflection_ratio": check.deflection_ratio,
        "combined_ratio": check.combined_ratio,
        "status": check.status,
        "duration": wood_standard.DURATION_LABELS.get(check.duration, ""),
        "location": wood_standard.location_label(check.location),
        "demand": {
            "load_case": check.demand.load_case,
            "axial": check.demand.axial,
            "shear_y": check.demand.shear_y,
            "shear_z": check.demand.shear_z,
            "moment_y": check.demand.moment_y,
            "moment_z": check.demand.moment_z,
            "deflection": check.demand.deflection,
        },
    }


def _check_wood_rated_walls(mdl, load_cases, load_case_indices, warnings):
    out = []
    for w in getattr(mdl, "wwalls", []):
        best = None
        qa = float(getattr(w, "qa_kN", 0.0))
        if qa <= DEFAULT_TOLERANCE:
            warnings.append("WOOD_RATED_WALL {0} has non-positive Qa.".format(w.id))
            continue
        for lc in load_cases:
            q = _wall_shear_for_load_case(mdl, w, lc, load_case_indices, warnings)
            util = abs(q) / qa if qa > DEFAULT_TOLERANCE else 0.0
            wc = WoodWallCheck(
                wall_id=int(w.id),
                wall_name=str(w.name),
                direction=str(w.direction),
                wall_magnification=float(w.multiplier),
                wall_length=float(w.length),
                wall_height=float(w.height),
                allowable_shear_capacity_Qa=qa,
                analysis_shear_force_Q=float(q),
                utilization_ratio=float(util),
                status="OK" if util <= 1.0 else "NG",
                governing_load_case=int(lc),
            )
            if best is None or wc.utilization_ratio > best.utilization_ratio:
                best = wc
        if best is not None:
            out.append(best)
    return out


def _wall_shear_for_load_case(mdl, w, lc, load_case_indices, warnings):
    clc = load_case_indices.get(lc)
    if clc is None:
        return 0.0
    model = str(getattr(w, "model_active", getattr(w, "model_requested", "EQUIVALENT_BRACE"))).upper()
    if model == "SHEAR_PANEL":
        if not getattr(mdl, "wshears", None):
            warnings.append("WOOD_RATED_WALL {0} has SHEAR_PANEL model but no panel object.".format(w.id))
            return 0.0
        panels = [sp for sp in mdl.wshears if getattr(sp, "wall_id", None) == w.id]
        if not panels:
            warnings.append("WOOD_RATED_WALL {0} has no SHEAR_PANEL record.".format(w.id))
            return 0.0
        return sum([_shear_panel_force(sp, clc) for sp in panels])
    return _wall_shear_from_equivalent_braces(mdl, w, clc, warnings)


def _wall_shear_from_equivalent_braces(mdl, w, clc, warnings):
    eids = list(getattr(w, "generated_elem_ids", []) or [])
    if not eids:
        warnings.append("WOOD_RATED_WALL {0} has no generated equivalent braces.".format(w.id))
        return 0.0
    d = float(getattr(w, "diagonal_length", math.sqrt(w.length ** 2 + w.height ** 2)))
    L = float(getattr(w, "length", 0.0))
    if d <= DEFAULT_TOLERANCE or L <= DEFAULT_TOLERANCE:
        return 0.0
    q = 0.0
    for eid in eids:
        e = mdl.FindElemFromEid(eid)
        if e == -1 or getattr(e, "forces", None) is None:
            continue
        f = e.forces[:, clc]
        n = max(abs(float(f[0])), abs(float(f[6])))
        # Convert brace axial force back to wall shear component.
        q += n * L / d
    return q * 1e-3  # N -> kN


def _shear_panel_force(sp, clc):
    return sp.shear_force(clc) * 1e-3  # N -> kN


def _wall_check_to_dict(check):
    return {
        "wall_id": check.wall_id,
        "wall_name": check.wall_name,
        "direction": check.direction,
        "wall_magnification": check.wall_magnification,
        "wall_length": check.wall_length,
        "wall_height": check.wall_height,
        "allowable_shear_capacity_Qa": check.allowable_shear_capacity_Qa,
        "analysis_shear_force_Q": check.analysis_shear_force_Q,
        "utilization_ratio": check.utilization_ratio,
        "status": check.status,
        "governing_load_case": check.governing_load_case,
    }
