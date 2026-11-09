"""Allowable-stress design check for rectangular wood members.

Implements load-duration allowable stresses, compression buckling reduction,
lateral buckling of beams, bearing and beam deflection. Member forces use the
solver's section convention: tension is positive for N, and My/Mz keep the same
sign at both ends and at mid-span.

Units are the solver's (N, m, Pa) unless a name says otherwise.
"""

from dataclasses import dataclass
import math
from typing import Optional, Tuple

from stb_project import WoodMaterialStrength, WoodMemberCondition


STRESS_UNIT = 1.0e6  # N/mm2 to N/m2
SECTION_TYPE_RECTANGLE = 0
RECTANGULAR_SHEAR_FACTOR = 1.5
MAX_LATERAL_SLENDERNESS = 50.0
TOLERANCE = 1.0e-9

LONG_TERM = "LONG_TERM"
LONG_TERM_SNOW = "LONG_TERM_SNOW"
SHORT_TERM_SNOW = "SHORT_TERM_SNOW"
SHORT_TERM = "SHORT_TERM"

DURATION_FACTORS = {
    LONG_TERM: 1.1 / 3.0,
    LONG_TERM_SNOW: 1.43 / 3.0,
    SHORT_TERM_SNOW: 1.6 / 3.0,
    SHORT_TERM: 2.0 / 3.0,
}
DURATION_LABELS = {
    LONG_TERM: "長期",
    LONG_TERM_SNOW: "長期積雪",
    SHORT_TERM_SNOW: "短期積雪",
    SHORT_TERM: "短期",
}
DURATION_ORDER = (LONG_TERM, LONG_TERM_SNOW, SHORT_TERM_SNOW, SHORT_TERM)

MESSAGE_SLENDERNESS = "細長比が制限値を超えています"
MESSAGE_LATERAL_SLENDERNESS = "横座屈細長比が制限値を超えています"

_LOCATION_LABELS = {"i": "i端", "mid": "中央", "j": "j端"}


@dataclass(frozen=True)
class WoodSectionProperties:
    area: float
    section_modulus_y: float
    section_modulus_z: float
    shear_area: float
    inertia_y: float
    inertia_z: float
    radius_y: float
    radius_z: float
    buckling_length_y: float
    buckling_length_z: float
    slenderness_y: float
    slenderness_z: float
    eta_y: float
    eta_z: float
    strong_axis: str
    lateral_ck: Optional[float]
    lateral_cs: Optional[float]
    lateral_cb: float
    lateral_length: Optional[float]

    @property
    def slenderness(self):
        return max(self.slenderness_y, self.slenderness_z)

    @property
    def eta(self):
        return min(self.eta_y, self.eta_z)


@dataclass(frozen=True)
class WoodDurationResult:
    duration: str
    load_case: int
    location: str
    axial: float
    moment_y: float
    moment_z: float
    shear: float
    allowable_compression: float
    allowable_tension: float
    allowable_bending_y: float
    allowable_bending_z: float
    allowable_shear: float
    allowable_bearing: float
    sigma_n: float
    sigma_by: float
    sigma_bz: float
    tau: float
    sigma_cv: float
    axial_ratio: float
    bending_ratio: float
    combined_stress_ratio: float
    shear_ratio: float
    bearing_ratio: float
    deflection: Optional[float]
    deflection_ratio: Optional[float]
    ratio: float


@dataclass(frozen=True)
class WoodStandardElement:
    properties: WoodSectionProperties
    results: Tuple[WoodDurationResult, ...]
    governing: WoodDurationResult
    messages: Tuple[str, ...]


def buckling_reduction(slenderness):
    """Compression buckling reduction factor eta for a slenderness ratio."""

    if slenderness <= 30.0:
        return 1.0
    if slenderness <= 100.0:
        return 1.3 - 0.01 * slenderness
    return 3000.0 / (slenderness * slenderness)


