import common
import math

import numpy as np

from load_case_types import (
    LC_TYPE_CUSTOM,
    canonical_name,
    parse_lnme_fields,
)


class Lcase:
    def __init__(self, _lc, _load_type, _label=""):
        self.lc = int(_lc)
        self.load_type = int(_load_type)
        self.label = str(_label or "").strip()

    @property
    def lname(self):
        return canonical_name(self.load_type, self.label)

    def OutputLnameInfo(self):
        from dat_format import record_line

        values: list[int | str] = [self.lc, self.load_type]
        fmts = [">6", ">4"]
        if self.load_type == LC_TYPE_CUSTOM or self.label:
            values.append(self.label)
            fmts.append(">10")
        return record_line("LNME", fmts, values) + "\n"

class Lcmb:
    def __init__(self, _lc, _name, _fcs, _lcs, _duration="LONG_TERM"):
        self.lc = int(_lc)
        self.name = str(_name)
        self.fcs = [float(f) for f in _fcs] # factors
        self.lcs = [int(lc) for lc in _lcs] # lcases
        self.duration = str(_duration or "LONG_TERM").strip().upper()

    def OutputLcmbInfo(self):

        props = ["LCMB",
                 "{0: >4}".format(self.lc), 
                 "{0: >8}".format(self.name), 
        ]

        for i in range(len(self.fcs)):
            props.append("{0: >5}".format(self.fcs[i]))
            props.append("{0: >5}".format(self.lcs[i]))

        lns = ', '.join(props) + "\n"

        return lns

class PLd:

    def __init__(self, 
                 _nid: int, 
                 _lc: int, 
                 _px: float, 
                 _py: float, 
                 _pz: float, 
                 _mx: float, 
                 _my: float, 
                 _mz: float,
                 _combi=False):

        self.nid =  _nid
        self.lc  =  _lc 
        self.lds = [_px, _py, _pz, _mx, _my, _mz]
        self.pv  =   common.Vec(_px, _py, _pz) # point load vector
        self.mv  =   common.Vec(_mx, _my, _mz) # moment vector

        self.clc =   None
        self.nd  =   None
        self.combi = _combi

    def FindNd(self, nodes_by_id):

        try:
            self.nd = nodes_by_id[self.nid]
        except KeyError:
            raise IndexError("PLOD refers to missing NODE id: {0}".format(self.nid)) from None

    def OutputLdInfo(self):

        props = ["PLOD",
                 "{0: >6}".format(self.nid), 
                 "{0: >4}".format(self.lc), 
        ]

        for l in self.lds:
            props.append("{0: >6.2f}".format(l * 1e-3)) # [N] -> [kN], [Nm] -> [kNm]

        lns = ', '.join(props) + "\n"

        return lns
    
# ----------------------------------------------------------------------
# Member line-load segments (ELOD with T0/T1).
#
# A segment is a linear load over x in [t0*L, t1*L] of a member of length L,
# given by its 6 local (ECS) intensities (wxi, wyi, wzi, wxj, wyj, wzj) [N/m]
# at t0 and t1. Helpers below are pure functions of (L, t0, t1, lds).
# ----------------------------------------------------------------------

# 3-point Gauss-Legendre: exact up to degree 5 (linear load x cubic shape fn)
_GAUSS3_X = np.array([-math.sqrt(0.6), 0.0, math.sqrt(0.6)])
_GAUSS3_W = np.array([5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0])


def _bending_shapes(L, x, phi):
    """Deflection / rotation shape functions of the exact Timoshenko beam
    (interdependent interpolation, still cubic); phi = 0 gives the cubic
    Hermite functions. n2, n4 keep the sign mapping of the fwe formulas."""

    xi = x / L
    d = 1.0 + phi
    n1 = (1.0 - 3.0 * xi ** 2 + 2.0 * xi ** 3 + phi * (1.0 - xi)) / d
    n2 = L * (xi - 2.0 * xi ** 2 + xi ** 3 + 0.5 * phi * (xi - xi ** 2)) / d
    n3 = (3.0 * xi ** 2 - 2.0 * xi ** 3 + phi * xi) / d
    n4 = L * (-xi ** 2 + xi ** 3 - 0.5 * phi * (xi - xi ** 2)) / d
    return n1, n2, n3, n4


