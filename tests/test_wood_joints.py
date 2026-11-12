"""Joint hardware checks. "Sample" numbers come from a reviewed calculation report."""

import dataclasses
import os
import sys
import tempfile
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_checks import build_wood_check_summary
from stb_checks import wood_joints as wj
from stb_checks.wood_standard import LONG_TERM, LONG_TERM_SNOW, SHORT_TERM, SHORT_TERM_SNOW
from stb_engine import run_from_file
from stb_project import ProjectSchemaError, WoodJointType, validate_project_dict

TH18C = WoodJointType("TH18C", 14.9, 27.1, 14.9, 27.1, 13.36, 24.3)
HDP20_N = WoodJointType("HDP20-N", 140.2, 255.0, 14.0, 25.5, 4.4, 8.0)
MOMENT_JOINT = WoodJointType("M", 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 5.0, 5.0, moment_weak_long=1.0, moment_weak_short=1.0)


def _end(n=0.0, q_z=0.0, q_y=0.0, m_y=0.0, m_z=0.0):
    """A 14-component force vector with these values (kN, kN*m) at both ends."""

    f = [0.0] * 14
    f[0] = f[6] = n * 1000.0
    f[1] = f[7] = q_y * 1000.0
    f[2] = f[8] = q_z * 1000.0
    f[4] = f[10] = m_y * 1000.0
    f[5] = f[11] = m_z * 1000.0
    return f


def _check(joint, cases, interaction="linear", strong_is_y=True):
    load_cases = list(range(len(cases)))
    forces = {i: cases[i][1] for i in load_cases}
    durations = {i: cases[i][0] for i in load_cases}
    return wj.check_joint_end(forces, joint, strong_is_y, load_cases, durations, 0, interaction)


def _component(group, label):
    return next(c for c in group.components if c.label == label)


class TestAllowable(unittest.TestCase):

    def test_snow_factors_match_sample(self):
        self.assertAlmostEqual(wj.allowable(LONG_TERM_SNOW, 10.0, 99.0), 13.0)
        self.assertAlmostEqual(wj.allowable(SHORT_TERM_SNOW, 99.0, 39.4), 31.52)
        self.assertAlmostEqual(wj.allowable(LONG_TERM, 10.0, 99.0), 10.0)
        self.assertAlmostEqual(wj.allowable(SHORT_TERM, 99.0, 39.4), 39.4)


class TestSampleEnds(unittest.TestCase):

    def test_beam_shear_matches_sample(self):
        groups, _ = _check(TH18C, [(LONG_TERM, _end(q_z=1.47)), (SHORT_TERM, _end(q_z=3.23))])
        long_group, short_group = groups
        self.assertAlmostEqual(_component(long_group, "Q").ratio, 0.110, delta=0.001)
        self.assertAlmostEqual(_component(short_group, "Q").ratio, 0.133, delta=0.001)

    def test_column_compression_matches_sample(self):
        groups, _ = _check(HDP20_N, [(LONG_TERM, _end(n=-6.02)), (SHORT_TERM_SNOW, _end(n=-6.91))])
        long_group, short_group = groups
        self.assertAlmostEqual(_component(long_group, "N").ratio, 0.043, delta=0.001)
        compression = _component(short_group, "cN")
        self.assertAlmostEqual(compression.capacity, 204.0)
        self.assertAlmostEqual(compression.ratio, 0.034, delta=0.001)


