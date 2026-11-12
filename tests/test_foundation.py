"""Mat foundation: bearing pressure, overturning and settings."""

import copy
import os
import sys
import tempfile
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_checks import foundation as fd
from stb_checks.foundation import build_foundation_check
from stb_engine import run_from_file
from stb_project import ProjectSchemaError, validate_project_dict
from stb_reports.calc_book import build_document
from stb_reports.calc_book.context import Naming, build_context
from stb_reports.calc_book.document import Heading, Table, Text

HEADER = """MATE, 1, Wood, 12000, 800, 5.0, 3e-06, 0
SECT, 1, S, 1, 0, 105.0, 105.0
"""


def _columns(xs, ys, height=3.0):
    lines = []
    node = element = 0
    tops = {}
    for y in ys:
        for x in xs:
            lines.append("NODE, {0}, {1}, {2}, 0.0".format(node + 1, x, y))
            lines.append("NODE, {0}, {1}, {2}, {3}".format(node + 2, x, y, height))
            element += 1
            lines.append("ELEM, {0}, {1}, {2}, 1, 0.0".format(element, node + 1, node + 2))
            lines.append("CONS, {0}, 1, 1, 1, 1, 1, 1".format(node + 1))
            tops[(x, y)] = node + 2
            node += 2
    return "\n".join(lines) + "\n", tops


def _point(node, case, fx=0.0, fz=0.0):
    return "PLOD, {0}, {1}, {2}, 0.0, {3}, 0.0, 0.0, 0.0\n".format(node, case, fx, fz)


def _solve(body):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "m.dat")
        with open(path, "w", encoding="utf-8") as f:
            f.write(HEADER + body)
        mdl, _txt = run_from_file(path)
    return mdl


SLAB = {
    "name": "FS1", "thickness": 200, "d_short": 140, "d_long": 123, "rebar": "SD295",
    "short": {"end": "D13@300", "mid": "D10@300"}, "long": {"end": "D13@300", "mid": "D10@300"},
}
BEAM = {
    "name": "FG1", "b": 150, "d": 700, "top": "1-D19", "bottom": "1-D19", "dt": 72,
    "stirrup": "1-D10@200", "main_rebar": "SD345", "stirrup_rebar": "SD295",
}
FOUNDATION = {
    "type": "mat",
    "soil": {"name": "砂質土", "bearing_long": 30.0, "bearing_short": 60.0, "young": 5000.0},
    "concrete": {"name": "FC21", "fc": 21.0},
    "extra_load": 1.0,
    "slab_types": [SLAB],
    "panels": [{"slab": "FS1", "x": ["X1", "X2"], "y": ["Y1", "Y2"]}],
}


def _project(foundation, durations):
    return validate_project_dict({
        "schema": 1,
        "model": {"dat": "m.dat"},
        "building": {"name": "b", "location": "", "use": "", "structure": "wood", "calculation_route": "",
                     "designer": {"name": "", "qualification": "", "license_number": "", "contact": ""}},
        "grids": [],
        "stories": [],
        "member_classes": [],
        "design_checks": {"wood": {
            "enabled": False,
            "load_case_durations": [{"load_case": k, "duration": v} for k, v in durations.items()],
        }},
        "report": {"title": "", "mode": "practice", "language": "ja", "format": "markdown",
                   "include_manual_items": True, "include_warnings": True},
        "foundation": foundation,
    })


class FourColumns(unittest.TestCase):
    """Columns at the corners of a 4 m x 3 m mat, each carrying 10 kN."""

    XS = (0.0, 4.0)
    YS = (0.0, 3.0)
    DURATIONS = {0: "LONG_TERM", 1: "SHORT_TERM", 2: "SHORT_TERM"}

    def _model(self, push=2.0):
        body, tops = _columns(self.XS, self.YS)
        for node in tops.values():
            body += _point(node, 0, fz=-10.0)
            body += _point(node, 1, fx=push, fz=-10.0)
            body += _point(node, 2, fx=push)
        return _solve(body)

    def _check(self, foundation=None, push=2.0):
        mdl = self._model(push)
        project = _project(foundation or FOUNDATION, self.DURATIONS)
        return build_foundation_check(mdl, project, Naming(mdl, project))


