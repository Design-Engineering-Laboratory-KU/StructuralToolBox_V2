import math
import os
import sys
import unittest

import numpy as np

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_lines
from stb_engine.errors import StbParseError
from classes.ld import segment_fixed_end_forces, segment_linear_equivalent, diagram_wsegs

# Normal material (shear deformation active).
HEAD = [
    "MATE,1,STEEL,205000,79000,77,0,235",
    "SECT,1,H,1,2,300,150,6.5,9",
]
# Shear deformation made negligible (huge G): a member split at the load ends is
# an exact reference even for linearly varying (non-uniform) partial loads,
# because the sub-members' own consistent fixed-end forces are then exact.
HEAD_EULER = [
    "MATE,1,STEEL,205000,1e12,77,0,235",
    "SECT,1,H,1,2,300,150,6.5,9",
]

FIX = "1,1,1,1,1,1"
PROP = "1,1,1,0,0,0"


def _fmt(v):
    return repr(float(v))


def _eld(eid, lc, glob, w6, t=None):
    s = "ELOD,%d,%d,%d," % (eid, lc, glob) + ",".join(_fmt(v) for v in w6)
    if t is not None:
        s += ",%s,%s" % (_fmt(t[0]), _fmt(t[1]))
    return s


def _old_fef(L, lds):
    """Closed-form full-length fixed-end forces (copy of Solve.CreateLoadMx)."""
    f = np.zeros(12)
    f[0] = L / 6.0 * (2.0 * lds[0] + 1.0 * lds[3])
    f[1] = L / 20.0 * (7.0 * lds[1] + 3.0 * lds[4])
    f[2] = L / 20.0 * (7.0 * lds[2] + 3.0 * lds[5])
    f[4] = -L ** 2 / 60.0 * (3.0 * lds[2] + 2.0 * lds[5])
    f[5] = L ** 2 / 60.0 * (3.0 * lds[1] + 2.0 * lds[4])
    f[6] = L / 6.0 * (1.0 * lds[0] + 2.0 * lds[3])
    f[7] = L / 20.0 * (3.0 * lds[1] + 7.0 * lds[4])
    f[8] = L / 20.0 * (3.0 * lds[2] + 7.0 * lds[5])
    f[10] = L ** 2 / 60.0 * (2.0 * lds[2] + 3.0 * lds[5])
    f[11] = -L ** 2 / 60.0 * (2.0 * lds[1] + 3.0 * lds[4])
    return f


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


def _result_vector(mdl, nids):
    """Displacements and reactions of the given nodes, all load cases."""
    out = []
    for nid in nids:
        n = _node(mdl, nid)
        out.append(np.asarray(n.disps, dtype=float).T.reshape(-1))
        if n.reacts is not None:
            out.append(np.asarray(n.reacts, dtype=float).reshape(-1))
    return np.concatenate(out)


def _rel_diff(a, b):
    return float(np.max(np.abs(a - b)) / max(np.max(np.abs(b)), 1e-300))


# ----------------------------------------------------------------------
# Section-force relations of the spec ("diagram convention")
# ----------------------------------------------------------------------
def _seg_int(seg, x, power):
    """int_0^x (x - xi)^power w(xi) dxi for each of wx, wy, wz of a segment
    ([t0, t1, wxi, wyi, wzi, wxj, wyj, wzj], loads in any force unit, L given
    through seg[8])."""
    t0, t1, L = seg[0], seg[1], seg[8]
    a, b = t0 * L, t1 * L
    u = min(b, x)
    if u <= a:
        return np.zeros(3)
    wa = np.array(seg[2:5])
    wb = np.array(seg[5:8])
    # 3-point Gauss: exact for the (linear w) x (power <= 1) polynomial
    gx = np.array([-math.sqrt(0.6), 0.0, math.sqrt(0.6)])
    gw = np.array([5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0])
    xs = 0.5 * (a + u) + 0.5 * (u - a) * gx
    ws = 0.5 * (u - a) * gw
    res = np.zeros(3)
    for xi, wt in zip(xs, ws):
        w = wa + (wb - wa) * (xi - a) / (b - a)
        res += wt * (x - xi) ** power * w
    return res


