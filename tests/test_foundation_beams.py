"""Foundation beams. "Sample" numbers come from a reviewed calculation report."""

import copy
import os
import sys
import tempfile
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_checks import foundation_beams as fb
from stb_checks.foundation import build_foundation_check
from stb_engine import run_from_file
from stb_project import validate_project_dict
from stb_reports.calc_book.context import Naming

SAMPLE_B, SAMPLE_D, SAMPLE_DT = 150.0, 700.0, 72.0
SAMPLE_J = 7.0 / 8.0 * (SAMPLE_D - SAMPLE_DT)


class TestSampleSection(unittest.TestCase):

    def test_allowable_moment_matches_sample(self):
        area = fb.bar_area(19)
        fc = 21.0 / 3.0
        long_term = fb.allowable_moment(SAMPLE_B, SAMPLE_D, SAMPLE_DT, area, area, fc, 215.0)
        short_term = fb.allowable_moment(SAMPLE_B, SAMPLE_D, SAMPLE_DT, area, area, fc * 2.0, 345.0)
        self.assertAlmostEqual(long_term, 35.4, delta=0.05)
        self.assertAlmostEqual(short_term, 56.8, delta=0.06)

    def test_concrete_can_govern(self):
        large = 5000.0
        governed = fb.allowable_moment(SAMPLE_B, SAMPLE_D, SAMPLE_DT, large, 0.0, 7.0, 215.0)
        self.assertLess(governed, large * 215.0 * SAMPLE_J * 1.0e-6)

    def test_shear_reinforcement_ratio_matches_sample(self):
        self.assertAlmostEqual(fb.stirrup_ratio("1-D10@200", SAMPLE_B) * 100.0, 0.24, delta=0.005)

    def test_allowable_shear_matches_sample(self):
        pw = fb.stirrup_ratio("1-D10@200", SAMPLE_B)
        fc, fs = fb.concrete_allowable(21.0)
        self.assertAlmostEqual(fs, 0.7)
        self.assertAlmostEqual(fb.allowable_shear(SAMPLE_B, SAMPLE_J, 2.0, fs, 195.0, pw), 118.4, delta=0.1)
        self.assertAlmostEqual(fb.allowable_shear(SAMPLE_B, SAMPLE_J, 2.0, fs * 1.5, 295.0, pw), 177.6, delta=0.15)

    def test_shear_span_factor_limits(self):
        self.assertEqual(fb.shear_span_factor(0.0, 10.0, 0.6), 2.0)
        self.assertEqual(fb.shear_span_factor(100.0, 1.0, 0.6), 1.0)
        self.assertAlmostEqual(fb.shear_span_factor(0.6, 1.0, 0.6), 2.0)
        self.assertAlmostEqual(fb.shear_span_factor(1.2, 1.0, 0.6), 4.0 / 3.0)

    def test_concrete_young_matches_sample(self):
        self.assertAlmostEqual(fb.concrete_young(21.0), 21682.0, delta=5.0)

    def test_main_bar_allowable(self):
        self.assertEqual(fb.main_bar_allowable("SD345", 19), (215.0, 345.0))
        self.assertEqual(fb.main_bar_allowable("SD345", 29), (195.0, 345.0))
        self.assertEqual(fb.main_bar_allowable("SD295", 13), (195.0, 295.0))
        with self.assertRaises(ValueError):
            fb.main_bar_allowable("SD490", 19)

    def test_shear_reinforcement_is_capped(self):
        high = fb.allowable_shear(SAMPLE_B, SAMPLE_J, 1.0, 0.7, 195.0, 0.02)
        capped = fb.allowable_shear(SAMPLE_B, SAMPLE_J, 1.0, 0.7, 195.0, 0.006)
        self.assertAlmostEqual(high, capped)


HEADER = """MATE, 1, Wood, 12000, 800, 0.0, 3e-06, 0
SECT, 1, S, 1, 0, 300.0, 300.0
"""
BEAM = {
    "name": "FG1", "b": 300, "d": 700, "top": "2-D19", "bottom": "2-D19", "dt": 72,
    "stirrup": "2-D10@200", "main_rebar": "SD345", "stirrup_rebar": "SD295",
}
SLAB = {
    "name": "FS1", "thickness": 200, "d_short": 140, "d_long": 123, "rebar": "SD295",
    "short": {"end": "D13@300", "mid": "D10@300"}, "long": {"end": "D13@300", "mid": "D10@300"},
}


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


def _solve(body):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "m.dat")
        with open(path, "w", encoding="utf-8") as f:
            f.write(HEADER + body)
        mdl, _txt = run_from_file(path)
    return mdl