class TestBearing(FourColumns):

    def test_long_term_pressure_is_load_over_area_plus_own_weight(self):
        summary = self._check()
        panel = summary.panels[0]
        self.assertAlmostEqual(summary.total_area, 12.0)
        self.assertAlmostEqual(summary.foundation_weight, (0.2 * 24.0 + 1.0) * 12.0)
        self.assertAlmostEqual(panel.long_pressure, 40.0 / 12.0 + 5.8, places=6)
        self.assertAlmostEqual(panel.average_long_pressure, 40.0 / 12.0 + 5.8, places=6)
        self.assertAlmostEqual(panel.long_ratio, (40.0 / 12.0 + 5.8) / 30.0, places=6)
        self.assertEqual(panel.status, "OK")

    def test_short_term_uses_the_short_allowable(self):
        panel = self._check().panels[0]
        self.assertAlmostEqual(panel.short_ratio, panel.short_pressure / 60.0)
        self.assertEqual(panel.short_load_case, 1)

    def test_low_bearing_capacity_is_ng(self):
        foundation = copy.deepcopy(FOUNDATION)
        foundation["soil"]["bearing_long"] = 5.0
        summary = self._check(foundation)
        self.assertEqual(summary.panels[0].status, "NG")
        self.assertEqual(summary.status, "NG")

    def test_beam_weight_is_added_above_the_mat(self):
        foundation = dict(FOUNDATION, beam_types=[BEAM], beam_lines=[{"beam": "FG1", "frame": "Y1", "span": ["X1", "X2"]}])
        web = 0.15 * (0.7 - 0.2) * 24.0 * 4.0
        self.assertAlmostEqual(self._check(foundation).foundation_weight, 5.8 * 12.0 + web)

    def test_support_outside_the_panels_is_a_warning(self):
        body, tops = _columns((0.0, 4.0, 8.0), self.YS)
        for node in tops.values():
            body += _point(node, 0, fz=-10.0)
        mdl = _solve(body)
        project = _project(FOUNDATION, {0: "LONG_TERM"})
        summary = build_foundation_check(mdl, project, Naming(mdl, project))
        self.assertEqual(summary.status, "WARN")
        self.assertTrue(any("outside" in w for w in summary.warnings))

    def test_unknown_grid_is_an_error(self):
        foundation = dict(FOUNDATION, panels=[{"slab": "FS1", "x": ["X1", "X9"], "y": ["Y1", "Y2"]}])
        with self.assertRaises(ValueError):
            self._check(foundation)


class TestShares(unittest.TestCase):

    def test_shared_support_is_split_by_panel_area(self):
        # Panels 1 m and 3 m wide; only the two middle columns carry load.
        body, tops = _columns((0.0, 1.0, 4.0), (0.0, 3.0))
        body += _point(tops[(1.0, 0.0)], 0, fz=-8.0) + _point(tops[(1.0, 3.0)], 0, fz=-8.0)
        mdl = _solve(body)
        foundation = dict(FOUNDATION, extra_load=0.0, panels=[
            {"slab": "FS1", "x": ["X1", "X2"], "y": ["Y1", "Y2"]},
            {"slab": "FS1", "x": ["X2", "X3"], "y": ["Y1", "Y2"]},
        ])
        project = _project(foundation, {0: "LONG_TERM"})
        summary = build_foundation_check(mdl, project, Naming(mdl, project))
        narrow, wide = summary.panels
        own = 0.2 * 24.0
        self.assertAlmostEqual(narrow.long_pressure, 16.0 * 0.25 / 3.0 + own, places=6)
        self.assertAlmostEqual(wide.long_pressure, 16.0 * 0.75 / 9.0 + own, places=6)