def _section_forces(f, L, segs, x):
    """N, Qy, Qz, My, Mz at x from the 14 EFRC values and diagram segments."""
    segs = [list(s) + [L] for s in segs]
    i0 = sum((_seg_int(s, x, 0) for s in segs), np.zeros(3))
    i1 = sum((_seg_int(s, x, 1) for s in segs), np.zeros(3))
    n = f[0] - i0[0]
    qy = f[1] + i0[1]
    qz = f[2] + i0[2]
    my = f[4] + f[2] * x + i1[2]
    mz = f[5] - f[1] * x - i1[1]
    return np.array([n, qy, qz, my, mz])


# ----------------------------------------------------------------------
# Model builders
# ----------------------------------------------------------------------
class Case:
    """One member i->j with supports, optional pin and a list of load cases.

    loads: {lc: [(glob, w6_kN, (t0, t1) or None), ...]}
    """

    def __init__(self, p0, p1, loads, beta=0.0, pin=False, cons_j=PROP):
        self.p0, self.p1, self.loads, self.beta = p0, p1, loads, beta
        self.pin, self.cons_j = pin, cons_j

    def _model(self, split):
        """split: None for the partial-load model, else sorted t breakpoints."""
        p0, p1 = np.array(self.p0, float), np.array(self.p1, float)
        ts = [0.0] + (list(split) if split else []) + [1.0]
        lines = []
        for k, t in enumerate(ts):
            nid = 1 if k == 0 else (2 if k == len(ts) - 1 else 100 + k)
            p = p0 + (p1 - p0) * t
            lines.append("NODE,%d,%s,%s,%s" % (nid, _fmt(p[0]), _fmt(p[1]), _fmt(p[2])))
        nids = [1] + [100 + k for k in range(1, len(ts) - 1)] + [2]
        for k in range(len(ts) - 1):
            lines.append("ELEM,%d,%d,%d,1,%s" % (k + 1, nids[k], nids[k + 1], _fmt(self.beta)))
        lines.append("CONS,1," + FIX)
        lines.append("CONS,2," + self.cons_j)
        if self.pin:
            lines.append("EJNT,1,0,0,,")
        for lc, items in self.loads.items():
            for glob, w6, t in items:
                if split is None:
                    lines.append(_eld(1, lc, glob, w6, t))
                    continue
                t0, t1 = t if t is not None else (0.0, 1.0)
                wa, wb = np.array(w6[:3]), np.array(w6[3:])
                for k in range(len(ts) - 1):
                    p, q = ts[k], ts[k + 1]
                    if p >= t0 - 1e-12 and q <= t1 + 1e-12:
                        wp = wa + (wb - wa) * (p - t0) / (t1 - t0)
                        wq = wa + (wb - wa) * (q - t0) / (t1 - t0)
                        lines.append(_eld(k + 1, lc, glob, list(wp) + list(wq)))
        return lines

    def breakpoints(self, nsub=0):
        pts = set()
        for items in self.loads.values():
            for _, _, t in items:
                if t is not None:
                    pts.update(t)
        pts.update(k / nsub for k in range(1, nsub))
        return sorted(p for p in pts if 1e-12 < p < 1 - 1e-12)

    def partial(self, head=HEAD):
        return run_from_lines(head + self._model(None))

    def reference(self, head=HEAD, nsub=0):
        """Member split at the load ends (and, optionally, into nsub equal parts)."""
        return run_from_lines(head + self._model(self.breakpoints(nsub)))