def lateral_buckling(young, long_term_bending, depth, width, effective_length):
    """Return (Ck, Cs, Cb) for a beam bent about its strong axis.

    young and long_term_bending share a stress unit; the lengths share a length unit.
    """

    cs = math.sqrt(effective_length * depth / (width * width))
    ck = math.sqrt(0.6 * young / long_term_bending)
    if cs <= 10.0:
        cb = 1.0
    elif cs <= ck:
        cb = 1.0 - (cs / ck) ** 4 / 3.0
    else:
        cb = 0.4 * young / (cs * cs * long_term_bending)
    return ck, cs, cb


def bending_depth_factor(material: WoodMaterialStrength, depth_mm):
    """Size factor for the bending strength; 1.0 when no table is configured."""

    factors = material.bending_depth_factors
    if not factors:
        return 1.0
    for row in factors:
        if depth_mm <= row.max_depth_mm + TOLERANCE:
            return row.factor
    return factors[-1].factor


def midspan_bending_deflection(moment_i, moment_j, moment_mid, length, flexural_rigidity):
    """Deflection at mid-span relative to the chord, for a parabolic moment diagram."""

    return length * length * (moment_i + moment_j + 10.0 * moment_mid) / (96.0 * flexural_rigidity)


def element_chord_deflection(e, clc):
    """Transverse displacement of one member end relative to the other."""

    ndisps = getattr(e, "ndisps", None)
    if ndisps is None:
        return None
    du = [float(ndisps[i + 6, clc]) - float(ndisps[i, clc]) for i in range(3)]
    length = max(getattr(e, "len", 0.0), TOLERANCE)
    axis = ((e.n1.x - e.n0.x) / length, (e.n1.y - e.n0.y) / length, (e.n1.z - e.n0.z) / length)
    axial = sum(du[i] * axis[i] for i in range(3))
    return math.sqrt(max(0.0, sum(v * v for v in du) - axial * axial))


def is_supported_section(section):
    return section.type == SECTION_TYPE_RECTANGLE


def section_properties(e, material: WoodMaterialStrength, condition: WoodMemberCondition, kind):
    section = e.sec
    width, depth = float(section.dims[0]), float(section.dims[1])
    area = section.A * (1.0 - condition.area_reduction_percent * 0.01)
    modulus_factor = 1.0 - condition.section_modulus_reduction_percent * 0.01
    inertia_factor = 1.0 - condition.inertia_reduction_percent * 0.01

    radius_y = math.sqrt(section.Iy / section.A)
    radius_z = math.sqrt(section.Iz / section.A)
    length_y = condition.buckling_factor_y * e.len
    length_z = condition.buckling_factor_z * e.len
    slenderness_y = length_y / radius_y
    slenderness_z = length_z / radius_z
    strong_axis = "y" if depth >= width else "z"

    ck = cs = effective_length = None
    cb = 1.0
    if kind == "beam":
        beam_depth, beam_width = (depth, width) if strong_axis == "y" else (width, depth)
        weak_axis_length = length_z if strong_axis == "y" else length_y
        effective_length = condition.lateral_buckling_coefficient * weak_axis_length
        long_term_bending = (
            material.bending
            * bending_depth_factor(material, beam_depth * 1000.0)
            * DURATION_FACTORS[LONG_TERM]
            * STRESS_UNIT
        )
        ck, cs, cb = lateral_buckling(section.mat.E, long_term_bending, beam_depth, beam_width, effective_length)

    return WoodSectionProperties(
        area=area,
        section_modulus_y=section.Wy * modulus_factor,
        section_modulus_z=section.Wz * modulus_factor,
        shear_area=section.A * (1.0 - condition.shear_area_reduction_percent * 0.01),
        inertia_y=section.Iy * inertia_factor,
        inertia_z=section.Iz * inertia_factor,
        radius_y=radius_y,
        radius_z=radius_z,
        buckling_length_y=length_y,
        buckling_length_z=length_z,
        slenderness_y=slenderness_y,
        slenderness_z=slenderness_z,
        eta_y=buckling_reduction(slenderness_y),
        eta_z=buckling_reduction(slenderness_z),
        strong_axis=strong_axis,
        lateral_ck=ck,
        lateral_cs=cs,
        lateral_cb=cb,
        lateral_length=effective_length,
    )


