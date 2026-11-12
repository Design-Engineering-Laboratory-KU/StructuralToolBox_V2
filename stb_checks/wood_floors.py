"""In-plane shear check of timber floor and roof diaphragms.

Allowable shear per unit length is 1.96 kN/m times the floor multiplier, so a
panel of length L has Qa = 1.96 * multiplier * L. The demand is the membrane
shear flow, which the solver reports in each triangle's own axes and which is
rotated here to the global X and Y directions before use.
"""

from dataclasses import dataclass
import math
from typing import Dict, Tuple

import numpy as np

UNIT_SHEAR_STRENGTH_KN_PER_M = 1.96
AXIS_TOLERANCE = 1.0e-6


@dataclass(frozen=True)
class WoodFloorCheck:
    element_id: int
    diaphragm_id: int
    diaphragm: str
    multiplier: float
    centroid: Tuple[float, float, float]
    shear_flow: float  # kN/m
    allowable: float  # kN/m
    ratio: float
    load_case: int
    status: str


def _plane_x_axis(ez):
    """Global X projected on the element plane, or Y for a plane facing X."""

    for axis in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)):
        vector = np.array(axis) - float(np.dot(axis, ez)) * ez
        length = float(np.linalg.norm(vector))
        if length > AXIS_TOLERANCE:
            return vector / length
    raise ValueError("Diaphragm element has a degenerate normal.")


def global_shear_stress(sx, sy, sxy, ex, ey, ez):
    """Shear stress on global X/Y faces from stresses in the element's own axes."""

    target = _plane_x_axis(ez)
    c = float(np.dot(ex, target))
    s = float(np.dot(ey, target))
    return -(sx - sy) * s * c + sxy * (c * c - s * s)


def _shear_flow(m, clc):
    sx, sy, sxy = (float(v) for v in m.stresses[:, clc])
    return abs(global_shear_stress(sx, sy, sxy, m.ex, m.ey, m.ez)) * float(m.diap.t) * 1.0e-3


def _multipliers(settings, mdl) -> Dict[int, float]:
    values = {d.id: float(d.timber_multiplier) for d in mdl.diaps if d.timber_multiplier}
    values.update({f.diaphragm: f.multiplier for f in settings.floor_multipliers})
    return values


def build_floor_checks(mdl, project, load_cases, load_case_indices, warnings) -> Tuple[WoodFloorCheck, ...]:
    settings = project.design_checks.wood
    multipliers = _multipliers(settings, mdl)
    skipped = set()
    out = []
    for m in getattr(mdl, "dmems", []):
        diap = m.diap
        if not diap.uses_membrane_stiffness or m.stresses is None:
            continue
        multiplier = multipliers.get(diap.id)
        if not multiplier:
            if diap.id not in skipped:
                skipped.add(diap.id)
                warnings.append(
                    "Diaphragm {0} ({1}) has no floor multiplier and was not checked.".format(diap.id, diap.name)
                )
            continue
        allowable = UNIT_SHEAR_STRENGTH_KN_PER_M * multiplier
        flow, load_case = max(
            ((_shear_flow(m, load_case_indices[lc]), lc) for lc in load_cases), key=lambda item: item[0]
        )
        ratio = flow / allowable
        out.append(WoodFloorCheck(
            element_id=m.id,
            diaphragm_id=diap.id,
            diaphragm=diap.name,
            multiplier=multiplier,
            centroid=tuple((getattr(m.n0, a) + getattr(m.n1, a) + getattr(m.n2, a)) / 3.0 for a in "xyz"),
            shear_flow=flow,
            allowable=allowable,
            ratio=ratio,
            load_case=load_case,
            status="OK" if ratio <= 1.0 else "NG",
        ))
    return tuple(out)