class TestOverturning(FourColumns):

    def test_moment_equals_force_times_height(self):
        summary = self._check()
        check = next(o for o in summary.overturning if o.direction == "X")
        self.assertAlmostEqual(check.moment, 8.0 * 3.0, places=6)
        self.assertAlmostEqual(check.weight, 40.0 + 5.8 * 12.0, places=6)
        self.assertAlmostEqual(check.arm, 2.0, places=6)
        self.assertAlmostEqual(check.resisting_moment, (40.0 + 69.6) * 2.0, places=6)
        self.assertEqual(check.status, "OK")

    def test_large_horizontal_force_overturns(self):
        summary = self._check(push=100.0)
        self.assertEqual(next(o for o in summary.overturning if o.direction == "X").status, "NG")
        self.assertEqual(summary.status, "NG")

    def test_slenderness_is_height_over_width(self):
        by_direction = {s.direction: s for s in self._check().slenderness}
        self.assertAlmostEqual(by_direction["X"].ratio, 3.0 / 4.0)
        self.assertAlmostEqual(by_direction["Y"].ratio, 1.0)

    def test_foundation_depth_adds_to_the_moment(self):
        foundation = dict(FOUNDATION, first_floor_height=400, embedment_depth=300)
        check = next(o for o in self._check(foundation).overturning if o.direction == "X")
        self.assertAlmostEqual(check.level_moment, 24.0, places=6)
        self.assertAlmostEqual(check.base_shear, 8.0, places=6)
        self.assertAlmostEqual(check.moment, 24.0 + 8.0 * 0.7, places=6)

    def test_sample_moment_is_reproduced(self):
        level = 23.8 * 2.519 + 52.8 * 2.94 + 73.7 * 2.581
        self.assertAlmostEqual(fd.base_moment(level, 73.7, 0.4, 0.3), 457.25, delta=0.5)

    def test_arm_is_measured_to_the_compression_side(self):
        # All gravity on the X1 side, so the centre of gravity is off the middle.
        body, tops = _columns(self.XS, self.YS)
        for key, node in tops.items():
            body += _point(node, 0, fz=-10.0 if key[0] == 0.0 else 0.0)
            body += _point(node, 1, fx=2.0)
            body += _point(node, 2, fx=-2.0)
        mdl = _solve(body)
        foundation = dict(FOUNDATION, extra_load=0.0, slab_types=[dict(SLAB, thickness=1)])
        for case, expected_high in ((1, True), (2, False)):
            durations = {0: "LONG_TERM", case: "SHORT_TERM"}
            project = validate_like(foundation, durations, keep=[0, case])
            summary = build_foundation_check(mdl, project, Naming(mdl, project))
            check = summary.overturning[0]
            self.assertEqual(check.compression_at_high_side, expected_high)
            weight = check.weight
            q0_load = 0.024 * 12.0
            centroid = q0_load * 2.0 / weight
            self.assertAlmostEqual(check.arm, 4.0 - centroid if expected_high else centroid, places=6)

    def test_slenderness_alone_does_not_require_the_pressure_check(self):
        tall = _columns(self.XS, self.YS, height=12.0)[0]
        self.assertFalse(self._required(tall, bearing_long=30.0))

    def test_low_bearing_alone_does_not_require_the_pressure_check(self):
        foundation = copy.deepcopy(FOUNDATION)
        foundation["soil"]["bearing_long"] = 29.0
        summary = self._check(foundation)
        self.assertTrue(summary.short_pressure_check_omitted)
        self.assertEqual(summary.short_pressure, ())

    def test_slender_building_on_weak_soil_is_checked(self):
        tall = _columns(self.XS, self.YS, height=12.0)[0]
        self.assertTrue(self._required(tall, bearing_long=20.0))

    def _required(self, body, bearing_long):
        _text, tops = _columns(self.XS, self.YS, height=12.0)
        for node in tops.values():
            body += _point(node, 0, fz=-10.0)
            body += _point(node, 1, fx=1.0, fz=-10.0)
        mdl = _solve(body)
        foundation = copy.deepcopy(FOUNDATION)
        foundation["soil"]["bearing_long"] = bearing_long
        project = _project(foundation, {0: "LONG_TERM", 1: "SHORT_TERM"})
        summary = build_foundation_check(mdl, project, Naming(mdl, project))
        return not summary.short_pressure_check_omitted