def check_element(
    e,
    material: WoodMaterialStrength,
    condition: WoodMemberCondition,
    kind,
    load_cases,
    load_case_indices,
    durations,
    is_cantilever=False,
    fallback_deflection_ratio=0.0,
):
    """Check one member over the load cases; the worst result per duration is kept."""

    props = section_properties(e, material, condition, kind)
    worst = {}
    for load_case in load_cases:
        result = _check_load_case(
            e,
            props,
            material,
            condition,
            kind,
            load_case,
            load_case_indices[load_case],
            durations[load_case],
            is_cantilever,
            fallback_deflection_ratio,
        )
        current = worst.get(result.duration)
        if current is None or result.ratio > current.ratio:
            worst[result.duration] = result

    results = tuple(worst[d] for d in DURATION_ORDER if d in worst)
    governing = max(results, key=lambda r: r.ratio)
    return WoodStandardElement(
        properties=props,
        results=results,
        governing=governing,
        messages=_section_messages(props, condition, kind),
    )


def location_label(location):
    return _LOCATION_LABELS.get(location, location)


def _section_messages(props, condition, kind):
    messages = []
    if kind == "column" and condition.slenderness_limit > 0.0 and props.slenderness > condition.slenderness_limit:
        messages.append(MESSAGE_SLENDERNESS)
    if kind == "beam" and props.lateral_cs is not None and props.lateral_cs > MAX_LATERAL_SLENDERNESS:
        messages.append(MESSAGE_LATERAL_SLENDERNESS)
    return tuple(messages)


def _check_load_case(
    e, props, material, condition, kind, load_case, clc, duration, is_cantilever, fallback_deflection_ratio
):
    forces = e.forces[:, clc]
    factor = DURATION_FACTORS[duration] * STRESS_UNIT
    section = e.sec
    width, depth = float(section.dims[0]), float(section.dims[1])

    fc = material.compression * factor
    ft = material.tension * factor
    fs = material.shear * factor
    fcv = material.bearing * factor
    fb_y = material.bending * bending_depth_factor(material, depth * 1000.0) * factor
    fb_z = material.bending * bending_depth_factor(material, width * 1000.0) * factor
    if kind == "beam":
        if props.strong_axis == "y":
            fb_y *= props.lateral_cb
        else:
            fb_z *= props.lateral_cb

    locations = (
        ("i", float(forces[0]), float(forces[4]), float(forces[5])),
        ("mid", 0.5 * (float(forces[0]) + float(forces[6])), float(forces[12]), float(forces[13])),
        ("j", float(forces[6]), float(forces[10]), float(forces[11])),
    )
    best = None
    for location, axial, moment_y, moment_z in locations:
        axial_ratio, bending_ratio, sigma_by, sigma_bz = _stress_ratios(
            axial, moment_y, moment_z, props, condition, kind, fc, ft, fb_y, fb_z
        )
        total = axial_ratio + bending_ratio
        if best is None or total > best[0]:
            best = (total, location, axial, moment_y, moment_z, axial_ratio, bending_ratio, sigma_by, sigma_bz)
    total, location, axial, moment_y, moment_z, axial_ratio, bending_ratio, sigma_by, sigma_bz = best

    shear = max(abs(float(forces[i])) for i in (1, 2, 7, 8))
    tau = RECTANGULAR_SHEAR_FACTOR * shear / props.shear_area
    shear_ratio = tau / fs

    sigma_cv, bearing_ratio = _bearing(forces, section, condition, kind, fcv)

    deflection, deflection_ratio = _deflection(
        e, props, condition, kind, duration, clc, forces, is_cantilever, fallback_deflection_ratio
    )
    ratio = max(total, shear_ratio, bearing_ratio, deflection_ratio or 0.0)

    return WoodDurationResult(
        duration=duration,
        load_case=load_case,
        location=location,
        axial=axial,
        moment_y=moment_y,
        moment_z=moment_z,
        shear=shear,
        allowable_compression=fc,
        allowable_tension=ft,
        allowable_bending_y=fb_y,
        allowable_bending_z=fb_z,
        allowable_shear=fs,
        allowable_bearing=fcv,
        sigma_n=abs(axial) / props.area,
        sigma_by=sigma_by,
        sigma_bz=sigma_bz,
        tau=tau,
        sigma_cv=sigma_cv,
        axial_ratio=axial_ratio,
        bending_ratio=bending_ratio,
        combined_stress_ratio=total,
        shear_ratio=shear_ratio,
        bearing_ratio=bearing_ratio,
        deflection=deflection,
        deflection_ratio=deflection_ratio,
        ratio=ratio,
    )