def segment_fixed_end_forces(L, t0, t1, lds, phi_y=0.0, phi_z=0.0):
    """Consistent fixed-end forces (ECS) of a linear load on x in [t0*L, t1*L].

    Returns 12 values with the index order and signs of the full-length
    formulas in Solve.CreateLoadMx (fxi, fyi, fzi, mxi, myi, mzi, fxj, ...).
    Linear shape functions for axial; for bending the deflection fields of the
    exact Timoshenko beam, so the result is the exact (Betti) fixed-end force
    of the shear-deformable member: phi_y = 12 E Iz / (G Asy L^2) for wy / rz,
    phi_z = 12 E Iy / (G Asz L^2) for wz / ry. Defaults (0) give Euler-Bernoulli.
    """

    lds = np.asarray(lds, dtype=np.float64)
    a = t0 * L
    b = t1 * L
    seg = b - a

    x = 0.5 * (a + b) + 0.5 * seg * _GAUSS3_X       # Gauss points [m]
    wt = 0.5 * seg * _GAUSS3_W                      # Gauss weights [m]
    u = (x - a) / seg                               # position within the segment
    w = lds[None, 0:3] * (1.0 - u)[:, None] + lds[None, 3:6] * u[:, None]  # (3 pts, xyz)

    xi = x / L
    n_ai = 1.0 - xi                                 # axial i
    n_aj = xi                                       # axial j
    y1, y2, y3, y4 = _bending_shapes(L, x, phi_y)   # local-y plane (wy, rz)
    z1, z2, z3, z4 = _bending_shapes(L, x, phi_z)   # local-z plane (wz, ry)

    fwe = np.zeros(12, dtype=np.float64)
    fwe[0] = np.sum(wt * n_ai * w[:, 0])            # fxi
    fwe[1] = np.sum(wt * y1 * w[:, 1])              # fyi
    fwe[2] = np.sum(wt * z1 * w[:, 2])              # fzi
    fwe[4] = -np.sum(wt * z2 * w[:, 2])             # myi
    fwe[5] = np.sum(wt * y2 * w[:, 1])              # mzi
    fwe[6] = np.sum(wt * n_aj * w[:, 0])            # fxj
    fwe[7] = np.sum(wt * y3 * w[:, 1])              # fyj
    fwe[8] = np.sum(wt * z3 * w[:, 2])              # fzj
    fwe[10] = -np.sum(wt * z4 * w[:, 2])            # myj
    fwe[11] = np.sum(wt * y4 * w[:, 1])             # mzj
    return fwe

def segment_linear_equivalent(L, t0, t1, lds):
    """Full-length linear load (6 values) with the same resultant and the same
    first moment about the i end as the segment, per component."""

    lds = np.asarray(lds, dtype=np.float64)
    a = t0 * L
    b = t1 * L
    seg = b - a
    wa = lds[0:3]
    wb = lds[3:6]

    res = seg * (wa + wb) / 2.0
    mom = wa * (b * b - a * a) / 2.0 + (wb - wa) * (seg * seg / 3.0 + a * seg / 2.0)

    wj = 6.0 * mom / (L * L) - 2.0 * res / L
    wi = 4.0 * res / L - 6.0 * mom / (L * L)
    return np.concatenate([wi, wj])


def segment_moment_integral(L, t0, t1, lds, x):
    """int_0^x (x - xi) w(xi) dxi per component (3 values) for the segment."""

    lds = np.asarray(lds, dtype=np.float64)
    a = t0 * L
    b = t1 * L
    u = min(b, x)
    if u <= a:
        return np.zeros(3, dtype=np.float64)

    q = (lds[3:6] - lds[0:3]) / (b - a)     # slope of w(xi) = p + q xi
    p = lds[0:3] - q * a
    return (p * (x * (u - a) - (u * u - a * a) / 2.0)
            + q * (x * (u * u - a * a) / 2.0 - (u ** 3 - a ** 3) / 3.0))


def diagram_wsegs(e, clc, scale=1e-3):
    """Load segments of member `e` for computational load case `clc` in the
    diagram convention: [[t0, t1, wxi, wyi, wzi, wxj, wyj, wzj], ...].
    Loads are N/m times `scale` (default 1e-3 -> kN/m; 1.0 -> N/m).

    wy, wz are multiplied by s = -1 for bottom-to-top vertical members (the
    members whose EFRC signs are flipped), s = +1 otherwise. Zero segments are
    skipped. e.wsegs holds the raw ECS segments in N/m (set by the solver).
    """

    segs = (getattr(e, "wsegs", None) or {}).get(clc, [])
    s = -1.0 if (bool(e.isVxZ) and e.pln.vx.v[2] > 0) else 1.0
    rows = []
    for seg in segs:
        w = seg[2:8]
        if max(abs(v) for v in w) < 1e-9:
            continue
        rows.append([
            float(seg[0]), float(seg[1]),
            0.0 + w[0] * scale, 0.0 + s * w[1] * scale, 0.0 + s * w[2] * scale,
            0.0 + w[3] * scale, 0.0 + s * w[4] * scale, 0.0 + s * w[5] * scale,
        ])
    return rows


