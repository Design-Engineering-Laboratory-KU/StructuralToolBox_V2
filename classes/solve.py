import nd, elm, mat, sec, cons, common, mdl, io
from ld import PLd, ALd, ELd, Lcase, Lcmb
import copy
import math
import numpy as np
import datetime

import scipy.sparse as sp
from scipy.sparse.linalg import (
    ArpackError, LinearOperator, eigsh, onenormest, splu,
)

# Below this many DOF a dense symmetric eigensolve is cheaper and more robust
# than ARPACK, so small models keep the original stability check verbatim.
DENSE_EIGEN_MAX_DOF = 2000

# A mode is treated as a mechanism when its eigenvalue falls this far below the
# largest one.
WEAK_MODE_REL_TOL = 1.0e-12

# No eigenvalue can breach WEAK_MODE_REL_TOL while the condition number stays
# below its reciprocal, so a comfortably conditioned matrix needs no
# eigensolve at all. Measured condition estimates run from 3e3 to 4e9 on sound
# models and 2e22 on an actual mechanism, so this leaves a wide margin on both
# sides while keeping the estimate's own error well inside it.
STABLE_COND_MAX = 1.0e10

# Above this many nonzeros, MMD_AT_PLUS_A's symmetric ordering pays off on a
# stiffness matrix: measured fill drops by more than half and factorization
# runs 1.1-1.6x faster. Below it SuperLU's default COLAMD is about twice as
# fast, so small and irregular models keep it.
LARGE_SYSTEM_NNZ = 200000