def _cases():
    cases = {}
    cases["horizontal_all_components"] = Case(
        (0, 0, 0), (6, 0, 0),
        {0: [(0, [0, 0, -10, 0, 0, -4], (0.2, 0.4))],
         1: [(0, [0, 7, 0, 0, -3, 0], (0.1, 0.9))],
         2: [(0, [5, 0, 0, 2, 0, 0], (0.3, 0.8))],
         3: [(1, [1.5, -2.0, -6.0, 0.5, 3.0, -1.0], (0.25, 0.65))]})
    cases["triangle_two_segments"] = Case(
        (0, 0, 0), (8, 0, 0),
        {0: [(0, [0, 0, 0, 0, 0, -12], (0.2, 0.5)),
             (0, [0, 0, -12, 0, 0, 0], (0.5, 0.8))],
         1: [(0, [0, 0, 0, 0, 6, 0], (0.0, 0.5)),
             (0, [0, 6, 0, 0, 0, 0], (0.5, 1.0))]})
    cases["sloped"] = Case(
        (0, 0, 0), (4, 3, 2),
        {0: [(0, [1, 2, -3, 2, 1, -5], (0.2, 0.4))],
         1: [(1, [0, 0, -10, 0, 0, -10], (0.3, 0.7))],
         2: [(1, [3, -4, 0, -2, 5, -8], (0.15, 0.55))]},
        beta=20.0)
    cases["column_up"] = Case(
        (0, 0, 0), (0, 0, 3.5),
        {0: [(0, [2, -6, 3, 1, -2, 5], (0.2, 0.6))],
         1: [(1, [4, 5, -2, 1, 0, 7], (0.4, 0.9))]},
        beta=25.0)
    cases["column_down"] = Case(
        (0, 0, 3.5), (0, 0, 0),
        {0: [(0, [2, -6, 3, 1, -2, 5], (0.2, 0.6))],
         1: [(1, [4, 5, -2, 1, 0, 7], (0.4, 0.9))]},
        beta=-15.0)
    cases["pinned_i_end"] = Case(
        (0, 0, 0), (6, 0, 0),
        {0: [(0, [0, 0, -10, 0, 0, -10], (0.2, 0.4))],
         1: [(0, [0, 8, 0, 0, 3, 0], (0.5, 0.95))]},
        pin=True)
    return cases


def _uniform_cases():
    """Uniform partial loads (Wi = Wj on the segment): the split model with
    full-length uniform sub-member loads is exact for any shear stiffness."""
    cases = {}
    cases["horizontal_all_components"] = Case(
        (0, 0, 0), (6, 0, 0),
        {0: [(0, [0, 0, -10, 0, 0, -10], (0.2, 0.4))],
         1: [(0, [0, 7, 0, 0, 7, 0], (0.1, 0.9))],
         2: [(0, [5, 0, 0, 5, 0, 0], (0.3, 0.8))],
         3: [(1, [1.5, -2.0, -6.0, 1.5, -2.0, -6.0], (0.25, 0.65))]})
    cases["sloped"] = Case(
        (0, 0, 0), (4, 3, 2),
        {0: [(0, [1, 2, -3, 1, 2, -3], (0.2, 0.4))],
         1: [(1, [3, -4, -8, 3, -4, -8], (0.15, 0.55))]},
        beta=20.0)
    cases["column_up"] = Case(
        (0, 0, 0), (0, 0, 3.5),
        {0: [(0, [2, -6, 3, 2, -6, 3], (0.2, 0.6))],
         1: [(1, [4, 5, -2, 4, 5, -2], (0.4, 0.9))]},
        beta=25.0)
    cases["column_down"] = Case(
        (0, 0, 3.5), (0, 0, 0),
        {0: [(0, [2, -6, 3, 2, -6, 3], (0.2, 0.6))],
         1: [(1, [4, 5, -2, 4, 5, -2], (0.4, 0.9))]},
        beta=-15.0)
    cases["pinned_i_end"] = Case(
        (0, 0, 0), (6, 0, 0),
        {0: [(0, [0, 0, -10, 0, 0, -10], (0.2, 0.4))],
         1: [(0, [0, 8, 0, 0, 8, 0], (0.5, 0.95))]},
        pin=True)
    cases["pinned_i_end_fixed_j"] = Case(
        (0, 0, 0), (6, 0, 0),
        {0: [(0, [0, 0, -10, 0, 0, -10], (0.3, 0.6))],
         1: [(0, [0, 8, 0, 0, 8, 0], (0.1, 0.5))]},
        pin=True, cons_j=FIX)
    cases["deep_short_member"] = Case(
        (0, 0, 0), (1.5, 0, 0),
        {0: [(0, [0, 0, -10, 0, 0, -10], (0.2, 0.7))],
         1: [(0, [0, 8, 0, 0, 8, 0], (0.1, 0.5))]})
    return cases