def _axial_ratio(axial, area, eta, fc, ft):
    sigma = abs(axial) / area
    return sigma / ft if axial > 0.0 else sigma / (eta * fc)


def _stress_ratios(axial, moment_y, moment_z, props, condition, kind, fc, ft, fb_y, fb_z):
    sigma_by = abs(moment_y) / props.section_modulus_y
    sigma_bz = abs(moment_z) / props.section_modulus_z
    if kind == "brace":
        return _axial_ratio(axial, props.area, props.eta, fc, ft), 0.0, 0.0, 0.0

    if condition.biaxial_bending:
        return (
            _axial_ratio(axial, props.area, props.eta, fc, ft),
            sigma_by / fb_y + sigma_bz / fb_z,
            sigma_by,
            sigma_bz,
        )

    # Without biaxial interaction each axis is checked alone. Beams buckle about
    # their weakest axis whichever way they bend; columns per bending direction.
    eta_y = props.eta if kind == "beam" else props.eta_y
    eta_z = props.eta if kind == "beam" else props.eta_z
    axial_y = _axial_ratio(axial, props.area, eta_y, fc, ft)
    axial_z = _axial_ratio(axial, props.area, eta_z, fc, ft)
    if axial_y + sigma_by / fb_y >= axial_z + sigma_bz / fb_z:
        return axial_y, sigma_by / fb_y, sigma_by, 0.0
    return axial_z, sigma_bz / fb_z, 0.0, sigma_bz


def _bearing(forces, section, condition, kind, fcv):
    if kind != "column" or not condition.check_bearing or fcv <= TOLERANCE:
        return 0.0, 0.0
    compression = max(0.0, -float(forces[0]), -float(forces[6]))
    area = section.A - condition.bearing_area_loss_mm2 * 1.0e-6
    if area <= TOLERANCE:
        return float("inf"), float("inf")
    sigma = compression / area
    return sigma, sigma / fcv


def _deflection_limits(condition, duration, fallback_ratio):
    key = duration.lower()
    ratio = getattr(condition, "deflection_ratio_" + key, 0.0)
    limit_mm = getattr(condition, "deflection_mm_" + key, 0.0)
    has_any_limit = any(
        getattr(condition, "deflection_ratio_" + d.lower()) > 0.0 or getattr(condition, "deflection_mm_" + d.lower()) > 0.0
        for d in (LONG_TERM, LONG_TERM_SNOW, SHORT_TERM_SNOW)
    )
    if not has_any_limit and duration == LONG_TERM:
        ratio = fallback_ratio
    return ratio, limit_mm


def _deflection(e, props, condition, kind, duration, clc, forces, is_cantilever, fallback_ratio):
    if kind != "beam" or duration == SHORT_TERM:
        return None, None
    ratio_limit, limit_mm = _deflection_limits(condition, duration, fallback_ratio)
    if ratio_limit <= 0.0 and limit_mm <= 0.0:
        return None, None

    if is_cantilever:
        deflection = element_chord_deflection(e, clc)
        if deflection is None:
            return None, None
    else:
        young = e.sec.mat.E
        deflection_y = midspan_bending_deflection(
            float(forces[4]), float(forces[10]), float(forces[12]), e.len, young * props.inertia_y
        )
        deflection_z = midspan_bending_deflection(
            float(forces[5]), float(forces[11]), float(forces[13]), e.len, young * props.inertia_z
        )
        deflection = math.hypot(deflection_y, deflection_z)

    # A member passes when it satisfies either limit, so the smaller ratio governs.
    ratios = []
    if ratio_limit > 0.0:
        ratios.append(deflection / (e.len / ratio_limit))
    if limit_mm > 0.0:
        ratios.append(deflection / (limit_mm * 1.0e-3))
    return deflection, min(ratios)
