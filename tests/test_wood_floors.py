"""In-plane shear check of timber diaphragms."""

import dataclasses
import math
import os
import sys
import unittest

import numpy as np

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_checks import build_wood_check_summary
from stb_checks import wood_floors as wf
from stb_engine import run_from_file
from stb_project import ProjectSchemaError, load_project_file, validate_project_dict
from stb_reports.calc_book import build_document
from stb_reports.calc_book.chapters_results import _bay
from stb_reports.calc_book.context import build_context
from stb_reports.calc_book.document import Heading, Table, Text

DATA = os.path.join(_STB_ROOT, "data")
EZ = np.array([0.0, 0.0, 1.0])


def _axes(angle_deg):
    a = math.radians(angle_deg)
    ex = np.array([math.cos(a), math.sin(a), 0.0])
    ey = np.array([-math.sin(a), math.cos(a), 0.0])
    return ex, ey


class TestStressRotation(unittest.TestCase):

    def test_aligned_axes_keep_the_shear(self):
        ex, ey = _axes(0.0)
        self.assertAlmostEqual(wf.global_shear_stress(5.0, -3.0, 2.0, ex, ey, EZ), 2.0)

    def test_quarter_turn_reverses_the_shear(self):
        ex, ey = _axes(90.0)
        self.assertAlmostEqual(wf.global_shear_stress(0.0, 0.0, 2.0, ex, ey, EZ), -2.0)

    def test_tension_and_compression_at_45_degrees_are_pure_shear(self):
        ex, ey = _axes(45.0)
        self.assertAlmostEqual(abs(wf.global_shear_stress(3.0, -3.0, 0.0, ex, ey, EZ)), 3.0)

    def test_result_does_not_depend_on_the_triangle_orientation(self):
        # A global shear stress of 2.0, expressed in element axes at several angles.
        for angle in (0.0, 17.0, 45.0, 90.0, 133.0):
            a = math.radians(angle)
            sx = 2.0 * 2.0 * math.sin(a) * math.cos(a)
            sy = -sx
            sxy = 2.0 * (math.cos(a) ** 2 - math.sin(a) ** 2)
            ex, ey = _axes(angle)
            self.assertAlmostEqual(wf.global_shear_stress(sx, sy, sxy, ex, ey, EZ), 2.0, msg=str(angle))

    def test_sloped_plane_uses_projected_x(self):
        s = math.sqrt(0.5)
        ex = np.array([s, 0.0, s])
        ey = np.array([0.0, 1.0, 0.0])
        ez = np.cross(ex, ey)
        self.assertAlmostEqual(wf.global_shear_stress(0.0, 0.0, 2.0, ex, ey, ez), 2.0)


class TestCapacity(unittest.TestCase):

    def test_capacity_matches_sample(self):
        for multiplier, length, expected in ((7.0, 0.910, 12.5), (4.0, 0.550, 4.3), (4.0, 0.996, 7.8), (5.6, 1.250, 13.7)):
            self.assertAlmostEqual(wf.UNIT_SHEAR_STRENGTH_KN_PER_M * multiplier * length, expected, delta=0.05)

    def test_sample_ratio_is_the_same_in_both_directions(self):
        # S1, t=24 mm, tau=0.07 N/mm2, 910 mm: QD=1.5 kN, Qa=12.5 kN, QD/Qa about 0.12.
        flow = 0.07 * 24.0
        ratio = flow * 0.91 / (wf.UNIT_SHEAR_STRENGTH_KN_PER_M * 7.0 * 0.91)
        self.assertAlmostEqual(ratio, 0.122, delta=0.002)
        self.assertAlmostEqual(flow * 0.91, 1.5, delta=0.05)


class TestModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.project = load_project_file(os.path.join(DATA, "UK_240416_floors_1to3_diaphragm.project.json"))
        cls.project = cls._enabled(cls.project)
        cls.mdl, _txt = run_from_file(os.path.join(DATA, cls.project.dat_path))

    @staticmethod
    def _enabled(project, **changes):
        wood = dataclasses.replace(project.design_checks.wood, enabled=True, **changes)
        return dataclasses.replace(project, design_checks=dataclasses.replace(project.design_checks, wood=wood))

    def test_all_membrane_elements_are_checked(self):
        summary = build_wood_check_summary(self.mdl, self.project)
        self.assertEqual(len(summary.floor_checks), len(self.mdl.dmems))
        check = max(summary.floor_checks, key=lambda c: c.ratio)
        self.assertGreater(check.shear_flow, 0.0)
        self.assertAlmostEqual(check.allowable, 1.96 * check.multiplier)
        self.assertAlmostEqual(check.ratio, check.shear_flow / check.allowable)
        self.assertGreaterEqual(summary.max_ratio, check.ratio)

    def test_multiplier_can_be_overridden(self):
        from stb_project import WoodFloorMultiplier

        base = build_wood_check_summary(self.mdl, self.project).floor_checks[0]
        project = self._enabled(
            self.project,
            floor_multipliers=(WoodFloorMultiplier(base.diaphragm_id, base.multiplier * 2.0),),
        )
        checked = build_wood_check_summary(self.mdl, project).floor_checks[0]
        self.assertAlmostEqual(checked.ratio, base.ratio / 2.0)

    def test_book_has_the_floor_section(self):
        doc = build_document(build_context(self.mdl, self.project, program_version="9.9"))
        titles = [b.text for b in doc.blocks if isinstance(b, Heading)]
        self.assertIn("7.10.1 木造床の設計", titles)
        self.assertIn("1.4.4 床リスト", titles)
        section = titles.index("7.10.1 木造床の設計")
        self.assertGreater(section, titles.index("7.9 耐力壁の断面検定表"))
        tables = [b for b in doc.blocks if isinstance(b, Table) and b.columns and b.columns[0].label == "符号" and len(b.columns) == 10]
        self.assertEqual(len(tables), 1)
        self.assertTrue(tables[0].rows)

    def test_rigid_floor_is_excluded_and_stated(self):
        project = self._enabled(load_project_file(os.path.join(DATA, "UK_240416_floors_1to3_rigid_diaphragm.project.json")))
        mdl, _txt = run_from_file(os.path.join(DATA, project.dat_path))
        self.assertEqual(build_wood_check_summary(mdl, project).floor_checks, ())
        doc = build_document(build_context(mdl, project, program_version="9.9"))
        self.assertTrue(any(isinstance(b, Text) and "対象外" in b.text and "剛床" in b.text for b in doc.blocks))


PANEL = """MATE, 1, Wood, 12000, 800, 5.0, 3e-06, 0
SECT, 1, S, 1, 0, 105.0, 105.0
NODE, 1, 0.0, 0.0, 3.0
NODE, 2, 4.0, 0.0, 3.0
NODE, 3, 4.0, 2.0, 3.0
NODE, 4, 0.0, 2.0, 3.0
DIAP, 10, F, 1, 1, 2.0, 1000, 0, 0.0066
DMEM, 1, 10, 1, 2, 3
DMEM, 2, 10, 1, 3, 4
CONS, 1, 1, 1, 1, 1, 1, 1
CONS, 2, 1, 1, 1, 1, 1, 1
CONS, 3, 0, 0, 1, 1, 1, 1
CONS, 4, 0, 0, 1, 1, 1, 1
PLOD, 3, 0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0
PLOD, 4, 0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0
"""


class TestPanelEquilibrium(unittest.TestCase):

    def test_average_shear_flow_equals_load_over_width(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "panel.dat")
            with open(path, "w", encoding="utf-8") as f:
                f.write(PANEL)
            mdl, _txt = run_from_file(path)
        total_area = sum(m.area for m in mdl.dmems)
        integral = 0.0
        for m in mdl.dmems:
            sx, sy, sxy = (float(v) for v in m.stresses[:, 0])
            integral += wf.global_shear_stress(sx, sy, sxy, m.ex, m.ey, m.ez) * m.area * float(m.diap.t)
        # 10 kN on a 4 m wide panel gives 2.5 kN/m (2500 N/m).
        self.assertAlmostEqual(abs(integral / total_area), 2500.0, delta=1.0)


class TestBay(unittest.TestCase):

    GRIDS = [(0.0, "X1"), (0.91, "X2"), (1.82, "X3")]

    def test_finds_the_interval(self):
        self.assertEqual(_bay(1.0, self.GRIDS), ("X2", "X3", 1.82 - 0.91))

    def test_outside_the_grid_has_no_bay(self):
        self.assertIsNone(_bay(5.0, self.GRIDS))


class TestSchema(unittest.TestCase):

    def _project(self, floor):
        project = load_project_file(os.path.join(DATA, "practice_wood_single_story.project.json"))
        raw = project.to_dict()
        raw["design_checks"]["wood"]["floor_multipliers"] = floor
        return raw

    def test_round_trip(self):
        project = validate_project_dict(self._project([{"diaphragm": 10, "multiplier": 2.5}]))
        self.assertEqual(project.design_checks.wood.floor_multipliers[0].multiplier, 2.5)
        self.assertEqual(validate_project_dict(project.to_dict()).to_dict(), project.to_dict())

    def test_rejects_non_positive_multiplier(self):
        with self.assertRaises(ProjectSchemaError):
            validate_project_dict(self._project([{"diaphragm": 10, "multiplier": 0.0}]))

    def test_rejects_non_integer_diaphragm(self):
        with self.assertRaises(ProjectSchemaError):
            validate_project_dict(self._project([{"diaphragm": "A", "multiplier": 1.0}]))


if __name__ == "__main__":
    unittest.main()