class TestEndCheck(unittest.TestCase):

    def test_tension_uses_tension_capacity(self):
        groups, _ = _check(HDP20_N, [(SHORT_TERM, _end(n=12.75))])
        self.assertAlmostEqual(_component(groups[0], "tN").ratio, 0.5)
        self.assertEqual(_component(groups[0], "cN").ratio, 0.0)

    def test_linear_interaction_adds_components(self):
        groups, _ = _check(MOMENT_JOINT, [(LONG_TERM, _end(n=2.0, q_z=3.0, m_y=1.0))])
        self.assertAlmostEqual(groups[0].combined_ratio, 0.2 + 0.2 + 0.3)

    def test_no_interaction_reports_components_only(self):
        groups, _ = _check(MOMENT_JOINT, [(LONG_TERM, _end(n=2.0, q_z=3.0))], interaction="none")
        self.assertEqual(groups[0].combined_ratio, 0.0)
        self.assertAlmostEqual(_component(groups[0], "Q").ratio, 0.3)

    def test_weak_axis_capacity_applies(self):
        groups, _ = _check(MOMENT_JOINT, [(LONG_TERM, _end(m_z=0.5))])
        self.assertAlmostEqual(_component(groups[0], "M").ratio, 0.5)

    def test_strong_axis_follows_the_section(self):
        groups, _ = _check(MOMENT_JOINT, [(LONG_TERM, _end(m_y=0.5))], strong_is_y=False)
        self.assertAlmostEqual(_component(groups[0], "M").ratio, 0.5)

    def test_pin_ignores_moment_but_flags_it(self):
        groups, on_pin = _check(TH18C, [(LONG_TERM, _end(m_y=2.0))])
        self.assertEqual(_component(groups[0], "M").ratio, 0.0)
        self.assertTrue(on_pin)

    def test_numerical_noise_on_pin_is_not_flagged(self):
        _, on_pin = _check(TH18C, [(LONG_TERM, _end(m_y=0.001))])
        self.assertFalse(on_pin)

    def test_force_on_zero_capacity_fails(self):
        joint = WoodJointType("dum")
        groups, _ = _check(joint, [(LONG_TERM, _end(q_z=1.0))])
        self.assertEqual(_component(groups[0], "Q").ratio, wj.NO_CAPACITY_RATIO)

    def test_end_index_follows_member_direction(self):
        self.assertEqual(wj._end_index(wj.END_BOTTOM, True), 0)
        self.assertEqual(wj._end_index(wj.END_TOP, True), 6)
        self.assertEqual(wj._end_index(wj.END_BOTTOM, False), 6)
        self.assertEqual(wj._end_index(wj.END_TOP, False), 0)


FRAME = """MATE, 1, Wood, 12000, 800, 5.0, 3e-06, 0
SECT, 1, S, 1, 0, 105.0, 105.0
NODE, 1, 0.0, 0.0, 3.0
NODE, 2, 0.0, 0.0, 0.0
ELEM, 1, 1, 2, 1, 0.0
CONS, 2, 1, 1, 1, 1, 1, 1
PLOD, 1, 0, 0.0, 0.0, -6.02, 0.0, 0.0, 0.0
"""


def _project(wood):
    return validate_project_dict({
        "schema": 1,
        "model": {"dat": "m.dat"},
        "building": {"name": "b", "location": "", "use": "", "structure": "wood", "calculation_route": "",
                     "designer": {"name": "", "qualification": "", "license_number": "", "contact": ""}},
        "grids": [],
        "stories": [{"name": "1", "elevation": 0.0, "height": 3.0}],
        "member_classes": [{"name": "columns", "kind": "column", "element_ids": [1], "story": "1", "use": "", "notes": ""}],
        "design_checks": {"wood": dict({"enabled": True, "load_cases": [0]}, **wood)},
        "report": {"title": "", "mode": "practice", "language": "ja", "format": "markdown",
                   "include_manual_items": True, "include_warnings": True},
    })


JOINT = {"name": "HDP20-N", "compression_long": 140.2, "compression_short": 255.0, "tension_long": 14.0,
         "tension_short": 25.5, "shear_long": 4.4, "shear_short": 8.0}


