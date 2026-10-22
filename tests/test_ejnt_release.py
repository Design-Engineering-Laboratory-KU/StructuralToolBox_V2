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


def _efrc(txt):
    out = []
    for line in txt.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if parts[0] == "EFRC":
            out.append([float(v) for v in parts[3:]])
    return out


def _solve(lines):
    _, txt = run_from_lines(HEAD + lines)
    return _rows(txt, "REAC"), _rows(txt, "NDSP")


class TestEjntRelease(unittest.TestCase):

    W = 10.0
    L = 6.0

    # Propped cantilever (fixed i, pinned j) under a uniform load, Timoshenko:
    #   R_i = wL (5 + PHI) / (2 (4 + PHI)),  M_i = wL^2 / (2 (4 + PHI))
    # which reduces to 5wL/8 and wL^2/8 without shear deformation.
    def _propped(self, phi):
        wl = self.W * self.L
        r_i = wl * (5.0 + phi) / (2.0 * (4.0 + phi))
        return r_i, wl - r_i, self.W * self.L ** 2 / (2.0 * (4.0 + phi))

    def test_pinned_j_end_vertical_udl_matches_propped_cantilever(self):
        mdl, txt = run_from_lines(HEAD + BEAM + ["EJNT,1,,,0,0", "ELOD,1,0,1,0,0,-10,0,0,-10"])
        reac = _rows(txt, "REAC")
        r_i, r_j, m_i = self._propped(mdl.elms[0].PHIz)
        self.assertAlmostEqual(reac[(0, 1)][2], r_i, places=2)
        self.assertAlmostEqual(reac[(0, 2)][2], r_j, places=2)
        self.assertAlmostEqual(abs(reac[(0, 1)][4]), m_i, places=2)
        self.assertAlmostEqual(reac[(0, 2)][4], 0.0, places=6)

    def test_pinned_j_end_horizontal_udl_matches_propped_cantilever(self):
        mdl, txt = run_from_lines(HEAD + BEAM + ["EJNT,1,,,0,0", "ELOD,1,0,1,0,-10,0,0,-10,0"])
        reac = _rows(txt, "REAC")
        r_i, r_j, m_i = self._propped(mdl.elms[0].PHIy)
        self.assertAlmostEqual(reac[(0, 1)][1], r_i, places=2)
        self.assertAlmostEqual(reac[(0, 2)][1], r_j, places=2)
        self.assertAlmostEqual(abs(reac[(0, 1)][5]), m_i, places=2)
        self.assertAlmostEqual(reac[(0, 2)][5], 0.0, places=6)

    def test_pins_on_subdivided_member_match_single_element(self):
        # A simply supported deep timber beam split into short elements, with
        # the pins on the end elements only: shear deformation (large PHI on
        # short elements) must not change the result.
        def beam(n):
            lines = ["MATE,2,GL,12000,800,0,0,33", "SECT,2,B,2,0,120,330"]
            lines += ["NODE,%d,%.6f,0,0" % (i + 1, 5.0 * i / n) for i in range(n + 1)]
            lines += ["ELEM,%d,%d,%d,2,0" % (i + 1, i + 1, i + 2) for i in range(n)]
            if n == 1:
                lines += ["EJNT,1,10,10,10,10"]
            else:
                lines += ["EJNT,1,10,10,,", "EJNT,%d,,,10,10" % n]
            lines += ["CONS,1,1,1,1,1,0,0", "CONS,%d,0,1,1,0,0,0" % (n + 1)]
            lines += ["ELOD,%d,0,1,0,0,-2,0,0,-2" % (i + 1) for i in range(n)]
            _, txt = run_from_lines(lines)
            mmax = max(max(abs(v[4]), abs(v[10]), abs(v[12])) for v in _efrc(txt))
            return mmax
        self.assertAlmostEqual(beam(1), 6.25, places=2)
        self.assertAlmostEqual(beam(10), 6.25, places=2)

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