def validate_like(foundation, durations, keep):
    """A project whose wood check is limited to some load cases."""

    project = _project(foundation, durations)
    raw = project.to_dict()
    raw["design_checks"]["wood"]["load_cases"] = keep
    return validate_project_dict(raw)


class TestShearPanelModel(unittest.TestCase):

    def test_vertical_reactions_balance_the_overturning_moment(self):
        import dataclasses

        from stb_project import load_project_file
        from stb_project.foundation_settings import parse_foundation_settings

        data = os.path.join(_STB_ROOT, "data")
        project = load_project_file(os.path.join(data, "UK_240416_floors_1to3_diaphragm.project.json"))
        foundation = dict(FOUNDATION, panels=[{"slab": "FS1", "x": ["X1", "X9"], "y": ["Y1", "Y10"]}])
        project = dataclasses.replace(project, foundation=parse_foundation_settings(foundation))
        mdl, _txt = run_from_file(os.path.join(data, project.dat_path))

        summary = build_foundation_check(mdl, project, Naming(mdl, project))
        check = next(o for o in summary.overturning if o.direction == "X")
        height = max(n.z for n in mdl.nds) - min(c.nd.z for c in mdl.cons)
        self.assertGreater(check.level_moment, 0.4 * check.base_shear * height)
        self.assertLessEqual(check.level_moment, check.base_shear * height + 1.0e-6)
        clc = list(mdl.lcs).index(1)  # the seismic case alone, without gravity
        balanced = sum(c.nd.x * float(c.nd.reacts[clc, 2]) for c in mdl.cons) * 1.0e-3
        self.assertAlmostEqual(abs(balanced), check.level_moment, delta=1.0)


class TestShortPressure(unittest.TestCase):

    B = 4.0
    WIDTH = 3.0

    def _panel(self):
        return [fd.PanelGeometry("FS1", ("X1", "X2"), ("Y1", "Y2"), 0.0, self.B, 0.0, self.WIDTH)]

    def _overturn(self, moment, weight):
        return fd.OverturningCheck("X", moment, 1.0, moment, weight, self.B / 2.0, weight * self.B / 2.0, 1, "OK", True)

    def test_within_the_kern_adds_bending_stress(self):
        check = fd.short_pressure_check(self._panel(), self._overturn(10.0, 120.0), 60.0)
        area = self.B * self.WIDTH
        z = self.WIDTH * self.B ** 2 / 6.0
        self.assertAlmostEqual(check.pressure, 120.0 / area + 10.0 / z)
        self.assertIsNone(check.alpha_e)

    def test_outside_the_kern_uses_the_rectangular_closed_form(self):
        weight = 120.0
        eccentricity = 1.2
        check = fd.short_pressure_check(self._panel(), self._overturn(weight * eccentricity, weight), 60.0)
        xn = 3.0 * (self.B / 2.0 - eccentricity)
        self.assertAlmostEqual(check.alpha_e, 2.0 * self.B / xn, places=3)
        self.assertAlmostEqual(check.pressure, 2.0 * weight / (self.WIDTH * xn), places=2)
        self.assertEqual(check.status, "OK")

    def test_excess_pressure_is_ng(self):
        check = fd.short_pressure_check(self._panel(), self._overturn(120.0 * 1.9, 120.0), 60.0)
        self.assertEqual(check.status, "NG")

    def test_section_of_two_panels(self):
        strips = fd._strips(
            [
                fd.PanelGeometry("A", ("X1", "X2"), ("Y1", "Y2"), 0.0, 2.0, 0.0, 3.0),
                fd.PanelGeometry("B", ("X2", "X3"), ("Y1", "Y2"), 2.0, 4.0, 0.0, 3.0),
            ],
            "X",
            True,
        )
        area, centroid, inertia = fd._section(strips)
        self.assertAlmostEqual(area, 12.0)
        self.assertAlmostEqual(centroid, 2.0)
        self.assertAlmostEqual(inertia, 3.0 * 4.0 ** 3 / 12.0)