class TestSummary(unittest.TestCase):

    def _mdl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.dat")
            with open(path, "w", encoding="utf-8") as f:
                f.write(FRAME)
            mdl, _txt = run_from_file(path)
        return mdl

    WOOD = {
        "load_case_durations": [{"load_case": 0, "duration": "LONG_TERM"}],
        "joint_types": [JOINT],
        "joint_assignments": [{"member_class": "columns", "top": "HDP20-N", "bottom": "HDP20-N"}],
    }

    def test_solved_column_is_checked_at_both_ends(self):
        summary = build_wood_check_summary(self._mdl(), _project(self.WOOD))
        ends = {c.end for c in summary.joint_checks}
        self.assertEqual(ends, {"top", "bottom"})
        for check in summary.joint_checks:
            axial = _component(check.groups[0], "N")
            self.assertAlmostEqual(axial.value, -6.02, places=6)
            self.assertAlmostEqual(axial.ratio, 0.043, delta=0.001)
            self.assertEqual(check.status, "OK")

    def test_overloaded_joint_makes_the_summary_ng(self):
        weak = dict(JOINT, compression_long=1.0)
        wood = dict(self.WOOD, joint_types=[weak])
        summary = build_wood_check_summary(self._mdl(), _project(wood))
        self.assertEqual(summary.status, "NG")
        self.assertIn(wj.MESSAGE_RATIO, summary.joint_checks[0].messages)
        self.assertGreater(summary.max_ratio, 1.0)

    def test_element_assignment_overrides_the_class(self):
        other = dict(JOINT, name="OTHER")
        wood = dict(
            self.WOOD,
            joint_types=[JOINT, other],
            joint_assignments=self.WOOD["joint_assignments"] + [{"element_ids": [1], "top": "OTHER"}],
        )
        summary = build_wood_check_summary(self._mdl(), _project(wood))
        names = {c.end: c.joint for c in summary.joint_checks}
        self.assertEqual(names, {"top": "OTHER", "bottom": "HDP20-N"})

    def test_no_assignments_means_no_joint_checks(self):
        summary = build_wood_check_summary(self._mdl(), _project({}))
        self.assertEqual(summary.joint_checks, ())


class TestSchema(unittest.TestCase):

    def test_round_trip(self):
        project = _project(dict(TestSummary.WOOD, joint_interaction="none"))
        wood = project.design_checks.wood
        self.assertEqual(wood.joint_types[0].shear_weak_long, None)
        self.assertEqual(wood.joint_interaction, "none")
        self.assertEqual(validate_project_dict(project.to_dict()).to_dict(), project.to_dict())

    def test_defaults_stay_out_of_the_file(self):
        out = _project({}).to_dict()["design_checks"]["wood"]
        for key in ("joint_types", "joint_assignments", "joint_interaction"):
            self.assertNotIn(key, out)

    def _rejected(self, **wood):
        with self.assertRaises(ProjectSchemaError):
            _project(wood)

    def test_rejects_unknown_joint_reference(self):
        self._rejected(joint_types=[JOINT], joint_assignments=[{"member_class": "columns", "top": "NOPE"}])

    def test_rejects_assignment_without_target(self):
        self._rejected(joint_types=[JOINT], joint_assignments=[{"top": "HDP20-N"}])

    def test_rejects_assignment_without_ends(self):
        self._rejected(joint_types=[JOINT], joint_assignments=[{"member_class": "columns"}])

    def test_rejects_negative_capacity(self):
        self._rejected(joint_types=[dict(JOINT, shear_long=-1.0)])

    def test_rejects_duplicate_names(self):
        self._rejected(joint_types=[JOINT, JOINT])

    def test_rejects_unknown_interaction(self):
        self._rejected(joint_interaction="other")


class TestBook(unittest.TestCase):

    def test_book_lists_joints_and_their_checks(self):
        from stb_project import load_project_file
        from stb_reports.calc_book import build_document
        from stb_reports.calc_book.context import build_context
        from stb_reports.calc_book.document import Heading, Table

        project = load_project_file(os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json"))
        mdl, _txt = run_from_file(os.path.join(_STB_ROOT, "data", project.dat_path))
        wood = dataclasses.replace(
            project.design_checks.wood,
            joint_types=(HDP20_N,),
            joint_assignments=(wj_assignment("wood_columns"),),
        )
        project = dataclasses.replace(project, design_checks=dataclasses.replace(project.design_checks, wood=wood))

        doc = build_document(build_context(mdl, project, program_version="9.9"))
        titles = [b.text for b in doc.blocks if isinstance(b, Heading)]
        self.assertIn("1.4.3 接合金物リスト", titles)
        self.assertIn("7.8.2 木造柱接合金物の設計", titles)
        cells = [c for b in doc.blocks if isinstance(b, Table) for r in b.rows for c in r if isinstance(c, str)]
        self.assertIn("柱脚", cells)
        self.assertIn("HDP20-N", cells)


def wj_assignment(name):
    from stb_project import WoodJointAssignment

    return WoodJointAssignment(member_class=name, top="HDP20-N", bottom="HDP20-N")


if __name__ == "__main__":
    unittest.main()