class TestFixedEndForceHelper(unittest.TestCase):

    def test_full_length_equals_closed_form(self):
        rng = np.random.RandomState(7)
        for _ in range(8):
            L = float(rng.uniform(0.5, 9.0))
            lds = rng.uniform(-10e3, 10e3, 6)
            got = segment_fixed_end_forces(L, 0.0, 1.0, lds)
            ref = _old_fef(L, lds)
            self.assertLess(np.max(np.abs(got - ref)), 1e-12 * max(1.0, np.max(np.abs(ref))))

    def test_phi_uniform_full_length_equals_closed_form(self):
        # a full-length uniform load has shear-independent fixed-end forces
        L = 3.7
        for phi_y, phi_z in ((0.0, 0.0), (0.3, 1.7), (5.0, 0.05)):
            lds = np.array([100.0, -200.0, 300.0, 100.0, -200.0, 300.0])
            got = segment_fixed_end_forces(L, 0.0, 1.0, lds, phi_y, phi_z)
            ref = _old_fef(L, lds)
            self.assertLess(np.max(np.abs(got - ref)), 1e-12 * np.max(np.abs(ref)))

    def test_phi_changes_partial_bending_forces_only(self):
        L = 4.0
        lds = np.array([100.0, -200.0, 300.0, 100.0, -200.0, 300.0])
        e0 = segment_fixed_end_forces(L, 0.2, 0.5, lds)
        e1 = segment_fixed_end_forces(L, 0.2, 0.5, lds, 0.8, 0.8)
        self.assertGreater(abs(e1[5] - e0[5]), 1e-3 * abs(e0[5]))
        self.assertEqual(e0[0], e1[0])
        self.assertEqual(e0[6], e1[6])
        # shear resultants are still equilibrated: fy_i + fy_j = resultant
        self.assertAlmostEqual(e1[1] + e1[7], -200.0 * 0.3 * L, places=9)
        self.assertAlmostEqual(e1[2] + e1[8], 300.0 * 0.3 * L, places=9)
        # moment equilibrium about the i end
        self.assertAlmostEqual(
            e1[5] + e1[11] + e1[7] * L, -200.0 * 0.3 * L * (0.35 * L), places=9)

    def test_partial_resultants(self):
        L, t0, t1 = 5.0, 0.2, 0.7
        lds = np.array([100.0, -200.0, 300.0, 50.0, 80.0, -120.0])
        f = segment_fixed_end_forces(L, t0, t1, lds)
        seg = (t1 - t0) * L
        res = seg * (lds[0:3] + lds[3:6]) / 2.0
        self.assertAlmostEqual(f[0] + f[6], res[0], places=9)
        self.assertAlmostEqual(f[1] + f[7], res[1], places=9)
        self.assertAlmostEqual(f[2] + f[8], res[2], places=9)

    def test_linear_equivalent_matches_resultant_and_moment(self):
        L, t0, t1 = 6.0, 0.2, 0.4
        lds = np.array([10.0, -20.0, 30.0, 5.0, 8.0, -12.0])
        eq = segment_linear_equivalent(L, t0, t1, lds)
        a, b = t0 * L, t1 * L
        for c in range(3):
            n = 20001
            x = np.linspace(a, b, n)
            w = lds[c] + (lds[3 + c] - lds[c]) * (x - a) / (b - a)
            res = np.trapezoid(w, x)
            mom = np.trapezoid(w * x, x)
            xf = np.linspace(0, L, n)
            wf = eq[c] + (eq[3 + c] - eq[c]) * xf / L
            self.assertAlmostEqual(np.trapezoid(wf, xf), res, places=5)
            self.assertAlmostEqual(np.trapezoid(wf * xf, xf), mom, places=5)