class ELd:

    T_TOL = 1e-12 # tolerance for treating (T0, T1) as the full member length

    def __init__(self, 
                 _eid: int, 
                 _lc: int, 
                 _isG: int,
                 _wxi: float, 
                 _wyi: float, 
                 _wzi: float, 
                 _wxj: float, 
                 _wyj: float, 
                 _wzj: float,
                 _combi=False,
                 _t0: float = 0.0,
                 _t1: float = 1.0):

        self.eid =  _eid
        self.lc  =  _lc
        self.isGlobal = _isG
        self.lds = [_wxi, _wyi, _wzi, _wxj, _wyj, _wzj] # can be in GCS or ECS
        # load range along the member, t = 0 at the i node, t = 1 at the j node;
        # wi acts at t0, wj at t1, linear in between, zero outside [t0, t1]
        _t0 = float(_t0)
        _t1 = float(_t1)
        if not (0.0 <= _t0 < _t1 <= 1.0 and _t1 - _t0 > 1e-9):
            raise ValueError(
                "ELOD on ELEM {0}: T0, T1 must satisfy 0 <= T0 < T1 <= 1 (got T0={1}, T1={2})".format(
                    _eid, _t0, _t1))
        # snap values within the writer tolerance to the exact full-length range
        self.t0 = 0.0 if abs(_t0) <= ELd.T_TOL else _t0
        self.t1 = 1.0 if abs(1.0 - _t1) <= ELd.T_TOL else _t1

        self.len = math.sqrt(max([abs(_wxi), abs(_wxj)])**2 + max([abs(_wyi), abs(_wyj)])**2 + max([abs(_wzi), abs(_wzj)])**2)

        self.clc =   None
        self.elm =   None
        self.combi = _combi

    def FindElm(self, elms_by_id):

        try:
            self.elm = elms_by_id[self.eid]
        except KeyError:
            raise IndexError("ELOD refers to missing ELEM id: {0}".format(self.eid)) from None

    def OutputELdInfo(self):

        props = ["ELOD",
                 "{0: >6}".format(self.eid), 
                 "{0: >4}".format(self.lc), 
                 "{0: >4}".format(self.isGlobal), 
        ]

        for l in self.lds:
            props.append("{0: >6.2f}".format(l * 1e-3)) # [N] -> [kN], [Nm] -> [kNm]

        if self.is_partial:
            props.append("{0: >6}".format("{0:.12g}".format(self.t0)))
            props.append("{0: >6}".format("{0:.12g}".format(self.t1)))

        lns = ', '.join(props) + "\n"

        return lns

    @property
    def is_partial(self):
        return self.t0 > ELd.T_TOL or self.t1 < 1.0 - ELd.T_TOL