class TestBook(FourColumns):

    def test_chapter_12_shows_the_checks(self):
        mdl = self._model()
        project = _project(FOUNDATION, self.DURATIONS)
        doc = build_document(build_context(mdl, project, program_version="9.9"))
        titles = [b.text for b in doc.blocks if isinstance(b, Heading)]
        for title in ("12.1 基礎概要", "12.3.2 地耐力検討", "12.6.1 転倒の検討", "12.2.2 基礎配置図"):
            self.assertIn(title, titles)
        cells = [c for b in doc.blocks if isinstance(b, Table) for r in b.rows for c in r if isinstance(c, str)]
        self.assertIn("X1-X2, Y1-Y2", cells)
        self.assertTrue(any(isinstance(b, Text) and "基礎の接地圧および転倒" in b.text for b in doc.blocks))


class TestSchema(unittest.TestCase):

    def _foundation(self, **changes):
        return dict(copy.deepcopy(FOUNDATION), **changes)

    def test_round_trip(self):
        foundation = self._foundation(beam_types=[BEAM], beam_lines=[{"beam": "FG1", "frame": "Y1", "span": ["X1", "X2"]}])
        project = _project(foundation, {})
        self.assertEqual(project.foundation.concrete.unit_weight, 24.0)
        self.assertEqual(project.foundation.panels[0].x, ("X1", "X2"))
        self.assertEqual(validate_project_dict(project.to_dict()).to_dict(), project.to_dict())

    def test_absent_stays_out_of_the_file(self):
        raw = _project(FOUNDATION, {}).to_dict()
        del raw["foundation"]
        self.assertNotIn("foundation", validate_project_dict(raw).to_dict())

    def _rejected(self, foundation):
        with self.assertRaises(ProjectSchemaError):
            _project(foundation, {})

    def test_rejects_other_foundation_types(self):
        self._rejected(self._foundation(type="pile"))

    def test_rejects_non_positive_bearing(self):
        foundation = self._foundation()
        foundation["soil"]["bearing_short"] = 0.0
        self._rejected(foundation)

    def test_rejects_unknown_slab(self):
        self._rejected(self._foundation(panels=[{"slab": "NO", "x": ["X1", "X2"], "y": ["Y1", "Y2"]}]))

    def test_requires_panels(self):
        self._rejected(self._foundation(panels=[]))

    def test_rejects_bad_bar_notation(self):
        bad = dict(SLAB, short={"end": "13@300", "mid": "D10@300"})
        self._rejected(self._foundation(slab_types=[bad]))

    def test_rejects_panel_with_one_grid(self):
        self._rejected(self._foundation(panels=[{"slab": "FS1", "x": ["X1"], "y": ["Y1", "Y2"]}]))

    def test_rejects_unknown_beam(self):
        self._rejected(self._foundation(beam_lines=[{"beam": "NO", "frame": "Y1", "span": ["X1", "X2"]}]))

    def test_rejects_manual_edges_for_now(self):
        self._rejected(self._foundation(panels=[{"slab": "FS1", "x": ["X1", "X2"], "y": ["Y1", "Y2"], "edges": "fixed"}]))


if __name__ == "__main__":
    unittest.main()