class TestParse(unittest.TestCase):

    BASE = [
        "NODE,1,0,0,0", "NODE,2,6,0,0", "ELEM,1,1,2,1,0",
        "CONS,1," + FIX, "CONS,2," + FIX,
    ]

    def _run(self, eld):
        return run_from_lines(HEAD + self.BASE + [eld])

    def test_invalid_ranges_are_parse_errors(self):
        for t in ("0.5,0.5", "0.6,0.4", "-0.1,0.5", "0.2,1.1", "0.5,0.5000000001"):
            with self.assertRaises(StbParseError) as cm:
                self._run("ELOD,1,0,0,0,0,-10,0,0,-10," + t)
            self.assertIn("ELOD", str(cm.exception))
            self.assertIn("1", str(cm.exception))

    def test_only_one_of_t0_t1_is_a_parse_error(self):
        with self.assertRaises(StbParseError) as cm:
            self._run("ELOD,1,0,0,0,0,-10,0,0,-10,0.2")
        self.assertIn("ELOD", str(cm.exception))
        with self.assertRaises(StbParseError):
            self._run("ELOD,1,0,0,0,0,-10,0,0,-10,0.2,")

    def test_empty_t_fields_mean_full_length(self):
        mdl, _ = self._run("ELOD,1,0,0,0,0,-10,0,0,-10,,")
        self.assertEqual((mdl.elds[0].t0, mdl.elds[0].t1), (0.0, 1.0))

    def test_explicit_full_range_is_identical_to_default(self):
        w = [1.0, -2.0, -10.0, 0.5, 3.0, -4.0]
        for glob in (0, 1):
            m0, t0 = self._run(_eld(1, 0, glob, w))
            m1, t1 = self._run(_eld(1, 0, glob, w, (0, 1)))
            self.assertEqual(
                [r for r in t0.splitlines() if r.startswith(("EFRC", "REAC", "NDSP", "EWLD"))],
                [r for r in t1.splitlines() if r.startswith(("EFRC", "REAC", "NDSP", "EWLD"))])
            self.assertEqual(
                np.asarray(_node(m0, 2).disps).tolist(), np.asarray(_node(m1, 2).disps).tolist())
            self.assertEqual(
                np.asarray(_node(m0, 1).reacts).tolist(), np.asarray(_node(m1, 1).reacts).tolist())