class ALd:
    def __init__(self, _lc, _px, _py, _pz, _e1, _e2, _e3, _e4, _combi=False):
        self.lc = _lc
        self.lds = [_px, _py, _pz]
        self.eids = [_e1, _e2, _e3, _e4]
        self.combi = _combi

        self.clc = None  # will be set by mdl

        self.nds = None  # kept for backward-compat (no longer used for corner point loads)
        self.elms = None # will be set by mdl
        self.nds_areas = None # kept for backward-compat
        self.elms_areas = None # tributary area [m^2] per boundary member (aligned to self.elms)
        self.elms_dc = None    # tributary-area centroid distance [m] from member.n0 (aligned to self.elms)
        self.elms_b0 = None    # tributary width [m] at member.n0 (aligned to self.elms)
        self.elms_b1 = None    # tributary width [m] at member.n1 (aligned to self.elms)
        self.elms_t = None     # sampled position t=[0..1] for tributary-width profile
        self.elms_b = None     # sampled tributary-width profile [m] aligned to self.elms_t

    # ------------------------------------------------------------------
    # Area-load distribution (tributary-area method).
    #
    # The panel pressure is distributed onto its boundary members using a
    # nearest-edge (medial-axis) tributary partition of the panel surface.
    # For each member we store the tributary area and the position of its
    # centroid along the member axis. The solver converts these into an
    # equivalent linearly-varying member load that exactly reproduces the
    # tributary resultant and its point of application (hence exact global
    # equilibrium and support reactions), including the member-axial
    # pressure component.
    # ------------------------------------------------------------------
    def SetMemberAreaLoads(self, grid_n: int = 240):

        elms = self.elms

        if elms is None or len(elms) < 3:
            raise ValueError("ALOD panel needs at least 3 boundary members")

        # 1. Order the boundary members into a closed loop of vertices.
        loop = ALd._BuildBoundaryLoop(elms)
        if loop is None:
            raise ValueError(
                f"ALOD elements {[e.id for e in elms]} do not form a single closed loop")

        # ordered start vertices of each edge (= polygon vertices)
        verts_3d = np.array([[seg["v0"].x, seg["v0"].y, seg["v0"].z] for seg in loop])
        n_edge = len(loop)

        # 2. Project the (possibly non-planar) panel onto its best-fit plane.
        centroid = verts_3d.mean(axis=0)
        rel = verts_3d - centroid
        # least-significant singular vector is the plane normal
        _, _, vt = np.linalg.svd(rel, full_matrices=True)
        normal = vt[2]
        e1 = verts_3d[1] - verts_3d[0]
        e1 = e1 - np.dot(e1, normal) * normal
        e1 = e1 / np.linalg.norm(e1)
        e2 = np.cross(normal, e1)

        verts_2d = np.column_stack([rel @ e1, rel @ e2])

        # 3. Exact polygon area (shoelace) used to normalise the tributary areas.
        poly_area = ALd._PolygonArea(verts_2d)
        if poly_area < common.PRES_ZERO:
            raise ValueError("ALOD panel has (near) zero area")

        # 4. Nearest-edge tributary partition -> per-edge area, centroid, end widths.
        areas, dcs, b0s, b1s, ts, bs = ALd._TributaryByEdge(verts_2d, grid_n)

        # normalise so the assigned areas sum exactly to the true panel area
        total = sum(areas)
        if total > common.PRES_ZERO:
            scale = poly_area / total
            areas = [a * scale for a in areas]

        # 5. Map each edge result back to its member (centroid measured from member.n0).
        self.elms = [seg["elm"] for seg in loop]
        self.elms_areas = areas
        self.elms_dc = []
        self.elms_b0 = []
        self.elms_b1 = []
        self.elms_t = []
        self.elms_b = []
        for k, seg in enumerate(loop):
            e = seg["elm"]
            dc_from_v0 = dcs[k]              # measured from edge start vertex (seg["v0"])
            b0_from_v0 = b0s[k]
            b1_from_v0 = b1s[k]
            t_from_v0 = ts[k]
            b_from_v0 = bs[k]
            if seg["v0"] is e.n0:
                self.elms_dc.append(dc_from_v0)
                self.elms_b0.append(b0_from_v0)
                self.elms_b1.append(b1_from_v0)
                self.elms_t.append(t_from_v0)
                self.elms_b.append(b_from_v0)
            else:                            # edge runs n1 -> n0, flip the coordinate
                self.elms_dc.append(e.len - dc_from_v0)
                self.elms_b0.append(b1_from_v0)
                self.elms_b1.append(b0_from_v0)
                self.elms_t.append(np.array([1.0 - t for t in t_from_v0[::-1]], dtype=np.float64))
                self.elms_b.append(np.array(b_from_v0[::-1], dtype=np.float64))

        # corner point loads are no longer used
        self.nds = None
        self.nds_areas = None

        return

    @staticmethod
    def _BuildBoundaryLoop(elms):
        """Order the given members into a single closed polygon loop.

        Returns a list of dicts {"elm", "v0", "v1"} where consecutive edges
        share a vertex (v1 of edge k == v0 of edge k+1), or None if the
        members do not form exactly one closed loop.
        """

        remaining = list(elms)
        first = remaining.pop(0)
        loop = [{"elm": first, "v0": first.n0, "v1": first.n1}]
        current = first.n1
        start = first.n0

        while remaining:
            nxt = None
            for e in remaining:
                if e.n0 is current:
                    nxt = {"elm": e, "v0": e.n0, "v1": e.n1}
                    break
                if e.n1 is current:
                    nxt = {"elm": e, "v0": e.n1, "v1": e.n0}
                    break
            if nxt is None:
                return None
            remaining.remove(nxt["elm"])
            loop.append(nxt)
            current = nxt["v1"]

        # the loop must close back onto the starting vertex
        if current is not start:
            return None

        return loop

    @staticmethod
    def _PolygonArea(pts_2d):
        x = pts_2d[:, 0]
        y = pts_2d[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

    @staticmethod
    def _PointsInPolygon(px, py, poly):
        """Vectorised ray-casting point-in-polygon test for a simple polygon."""

        n = len(poly)
        inside = np.zeros(px.shape, dtype=bool)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i, 0], poly[i, 1]
            xj, yj = poly[j, 0], poly[j, 1]
            cond = ((yi > py) != (yj > py)) & (
                px < (xj - xi) * (py - yi) / (yj - yi + 1e-300) + xi)
            inside ^= cond
            j = i
        return inside

    @staticmethod
    def _TributaryByEdge(verts_2d, grid_n):
        """Partition the polygon by nearest boundary edge (medial-axis / 45-deg
        tributary rule) and return per-edge (area, centroid-distance-from-v0)."""

        n_edge = len(verts_2d)

        min_x, min_y = verts_2d.min(axis=0)
        max_x, max_y = verts_2d.max(axis=0)
        span = max(max_x - min_x, max_y - min_y)
        h = span / grid_n
        cell_area = h * h

        # cell-centre grid covering the bounding box
        xs = np.arange(min_x + 0.5 * h, max_x, h)
        ys = np.arange(min_y + 0.5 * h, max_y, h)
        gx, gy = np.meshgrid(xs, ys)
        gx = gx.ravel()
        gy = gy.ravel()

        inside = ALd._PointsInPolygon(gx, gy, verts_2d)
        gx = gx[inside]
        gy = gy[inside]

        pts = np.column_stack([gx, gy])

        # distance from every interior cell to every edge segment (clamped)
        dist = np.empty((n_edge, pts.shape[0]), dtype=np.float64)
        tparam = np.empty((n_edge, pts.shape[0]), dtype=np.float64)  # length along edge from v0
        for k in range(n_edge):
            a = verts_2d[k]
            b = verts_2d[(k + 1) % n_edge]
            ab = b - a
            L2 = np.dot(ab, ab)
            ap = pts - a
            t = (ap @ ab) / L2
            tc = np.clip(t, 0.0, 1.0)
            proj = a + np.outer(tc, ab)
            dvec = pts - proj
            dist[k] = np.sqrt(np.sum(dvec * dvec, axis=1))
            tparam[k] = t * np.sqrt(L2)  # projected length along edge from v0

        owner = np.argmin(dist, axis=0)

        n_bin = max(24, grid_n // 10)
        areas = []
        dcs = []
        b0s = []
        b1s = []
        ts = []
        bs = []
        for k in range(n_edge):
            a = verts_2d[k]
            b = verts_2d[(k + 1) % n_edge]
            Lk = float(np.linalg.norm(b - a))
            mask = owner == k
            cnt = int(np.count_nonzero(mask))
            areas.append(cnt * cell_area)
            if cnt > 0:
                dcs.append(float(np.mean(tparam[k][mask])))
            else:
                dcs.append(0.5 * Lk)

            # Tributary width along the edge from cell strips (zero at convex corners).
            widths = np.zeros(n_bin, dtype=np.float64)
            if cnt > 0:
                tk = tparam[k][mask]
                bins = np.linspace(0.0, Lk, n_bin + 1)
                for bi in range(n_bin):
                    lo, hi = bins[bi], bins[bi + 1]
                    in_bin = (tk >= lo) & (tk < hi if bi < n_bin - 1 else tk <= hi)
                    if np.any(in_bin):
                        widths[bi] = np.count_nonzero(in_bin) * cell_area / max(hi - lo, 1e-12)
            b0s.append(float(widths[0]))
            b1s.append(float(widths[-1]))
            ts.append(np.array([(bi + 0.5) / n_bin for bi in range(n_bin)], dtype=np.float64))
            bs.append(widths)

        return areas, dcs, b0s, b1s, ts, bs

    def OutputALdInfo(self):
        props = ["ALOD",
                 "{0: >6}".format(self.lc), 
        ]

        for l in self.lds:
            props.append("{0: >6.2f}".format(l * 1e-3)) # [N/m2] -> [kN/m2]

        for eid in self.eids:
            props.append("{0: >4}".format(eid)) 

        lns = ', '.join(props) + "\n"

        return lns

class GLd:

    def __init__(self, 
                 _lc:   int, 
                 _gx: float,
                 _gy: float, 
                 _gz: float,
                 _combi=False):
        
        self.lc = _lc
        self.gx = _gx
        self.gy = _gy
        self.gz = _gz 

        self.clc =   None
        self.combi = _combi
        
    def OutputGLdInfo(self):

        props = ["GLOD",
                 "{0: >6}".format(self.lc), 
                 "{0: >9.6f}".format(self.gx),
                 "{0: >9.6f}".format(self.gy),
                 "{0: >9.6f}".format(self.gz)
        ]

        lns = ', '.join(props) + "\n"

        return lns