def _project(foundation, durations):
    return validate_project_dict({
        "schema": 1,
        "model": {"dat": "m.dat"},
        "building": {"name": "b", "location": "", "use": "", "structure": "wood", "calculation_route": "",
                     "designer": {"name": "", "qualification": "", "license_number": "", "contact": ""}},
        "grids": [], "stories": [], "member_classes": [],
        "design_checks": {"wood": {
            "enabled": False,
            "load_case_durations": [{"load_case": k, "duration": v} for k, v in durations.items()],
        }},
        "report": {"title": "", "mode": "practice", "language": "ja", "format": "markdown",
                   "include_manual_items": True, "include_warnings": True},
        "foundation": foundation,
    })


FOUNDATION = {
    "type": "mat",
    "soil": {"name": "s", "bearing_long": 30.0, "bearing_short": 60.0, "young": 5000.0},
    "concrete": {"name": "FC21", "fc": 21.0},
    "slab_types": [SLAB],
    "panels": [{"slab": "FS1", "x": ["X1", "X2"], "y": ["Y1", "Y2"]}],
    "beam_types": [BEAM],
    "beam_lines": [
        {"beam": "FG1", "frame": "Y1", "span": ["X1", "X2"]},
        {"beam": "FG1", "frame": "Y2", "span": ["X1", "X2"]},
        {"beam": "FG1", "frame": "X1", "span": ["Y1", "Y2"]},
        {"beam": "FG1", "frame": "X2", "span": ["Y1", "Y2"]},
    ],
}
L, W = 6.0, 4.0  # X and Y spans of the panel


def _check(body, durations, foundation=None):
    mdl = _solve(body)
    project = _project(foundation or FOUNDATION, durations)
    naming = Naming(mdl, project)
    summary = build_foundation_check(mdl, project, naming)
    return fb.build_foundation_beam_check(mdl, project, naming, summary), mdl


def _gravity(p=30.0):
    body, tops = _columns((0.0, L), (0.0, W))
    for node in tops.values():
        body += "PLOD, {0}, 0, 0.0, 0.0, {1}, 0.0, 0.0, 0.0\n".format(node, -p)
    return body, tops


class TestGravity(unittest.TestCase):

    def test_ground_reaction_is_carried_by_all_four_beams(self):
        # The 120 kN column load comes back as 5 kN/m2 under the 6 x 4 m panel.
        result, _mdl = _check(_gravity()[0], {0: "LONG_TERM"})
        self.assertEqual(len(result.checks), 4)
        by_frame = {c.frame: c for c in result.checks}
        pressure = 120.0 / (L * W)
        half = W / 2.0

        # Long side: trapezoid, peak p*W/2. Midspan moment of a simple beam.
        a = half
        moment_long = pressure * half * (3.0 * L ** 2 - 4.0 * a ** 2) / 24.0
        shear_long = pressure * half * (L - a) / 2.0
        middle = by_frame["Y1"].sections[1]
        self.assertAlmostEqual(abs(middle.long_moment), moment_long, delta=moment_long * 0.01)
        end = by_frame["Y1"].sections[0]
        self.assertAlmostEqual(abs(end.long_shear), shear_long, delta=shear_long * 0.02)

        # Short side: triangle, peak p*W/2.
        moment_short = pressure * half * W ** 2 / 12.0
        self.assertAlmostEqual(abs(by_frame["X1"].sections[1].long_moment), moment_short, delta=moment_short * 0.01)

    def test_upward_reaction_tensions_the_top_at_midspan(self):
        result, _mdl = _check(_gravity()[0], {0: "LONG_TERM", 1: "SHORT_TERM_SNOW"})
        self.assertLess(result.checks[0].sections[1].long_moment, 0.0)

    def test_ratio_uses_the_allowable_moment(self):
        result, _mdl = _check(_gravity()[0], {0: "LONG_TERM"})
        check = result.checks[0]
        section = check.sections[1]
        self.assertAlmostEqual(section.long_moment_ratio, abs(section.long_moment) / check.allowable_long)
        self.assertEqual(result.status, "OK")

    def test_overstressed_beam_is_ng(self):
        result, _mdl = _check(_gravity(p=3000.0)[0], {0: "LONG_TERM"})
        self.assertEqual(result.status, "NG")

    def test_no_lines_means_no_check(self):
        foundation = dict(FOUNDATION, beam_lines=[])
        result, _mdl = _check(_gravity()[0], {0: "LONG_TERM"}, foundation)
        self.assertIsNone(result)

    def test_panel_edge_without_a_beam_warns(self):
        foundation = copy.deepcopy(FOUNDATION)
        foundation["beam_lines"] = foundation["beam_lines"][:3]
        result, _mdl = _check(_gravity()[0], {0: "LONG_TERM"}, foundation)
        self.assertTrue(any("no foundation beam" in w for w in result.warnings))

    def test_unknown_grade_is_an_error(self):
        foundation = copy.deepcopy(FOUNDATION)
        foundation["beam_types"][0]["main_rebar"] = "SD490"
        with self.assertRaises(ValueError):
            _check(_gravity()[0], {0: "LONG_TERM"}, foundation)