class TestPartialAgainstSplitModel(unittest.TestCase):

    def test_uniform_partial_matches_split_reference_with_normal_g(self):
        for name, case in _uniform_cases().items():
            with self.subTest(case=name):
                mdl_p, _ = case.partial()
                mdl_r, _ = case.reference()
                self.assertGreater(_elem(mdl_p, 1).PHIy, 1e-4)   # shear deformation is active
                a = _result_vector(mdl_p, [1, 2])
                b = _result_vector(mdl_r, [1, 2])
                self.assertGreater(np.max(np.abs(b)), 1e-3)
                self.assertLess(_rel_diff(a, b), 1e-9)

    def test_linear_partial_matches_split_reference_without_shear(self):
        for name, case in _cases().items():
            with self.subTest(case=name):
                mdl_p, _ = case.partial(HEAD_EULER)
                mdl_r, _ = case.reference(HEAD_EULER)
                a = _result_vector(mdl_p, [1, 2])
                b = _result_vector(mdl_r, [1, 2])
                self.assertGreater(np.max(np.abs(b)), 1e-3)
                self.assertLess(_rel_diff(a, b), 1e-8)

    def test_linear_partial_converges_to_fine_reference_with_normal_g(self):
        # Linear partial loads on a shear-deformable member: the split reference
        # (non-uniform full-length loads on sub-members) is itself approximate,
        # so it must converge to the partial-load result as it is refined.
        for name, case in _cases().items():
            with self.subTest(case=name):
                a = _result_vector(case.partial()[0], [1, 2])
                errs = []
                for nsub in (4, 16, 64):
                    b = _result_vector(case.reference(nsub=nsub)[0], [1, 2])
                    errs.append(_rel_diff(a, b))
                self.assertLess(errs[2], 1e-4)
                self.assertLessEqual(errs[2], max(errs[0], 1e-9))

    def test_closure_of_section_force_relations(self):
        for name, case in _cases().items():
            with self.subTest(case=name):
                mdl, txt = case.partial()
                e = _elem(mdl, 1)
                L = e.len
                for i, lc in enumerate(mdl.lcs):
                    f = np.asarray(e.forces[:, i], float) * 1e-3          # kN, kNm
                    segs = diagram_wsegs(e, i)
                    self.assertGreaterEqual(len(segs), 1)
                    scale = max(np.max(np.abs(f)), 1e-9)
                    end = _section_forces(f, L, segs, L)
                    ref = np.array([f[6], f[7], f[8], f[10], f[11]])
                    self.assertLess(np.max(np.abs(end - ref)) / scale, 1e-6)
                    mid = _section_forces(f, L, segs, 0.5 * L)
                    self.assertLess(abs(mid[3] - f[12]) / scale, 1e-6)
                    self.assertLess(abs(mid[4] - f[13]) / scale, 1e-6)

    def test_closure_from_out_text(self):
        # the same relations evaluated from the rounded .out records only
        for name, case in _cases().items():
            with self.subTest(case=name):
                mdl, txt = case.partial()
                L = _elem(mdl, 1).len
                efrc = {int(r[0]): r[2:] for r in _rows(txt, "EFRC")}
                ewld = {}
                for r in _rows(txt, "EWLD"):
                    ewld.setdefault(int(r[0]), []).append(r[2:])
                for lc, f in efrc.items():
                    segs = ewld.get(lc, [])
                    scale = max(max(abs(v) for v in f), 1e-9)
                    end = _section_forces(f, L, segs, L)
                    ref = np.array([f[6], f[7], f[8], f[10], f[11]])
                    self.assertLess(np.max(np.abs(end - ref)) / scale, 5e-3)
                    mid = _section_forces(f, L, segs, 0.5 * L)
                    self.assertLess(abs(mid[3] - f[12]) / scale, 5e-3)
                    self.assertLess(abs(mid[4] - f[13]) / scale, 5e-3)

    def test_wsegs_sign_convention_for_vertical_members(self):
        up = _cases()["column_up"]
        mdl, _ = up.partial()
        e = _elem(mdl, 1)
        raw = e.wsegs[0][0]
        row = diagram_wsegs(e, 0)[0]
        self.assertEqual(row[0:2], [raw[0], raw[1]])
        self.assertAlmostEqual(row[2], raw[2] * 1e-3)       # wx unchanged
        self.assertAlmostEqual(row[3], -raw[3] * 1e-3)      # wy flipped (up-going column)
        self.assertAlmostEqual(row[4], -raw[4] * 1e-3)
        down = _cases()["column_down"]
        mdl, _ = down.partial()
        e = _elem(mdl, 1)
        raw = e.wsegs[0][0]
        row = diagram_wsegs(e, 0)[0]
        self.assertAlmostEqual(row[3], raw[3] * 1e-3)


