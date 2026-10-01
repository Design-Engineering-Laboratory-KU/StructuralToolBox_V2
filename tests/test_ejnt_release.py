import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_lines
from stb_engine.errors import StbParseError, StbSolveError

HEAD = [
    "MATE,1,STEEL,205000,79000,0,0,235",
    "SECT,1,H,1,2,300,150,6.5,9",
]

BEAM = [
    "NODE,1,0,0,0",
    "NODE,2,6,0,0",
    "ELEM,1,1,2,1,0",
    "CONS,1,1,1,1,1,1,1",
    "CONS,2,1,1,1,1,1,1",
]

COLUMN = [
    "NODE,1,0,0,0",
    "NODE,2,0,0,3",
    "ELEM,1,1,2,1,0",
    "CONS,1,1,1,1,1,1,1",
    "PLOD,2,0,10,0,0,0,0,0",
]


def _rows(txt, tag):
    rows = {}
    for line in txt.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if parts[0] == tag:
            rows[(int(parts[1]), int(parts[2]))] = [float(v) for v in parts[3:9]]
    return rows


def _solve(lines):
    _, txt = run_from_lines(HEAD + lines)
    return _rows(txt, "REAC"), _rows(txt, "NDSP")


class TestEjntRelease(unittest.TestCase):

    W = 10.0
    L = 6.0

    def test_pinned_j_end_vertical_udl_matches_propped_cantilever(self):
        reac, _ = _solve(BEAM + ["EJNT,1,,,0,0", "ELOD,1,0,1,0,0,-10,0,0,-10"])
        self.assertAlmostEqual(reac[(0, 1)][2], 5 * self.W * self.L / 8, places=6)
        self.assertAlmostEqual(reac[(0, 2)][2], 3 * self.W * self.L / 8, places=6)
        self.assertAlmostEqual(abs(reac[(0, 1)][4]), self.W * self.L ** 2 / 8, places=6)
        self.assertAlmostEqual(reac[(0, 2)][4], 0.0, places=6)

    def test_pinned_j_end_horizontal_udl_matches_propped_cantilever(self):
        reac, _ = _solve(BEAM + ["EJNT,1,,,0,0", "ELOD,1,0,1,0,-10,0,0,-10,0"])
        self.assertAlmostEqual(reac[(0, 1)][1], 5 * self.W * self.L / 8, places=6)
        self.assertAlmostEqual(reac[(0, 2)][1], 3 * self.W * self.L / 8, places=6)
        self.assertAlmostEqual(abs(reac[(0, 1)][5]), self.W * self.L ** 2 / 8, places=6)
        self.assertAlmostEqual(reac[(0, 2)][5], 0.0, places=6)

    def test_pinned_both_ends_carries_no_end_moment(self):
        reac, _ = _solve(BEAM + ["EJNT,1,0,0,0,0", "ELOD,1,0,1,0,0,-10,0,0,-10"])
        for node in (1, 2):
            self.assertAlmostEqual(reac[(0, node)][2], self.W * self.L / 2, places=6)
            self.assertAlmostEqual(reac[(0, node)][4], 0.0, places=6)

    def test_rzi_is_read_from_its_own_field(self):
        # Ryi pinned, Rzi blank (rigid): horizontal bending must stay fixed-fixed.
        reac, _ = _solve(BEAM + ["EJNT,1,0,,0,", "ELOD,1,0,1,0,-10,0,0,-10,0"])
        self.assertAlmostEqual(abs(reac[(0, 1)][5]), self.W * self.L ** 2 / 12, places=6)

    def test_end_spring_adds_rotation_flexibility(self):
        E, H, B, tw, tf = 205000e6, 0.3, 0.15, 0.0065, 0.009
        iy = (B * H ** 3 - (B - tw) * (H - 2 * tf) ** 3) / 12.0
        spring_knm = E * iy * 6.0 / 3.0 / 1e3
        _, rigid = _solve(COLUMN)
        _, sprung = _solve(COLUMN + ["EJNT,1,%.9g,%.9g,," % (spring_knm, spring_knm)])
        added = sprung[(0, 2)][0] - rigid[(0, 2)][0]
        expected = 10e3 * 3.0 ** 2 / (spring_knm * 1e3)
        self.assertAlmostEqual(added / expected, 1.0, delta=0.03)

    def test_negative_spring_is_rejected(self):
        with self.assertRaises((StbParseError, StbSolveError, ValueError)):
            _solve(BEAM + ["EJNT,1,-1,,,", "ELOD,1,0,1,0,0,-10,0,0,-10"])


if __name__ == "__main__":
    unittest.main()