# Sign flips applied to member-end forces for reporting. Index 6 (fxj) and
# 9 (mxj) are left as-is; the rest depend on whether the member is vertical.
# In both tables each j-end entry is the negated i-end entry, so a section
# force keeps one sign convention along the member.
_FORCE_SIGN_VERT = np.array(
    [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
)
_FORCE_SIGN_FLAT = np.array(
    [-1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0, -1.0, -1.0, 1.0, -1.0, -1.0]
)

#from classes.elm import Elm1D


def _condense_plane_fixed_end_forces(f, vi, mi, vj, mj, li, lj, L, sign):
    """Condense rigid fixed-end forces of one bending plane through end springs.

    f rows vi/mi/vj/mj are shear/moment at the i and j ends (all load cases).
    li, lj are the joint factors (0 = pin, 1 = rigid). sign is +1 when the
    shear-rotation coupling is +6EI/L^2 (local z bending) and -1 otherwise.
    """
    if li >= 1.0 and lj >= 1.0:
        return
    ui = 1.0 - li
    uj = 1.0 - lj
    ai = 4.0 * ui + 6.0 * li
    aj = 4.0 * uj + 6.0 * lj
    den = ai * aj - 4.0 * ui * uj
    pmi = f[mi].copy()
    pmj = f[mj].copy()
    f[mi] = 6.0 * li * (aj * pmi - 2.0 * uj * pmj) / den
    f[mj] = 6.0 * lj * (ai * pmj - 2.0 * ui * pmi) / den
    shear = 6.0 / L * (ui * (2.0 * uj + 6.0 * lj) * pmi + uj * (2.0 * ui + 6.0 * li) * pmj) / den
    f[vi] -= sign * shear
    f[vj] += sign * shear


def _release_fixed_end_forces(e):
    """Adjust member fixed-end forces (e.elds) for EJNT end springs / pins."""
    jnt = e.jnt
    if jnt is None or e.elds is None or jnt.Ryi is None:
        return
    EIy = e.sec.mat.E * e.sec.Iy
    EIz = e.sec.mat.E * e.sec.Iz
    lyi = min(max(jnt.Ryi / EIy, 0.0), 1.0)
    lyj = min(max(jnt.Ryj / EIy, 0.0), 1.0)
    lzi = min(max(jnt.Rzi / EIz, 0.0), 1.0)
    lzj = min(max(jnt.Rzj / EIz, 0.0), 1.0)
    _condense_plane_fixed_end_forces(e.elds, 1, 5, 7, 11, lzi, lzj, e.len, 1.0)
    _condense_plane_fixed_end_forces(e.elds, 2, 4, 8, 10, lyi, lyj, e.len, -1.0)


def _as_dense_disps(disps):
    """Normalize solver output to a dense 2D displacement matrix."""
    if np.ndim(disps) == 1:
        return np.expand_dims(disps, axis=1)
    if hasattr(disps, "toarray"):
        return disps.toarray()
    return np.asarray(disps)


class Solve:

    def __init__(self, _mdl):
        
        self.mdl     = _mdl 
        self.ndof    = 6
        self.num_row = 0
        self.num_lcs = 0

        self.kG_orig =  None
        self.constrained_rows = []
        self._assoc_by_member = None

        # solve
        self.solve()

    def solve(self):

        # register date analysis
        self.mdl.date_analysis = str(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'))

        # global stiffness and load matrices before support constraints
        kG  = self.CreateGlobalStiffMX(apply_constraints=False)

        lm  = self.CreateLoadMx(apply_constraints=False)
        self.InitConstrainedReactions(lm)

        mpcs = getattr(self.mdl, "mpcs", [])
        if mpcs:
            T, reduced_dofs = self.BuildMPCTransformation()
            kG = T.T @ kG @ T
            lm = T.T @ lm
            kG, lm = self.ApplySupportConstraints(kG, lm, reduced_dofs)
        else:
            T = None
            kG, lm = self.ApplySupportConstraints(kG, lm)

        if self.num_lcs < 1:
            raise ValueError("Model has no load cases to solve")

        # Solve. The factorization is shared with the stability check so the
        # check costs a handful of extra back-substitutions instead of a full
        # eigendecomposition.
        kG = kG.tocsc()
        try:
            lu = splu(
                kG,
                permc_spec="MMD_AT_PLUS_A" if kG.nnz > LARGE_SYSTEM_NNZ else "COLAMD",
            )
        except RuntimeError as ex:
            raise ValueError(
                "Model stiffness matrix is singular: {0}".format(ex)
            )

        self.CheckStability(kG, lm, lu)

        x = lu.solve(np.asarray(lm, dtype=np.float64))

        if T is not None:
            # spsolve returns a sparse matrix for multi-column right-hand sides,
            # which np.asarray would turn into a 0-d object array.
            x = T @ _as_dense_disps(x)
        
        self.SetNodalDisps(x) 
        self.CalcElemForces()
        self.CalcMembraneForces()
        self.CalcReactions(x)

        self.isModelSolved = True

        return

    def LowStiffnessModes(self, _kG, _lu=None):
        """Spectrum scale plus the eigenpairs at the low end of the stiffness.

        Small systems use a dense symmetric eigensolve, which is exact and
        cheap enough. Larger ones reuse the solve's LU factorization for a
        shift-invert Lanczos pass, so the check costs a few back-substitutions
        instead of a full O(N^3) eigendecomposition.
        Returns None if no reliable spectrum could be obtained.
        """

        n = _kG.shape[0]

        if n <= DENSE_EIGEN_MAX_DOF or _lu is None:
            dense = _kG.toarray() if sp.issparse(_kG) else np.asarray(_kG)
            try:
                vals, vecs = np.linalg.eigh(dense)
            except np.linalg.LinAlgError:
                return None
            return float(np.max(np.abs(vals))), vals, vecs

        try:
            scale = float(abs(eigsh(
                _kG, k=1, which="LM", return_eigenvectors=False, tol=1.0e-3
            )[0]))
        except (ArpackError, RuntimeError, ValueError):
            # Max absolute row sum bounds the spectral radius from above, which
            # only makes the weak-mode threshold below slightly stricter.
            scale = float(abs(_kG).sum(axis=1).max())

        OPinv = LinearOperator(_kG.shape, matvec=_lu.solve, dtype=np.float64)
        try:
            # The eigenvalues are only compared against a threshold spanning
            # orders of magnitude, so loosening the tolerance from machine
            # precision roughly halves the iteration count for free.
            vals, vecs = eigsh(
                _kG, k=min(6, n - 1), sigma=0.0, which="LM", OPinv=OPinv,
                tol=1.0e-4,
            )
        except (ArpackError, RuntimeError, ValueError):
            return None

        return scale, vals, vecs

    def ConditionEstimate(self, _kG, _lu):
        """1-norm condition estimate, costing about eight back-substitutions.

        Returns None if the estimate could not be formed.
        """

        inv = LinearOperator(
            _kG.shape,
            matvec=_lu.solve,
            rmatvec=lambda b: _lu.solve(b, trans="T"),
            dtype=np.float64,
        )
        try:
            return float(onenormest(inv)) * float(abs(_kG).sum(axis=0).max())
        except (RuntimeError, ValueError):
            return None

    def CheckStability(self, _kG, _lm, _lu=None):
        """Reject near-mechanisms before sparse solve returns meaningless drifts."""

        if _kG.shape[0] == 0 or _kG.nnz == 0:
            return

        if _lu is not None:
            cond = self.ConditionEstimate(_kG, _lu)
            if cond is not None and cond < STABLE_COND_MAX:
                return

        modes = self.LowStiffnessModes(_kG, _lu)
        if modes is None:
            return
        scale, vals, vecs = modes

        if scale <= common.PRES_ZERO:
            raise ValueError("Model stiffness matrix is singular: no effective stiffness")

        # Near-pin releases intentionally use tiny springs; if the loaded
        # structure relies on them, the resulting displacement is not meaningful.
        load_tol = 1.0e-8
        weak = np.where(np.abs(vals) / scale < WEAK_MODE_REL_TOL)[0]
        if weak.size == 0:
            return

        load_cols = _lm if np.ndim(_lm) == 2 else np.expand_dims(_lm, axis=1)
        loaded_cases = []
        for col in range(load_cols.shape[1]):
            load_norm = float(np.linalg.norm(load_cols[:, col]))
            if load_norm <= common.PRES_ZERO:
                continue
            for idx in weak:
                projection = abs(float(vecs[:, idx].T @ load_cols[:, col]))
                if projection > load_tol * load_norm:
                    if getattr(self.mdl, "lcs", None) is not None and col < len(self.mdl.lcs):
                        loaded_cases.append(self.mdl.lcs[col])
                    else:
                        loaded_cases.append(col)
                    break

        if not loaded_cases:
            return

        min_idx = int(weak[np.argmin(np.abs(vals[weak]))])
        rel = abs(float(vals[min_idx])) / scale
        raise ValueError(
            "Model is unstable or ill-conditioned under load case(s) {0}: "
            "weak stiffness mode detected (min eigenvalue={1:.3e}, relative={2:.3e}). "
            "Add lateral resistance/constraints or remove loads on the mechanism."
            .format(loaded_cases, vals[min_idx], rel)
        )

    def CalcMembraneForces(self):
        for m in getattr(self.mdl, "dmems", []):
            m.CalcResults(self.num_lcs)

        return
    
    def CalcReactions(self, _disps):

        kG_orig = self.kG_orig
        if kG_orig is None:
            return

        U = _as_dense_disps(_disps)

        # KU = F, for every DOF and load case at once.
        F = np.asarray(kG_orig @ U)

        for c in self.mdl.cons:

            ind = c.nd.cid * self.ndof

            for i in range(self.ndof): # each of 6 dof

                if c.csts[i] == False:

                    continue

                c.nd.reacts[:, i] += F[ind + i, :self.num_lcs]

        return


    @staticmethod
    def SetElemDisps(_mdl, _scale, _num_ediv): 

        elms    = _mdl.elms 
        scale   = _scale
        num_div = _num_ediv

        # if elms[0].ndisps is None: 
        #     print ("no elem disp result. Solve first.")
        #     return

        max_clc_pld  = max(list(map(lambda l: l.clc, _mdl.lds))) if _mdl.lds else 0
        max_clc_eld  = max(list(map(lambda l: l.clc, _mdl.elds))) if _mdl.elds else 0
        max_clc_gld  = max(list(map(lambda l: l.clc, _mdl.glds))) if _mdl.glds else 0
        num_lcs = max([max_clc_pld, max_clc_eld, max_clc_gld])+1 


        np.set_printoptions(precision=1, linewidth=200, suppress=True, formatter={'float': '{: 0.1e}'.format})  

        # for each element
        for e in elms:

            # element's transformation matrix
            T  = e.tm

            #np.set_printoptions(precision=1, linewidth=np.inf, suppress=True, formatter={'float': '{: 0.1e}'.format})  

            # identify the both ends' nodal disps in element coordinate system
            # nd_ecs for nodal displacements in element coordinate system
            # [2 * ndof, num_lcs]

            nd_ecs = np.matmul(T, e.ndisps) # e.ndisps: GCS

            # print(f"nd_ecs=\n{nd_ecs}")

            lyi  = e.lyi       # lambda
            lyj  = e.lyj       
            lzi  = e.lzi       
            lzj  = e.lzj       
            PHIy = e.PHIy      
            PHIz = e.PHIz 

            L    = e.len

            rlyi  = 1 - lyi
            rlyj  = 1 - lyj
            rlzi  = 1 - lzi
            rlzj  = 1 - lzj

            # based on Fujii eq.(2.81)
            Av_inv_x_B = (1.0 + PHIy) / (2.0 + (2.0 + PHIy) * lzi + (2.0 + PHIy) * lzj + 4.0 * PHIy * lzi * lzj) * np.array([
                [-2.0 * rlzi * (1.0 + 2.0 * lzj) / L, (4.0 + PHIy + (2.0 + 5.0 * PHIy) * lzj) * lzi, 2.0 * rlzi * (1.0 + 2.0 * lzj) / L, -(2.0 - PHIy) * rlzi * lzj],
                [-2.0 * rlzj * (1.0 + 2.0 * lzi) / L, -(2.0 - PHIy) * rlzj * lzi, 2.0 * rlzj * (1.0 + 2.0 * lzi) / L, (4.0 + PHIy + (2.0 + 5.0 * PHIy) * lzi) * lzj]
            ])

            Aw_inv_x_B = (1.0 + PHIz) / (2.0 + (2.0 + PHIz) * lyi + (2.0 + PHIz) * lyj + 4.0 * PHIz * lyi * lyj) * np.array([
                [2.0 * rlyi * (1.0 + 2.0 * lyj) / L, (4.0 + PHIz + (2.0 + 5.0 * PHIz) * lyj) * lyi, -2.0 * rlyi * (1.0 + 2.0 * lyj) / L, -(2.0 - PHIz) * rlyi * lyj],
                [2.0 * rlyj * (1.0 + 2.0 * lyi) / L, -(2.0 - PHIz) * rlyj * lyi, -2.0 * rlyj * (1.0 + 2.0 * lyi) / L, (4.0 + PHIz + (2.0 + 5.0 * PHIz) * lyi) * lyj]
            ])

            disps = []
            # for each load case
            for i in range(num_lcs):
        
                dv = np.array([
                    [nd_ecs[ 1,  i]],
                    [nd_ecs[ 5,  i]],
                    [nd_ecs[ 7,  i]],
                    [nd_ecs[11,  i]]
                ])

                dw = np.array([
                    [nd_ecs[ 2,  i]],
                    [nd_ecs[ 4,  i]],
                    [nd_ecs[ 8,  i]],
                    [nd_ecs[10,  i]]
                ])

                theta_zp_zq = Av_inv_x_B @ dv
                theta_yp_yq = Aw_inv_x_B @ dw

                #print(f"theta_zp_zq: {theta_zp_zq}")
                #print(f"theta_yp_yq: {theta_yp_yq}")
                # need to implement edge moment Myp, Myq, Mzp, Mzq

                disp = []
                # for each division point
                for j in range(num_div + 1): 

                    # shape function: see also Kassimali 1999 pp537-538 sec 5.3 
                    
                    n  = j / num_div

                    ue = (1 - n) * nd_ecs[0, i] + n * nd_ecs[6, i]
                    
                    ve =  (1 - 3 * n ** 2 + 2 * n ** 3) * nd_ecs[1,  i] \
                    + e.len * (n - 2 * n ** 2 + n ** 3) * theta_zp_zq[0][0] \
                    +         (3 * n ** 2 - 2 * n ** 3) * nd_ecs[7,  i] \
                    + e.len * ( (-1) * n ** 2 + n ** 3) * theta_zp_zq[1][0]
                    
                    we =  (1 - 3 * n ** 2 + 2 * n ** 3) * nd_ecs[2,  i] \
                    - e.len * (n - 2 * n ** 2 + n ** 3) * theta_yp_yq[0][0] \
                    +         (3 * n ** 2 - 2 * n ** 3) * nd_ecs[8,  i] \
                    - e.len * ( (-1) * n ** 2 + n ** 3) * theta_yp_yq[1][0] 
                    
                    ug = T[0, 0] * ue + T[1, 0] * ve +  T[2, 0] * we
                    vg = T[0, 1] * ue + T[1, 1] * ve +  T[2, 1] * we
                    wg = T[0, 2] * ue + T[1, 2] * ve +  T[2, 2] * we

                    xg = (1 - n) * (e.n0.x) + n * (e.n1.x) + ug * scale
                    yg = (1 - n) * (e.n0.y) + n * (e.n1.y) + vg * scale
                    zg = (1 - n) * (e.n0.z) + n * (e.n1.z) + wg * scale

                    pnt = common.Pnt(xg, yg, zg) 
                    disp.append(pnt)

                disps.append(disp) 
            
            e.edisps = disps 

        return

    def SetNodalDisps(self, _disps):

        mdl  = self.mdl
        ndof = self.ndof

        disps = _as_dense_disps(_disps)
            
        cnt = 0 # loop counter
        while cnt * ndof < self.num_row:

            cid   = cnt
            s_row = cid * ndof
            e_row = s_row + ndof

            nd = mdl.FindNodeFromCid(cid)
            if nd == -1:
                cnt += 1
                continue
            nd.disps = disps[s_row:e_row, :]
  
            cnt += 1 

        return
    
    def CalcElemForces(self): 

        elms = self.mdl.elms
        n = len(elms)
        nlc = self.num_lcs
        if n < 1 or nlc < 1:
            return

        ndof = self.ndof
        disps = np.empty((n, 2 * ndof, nlc), dtype=np.float64)
        ek = np.empty((n, 12, 12), dtype=np.float64)
        tm = np.empty((n, 12, 12), dtype=np.float64)
        lens = np.empty(n, dtype=np.float64)
        vert = np.empty(n, dtype=bool)
        for k, e in enumerate(elms):
            disps[k, 0:ndof, :] = e.n0.disps
            disps[k, ndof:2 * ndof, :] = e.n1.disps
            ek[k] = e.ek
            tm[k] = e.tm
            lens[k] = e.len
            vert[k] = bool(e.isVxZ) and (e.pln.vx.v[2] > 0)

        forces12 = np.matmul(ek, np.matmul(tm, disps))
        for k, e in enumerate(elms):
            if e.elds is not None:
                forces12[k] -= e.elds

        signs = np.where(vert[:, None], _FORCE_SIGN_VERT, _FORCE_SIGN_FLAT)
        forces12 *= signs[:, :, None]

        forces = np.zeros((n, 14, nlc), dtype=np.float64)
        forces[:, :12, :] = forces12

        w = self._ElemLocalWLoadsBatch(elms, nlc)
        half = 0.5 * lens
        half2 = half ** 2
        # Vertical members report shear and moment with flipped signs, so the
        # load term of the mid-span moment flips with them.
        load_sign = np.where(vert, -1.0, 1.0)[:, None]
        wzi = w[:, 2, :]
        wzj = w[:, 5, :]
        wyi = w[:, 1, :]
        wyj = w[:, 4, :]
        wxc_z = wzi + (wzj - wzi) * 0.5
        wxc_y = wyi + (wyj - wyi) * 0.5
        forces[:, 12, :] = (
            forces[:, 4, :] + forces[:, 2, :] * half[:, None]
            + load_sign * (1.0 / 6.0) * (2.0 * wzi + wxc_z) * half2[:, None]
        )
        forces[:, 13, :] = (
            forces[:, 5, :] - forces[:, 1, :] * half[:, None]
            - load_sign * (1.0 / 6.0) * (2.0 * wyi + wxc_y) * half2[:, None]
        )

        for k, e in enumerate(elms):
            e.ndisps = disps[k]
            e.forces = forces[k]

        return

    def _ElemLocalWLoadsBatch(self, elms, nlc):
        """Distributed ECS line loads (wyi, wzi, ...) for every member and load case."""

        n = len(elms)
        w = np.zeros((n, 6, nlc), dtype=np.float64)
        index_by_id = {e.id: k for k, e in enumerate(elms)}

        for el in self.mdl.elds:
            k = index_by_id.get(el.eid)
            if k is None:
                continue
            e = elms[k]
            lds = np.asarray(el.lds, dtype=np.float64)
            if el.isGlobal == True:
                lds = e.tm[0:6, 0:6] @ lds
            w[k, :, el.clc] += lds

        for k, e in enumerate(elms):
            if e.glds is not None:
                ncols = min(nlc, e.glds.shape[1])
                w[k, :, :ncols] += e.glds[:, :ncols]
            if e.alds is not None:
                ncols = min(nlc, e.alds.shape[1])
                w[k, :, :ncols] += e.alds[:, :ncols]

        connected = self._IndexBoundaryAssocs()
        if connected:
            for k, e in enumerate(elms):
                if e.id in connected:
                    w[k, 1, :] = 0.0
                    w[k, 4, :] = 0.0

        return w

    def EffectiveElemLocalWLoads(self, _e, _lc_idx):
        """Element local distributed loads after diaphragm boundary transfer."""

        lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)

        for el in self.mdl.elds:
            if (el.clc != _lc_idx) or (el.eid != _e.id):
                continue
            el_lds = np.array(el.lds, dtype=np.float64).reshape(6, 1)
            if el.isGlobal == True:
                el_lds = _e.tm[0:6, 0:6] @ el_lds
            lds += el_lds.reshape(6)

        if _e.glds is not None and _lc_idx < _e.glds.shape[1]:
            lds += _e.glds[:, _lc_idx]

        if _e.alds is not None and _lc_idx < _e.alds.shape[1]:
            lds += _e.alds[:, _lc_idx]

        if self._IndexBoundaryAssocs() and (_e.id in self._assoc_by_member):
            # The in-plane transverse member load is carried by the diaphragm.
            # Keep axial and vertical components on the member.
            lds[1] = 0.0
            lds[4] = 0.0

        return lds
    
    def InitConstrainedReactions(self, _lm):

        for c in self.mdl.cons:
            reacts = np.zeros((self.num_lcs, self.ndof))
            ind = c.nd.cid * self.ndof
            for i in range(self.ndof):
                if c.csts[i] == False:
                    continue
                for j in range(self.num_lcs):
                    reacts[j, i] = -1 * _lm[ind + i, j]
            c.nd.reacts = reacts

        return

    def ConstrainedRows(self, _reduced_dofs=None):
        """Rows fixed by supports, expressed in the solved system's ordering."""

        row_map = None
        if _reduced_dofs is not None:
            row_map = {dof: i for i, dof in enumerate(_reduced_dofs)}

        rows = []
        for c in self.mdl.cons:
            ind = c.nd.cid * self.ndof
            for i in range(self.ndof):
                if c.csts[i] == False:
                    continue

                full_dof = ind + i
                if row_map is None:
                    rows.append(full_dof)
                else:
                    row = row_map.get(full_dof)
                    if row is not None:
                        rows.append(row)
        return rows

    def ApplySupportConstraints(self, _kG, _lm, _reduced_dofs=None):
        """Decouple the constrained rows/columns and pin their diagonal."""

        rows = self.ConstrainedRows(_reduced_dofs)
        self.constrained_rows = rows
        if not rows:
            return _kG, _lm

        n = _kG.shape[0]
        free = np.ones(n, dtype=np.float64)
        free[rows] = 0.0

        # The constrained rows are fully decoupled and their load is zero, so
        # their displacement is zero for any positive diagonal. Using the free
        # part's scale rather than 1.0 keeps the diagonal within a few orders of
        # magnitude across the matrix, which both conditions the factorization
        # and keeps these artificial DOF out of the low end of the spectrum
        # where CheckStability looks for mechanisms.
        free_diag = np.abs(_kG.diagonal()) * free
        pin = float(np.max(free_diag)) if n else 0.0
        if not pin > 0.0:
            pin = 1.0

        keep = sp.diags(free, format="csr")
        kG = (keep @ _kG @ keep + sp.diags(pin * (1.0 - free), format="csr")).tocsr()
        _lm[rows, :] = 0.0

        return kG, _lm

    def BuildMPCTransformation(self):

        mpcs = getattr(self.mdl, "mpcs", [])
        slave_dofs = set([m.slave_dof for m in mpcs])
        reduced_dofs = [i for i in range(self.num_row) if i not in slave_dofs]
        reduced_index = {dof: i for i, dof in enumerate(reduced_dofs)}

        rows = list(reduced_dofs)
        cols = list(range(len(reduced_dofs)))
        vals = [1.0] * len(reduced_dofs)

        for m in mpcs:
            if abs(getattr(m, "constant_term", 0.0)) > common.PRES_ZERO:
                raise ValueError("MPC constant terms are not supported yet")
            if m.slave_dof not in slave_dofs:
                continue
            for mdof, coeff in zip(m.master_dofs, m.coefficients):
                if mdof in slave_dofs:
                    raise ValueError("Nested MPC master DOF is not supported")
                ridx = reduced_index.get(mdof)
                if ridx is None:
                    continue
                # Duplicate entries are summed by the COO conversion.
                rows.append(m.slave_dof)
                cols.append(ridx)
                vals.append(coeff)

        T = sp.coo_matrix(
            (np.asarray(vals, dtype=np.float64),
             (np.asarray(rows, dtype=np.int64), np.asarray(cols, dtype=np.int64))),
            shape=(self.num_row, len(reduced_dofs)),
            dtype=np.float64,
        ).tocsr()

        return T, reduced_dofs

    def CreateGlobalStiffMX(self, apply_constraints=True):

        mdl   = self.mdl
        ndof  = self.ndof 
 
        nsize = len(mdl.nds)
        self.num_row = ndof * nsize

        blocks = []

        # 1D elements: 12x12 in the two end nodes' 6 DOF each.
        if mdl.elms:
            dofs = np.empty((len(mdl.elms), 2 * ndof), dtype=np.int64)
            for k, e in enumerate(mdl.elms):
                dofs[k, 0:ndof] = ndof * e.n0.cid + np.arange(ndof)
                dofs[k, ndof:2 * ndof] = ndof * e.n1.cid + np.arange(ndof)
            vals = np.stack([np.asarray(e.ekG, dtype=np.float64) for e in mdl.elms])
            blocks.append((dofs, vals))

        # CST membranes: 9x9 in the three corner nodes' translational DOF.
        dmems = getattr(mdl, "dmems", [])
        if dmems:
            dofs = np.empty((len(dmems), 9), dtype=np.int64)
            for k, m in enumerate(dmems):
                for c, n in enumerate([m.n0, m.n1, m.n2]):
                    dofs[k, 3 * c:3 * c + 3] = ndof * n.cid + np.arange(3)
            vals = np.stack([np.asarray(m.ekG, dtype=np.float64) for m in dmems])
            blocks.append((dofs, vals))

        # Wood shear panels: rank-one 4x4 spring on one translational DOF.
        wshears = getattr(mdl, "wshears", [])
        if wshears:
            dofs = np.empty((len(wshears), 4), dtype=np.int64)
            vals = np.empty((len(wshears), 4, 4), dtype=np.float64)
            for k, w in enumerate(wshears):
                dof = w.dof()
                weights = np.asarray(w.stiffness_weights(), dtype=np.float64)
                dofs[k] = [ndof * n.cid + dof for n in w.nodes()]
                vals[k] = w.k * np.outer(weights, weights)
            blocks.append((dofs, vals))

        kG = self._AssembleSparse(blocks, self.num_row)

        self.kG_orig = kG # unconstrained copy, for calculating reactions later.

        # apply constraints
        if apply_constraints:
            kG, _ = self.ApplySupportConstraints(
                kG, np.zeros((self.num_row, max(self.num_lcs or 1, 1)), dtype=np.float64)
            )

        return kG

    @staticmethod
    def _AssembleSparse(_blocks, _num_row):
        """Scatter per-entity local matrices into one sparse global matrix.

        Each block is (dof_map[n_entity, m], values[n_entity, m, m]).
        Duplicate (row, col) pairs are summed by the COO conversion, which is
        what the element-by-element accumulation needs.
        """

        rows = []
        cols = []
        vals = []
        for dofs, values in _blocks:
            m = dofs.shape[1]
            rows.append(np.repeat(dofs, m, axis=1).ravel())
            cols.append(np.tile(dofs, (1, m)).ravel())
            vals.append(values.reshape(-1))

        if not rows:
            return sp.csr_matrix((_num_row, _num_row), dtype=np.float64)

        return sp.coo_matrix(
            (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
            shape=(_num_row, _num_row),
            dtype=np.float64,
        ).tocsr()
    
    def CreateLoadMx(self, apply_constraints=True):

        # ALOD / ELOD / GLOD accumulate into e.elds (and related arrays) with +=.
        # Clear them so a second Solve on the same model does not double-count.
        for e in self.mdl.elms:
            e.elds = None
            e.alds = None
            e.glds = None

        # max_clc_pld  = max(list(map(lambda l: l.clc, self.mdl.lds))) if self.mdl.lds else 0
        # max_clc_eld  = max(list(map(lambda l: l.clc, self.mdl.elds))) if self.mdl.elds else 0
        # max_clc_gld  = max(list(map(lambda l: l.clc, self.mdl.glds))) if self.mdl.glds else 0
        # max_clc_ald  = max(list(map(lambda l: l.clc, self.mdl.alds))) if self.mdl.alds else 0
        # self.num_lcs = max([max_clc_pld, max_clc_eld, max_clc_gld, max_clc_ald])+1 

        self.num_lcs = self.mdl.max_clc

        #
        # Area loads (ALOD) -- tributary-area method.
        #
        # The panel pressure is distributed to its boundary members as an
        # equivalent linearly-varying member load that reproduces the exact
        # tributary resultant and its centroid (hence exact global equilibrium
        # and reactions), including the member-axial pressure component.
        # The equivalent intensities are accumulated in e.alds (ECS, N/m) and
        # the corresponding consistent fixed-end forces in e.elds (ECS).
        #
        for al in self.mdl.alds:

            col  = al.clc # should have been set at mdl
            elms = al.elms

            if elms is None:
                continue

            for idx, e in enumerate(elms):

                area = al.elms_areas[idx]  # tributary area [m^2]
                dc   = al.elms_dc[idx]     # centroid distance [m] from e.n0
                L    = e.len

                if area <= 0.0 or L <= 0.0:
                    continue

                # pressure vector in ECS [N/m^2]
                p_ecs = e.tm[0:3, 0:3] @ np.array(al.lds)

                # equivalent linear tributary width [m] at the two ends so that
                #   integral(w) = area, centroid(w) = dc
                S  = 2.0 * area / L
                wi = S * (2.0 - 3.0 * dc / L)
                wj = S * (3.0 * dc / L - 1.0)

                # ECS line-load intensities [N/m] at i (n0) and j (n1)
                wxi, wyi, wzi = wi * p_ecs
                wxj, wyj, wzj = wj * p_ecs

                # consistent fixed-end forces for a linearly-varying load (ECS),
                # same convention as ELOD/gravity (axial included).
                fwe = np.zeros((self.ndof * 2, 1), dtype=np.float64)
                fwe[ 0] =  L / 6.0  * (2.0 * wxi + 1.0 * wxj)       # fxi
                fwe[ 1] =  L / 20.0 * (7.0 * wyi + 3.0 * wyj)       # fyi
                fwe[ 2] =  L / 20.0 * (7.0 * wzi + 3.0 * wzj)       # fzi
                fwe[ 3] =  0.0                                      # mxi
                fwe[ 4] = -L**2 / 60.0 * (3.0 * wzi + 2.0 * wzj)    # myi
                fwe[ 5] =  L**2 / 60.0 * (3.0 * wyi + 2.0 * wyj)    # mzi

                fwe[ 6] =  L / 6.0  * (1.0 * wxi + 2.0 * wxj)       # fxj
                fwe[ 7] =  L / 20.0 * (3.0 * wyi + 7.0 * wyj)       # fyj
                fwe[ 8] =  L / 20.0 * (3.0 * wzi + 7.0 * wzj)       # fzj
                fwe[ 9] =  0.0                                      # mxj
                fwe[10] =  L**2 / 60.0 * (2.0 * wzi + 3.0 * wzj)    # myj
                fwe[11] = -L**2 / 60.0 * (2.0 * wyi + 3.0 * wyj)    # mzj

                if e.elds is None:
                    e.elds = np.zeros((self.ndof * 2, self.num_lcs), dtype=np.float64)
                e.elds[:, col] += fwe.reshape(-1)  ### ECS

                if e.alds is None:
                    e.alds = np.zeros((6, self.num_lcs), dtype=np.float64)
                e.alds[:, col] += np.array([wxi, wyi, wzi, wxj, wyj, wzj])  ### ECS

        nr= self.num_row  # self.num_row = ndof * nsize @ stiffness matrix
        lm = np.zeros((nr, self.num_lcs), dtype = np.float64)

        #
        # for point load
        #
        for l in self.mdl.lds:

            row = l.nd.cid * self.ndof
            col = l.clc

            for i in range(self.ndof): 

                ld = l.lds[i]           
                lm[row + i, col] += ld

        self.AddDiaphragmLoads(lm)

        #
        # for element load
        #
        for el in self.mdl.elds:

            fwe     = np.zeros((self.ndof*2, 1), dtype = np.float64)

            col     = el.clc
            e       = el.elm
            lds     = el.lds # self.lds = [_wxi, _wyi, _wzi, _wxj, _wyj, _wzj]

            if el.isGlobal == True:
                lds = e.tm[0:6, 0:6] @ np.array(lds) 
            else: 
                lds = np.array(lds)

            # all lds are now in ECS
            fwe[ 0] =  0.0                                                # fxi
            fwe[ 1] =  e.len / 20.0 * (7.0 * lds[1] + 3.0 * lds[4])       # fyi
            fwe[ 2] =  e.len / 20.0 * (7.0 * lds[2] + 3.0 * lds[5])       # fzi
            fwe[ 3] =  0.0                                                # mxi
            fwe[ 4] = -e.len**2 / 60.0 * (3.0 * lds[2] + 2.0 * lds[5]) #+ # myi
            fwe[ 5] =  e.len**2 / 60.0 * (3.0 * lds[1] + 2.0 * lds[4])    # mzi -

            fwe[ 6] =  0.0                                                # fxj
            fwe[ 7] =  e.len / 20.0 * (3.0 * lds[1] + 7.0 * lds[4])       # fyj
            fwe[ 8] =  e.len / 20.0 * (3.0 * lds[2] + 7.0 * lds[5])       # fzj
            fwe[ 9] =  0.0                                                # mxj
            fwe[10] =  e.len**2 / 60.0 * (2.0 * lds[2] + 3.0 * lds[5]) #- # myj
            fwe[11] = -e.len**2 / 60.0 * (2.0 * lds[1] + 3.0 * lds[4])    # mzj +
            
            if e.elds is None:
                e.elds = np.zeros((self.ndof*2, self.num_lcs), dtype = np.float64)
            e.elds[:, col] += fwe.reshape(-1)  ### ECS 
        
        #
        # Gravity loads
        #
        elms = self.mdl.elms
        n_elms = len(elms)
        if self.mdl.glds and n_elms:
            L = np.empty(n_elms, dtype=np.float64)
            mass = np.empty(n_elms, dtype=np.float64)
            R = np.empty((n_elms, 3, 3), dtype=np.float64)
            for k, e in enumerate(elms):
                L[k] = e.len
                mass[k] = e.sec.A * e.sec.mat.gamma / common.GRAVITY
                R[k] = e.tm[0:3, 0:3]
                if e.elds is None:
                    e.elds = np.zeros((self.ndof * 2, self.num_lcs), dtype=np.float64)
                if e.glds is None:
                    e.glds = np.zeros((6, self.num_lcs), dtype=np.float64)
            L2 = L ** 2
            for g in self.mdl.glds:
                col = g.clc
                w = np.einsum(
                    "kij,j->ki", R,
                    np.array([g.gx, g.gy, g.gz], dtype=np.float64),
                )
                w *= mass[:, None]
                wxi = w[:, 0]
                wyi = w[:, 1]
                wzi = w[:, 2]
                wxj = wxi
                wyj = wyi
                wzj = wzi
                f = np.empty((n_elms, 12), dtype=np.float64)
                f[:, 0] = L / 6.0 * (2.0 * wxi + 1.0 * wxj)
                f[:, 1] = L / 20.0 * (7.0 * wyi + 3.0 * wyj)
                f[:, 2] = L / 20.0 * (7.0 * wzi + 3.0 * wzj)
                f[:, 3] = 0.0
                f[:, 4] = -L2 / 60.0 * (3.0 * wzi + 2.0 * wzj)
                f[:, 5] = L2 / 60.0 * (3.0 * wyi + 2.0 * wyj)
                f[:, 6] = L / 6.0 * (1.0 * wxi + 2.0 * wxj)
                f[:, 7] = L / 20.0 * (3.0 * wyi + 7.0 * wyj)
                f[:, 8] = L / 20.0 * (3.0 * wzi + 7.0 * wzj)
                f[:, 9] = 0.0
                f[:, 10] = L2 / 60.0 * (2.0 * wzi + 3.0 * wzj)
                f[:, 11] = -L2 / 60.0 * (2.0 * wyi + 3.0 * wyj)
                gvec = np.empty((n_elms, 6), dtype=np.float64)
                gvec[:, 0] = wxi
                gvec[:, 1] = wyi
                gvec[:, 2] = wzi
                gvec[:, 3] = wxj
                gvec[:, 4] = wyj
                gvec[:, 5] = wzj
                for k, e in enumerate(elms):
                    e.elds[:, col] += f[k]
                    e.glds[:, col] += gvec[k]

        for e in self.mdl.elms:
            _release_fixed_end_forces(e)

        connected = self._IndexBoundaryAssocs()
        for e in self.mdl.elms:

            if e.elds is None: continue 

            for i in range(2):
                
                if i==0:
                    row = e.n0.cid * self.ndof
                    f = e.elds[:self.ndof, :] 
                else:
                    row = e.n1.cid * self.ndof
                    f = e.elds[self.ndof:2*self.ndof, :]

                f_gcs = e.tm[0:6, 0:6].T @ f
                if connected:
                    self.RedirectConnectedBoundaryMemberLoads(e, i, f, f_gcs, lm)
                lm[row:row+self.ndof, :] += f_gcs
            
            #print(f"e.elds: \n{e.elds}")

        if apply_constraints:
            self.InitConstrainedReactions(lm)
            rows = self.ConstrainedRows()
            if rows:
                lm[rows, :] = 0.0

        return lm

    def AddDiaphragmLoads(self, lm):
        by_diap = {d.id: d for d in getattr(self.mdl, "diaps", [])}
        by_node = {n.id: n for n in getattr(self.mdl, "nds", [])}
        for dl in getattr(self.mdl, "dloads", []):
            col = dl.clc
            if col is None:
                continue
            if dl.load_type == "AREA":
                for node, fx, fy in self._diaphragm_area_nodal_loads(dl, by_diap):
                    self._add_xy_load(lm, node, col, fx, fy)
            elif dl.load_type == "LINE":
                if len(dl.node_ids) < 2:
                    continue
                n0 = by_node.get(dl.node_ids[0])
                n1 = by_node.get(dl.node_ids[1])
                if n0 is None or n1 is None:
                    continue
                L = math.sqrt((n1.x - n0.x) ** 2 + (n1.y - n0.y) ** 2 + (n1.z - n0.z) ** 2)
                fx = dl.px * L * 0.5
                fy = dl.py * L * 0.5
                self._add_xy_load(lm, n0, col, fx, fy)
                self._add_xy_load(lm, n1, col, fx, fy)
            elif dl.load_type in ["MASS", "WEIGHT"]:
                if abs(dl.ax) < common.PRES_ZERO and abs(dl.ay) < common.PRES_ZERO:
                    if dl.load_type == "WEIGHT":
                        w_area = dl.weight
                    else:
                        w_area = dl.mass * common.GRAVITY
                    if w_area > common.PRES_ZERO:
                        for node, fz in self._diaphragm_area_nodal_vertical_loads(dl, by_diap, w_area):
                            row = node.cid * self.ndof
                            lm[row + 2, col] += fz
                    continue
                px = dl.mass * dl.ax + dl.weight / common.GRAVITY * dl.ax
                py = dl.mass * dl.ay + dl.weight / common.GRAVITY * dl.ay
                if abs(px) < common.PRES_ZERO and abs(py) < common.PRES_ZERO:
                    continue
                mass_load = copy.copy(dl)
                mass_load.px = px
                mass_load.py = py
                for node, fx, fy in self._diaphragm_area_nodal_loads(mass_load, by_diap):
                    self._add_xy_load(lm, node, col, fx, fy)

    def _add_xy_load(self, lm, node, col, fx, fy):
        row = node.cid * self.ndof
        lm[row + 0, col] += fx
        lm[row + 1, col] += fy

    def _diaphragm_area_nodal_loads(self, dl, by_diap):
        from diaphragm import dreg_polygon_xy, diaphragm_floor_nodes

        diap = by_diap.get(dl.diap_id)
        if diap is None:
            return []

        _, area = dreg_polygon_xy(self.mdl, dl.diap_id)
        nodes = diaphragm_floor_nodes(self.mdl, dl.diap_id)
        if area > common.PRES_ZERO and len(nodes) >= 1:
            f = area / float(len(nodes))
            return [(n, dl.px * f, dl.py * f) for n in nodes]

        dmems = [m for m in getattr(self.mdl, "dmems", []) if m.diap.id == dl.diap_id]
        if dmems:
            loads = []
            for m in dmems:
                f = m.area / 3.0
                for n in [m.n0, m.n1, m.n2]:
                    loads.append((n, dl.px * f, dl.py * f))
            return loads

        loads = []
        for reg in getattr(self.mdl, "dregs", []):
            if reg.diap_id != dl.diap_id:
                continue
            nodes = []
            for nid in reg.node_ids:
                n = self.mdl.FindNodeFromId(nid)
                if n != -1:
                    nodes.append(n)
            if len(nodes) < 3:
                continue
            poly_area = 0.0
            for i in range(len(nodes)):
                n0 = nodes[i]
                n1 = nodes[(i + 1) % len(nodes)]
                poly_area += n0.x * n1.y - n0.y * n1.x
            poly_area = abs(poly_area) * 0.5
            if poly_area <= common.PRES_ZERO:
                continue
            f = poly_area / float(len(nodes))
            for n in nodes:
                loads.append((n, dl.px * f, dl.py * f))
        return loads

    def _diaphragm_area_nodal_vertical_loads(self, dl, by_diap, w_area):
        from diaphragm import dreg_polygon_xy, diaphragm_floor_nodes

        diap = by_diap.get(dl.diap_id)
        if diap is None:
            return []

        _, area = dreg_polygon_xy(self.mdl, dl.diap_id)
        nodes = diaphragm_floor_nodes(self.mdl, dl.diap_id)
        if area > common.PRES_ZERO and len(nodes) >= 1:
            fz = -w_area * (area / float(len(nodes)))
            return [(n, fz) for n in nodes]

        dmems = [m for m in getattr(self.mdl, "dmems", []) if m.diap.id == dl.diap_id]
        if dmems:
            loads = []
            for m in dmems:
                fz = -w_area * (m.area / 3.0)
                for n in [m.n0, m.n1, m.n2]:
                    loads.append((n, fz))
            return loads

        loads = []
        for reg in getattr(self.mdl, "dregs", []):
            if reg.diap_id != dl.diap_id:
                continue
            nodes = []
            for nid in reg.node_ids:
                n = self.mdl.FindNodeFromId(nid)
                if n != -1:
                    nodes.append(n)
            if len(nodes) < 3:
                continue
            poly_area = 0.0
            for i in range(len(nodes)):
                n0 = nodes[i]
                n1 = nodes[(i + 1) % len(nodes)]
                poly_area += n0.x * n1.y - n0.y * n1.x
            poly_area = abs(poly_area) * 0.5
            if poly_area <= common.PRES_ZERO:
                continue
            fz = -w_area * (poly_area / float(len(nodes)))
            for n in nodes:
                loads.append((n, fz))
        return loads

    def _IndexBoundaryAssocs(self):
        by = getattr(self, "_assoc_by_member", None)
        if by is not None:
            return by

        by = {}
        for a in getattr(self.mdl, "dassocs", []):
            if a.connection_type != "CONNECTED_RIGID":
                continue
            if a.association_type != "boundary_member":
                continue
            if a.member_id not in by:
                by[a.member_id] = a
        self._assoc_by_member = by
        return by

    def _connected_boundary_assoc(self, _e):
        return self._IndexBoundaryAssocs().get(_e.id)

    def RedirectConnectedBoundaryMemberLoads(self, _e, _end_index, _f_ecs, _f_gcs, _lm):
        """For connected boundary members, transfer horizontal line-load resultants
        from member end DOFs to diaphragm host nodes.

        This suppresses spurious weak-axis beam bending due façade/wind line loads
        when the diaphragm tie is intended to carry the in-plane action.
        """

        assoc = self._connected_boundary_assoc(_e)
        if assoc is None:
            return

        end_node = _e.n0 if _end_index == 0 else _e.n1
        cp = None
        for p in assoc.generated_constraint_points:
            if getattr(p, "target_node", None) is end_node:
                cp = p
                break
        if cp is None:
            return

        # Transfer only horizontal force components (global ux, uy).
        transferred = False
        for dof in [0, 1]:
            vals = _f_gcs[dof, :].copy()
            if np.max(np.abs(vals)) < common.PRES_ZERO:
                continue

            for n, w in zip(cp.host_nodes, cp.shape_function_weights):
                if abs(w) < common.PRES_ZERO:
                    continue
                host_row = n.cid * self.ndof + dof
                _lm[host_row, :] += w * vals

            _f_gcs[dof, :] = 0.0
            transferred = True

        if not transferred:
            return

        # Drop global Rz nodal couple from redirected horizontal line loads.
        # This is an MVP approximation to avoid keeping weak-axis member bending
        # while in-plane forces are redirected to diaphragm nodes.
        _f_gcs[5, :] = 0.0
        # Also drop associated local weak-axis force/moment components so
        # member-force postprocessing does not retain redirected load effects.
        _f_ecs[1, :] = 0.0
        _f_ecs[5, :] = 0.0