class TestOutputAndCombination(unittest.TestCase):

    BASE = [
        "NODE,1,0,0,0", "NODE,2,6,0,0", "ELEM,1,1,2,1,0",
        "CONS,1," + FIX, "CONS,2," + FIX,
    ]

    def test_out_contains_ewld_rows_and_elod_echo(self):
        lines = HEAD + self.BASE + [
            "ELOD,1,0,0,0,0,-10,0,0,-20,0.2,0.4",
            "ELOD,1,1,0,0,0,-10,0,0,-10",
        ]
        mdl, txt = run_from_lines(lines)
        self.assertIn("# --- ELEMENT LOAD SEGMENT (local axes, diagram convention) ---", txt)
        self.assertIn(
            "#        LC,  ELEM,        T0,        T1,       WXi,       WYi,       WZi,       WXj,       WYj,       WZj",
            txt)
        self.assertIn(
            "#                          (-)        (-)    (kN/m)    (kN/m)    (kN/m)    (kN/m)    (kN/m)    (kN/m)",
            txt)
        # ordering: after the ELEMENT FORCE block
        self.assertLess(txt.index("# --- ELEMENT FORCE ---"),
                        txt.index("# --- ELEMENT LOAD SEGMENT"))
        ewld = [l for l in txt.splitlines() if l.startswith("EWLD")]
        self.assertEqual(len(ewld), 2)
        self.assertEqual(
            ewld[0],
            "EWLD,     0,     1, 2.000e-01, 4.000e-01, 0.000e+00, 0.000e+00,-1.000e+01,"
            " 0.000e+00, 0.000e+00,-2.000e+01")
        r0 = [float(v) for v in ewld[0].split(",")[1:]]
        self.assertEqual(r0, [0, 1, 0.2, 0.4, 0, 0, -10, 0, 0, -20])
        r1 = [float(v) for v in ewld[1].split(",")[1:]]
        self.assertEqual(r1, [1, 1, 0.0, 1.0, 0, 0, -10, 0, 0, -10])
        # ELOD echo of the input section: T0,T1 only for the partial record
        from classes.io import RegisterInputData
        inp = RegisterInputData(mdl)
        rows = [l for l in inp.splitlines() if l.startswith("ELOD")]
        self.assertEqual(len(rows), 2)
        part = [l for l in rows if len(l.split(",")) == 12]
        full = [l for l in rows if len(l.split(",")) == 10]
        self.assertEqual(len(part), 1)
        self.assertEqual(len(full), 1)
        self.assertEqual([float(v) for v in part[0].split(",")[-2:]], [0.2, 0.4])

    def test_no_ewld_block_without_member_loads(self):
        lines = HEAD + self.BASE + ["PLOD,2,0,0,0,-5,0,0,0"]
        _, txt = run_from_lines(lines)
        self.assertNotIn("EWLD", txt)

    def test_ewld_diagram_sign_for_up_going_column(self):
        lines = HEAD + [
            "NODE,1,0,0,0", "NODE,2,0,0,3", "ELEM,1,1,2,1,0",
            "CONS,1," + FIX,
            "ELOD,1,0,0,0,4,5,0,4,5,0.2,0.6",
        ]
        _, txt = run_from_lines(lines)
        r = [float(v) for v in [l for l in txt.splitlines() if l.startswith("EWLD")][0].split(",")[1:]]
        self.assertEqual(r[4:], [0.0, -4.0, -5.0, 0.0, -4.0, -5.0])

    def test_lcmb_of_partial_case(self):
        w = [0, 3, -10, 0, 5, -4]
        lines = HEAD + self.BASE + [
            _eld(1, 0, 0, w, (0.2, 0.4)),
            _eld(1, 1, 1, [0, -2, -6, 0, -2, -1], (0.5, 0.9)),
            "LCMB,10,COMB,1.5,0,0.5,1",
        ]
        mdl, txt = run_from_lines(lines)
        ewld = [r for r in _rows(txt, "EWLD") if int(r[0]) == 10]
        self.assertEqual(len(ewld), 2)
        by_t0 = {round(r[2], 6): r for r in ewld}
        self.assertEqual((by_t0[0.2][2], by_t0[0.2][3]), (0.2, 0.4))
        self.assertEqual((by_t0[0.5][2], by_t0[0.5][3]), (0.5, 0.9))
        np.testing.assert_allclose(by_t0[0.2][4:], 1.5 * np.array(w), atol=1e-9)
        # combination results = linear combination of the cases
        i0, i1, ic = (mdl.lcs.index(k) for k in (0, 1, 10))
        for nid in (1, 2):
            n = _node(mdl, nid)
            np.testing.assert_allclose(
                n.reacts[ic], 1.5 * n.reacts[i0] + 0.5 * n.reacts[i1], rtol=1e-9, atol=1e-6)
        e = _elem(mdl, 1)
        np.testing.assert_allclose(
            e.forces[:, ic], 1.5 * e.forces[:, i0] + 0.5 * e.forces[:, i1], rtol=1e-9, atol=1e-6)
        # the combination keeps the partial range
        combo = [el for el in mdl.elds if el.combi]
        self.assertEqual(sorted((el.t0, el.t1) for el in combo), [(0.2, 0.4), (0.5, 0.9)])



