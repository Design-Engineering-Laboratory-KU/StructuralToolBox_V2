"""Everything the chapters read, computed once per calculation book."""

from dataclasses import dataclass
from datetime import datetime
import base64
import hashlib
import os
from typing import Optional, Sequence, Tuple

from stb_checks import build_wood_check_summary
from stb_checks.foundation import build_foundation_check
from stb_checks.foundation_beams import build_foundation_beam_check
from stb_practice import build_practice_summary, build_structural_indices

LEVEL_TOLERANCE = 1.0e-3
AXIS_TOLERANCE = 1.0e-6

KIND_BEAM = "beam"
KIND_COLUMN = "column"
KIND_OTHER = "other"


def _unique_sorted(values, tolerance):
    out = []
    for value in sorted(values):
        if not out or value - out[-1] > tolerance:
            out.append(value)
    return out


def _is_vertical(e):
    return abs(e.n0.x - e.n1.x) < LEVEL_TOLERANCE and abs(e.n0.y - e.n1.y) < LEVEL_TOLERANCE


def _named(coords, prefix):
    return [(c, "{0}{1}".format(prefix, i + 1)) for i, c in enumerate(coords)]


def _name_at(named, value, fallback_prefix):
    for coordinate, name in named:
        if abs(coordinate - value) <= LEVEL_TOLERANCE:
            return name
    return "{0}={1:.3f}".format(fallback_prefix, value)


class Naming:
    """Grid-line, level and span labels for nodes and members."""

    def __init__(self, mdl, project):
        columns = [e for e in mdl.elms if _is_vertical(e) and not getattr(e, "auto_generated", False)]
        grid_nodes = [n for e in columns for n in (e.n0, e.n1)] or list(mdl.nds)

        self.x_grids = self._grids(project, "x", [n.x for n in grid_nodes], "X")
        self.y_grids = self._grids(project, "y", [n.y for n in grid_nodes], "Y")
        self.levels = self._levels(project, mdl)

    @staticmethod
    def _grids(project, direction, inferred, prefix):
        defined = sorted((g.coordinate, g.name) for g in project.grids if g.direction == direction)
        return defined or _named(_unique_sorted(inferred, LEVEL_TOLERANCE), prefix)

    @staticmethod
    def _levels(project, mdl):
        elevations = {s.elevation for s in project.stories}
        elevations.update(s.elevation + s.height for s in project.stories)
        if elevations:
            elevations.update(c.nd.z for c in mdl.cons)
        coords = _unique_sorted(elevations or [n.z for n in mdl.nds], LEVEL_TOLERANCE)
        used = [c for c in coords if any(abs(n.z - c) <= LEVEL_TOLERANCE for n in mdl.nds)]
        return _named(used, "Z")

    def x(self, value):
        return _name_at(self.x_grids, value, "x")

    def y(self, value):
        return _name_at(self.y_grids, value, "y")

    def level(self, value):
        return _name_at(self.levels, value, "z")

    def kind(self, e):
        if _is_vertical(e):
            return KIND_COLUMN
        if abs(e.n0.z - e.n1.z) < LEVEL_TOLERANCE:
            return KIND_BEAM
        return KIND_OTHER

    def node_location(self, n):
        return self.level(n.z), self.y(n.y), self.x(n.x)

    def member_location(self, e):
        """(level, frame line, span) in the style Z2, Y1, X1-X2."""

        if self.kind(e) == KIND_COLUMN:
            low, high = sorted((e.n0.z, e.n1.z))
            return self.level(low) + "-" + self.level(high), self.y(e.n0.y), self.x(e.n0.x)
        if self.kind(e) == KIND_BEAM:
            if abs(e.n0.y - e.n1.y) < LEVEL_TOLERANCE:
                low, high = sorted((e.n0.x, e.n1.x))
                return self.level(e.n0.z), self.y(e.n0.y), self.x(low) + "-" + self.x(high)
            if abs(e.n0.x - e.n1.x) < LEVEL_TOLERANCE:
                low, high = sorted((e.n0.y, e.n1.y))
                return self.level(e.n0.z), self.x(e.n0.x), self.y(low) + "-" + self.y(high)
        return (
            self.level(e.n0.z) + "-" + self.level(e.n1.z),
            "-",
            "N{0}-N{1}".format(e.n0.id, e.n1.id),
        )


@dataclass(frozen=True)
class ReportContext:
    mdl: object
    project: object
    naming: Naming
    practice: object
    indices: object
    wood: Optional[object]
    program_version: str
    generated_at: datetime
    input_id: str
    dat_lines: Tuple[str, ...]
    warnings: Tuple[str, ...]
    foundation: Optional[object] = None
    foundation_beams: Optional[object] = None

    def lc_label(self, lc):
        for c in self.mdl.lcmbs:
            if c.lc == lc:
                return c.name
        for case in self.mdl.lcases:
            if case.lc == lc:
                return case.lname
        return "LC{0}".format(lc)

    def lc_index(self, lc):
        return list(self.mdl.lcs).index(lc)

    def real_members(self):
        return [e for e in self.mdl.elms if not getattr(e, "auto_generated", False)]

    def members_sorted(self, kind):
        members = [e for e in self.real_members() if self.naming.kind(e) == kind]
        return sorted(members, key=lambda e: (self.naming.member_location(e), e.id))


def _read_dat(mdl):
    path = getattr(mdl, "filepath", None)
    if not path or not os.path.isfile(path):
        return ()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return tuple(fh.read().splitlines())


def _input_id(lines: Sequence[str]) -> str:
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest[:7]).decode("ascii").rstrip("=")


def build_context(mdl, project, generated_at=None, program_version="") -> ReportContext:
    practice = build_practice_summary(mdl, project)
    indices = build_structural_indices(mdl, project)
    wood = build_wood_check_summary(mdl, project) if project.design_checks.wood.enabled else None

    warnings = list(getattr(mdl, "input_warnings", []) or [])
    warnings.extend(practice.warnings)
    warnings.extend(indices.warnings)
    if wood is not None:
        warnings.extend(wood.warnings)

    naming = Naming(mdl, project)
    foundation = build_foundation_check(mdl, project, naming)
    if foundation is not None:
        warnings.extend(foundation.warnings)
    foundation_beams = None
    if foundation is not None:
        foundation_beams = build_foundation_beam_check(mdl, project, naming, foundation)
    if foundation_beams is not None:
        warnings.extend(foundation_beams.warnings)

    lines = _read_dat(mdl)
    return ReportContext(
        mdl=mdl,
        project=project,
        naming=naming,
        foundation=foundation,
        foundation_beams=foundation_beams,
        practice=practice,
        indices=indices,
        wood=wood,
        program_version=program_version,
        generated_at=generated_at or datetime.now(),
        input_id=_input_id(lines) if lines else "-",
        dat_lines=lines,
        warnings=tuple(dict.fromkeys(warnings)),
    )
