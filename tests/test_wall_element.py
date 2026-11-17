"""EJNT axial end springs and the ASTIM-style wall element (WWLL MODEL=3)."""

import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import parse_input  # puts classes/ on the import path
from stb_engine.run import solve_model

from classes.io import RegisterInputData

E_WOOD = 12000.0  # N/mm2

BAR = """MATE, 1, Wood, 12000, 800, 0.0, 0.0, 0
SECT, 1, C, 1, 0, 105.0, 105.0
NODE, 1, 0.0, 0.0, 0.0
NODE, 2, 0.0, 0.0, 2.5
ELEM, 1, 1, 2, 1, 0
EJNT, 1, , , , , {springs}
CONS, 1, 1, 1, 1, 1, 1, 1
CONS, 2, 1, 1, 0, 1, 1, 1
PLOD, 2, 1, 0.0, 0.0, -10.0, 0.0, 0.0, 0.0
"""

# One bay: wall between columns on Y=0, a stiff beam on top, loads at the top corners.
FRAME = """MATE, 1, Wood, 12000, 800, 0.0, 0.0, 0
MATE, 2, Ply, 2500, 392, 0.0, 0.0, 0
SECT, 1, C, 1, 0, 105.0, 105.0
SECT, 2, B, 1, 0, 120.0, 3000.0
NODE, 1, 0.0, 0.0, 0.0
NODE, 2, 0.91, 0.0, 0.0
NODE, 3, 0.91, 0.0, 2.94
NODE, 4, 0.0, 0.0, 2.94
ELEM, 1, 1, 4, 1, 0
ELEM, 2, 2, 3, 1, 0
ELEM, 3, 4, 3, 2, 0
EJNT, 1, 0, 0, 0, 0{axial}
EJNT, 2, 0, 0, 0, 0{axial}
CONS, 1, 1, 1, 1, 1, 1, 1
CONS, 2, 1, 1, 1, 1, 1, 1
CONS, 3, 0, 1, 0, 1, 0, 1
CONS, 4, 0, 1, 0, 1, 0, 1
WWLL, 1, W, {model}, {mult}, , , 0, 0.0066666667, 1, 2, 3, 4, , 1{panel}
PLOD, 4, 1, 10.0, 0.0, -5.0, 0.0, 0.0, 0.0
PLOD, 3, 1, 0.0, 0.0, -5.0, 0.0, 0.0, 0.0
"""

# Report 6.1.6 of the ASTIM sample: Z2-Z3 Y1 X2-X3, 910 x 2940 mm, t = 9 mm, K = 391 N/mm.
ASTIM_K = 391.0
ASTIM_MULT = ASTIM_K / (1.96 * 0.91 * 150.0 / 2.94)


def _solve(text):
    mdl = parse_input(text.splitlines())
    solve_model(mdl)
    return mdl


def _frame(model=3, axial="", mult=ASTIM_MULT, panel=", 2, 9"):
    return _solve(FRAME.format(model=model, axial=axial, mult=mult, panel=panel if model == 3 else ""))


def _top_drift(mdl):
    nodes = {n.id: n for n in mdl.nds}
    return 0.5 * (float(nodes[3].disps[0, 0]) + float(nodes[4].disps[0, 0]))


class TestAxialSprings(unittest.TestCase):

    def _shortening(self, springs):
        mdl = _solve(BAR.format(springs=springs))
        return -float(next(n for n in mdl.nds if n.id == 2).disps[2, 0])

    def test_springs_act_in_series_with_the_member(self):
        ea = E_WOOD * 105.0 * 105.0  # N
        bar = 10.0e3 * 2500.0 / ea  # mm
        springs = 10.0e3 / 5.0e3 + 10.0e3 / 20.0e3  # mm, Ni = 5 kN/mm, Nj = 20 kN/mm
        self.assertAlmostEqual(self._shortening("5, 20") * 1e3, bar + springs, places=6)

    def test_blank_springs_are_rigid(self):
        ea = E_WOOD * 105.0 * 105.0
        self.assertAlmostEqual(self._shortening(",") * 1e3, 10.0e3 * 2500.0 / ea, places=6)

    def test_springs_must_be_positive(self):
        with self.assertRaises(Exception):
            _solve(BAR.format(springs="0, 5"))

    def test_springs_are_written_back(self):
        mdl = parse_input(BAR.format(springs="5, 20").splitlines())
        line = next(l for l in RegisterInputData(mdl).splitlines() if l.startswith("EJNT"))
        values = [v.strip() for v in line.split(",")]
        self.assertEqual([float(values[6]), float(values[7])], [5.0, 20.0])