class TestLateral(unittest.TestCase):

    PUSH = 20.0

    def _body(self):
        # Rated walls on Y1 and Y2 give the columns a couple under a push along X.
        body, tops = _columns((0.0, L), (0.0, W))
        node_ids = {key: tops[key] - 1 for key in tops}
        for index, y in enumerate((0.0, W)):
            body += "WWLL, {0}, W{0}, 1, 2.0, {1}, 3.0, 0, 0.0083333333, {2}, {3}, {4}, {5}, , 1\n".format(
                index + 1, L, node_ids[(0.0, y)], node_ids[(L, y)], tops[(L, y)], tops[(0.0, y)]
            )
        for (x, y), node in tops.items():
            body += "PLOD, {0}, 0, 0.0, 0.0, -30.0, 0.0, 0.0, 0.0\n".format(node)
            body += "PLOD, {0}, 1, {1}, 0.0, -30.0, 0.0, 0.0, 0.0\n".format(node, self.PUSH / 4.0)
        return body

    def test_column_couple_reaches_the_beams(self):
        result, _mdl = _check(self._body(), {0: "LONG_TERM", 1: "SHORT_TERM"})
        beam = next(c for c in result.checks if c.frame == "Y1")
        section = beam.sections[0]
        self.assertGreater(section.design_shear, abs(section.long_shear) + 0.1)
        self.assertEqual(section.shear_case, 1)

    def test_design_shear_applies_the_factor_to_the_lateral_part(self):
        mdl = _solve(self._body())
        project = _project(FOUNDATION, {0: "LONG_TERM", 1: "SHORT_TERM"})
        naming = Naming(mdl, project)
        summary = build_foundation_check(mdl, project, naming)
        panels = [c.panel for c in summary.panels]
        supports = [c.nd for c in mdl.cons]
        warnings = []
        grillage = fb._Grillage(project.foundation, naming, panels, supports, warnings)
        loads = fb._lateral_loads(grillage, supports, [1], {0: 0, 1: 1}, 0, warnings)
        spring = fb._spring_model(grillage, fb.concrete_young(21.0), 5000.0, loads)
        members = [m for m in grillage.members if grillage.spans[m.span].frame == "Y1"]
        lateral = fb._span_forces(spring, members, list(spring.lcs).index(1))[0][1]

        result = fb.build_foundation_beam_check(mdl, project, naming, summary)
        section = next(c for c in result.checks if c.frame == "Y1").sections[0]
        self.assertAlmostEqual(section.design_shear, abs(section.long_shear) + 1.5 * abs(lateral), places=6)

    def test_spring_model_is_in_equilibrium(self):
        mdl = _solve(self._body())
        project = _project(FOUNDATION, {0: "LONG_TERM", 1: "SHORT_TERM"})
        naming = Naming(mdl, project)
        summary = build_foundation_check(mdl, project, naming)
        grillage = fb._Grillage(project.foundation, naming, [c.panel for c in summary.panels], [c.nd for c in mdl.cons], [])
        loads = {1: {node: force for node, force in zip(sorted(grillage.nodes.values())[:2], (-5.0, -3.0))}}
        spring = fb._spring_model(grillage, fb.concrete_young(21.0), 5000.0, loads)
        clc = list(spring.lcs).index(1)
        total = sum(float(c.nd.reacts[clc, 2]) for c in spring.cons) * 1.0e-3
        self.assertAlmostEqual(total, 8.0, places=6)


class TestBook(unittest.TestCase):

    def test_book_shows_the_beam_checks(self):
        from stb_reports.calc_book import build_document
        from stb_reports.calc_book.context import build_context
        from stb_reports.calc_book.document import Heading

        mdl = _solve(_gravity()[0])
        project = _project(FOUNDATION, {0: "LONG_TERM"})
        doc = build_document(build_context(mdl, project, program_version="9.9"))
        titles = [b.text for b in doc.blocks if isinstance(b, Heading)]
        self.assertIn("12.5.3 基礎梁断面検定表", titles)


if __name__ == "__main__":
    unittest.main()
