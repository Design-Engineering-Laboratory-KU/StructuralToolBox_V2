import os
import sys
import unittest

import numpy as np

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_lines
from classes.io import RegisterInputData
from classes.ld import diagram_wsegs, point_fixed_end_forces, segment_fixed_end_forces

HEAD = [
    "MATE,1,STEEL,205000,79000,77,0,235",
    "SECT,1,H,1,2,300,150,6.5,9",
]

FIX = "1,1,1,1,1,1"
PIN = "1,1,1,1,0,0"


def _rows(txt, tag):
    out = []
    for line in txt.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if parts[0] == tag:
            out.append([float(v) for v in parts[1:]])
    return out


def _node(mdl, nid):
    return [n for n in mdl.nds if n.id == nid][0]


def _elem(mdl, eid):
    return [e for e in mdl.elms if e.id == eid][0]


def _beam(p0, p1, t, load, glob=1, beta=0.0, cons=(FIX, PIN), lc_lines=()):
    """One member 1-2 carrying EPLD at t, and the reference with an extra node 3
    at t (members 1-3, 3-2) carrying the same force as PLOD at node 3."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    pm = p0 + t * (p1 - p0)

    def node(nid, p):
        return "NODE,%d,%r,%r,%r" % (nid, float(p[0]), float(p[1]), float(p[2]))

    common = HEAD + [
        node(1, p0), node(2, p1),
        "CONS,1," + cons[0], "CONS,2," + cons[1],
    ] + list(lc_lines)
    px, py, pz = load
    epld = common + [
        "ELEM,1,1,2,1,%r" % beta,
        "EPLD,1,0,%d,%r,%r,%r,%r" % (glob, px, py, pz, t),
    ]
    ref = common + [
        node(3, pm),
        "ELEM,1,1,3,1,%r" % beta,
        "ELEM,2,3,2,1,%r" % beta,
    ]
    return epld, ref


class PointFixedEndForceTests(unittest.TestCase):

    def test_limit_of_a_narrow_segment(self):
        L = 4.0
        p = np.array([3.0, -7.0, 11.0])
        for t in (0.0, 0.3, 0.5, 1.0):
            for phi in (0.0, 0.4):
                exact = point_fixed_end_forces(L, t, p, phi, phi)
                h = 1e-8
                t0, t1 = (t, t + h) if t < 1.0 else (t - h, t)
                w = np.concatenate([p, p]) / (h * L)
                narrow = segment_fixed_end_forces(L, t0, t1, w, phi, phi)
                np.testing.assert_allclose(exact, narrow, rtol=1e-5, atol=1e-5)

    def test_end_points_load_the_nodes(self):
        p = np.array([1.0, 2.0, 3.0])
        f0 = point_fixed_end_forces(5.0, 0.0, p)
        np.testing.assert_allclose(f0[[0, 1, 2]], p)
        np.testing.assert_allclose(np.delete(f0, [0, 1, 2]), 0.0, atol=1e-14)
        f1 = point_fixed_end_forces(5.0, 1.0, p)
        np.testing.assert_allclose(f1[[6, 7, 8]], p)
        np.testing.assert_allclose(np.delete(f1, [6, 7, 8]), 0.0, atol=1e-14)


class EpldSolveTests(unittest.TestCase):

    def _compare(self, epld_lines, ref_lines, ref_load, t):
        mdl, txt = run_from_lines(epld_lines)
        px, py, pz = ref_load
        ref, ref_txt = run_from_lines(ref_lines + ["PLOD,3,0,%r,%r,%r,0,0,0" % (px, py, pz)])

        for nid in (1, 2):
            np.testing.assert_allclose(
                np.asarray(_node(mdl, nid).disps, float),
                np.asarray(_node(ref, nid).disps, float),
                rtol=1e-9, atol=1e-12)
            np.testing.assert_allclose(
                np.asarray(_node(mdl, nid).reacts, float),
                np.asarray(_node(ref, nid).reacts, float),
                rtol=1e-9, atol=1e-6)

        # End forces at i and j equal those of the split reference members.
        f = _rows(txt, "EFRC")[0]
        fa = _rows(ref_txt, "EFRC")[0]
        fb = _rows(ref_txt, "EFRC")[1]
        np.testing.assert_allclose(f[2:8], fa[2:8], rtol=1e-7, atol=1e-6)
        np.testing.assert_allclose(f[8:14], fb[8:14], rtol=1e-7, atol=1e-6)
        return txt, mdl, ref_txt

    def test_horizontal_beam_global_vertical_load(self):
        epld, ref = _beam([0, 0, 0], [6, 0, 0], 0.3, (0.0, 0.0, -20.0))
        self._compare(epld, ref, (0.0, 0.0, -20.0), 0.3)

    def test_skew_member_global_load_with_all_components(self):
        load = (4.0, -6.0, -15.0)
        epld, ref = _beam([0, 0, 0], [4, 3, 2], 0.7, load, beta=20.0)
        self._compare(epld, ref, load, 0.7)

    def test_local_load_matches_global_equivalent(self):
        load_local = (2.0, 5.0, -9.0)
        epld, _ = _beam([0, 0, 0], [3, 4, 0], 0.4, load_local, glob=0, beta=30.0)
        mdl, txt = run_from_lines(epld)
        R = _elem(mdl, 1).tm[0:3, 0:3]
        load_global = [float(v) for v in R.T @ np.array(load_local)]
        epld_g, ref = _beam([0, 0, 0], [3, 4, 0], 0.4, tuple(load_global), glob=1, beta=30.0)
        self._compare(epld_g, ref, tuple(load_global), 0.4)
        mdl_g, _ = run_from_lines(epld_g)
        for nid in (1, 2):
            np.testing.assert_allclose(
                np.asarray(_node(mdl, nid).reacts, float),
                np.asarray(_node(mdl_g, nid).reacts, float),
                rtol=1e-9, atol=1e-6)

    def test_mid_span_moment_and_diagram_segment(self):
        # Simply supported beam (pins at both ends, torsion fixed at node 1).
        L, t, P = 6.0, 0.25, -12.0
        epld, ref = _beam([0, 0, 0], [L, 0, 0], t, (0.0, 0.0, P),
                          cons=("1,1,1,1,0,0", "0,1,1,0,0,0"))
        txt, mdl, _ = self._compare(epld, ref, (0.0, 0.0, P), t)
        # Myc at mid-span: reaction at j times L/2 (load lies left of the centre).
        a = t * L
        r_j = -P * a / L
        myc = _rows(txt, "EFRC")[0][14]
        self.assertAlmostEqual(abs(myc), abs(r_j * L / 2.0), places=6)

        ewld = _rows(txt, "EWLD")
        self.assertEqual(len(ewld), 1)
        lc, eid, t0, t1, wx, wy, wz = ewld[0][:7]
        self.assertEqual((t0, t1), (t, t))
        self.assertAlmostEqual(wz, P, places=6)
        self.assertIn("T0 = T1: concentrated load", txt)
        echo = RegisterInputData(mdl)
        self.assertIn("ELEMENT POINT LOAD(EPLD)", echo)
        epld = [r for r in _rows(echo, "EPLD")]
        self.assertEqual(len(epld), 1)
        self.assertEqual(epld[0][:3], [1, 0, 1])
        self.assertAlmostEqual(epld[0][5], P, places=2)
        self.assertAlmostEqual(epld[0][6], t)

    def test_combination_scales_point_load(self):
        lines, _ = _beam([0, 0, 0], [5, 0, 0], 0.5, (0.0, 0.0, -10.0))
        mdl, txt = run_from_lines(lines + ["LCMB,1,C1,1.5,0"])
        r = _rows(txt, "REAC")
        r0 = sum(row[4] for row in r if int(row[0]) == 0)
        r1 = sum(row[4] for row in r if int(row[0]) == 1)
        self.assertAlmostEqual(r0, 10.0, places=4)
        self.assertAlmostEqual(r1, 15.0, places=4)

    def test_point_at_member_end(self):
        epld, ref = _beam([0, 0, 0], [4, 0, 0], 1.0, (0.0, 0.0, -8.0))
        mdl, txt = run_from_lines(epld)
        r = _rows(txt, "REAC")
        self.assertAlmostEqual(sum(row[4] for row in r), 8.0, places=6)
        segs = diagram_wsegs(_elem(mdl, 1), 0)
        self.assertEqual(segs[0][0:2], [1.0, 1.0])

    def test_position_out_of_range_is_rejected(self):
        lines, _ = _beam([0, 0, 0], [4, 0, 0], 0.5, (0.0, 0.0, -8.0))
        bad = [l if not l.startswith("EPLD") else "EPLD,1,0,1,0,0,-8,1.5" for l in lines]
        with self.assertRaises(Exception):
            run_from_lines(bad)


if __name__ == "__main__":
    unittest.main()