class TestWallElementSection(unittest.TestCase):

    def test_section_matches_the_astim_table(self):
        mdl = parse_input(FRAME.format(model=3, axial="", mult=ASTIM_MULT, panel=", 2, 9").splitlines())
        wall = mdl.wwalls[0]
        mat = next(m for m in mdl.mats if m.id == 2)
        area, inertia, shear_area, _alpha = wall.wall_element_properties(mat)
        self.assertAlmostEqual(wall.k_n_per_m * 1e-3, ASTIM_K, places=3)
        self.assertAlmostEqual(area * 1e6, 8190.0, places=3)
        self.assertAlmostEqual(inertia * 1e12 / 5.3398e8, 1.0, delta=2e-3)
        self.assertAlmostEqual(shear_area * 1e6 / 7738.0, 1.0, delta=2e-3)

    def test_needs_panel_material_and_thickness(self):
        with self.assertRaises(Exception):
            parse_input(FRAME.format(model=3, axial="", mult=2.0, panel="").splitlines())

    def test_fixed_ended_wall_column_has_the_rated_stiffness(self):
        mdl = parse_input(FRAME.format(model=3, axial="", mult=ASTIM_MULT, panel=", 2, 9").splitlines())
        wall = mdl.wwalls[0]
        mat = next(m for m in mdl.mats if m.id == 2)
        _a, inertia, shear_area, _alpha = wall.wall_element_properties(mat)
        h = wall.height
        k = 1.0 / (h ** 3 / (12.0 * mat.E * inertia) + h / (mat.G * shear_area))
        self.assertAlmostEqual(k / wall.k_n_per_m, 1.0, places=9)


class TestWallElementFrame(unittest.TestCase):

    def test_wall_takes_the_storey_shear_and_the_model_is_in_equilibrium(self):
        mdl = _frame()
        element = mdl.wwelems[0]
        self.assertAlmostEqual(element.shear_force(0) * 1e-3, 10.0, places=6)
        reactions = [sum(float(c.nd.reacts[0, k]) for c in mdl.cons) * 1e-3 for k in range(3)]
        self.assertAlmostEqual(reactions[0], -10.0, places=6)
        self.assertAlmostEqual(reactions[2], 10.0, places=6)

    def test_drift_is_close_to_the_rated_stiffness_with_stiff_columns(self):
        drift = _top_drift(_frame())
        rated = 10.0e3 / (ASTIM_K * 1e3)
        # The column shortening adds a little; the wall itself follows K.
        self.assertGreater(drift, rated)
        self.assertLess(drift, 1.10 * rated)

    def test_sign_matches_the_shear_panel(self):
        panel = _frame(model=1)
        element = _frame()
        self.assertGreater(panel.wshears[0].shear_force(0) * element.wwelems[0].shear_force(0), 0.0)

    def test_axially_free_columns_leave_the_vertical_load_to_the_wall(self):
        mdl = _frame(axial=", 0.01, 0.01")
        element = mdl.wwelems[0]
        self.assertAlmostEqual(element.axial_force(0) * 1e-3, -10.0, delta=0.05)
        columns = [e for e in mdl.elms if e.id in (1, 2)]
        for column in columns:
            self.assertLess(abs(float(column.forces[0, 0])) * 1e-3, 0.2)

    def test_generated_items_are_not_written_back(self):
        mdl = parse_input(FRAME.format(model=3, axial="", mult=ASTIM_MULT, panel=", 2, 9").splitlines())
        text = RegisterInputData(mdl)
        node_lines = [l for l in text.splitlines() if l.startswith("NODE")]
        elem_lines = [l for l in text.splitlines() if l.startswith("ELEM")]
        self.assertEqual(len(node_lines), 4)
        self.assertEqual(len(elem_lines), 3)
        wall_line = next(l for l in text.splitlines() if l.startswith("WWLL"))
        values = [v.strip() for v in wall_line.split(",")]
        self.assertEqual(values[3], "3")
        self.assertEqual((int(values[15]), float(values[16])), (2, 9.0))
        again = parse_input(text.splitlines())
        self.assertEqual(len(again.wwelems), 1)

    def test_wood_check_reads_the_wall_element_shear(self):
        from stb_checks.wood import _wall_shear_for_load_case

        mdl = _frame()
        warnings = []
        q = _wall_shear_for_load_case(mdl, mdl.wwalls[0], 1, {1: 0}, warnings)
        self.assertAlmostEqual(abs(q), 10.0, places=6)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
