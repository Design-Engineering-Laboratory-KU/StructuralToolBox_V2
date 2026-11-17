"""Check of joint hardware at wood member ends.

Each end gets the allowable forces of its assigned hardware. Snow cases scale
them: long-term snow is long-term x 1.3, short-term snow is short-term x 0.8.
Forces use the solver's section convention, tension positive.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from stb_checks.wood_standard import LONG_TERM, LONG_TERM_SNOW, SHORT_TERM, SHORT_TERM_SNOW

INTERACTION_LINEAR = "linear"
LONG_GROUP = "長期"
SHORT_GROUP = "短期"
END_I = "i"
END_J = "j"
END_TOP = "top"
END_BOTTOM = "bottom"
END_LABELS = {END_I: "i端", END_J: "j端", END_TOP: "柱頭", END_BOTTOM: "柱脚"}

KILO = 1.0e-3
# Demands below this (kN, kN*m) are numerical noise at a released end.
NOISE = 0.05
# Shown when a force acts on hardware whose allowable value is zero.
NO_CAPACITY_RATIO = 99.999

MESSAGE_RATIO = "検定値が1.0を超えています"
MESSAGE_MOMENT_ON_PIN = "許容曲げが0の金物に曲げモーメントが生じています"


@dataclass(frozen=True)
class JointComponent:
    label: str
    value: float
    capacity: float
    ratio: float
    load_case: int


@dataclass(frozen=True)
class JointGroup:
    term: str
    components: Tuple[JointComponent, ...]
    combined_ratio: float
    combined_load_case: int


@dataclass(frozen=True)
class WoodJointCheck:
    element_id: int
    member_class: str
    kind: str
    end: str
    joint: str
    groups: Tuple[JointGroup, ...]
    max_ratio: float
    status: str
    messages: Tuple[str, ...]


def allowable(duration, long_value, short_value):
    if duration == LONG_TERM:
        return long_value
    if duration == LONG_TERM_SNOW:
        return long_value * 1.3
    if duration == SHORT_TERM_SNOW:
        return short_value * 0.8
    return short_value


def ratio(demand, capacity):
    """Demand over capacity; demand above noise on zero capacity is reported as failing."""

    magnitude = abs(demand)
    if capacity > 0.0:
        return magnitude / capacity
    return NO_CAPACITY_RATIO if magnitude > NOISE else 0.0


def _end_forces(forces, end_index):
    """(N, Qy, Qz, My, Mz) in kN and kN*m at an end (0 for i, 6 for j)."""

    return (
        float(forces[end_index]) * KILO,
        float(forces[end_index + 1]) * KILO,
        float(forces[end_index + 2]) * KILO,
        float(forces[end_index + 4]) * KILO,
        float(forces[end_index + 5]) * KILO,
    )


def _weak(value, fallback):
    return fallback if value is None else value


def _bending_and_shear(strong_is_y, joint, duration, q_y, q_z, m_y, m_z):
    shear_strong = allowable(duration, joint.shear_long, joint.shear_short)
    shear_weak = allowable(
        duration,
        _weak(joint.shear_weak_long, joint.shear_long),
        _weak(joint.shear_weak_short, joint.shear_short),
    )
    moment_strong = allowable(duration, joint.moment_long, joint.moment_short)
    moment_weak = allowable(
        duration,
        _weak(joint.moment_weak_long, joint.moment_long),
        _weak(joint.moment_weak_short, joint.moment_short),
    )
    if strong_is_y:
        shear_pairs = ((q_z, shear_strong), (q_y, shear_weak))
        moment_pairs = ((m_y, moment_strong), (m_z, moment_weak))
    else:
        shear_pairs = ((q_y, shear_strong), (q_z, shear_weak))
        moment_pairs = ((m_z, moment_strong), (m_y, moment_weak))
    return max(shear_pairs, key=lambda p: ratio(*p)), max(moment_pairs, key=lambda p: _moment_ratio(*p))


def _moment_ratio(demand, capacity):
    # Zero bending capacity means a pinned connection, so moment is not checked here.
    return abs(demand) / capacity if capacity > 0.0 else 0.0


def _better(current, label, value, capacity, value_ratio, load_case):
    if current is None or value_ratio > current.ratio:
        return JointComponent(label, value, capacity, value_ratio, load_case)
    return current


def check_joint_end(
    forces_by_case, joint, strong_is_y, load_cases, durations, end_index, interaction=INTERACTION_LINEAR
):
    """Return (groups, moment_on_pin); forces_by_case maps a load case to its force vector."""

    groups = []
    moment_on_pin = False
    for term, members in ((LONG_GROUP, (LONG_TERM, LONG_TERM_SNOW)), (SHORT_GROUP, (SHORT_TERM_SNOW, SHORT_TERM))):
        cases = [lc for lc in load_cases if durations[lc] in members]
        if not cases:
            continue
        axial = compression = tension = moment = shear = None
        combined = -1.0
        combined_case = cases[0]
        for lc in cases:
            duration = durations[lc]
            n, q_y, q_z, m_y, m_z = _end_forces(forces_by_case[lc], end_index)
            is_tension = n > 0.0
            na = allowable(
                duration,
                joint.tension_long if is_tension else joint.compression_long,
                joint.tension_short if is_tension else joint.compression_short,
            )
            axial_ratio = ratio(n, na)
            if term == LONG_GROUP:
                axial = _better(axial, "N", n, na, axial_ratio, lc)
            elif is_tension:
                tension = _better(tension, "tN", n, na, axial_ratio, lc)
            else:
                compression = _better(compression, "cN", n, na, axial_ratio, lc)

            (q, qa), (m, ma) = _bending_and_shear(strong_is_y, joint, duration, q_y, q_z, m_y, m_z)
            shear_ratio = ratio(q, qa)
            moment_ratio = _moment_ratio(m, ma)
            shear = _better(shear, "Q", q, qa, shear_ratio, lc)
            moment = _better(moment, "M", m, ma, moment_ratio, lc)
            if max(ma, 0.0) == 0.0 and max(abs(m_y), abs(m_z)) > NOISE:
                moment_on_pin = True

            total = axial_ratio + moment_ratio + shear_ratio if interaction == INTERACTION_LINEAR else 0.0
            if total > combined:
                combined, combined_case = total, lc

        if term == SHORT_GROUP:
            compression = compression or JointComponent("cN", 0.0, joint.compression_short, 0.0, cases[0])
            tension = tension or JointComponent("tN", 0.0, joint.tension_short, 0.0, cases[0])
            components = (compression, tension, moment, shear)
        else:
            components = (axial, moment, shear)
        groups.append(JointGroup(term, components, max(combined, 0.0), combined_case))
    return tuple(groups), moment_on_pin


def build_joint_checks(mdl, project, load_cases, load_case_indices, durations, member_classes, warnings):
    settings = project.design_checks.wood
    if not settings.joint_assignments:
        return ()

    types = {j.name: j for j in settings.joint_types}
    by_element = {}
    for assignment in settings.joint_assignments:
        targets = list(assignment.element_ids)
        for member_class in member_classes:
            if member_class.name == assignment.member_class:
                targets.extend(member_class.element_ids)
        for element_id in targets:
            by_element.setdefault(element_id, {}).update(
                {k: v for k, v in ((END_I, assignment.i), (END_J, assignment.j), (END_TOP, assignment.top), (END_BOTTOM, assignment.bottom)) if v}
            )

    class_of = {e: (mc.name, mc.kind) for mc in member_classes for e in mc.element_ids}
    out = []
    for element_id in sorted(by_element):
        e = mdl.FindElemFromEid(element_id)
        if e == -1 or getattr(e, "forces", None) is None:
            warnings.append("Joint check skipped: element {0} has no solved forces.".format(element_id))
            continue
        class_name, kind = class_of.get(element_id, ("", "beam"))
        forces_by_case = {lc: e.forces[:, load_case_indices[lc]] for lc in load_cases}
        strong_is_y = float(e.sec.dims[1]) >= float(e.sec.dims[0]) if e.sec.type == 0 else True
        lower_is_i = e.n0.z <= e.n1.z
        for end, joint_name in by_element[element_id].items():
            end_index = _end_index(end, lower_is_i)
            joint = types[joint_name]
            groups, moment_on_pin = check_joint_end(
                forces_by_case, joint, strong_is_y, load_cases, durations, end_index, settings.joint_interaction
            )
            max_ratio = max(
                [c.ratio for g in groups for c in g.components] + [g.combined_ratio for g in groups] + [0.0]
            )
            messages = []
            if max_ratio > 1.0:
                messages.append(MESSAGE_RATIO)
            if moment_on_pin:
                messages.append(MESSAGE_MOMENT_ON_PIN)
            out.append(WoodJointCheck(
                element_id=element_id,
                member_class=class_name,
                kind=kind,
                end=end,
                joint=joint_name,
                groups=groups,
                max_ratio=max_ratio,
                status="OK" if max_ratio <= 1.0 else "NG",
                messages=tuple(messages),
            ))
    return tuple(out)


def _end_index(end, lower_is_i) -> int:
    if end == END_I:
        return 0
    if end == END_J:
        return 6
    if end == END_BOTTOM:
        return 0 if lower_is_i else 6
    return 6 if lower_is_i else 0
