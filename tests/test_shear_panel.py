"""Shear panel walls: rigid-body behaviour and equilibrium against hand results."""

import math
import os
import sys
import tempfile
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import parse_input, run_from_file  # puts classes/ on the import path

from classes.nd import Nd
from classes.wood_wall import WoodShearPanel

HEADER = """MATE, 1, Wood, 12000, 800, 0.0, 3e-06, 0
SECT, 1, S, 1, 0, 300.0, 300.0
"""


def _panel(corners, direction="X", k=1.0e6):
    nodes = [Nd(i + 1, *c) for i, c in enumerate(corners)]
    return WoodShearPanel(1, 1, "W", nodes[0], nodes[1], nodes[2], nodes[3], direction, k)


def _delta(panel, field):
    weights = panel.stiffness_weights()
    return sum(weights[3 * i + d] * field(n)[d] for i, n in enumerate(panel.nodes()) for d in range(3))


X_WALL = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 0.0, 3.0), (0.0, 0.0, 3.0)]
Y_WALL = [(1.0, 0.0, 0.0), (1.0, 2.0, 0.0), (1.0, 2.0, 3.0), (1.0, 0.0, 3.0)]
SKEW_WALL = [(0.0, 0.0, 0.0), (1.6, 1.2, 0.0), (1.6, 1.2, 3.0), (0.0, 0.0, 3.0)]
ROOF_PANEL = [(0.0, -0.455, 0.0), (0.0, 0.0, 0.0), (0.9, 0.0, 0.275), (0.9, -0.455, 0.275)]
TAPERED_WALL = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (1.5, 0.0, 3.0), (0.5, 0.0, 3.0)]


class TestKinematics(unittest.TestCase):

    def test_rigid_translation_has_no_deformation(self):
        for corners in (X_WALL, Y_WALL, SKEW_WALL, TAPERED_WALL, ROOF_PANEL):
            panel = _panel(corners)
            for t in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)):
                self.assertAlmostEqual(_delta(panel, lambda n: t), 0.0, places=12)

    def test_rigid_rotation_has_no_deformation(self):
        for corners in (X_WALL, Y_WALL, SKEW_WALL, TAPERED_WALL, ROOF_PANEL):
            panel = _panel(corners)
            for w in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)):
                def field(n):
                    return (w[1] * n.z - w[2] * n.y, w[2] * n.x - w[0] * n.z, w[0] * n.y - w[1] * n.x)

                self.assertAlmostEqual(_delta(panel, field), 0.0, places=12)

    def test_horizontal_drift_along_the_wall_is_the_deformation(self):
        panel = _panel(SKEW_WALL)
        c, s = 0.8, 0.6
        self.assertAlmostEqual(abs(_delta(panel, lambda n: (c * n.z, s * n.z, 0.0))), 3.0, places=9)

    def test_drift_across_the_wall_does_nothing(self):
        panel = _panel(SKEW_WALL)
        c, s = 0.8, 0.6
        self.assertAlmostEqual(_delta(panel, lambda n: (-s * n.z, c * n.z, 0.0)), 0.0, places=9)

    def test_direction_check(self):
        self.assertTrue(_panel(X_WALL, "X").direction_matches_wall())
        self.assertFalse(_panel(Y_WALL, "X").direction_matches_wall())
        self.assertTrue(_panel(Y_WALL, "Y").direction_matches_wall())


# One 2 m wide, 3 m high wall between two columns; the columns take almost no shear.
WALL_MODEL = HEADER + """NODE, 1, 0.0, 0.0, 0.0
NODE, 2, 2.0, 0.0, 0.0
NODE, 3, 2.0, 0.0, 3.0
NODE, 4, 0.0, 0.0, 3.0
ELEM, 1, 1, 4, 1, 0.0
ELEM, 2, 2, 3, 1, 0.0
ELEM, 3, 4, 3, 1, 0.0
EJNT, 1, 0, 0, 0, 0
EJNT, 2, 0, 0, 0, 0
CONS, 1, 1, 1, 1, 1, 1, 1
CONS, 2, 1, 1, 1, 1, 1, 1
CONS, 3, 0, 1, 0, 1, 0, 1
CONS, 4, 0, 1, 0, 1, 0, 1
WWLL, 1, W, 1, 2.0, 2.0, 3.0, 0, 0.0083333333, 1, 2, 3, 4, , 1
PLOD, 4, 0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0
"""


def _solve(text):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "m.dat")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        mdl, _txt = run_from_file(path)
    return mdl


class TestEquilibrium(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mdl = _solve(WALL_MODEL)

    def _reaction(self, node_id, dof):
        return float(self.mdl.nodes_by_id[node_id].reacts[0, dof]) * 1.0e-3

    def test_vertical_reactions_carry_the_overturning_couple(self):
        expected = 10.0 * 3.0 / 2.0
        self.assertAlmostEqual(abs(self._reaction(1, 2)), expected, delta=0.05)
        self.assertAlmostEqual(abs(self._reaction(2, 2)), expected, delta=0.05)
        self.assertAlmostEqual(self._reaction(1, 2) + self._reaction(2, 2), 0.0, places=6)

    def test_windward_column_is_in_tension(self):
        # A push towards +X lifts the column on the -X side, so its support pulls down.
        self.assertLess(self._reaction(1, 2), 0.0)
        self.assertGreater(self._reaction(2, 2), 0.0)

    def test_columns_get_the_couple_as_axial_force(self):
        axial = float(self.mdl.FindElemFromEid(1).forces[0, 0]) * 1.0e-3
        self.assertAlmostEqual(abs(axial), 15.0, delta=0.05)

    def test_wall_shear_equals_the_applied_force(self):
        force = self.mdl.wshears[0].shear_force(0) * 1.0e-3
        self.assertAlmostEqual(abs(force), 10.0, delta=0.05)

    def test_drift_includes_the_axial_deformation_of_columns(self):
        panel = self.mdl.wshears[0]
        drift = float(self.mdl.nodes_by_id[4].disps[0, 0])
        shear_only = 10000.0 / panel.k
        ea = 12000.0e6 * 0.3 * 0.3
        axial = 2.0 * (15000.0 * 3.0 / ea) * 3.0 / 2.0
        self.assertAlmostEqual(drift, shear_only + axial, delta=abs(shear_only) * 0.01)


class TestInputWarnings(unittest.TestCase):

    def test_direction_mismatch_warns_but_still_loads(self):
        text = WALL_MODEL.replace(", 3.0, 0, 0.0083333333", ", 3.0, 1, 0.0083333333")
        mdl = parse_input(text.splitlines())
        self.assertTrue(any("differs from the wall line" in w for w in mdl.input_warnings))

    def test_free_corner_warns(self):
        text = WALL_MODEL.replace("ELEM, 2, 2, 3, 1, 0.0\n", "").replace("ELEM, 3, 4, 3, 1, 0.0\n", "")
        text = text.replace("CONS, 2, 1, 1, 1, 1, 1, 1\n", "").replace("EJNT, 2, 0, 0, 0, 0\n", "")
        mdl = parse_input(text.splitlines())
        self.assertTrue(any("no member or vertical support" in w for w in mdl.input_warnings))

    def test_matching_wall_has_no_panel_warning(self):
        mdl = parse_input(WALL_MODEL.splitlines())
        self.assertFalse(any("WOOD_RATED_WALL" in w and ("differs from the wall line" in w or "no member" in w) for w in mdl.input_warnings))


if __name__ == "__main__":
    unittest.main()