class TestModelJson(unittest.TestCase):

    def test_wsegs_and_element_load_ranges(self):
        from stb_gui.model_json import mdl_to_dict

        lines = HEAD + [
            "NODE,1,0,0,0", "NODE,2,6,0,0", "ELEM,1,1,2,1,0",
            "CONS,1," + FIX, "CONS,2," + FIX,
            "GLOD,1,0,0,-9.8",
            _eld(1, 0, 0, [0, 0, -10, 0, 0, -20], (0.2, 0.4)),
            _eld(1, 0, 1, [0, 3, 0, 0, 3, 0]),
        ]
        mdl, _ = run_from_lines(lines)
        d = mdl_to_dict(mdl, solved=True)
        el = d["elements"][0]
        self.assertEqual(sorted(el["wsegs"].keys()), sorted(el["forces"].keys()))
        grav = el["wsegs"]["1"]
        self.assertEqual(len(grav), 1)
        self.assertEqual(grav[0][:2], [0.0, 1.0])
        self.assertLess(grav[0][4], 0.0)
        self.assertEqual(grav[0][4], grav[0][7])
        self.assertEqual((grav[0][2], grav[0][3], grav[0][5], grav[0][6]), (0.0, 0.0, 0.0, 0.0))
        segs = el["wsegs"]["0"]
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0][:2], [0.0, 1.0])
        self.assertEqual(segs[1], [0.2, 0.4, 0.0, 0.0, -10000.0, 0.0, 0.0, -20000.0])  # N/m
        loads = {(l["lc"], l.get("gravity", False)): l for l in d["element_loads"]}
        partial = [l for l in d["element_loads"] if l["lc"] == 0 and (l["t0"], l["t1"]) == (0.2, 0.4)]
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0]["w"], [0.0, 0.0, -10.0, 0.0, 0.0, -20.0])
        for l in d["element_loads"]:
            self.assertIn("t0", l)
            self.assertIn("t1", l)
            if l.get("gravity") or l["lc"] != 0:
                self.assertEqual((l["t0"], l["t1"]), (0.0, 1.0))
        # legacy 6-value local load of the partial segment: linear equivalent
        lw = el["local_wloads"]["0"]
        from classes.ld import segment_linear_equivalent
        eq = segment_linear_equivalent(6.0, 0.2, 0.4, [0, 0, -10e3, 0, 0, -20e3])
        full_glob = np.array([0, 3e3, 0, 0, 3e3, 0], float)  # local_wloads are in N/m
        np.testing.assert_allclose(lw, eq + full_glob, atol=1e-9)


if __name__ == "__main__":
    unittest.main()
