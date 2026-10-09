import numpy as np
import math

import common
from nd   import Nd
from mat  import Mat
from sec  import Sec
from ejnt import EJnt

# Bending-plane DOF order used below: (v_i, theta_i, v_j, theta_j) with the
# +6EI/L^2 shear-rotation coupling (local z bending: v, rz). The local y
# bending plane (w, ry) uses the opposite sign; flip the rotations with
# PLANE_Y_FLIP before and after.
PLANE_ROWS_Z = (1, 5, 7, 11)
PLANE_ROWS_Y = (2, 4, 8, 10)
PLANE_Y_FLIP = np.array([1.0, -1.0, 1.0, -1.0])


def timoshenko_plane_stiffness(EI, L, phi):
    """4x4 Timoshenko beam stiffness for one bending plane (rigid ends)."""
    c = EI / (L ** 3 * (1.0 + phi))
    L2 = L * L
    return c * np.array([
        [ 12.0,              6.0 * L, -12.0,              6.0 * L],
        [  6.0 * L, (4.0 + phi) * L2,  -6.0 * L, (2.0 - phi) * L2],
        [-12.0,             -6.0 * L,  12.0,             -6.0 * L],
        [  6.0 * L, (2.0 - phi) * L2,  -6.0 * L, (4.0 + phi) * L2],
    ])


def _spring_system(Kb, ki, kj):
    """Member stiffness plus end springs on node DOFs and internal member-end
    rotations. ki/kj: rotational springs [Nm/rad], None = rigid.
    Returns (K, internal indices, member-DOF -> system index map)."""
    dof = [0, 1, 2, 3]
    nint = 0
    for end, k in ((1, ki), (3, kj)):
        if k is not None:
            dof[end] = 4 + nint
            nint += 1
    n = 4 + nint
    K = np.zeros((n, n))
    K[np.ix_(dof, dof)] += Kb
    for end, k in ((1, ki), (3, kj)):
        if k is not None:
            m = dof[end]
            K[end, end] += k
            K[m, m] += k
            K[end, m] -= k
            K[m, end] -= k
    return K, list(range(4, n)), dof


def condense_end_springs(Kb, ki, kj, f=None):
    """Static condensation of a beam plane with rotational end springs.

    Kb: 4x4 plane stiffness on member-end DOFs. f: member-end equivalent
    nodal loads (4 x nlc) of the rigid-ended member, or None.
    Returns the 4x4 stiffness and loads on the node DOFs (exact series
    springs, shear deformation included).
    """
    K, ii, dof = _spring_system(Kb, ki, kj)
    if not ii:
        return Kb.copy(), (None if f is None else np.array(f, dtype=np.float64))
    ee = [0, 1, 2, 3]
    Kii_inv = np.linalg.inv(K[np.ix_(ii, ii)])
    Kei = K[np.ix_(ee, ii)]
    Kc = K[np.ix_(ee, ee)] - Kei @ Kii_inv @ K[np.ix_(ii, ee)]
    if f is None:
        return Kc, None
    f = np.atleast_2d(np.asarray(f, dtype=np.float64).reshape(4, -1))
    fs = np.zeros((K.shape[0], f.shape[1]))
    fs[dof, :] += f
    fc = fs[ee, :] - Kei @ Kii_inv @ fs[ii, :]
    return Kc, fc


def member_end_rotations(Kb, ki, kj, d, f):
    """Member-end bending rotations (theta_i, theta_j) for node DOFs d
    (4 x nlc) and rigid-ended member loads f (4 x nlc)."""
    d = np.atleast_2d(np.asarray(d, dtype=np.float64).reshape(4, -1))
    K, ii, dof = _spring_system(Kb, ki, kj)
    out = np.empty((2, d.shape[1]))
    out[0] = d[1]
    out[1] = d[3]
    if not ii:
        return out
    ee = [0, 1, 2, 3]
    fs = np.zeros((K.shape[0], d.shape[1]))
    fs[dof, :] += np.atleast_2d(np.asarray(f, dtype=np.float64).reshape(4, -1))
    th = np.linalg.solve(K[np.ix_(ii, ii)], fs[ii, :] - K[np.ix_(ii, ee)] @ d)
    for r, end in enumerate([e for e in (1, 3) if dof[e] >= 4]):
        out[0 if end == 1 else 1] = th[r]
    return out


def element_end_springs(e):
    """(kyi, kyj, kzi, kzj) rotational end springs [Nm/rad]; None = rigid."""
    jnt = e.jnt
    if jnt is None:
        return (None, None, None, None)
    return (jnt.ryi, jnt.ryj, jnt.rzi, jnt.rzj)


class Elm1D:

    def __init__(self, 
                 _id, 
                 _n0, 
                 _n1, 
                 _sec, 
                 _theta,
                 _bucklen: float | None = None):
        
        self.id      = _id
        self.n0      = _n0 # node class instance
        self.n1      = _n1 # node class instance
        self.sec     = _sec
        self.theta   = _theta # in degree
        self.jnt     =  None
        self.auto_generated = False
        self.generated_from: str | None = None
        self.generated_from_id: int | None = None
        
        # self.vecz    =  Elm1D.CalcVecZ(_vecz)
        self.bucklen: float | None = _bucklen
        self.pln     =  None
        self.len     =  self.CalcLen()
        self.weight  =  self.CalcWeight()
        self.beta    =  self.CalcBeta()
        # self.pln   is set in CalcBeta()
        # self.isVxZ is set in CalcBeta()

        self.ek      =  None # self.ElmStiffMX()
        self.tm      =  None # self.ElmTransMX()
        self.sub_tm1 =  None
        self.sub_tm2 =  None
        self.ekG     =  None # np.matmul(np.matmul(self.tm.T, self.ek), self.tm)
        
        self.ndisps  =  None # nodal displacements
        self.edisps  =  None 
        self.forces  =  None
        # self.elds    =  None # element forces defined in GCS
        self.elds    =  None # element forces defined in ECS 
        self.glds    =  None
        self.alds    =  None # added on 2025-01-19

        self.cy      =  None
        self.cz      =  None
        self.lyi     =  None
        self.lyj     =  None
        self.lzi     =  None
        self.lzj     =  None
        self.PHIy    =  None
        self.PHIz    =  None

    def CalcLen(self):

        len = self.n0.DistanceTo(self.n1)

        return len
    
    def CalcWeight(self):

        a = self.sec.A          
        v = self.len * a        
        d = self.sec.mat.gamma  

        w = v*d                 

        return w 
    
    def CalcBeta(self):

        vxx = (self.n1.x - self.n0.x) / self.len
        vxy = (self.n1.y - self.n0.y) / self.len
        vxz = (self.n1.z - self.n0.z) / self.len
        theta_rad = self.theta * math.pi / 180.0

        self.isVxZ = False
        angle = Elm1D.CalcAngle(vxx, vxy, vxz, 0.0, 0.0, 1.0)

        if (abs(angle) < common.PRES_ANGLE) or (abs(angle - math.pi) < common.PRES_ANGLE): 
            self.isVxZ = True
            #print("isVxZ True")
        
        # parallel to Z-axis 
        if self.isVxZ:

            if abs(angle - math.pi) < common.PRES_ANGLE:
                alpha = 0.5 * math.pi
            else:
                alpha =-0.5 * math.pi

            ang = theta_rad + alpha
            c   = math.cos(ang)
            s   = math.sin(ang)
            omc = 1.0 - c
            kdx = vxx
            # rotate X=(1,0,0) around vx; cross(vx, X) = (0, vxz, -vxy)
            vyx = 1.0 * c + vxx * kdx * omc
            vyy = s * vxz + vxy * kdx * omc
            vyz = -s * vxy + vxz * kdx * omc
            vzx = vxy * vyz - vxz * vyy
            vzy = vxz * vyx - vxx * vyz
            vzz = vxx * vyy - vxy * vyx
            nvz = math.sqrt(vzx ** 2 + vzy ** 2 + vzz ** 2)
            vzx = vzx / nvz
            vzy = vzy / nvz
            vzz = vzz / nvz
            beta = ang
            
        # not parallel to Z-axis
        else: 

            # cross(Z, vx) = (-vxy, vxx, 0)
            vyx = -vxy
            vyy =  vxx
            vyz =  0.0
            nvy = math.sqrt(vyx ** 2 + vyy ** 2 + vyz ** 2)
            vyx = vyx / nvy
            vyy = vyy / nvy
            vyz = vyz / nvy
            c   = math.cos(theta_rad)
            s   = math.sin(theta_rad)
            omc = 1.0 - c
            kdv = vxx * vyx + vxy * vyy + vxz * vyz
            cxx = vxy * vyz - vxz * vyy
            cxy = vxz * vyx - vxx * vyz
            cxz = vxx * vyy - vxy * vyx
            ryx = vyx * c + cxx * s + vxx * kdv * omc
            ryy = vyy * c + cxy * s + vxy * kdv * omc
            ryz = vyz * c + cxz * s + vxz * kdv * omc
            vyx = ryx
            vyy = ryy
            vyz = ryz
            vzx = vxy * vyz - vxz * vyy
            vzy = vxz * vyx - vxx * vyz
            vzz = vxx * vyy - vxy * vyx
            nvz = math.sqrt(vzx ** 2 + vzy ** 2 + vzz ** 2)
            vzx = vzx / nvz
            vzy = vzy / nvz
            vzz = vzz / nvz
            beta = theta_rad
        
        # plane 
        #print(f"vx:{vx}, vy:{vy}, vz:{vz}")
        self.pln = common.Plane(self.n0, (vxx, vxy, vxz), (vyx, vyy, vyz), (vzx, vzy, vzz))
        #print(f"elemid: {self.id}, beta= {math.degrees(beta)}")
        return beta
    
    @staticmethod
    def CalcAngle(x1, y1, z1, x2, y2, z2):
        n1 = math.sqrt(x1 ** 2 + y1 ** 2 + z1 ** 2)
        n2 = math.sqrt(x2 ** 2 + y2 ** 2 + z2 ** 2)
        dp = (x1 * x2 + y1 * y2 + z1 * z2) / (n1 * n2)
        if dp > 1.0:
            dp = 1.0
        if dp < -1.0:
            dp = -1.0
        a  = math.acos(dp)                            # in radian

        return a
    
    def ElmTransMX(self):

        tm      = np.zeros((12, 12), dtype = np.float64) 
        sub_tm  = np.zeros(( 3,  3), dtype = np.float64)
        sub_tm1 = np.zeros(( 3,  3), dtype = np.float64)
        sub_tm2 = np.zeros(( 3,  3), dtype = np.float64)

        l       = (self.n1.x - self.n0.x) / self.len
        m       = (self.n1.y - self.n0.y) / self.len
        n       = (self.n1.z - self.n0.z) / self.len
        lm      = math.sqrt(l**2 + m**2)

        #print(f"self.beta = {self.beta}")

        sub_tm1[0, 0] =  1.0
        sub_tm1[1, 1] =  1.0 * math.cos(self.beta)
        sub_tm1[1, 2] =  1.0 * math.sin(self.beta)
        sub_tm1[2, 1] = -1.0 * math.sin(self.beta)
        sub_tm1[2, 2] =  1.0 * math.cos(self.beta) 

        # parallel to Z-Axis
        #if self.isVxZ:
        if lm < common.PRES_ZERO:
            self.isVxZ = True

            #print(f"elem parallel to Z")

            sub_tm2[0, 2] = n
            sub_tm2[1, 0] = n
            sub_tm2[2, 1] = 1.0
        
        # not parallel to Z-Axis
        else: 
            sub_tm2[0, 0] =  l
            sub_tm2[0, 1] =  m
            sub_tm2[0, 2] =  n
            sub_tm2[1, 0] = -m / lm
            sub_tm2[1, 1] =  l / lm
            sub_tm2[2, 0] = -l * n / lm 
            sub_tm2[2, 1] = -m * n / lm
            sub_tm2[2, 2] =  lm

        sub_tm = np.matmul(sub_tm1, sub_tm2)
        
        for i in range(4):
            tm[3 * i : 3 * (i + 1), 3 * i : 3 * (i + 1)] = sub_tm

        self.sub_tm1 = sub_tm1
        self.sub_tm2 = sub_tm2

        return tm

    def SS0_ElmStiffMX(self):

        esm  = np.zeros((12, 12), dtype = np.float64)

        L    = self.len                     #         # m
        EA   = self.sec.mat.E * self.sec.A  #         # N/mm2 * mm2 = N 
        EIy  = self.sec.mat.E * self.sec.Iy #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2
        EIz  = self.sec.mat.E * self.sec.Iz #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2
        GJ   = self.sec.mat.G * self.sec.J  #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2

        # axial direction
        esm[ 0,  0] =  EA / L 
        esm[ 0,  6] = -1.0 * esm[ 0,  0]
        esm[ 6,  0] = -1.0 * esm[ 0,  0]
        esm[ 6,  6] =  1.0 * esm[ 0,  0]

        # bending around z-axis
        esm[ 1,  1] = 12.0 * EIz / L ** 3 
        esm[ 1,  7] = -1.0 * esm[ 1,  1]
        esm[ 7,  1] = -1.0 * esm[ 1,  1]
        esm[ 7,  7] =  1.0 * esm[ 1,  1]

        esm[ 1,  5] =  6.0 * EIz / L ** 2 
        esm[ 5,  1] =  1.0 * esm[ 1,  5]
        esm[ 5,  7] = -1.0 * esm[ 1,  5]
        esm[ 7,  5] = -1.0 * esm[ 1,  5]

        esm[ 1, 11] =  6.0 * EIz / L ** 2 
        esm[11,  1] =  1.0 * esm[ 1, 11]
        esm[ 7, 11] = -1.0 * esm[ 1, 11] 
        esm[11,  7] = -1.0 * esm[ 1, 11]

        esm[ 5,  5] =  4.0 * EIz / L 
        esm[11, 11] =  1.0 * esm[ 5,  5] 
        esm[ 5, 11] =  2.0 * EIz / L
        esm[11,  5] =  1.0 * esm[ 5, 11] 

        # bending around y-axis
        esm[ 2,  2] = 12.0 * EIy / L ** 3 
        esm[ 2,  8] = -1.0 * esm[ 2,  2]
        esm[ 8,  2] = -1.0 * esm[ 2,  2]
        esm[ 8,  8] =  1.0 * esm[ 2,  2]

        esm[ 2,  4] = -6.0 * EIy / L ** 2 
        esm[ 4,  2] =  1.0 * esm[ 2,  4]
        esm[ 4,  8] = -1.0 * esm[ 2,  4]
        esm[ 8,  4] = -1.0 * esm[ 2,  4]

        esm[ 2, 10] = -6.0 * EIy / L ** 2 
        esm[10,  2] =  1.0 * esm[ 2, 10]
        esm[ 8, 10] = -1.0 * esm[ 2, 10]
        esm[10,  8] = -1.0 * esm[ 2, 10]

        esm[ 4,  4] =  4.0 * EIy / L
        esm[10, 10] =  1.0 * esm[ 4,  4]
        esm[ 4, 10] =  2.0 * EIy / L 
        esm[10,  4] =  1.0 * esm[ 4, 10]

        # torsion
        esm[ 3,  3] =  GJ / L
        esm[ 3,  9] = -1.0 * esm[ 3,  3]
        esm[ 9,  3] = -1.0 * esm[ 3,  3]
        esm[ 9,  9] =  1.0 * esm[ 3,  3]

        return esm

    def ElmStiffMX(self):

        esm  = np.zeros((12, 12), dtype = np.float64)
        jnt = self.jnt
        if jnt is None:
            raise RuntimeError("Element {0} has no joint definition".format(self.id))

        L    = self.len                     #         # m
        EA   = self.sec.mat.E * self.sec.A  #         # N/mm2 * mm2 = N 
        EIy  = self.sec.mat.E * self.sec.Iy #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2
        EIz  = self.sec.mat.E * self.sec.Iz #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2
        GJ   = self.sec.mat.G * self.sec.J  #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2

        # considering shear deformation
        # according to Przemieniecki-Theory-of-matrix-structural-analysis
        PHIy = 12.0 * self.sec.mat.E * self.sec.Iz / (self.sec.mat.G * self.sec.Asy * L ** 2) #* 1e-6 
        PHIz = 12.0 * self.sec.mat.E * self.sec.Iy / (self.sec.mat.G * self.sec.Asz * L ** 2) #* 1e-6 

        # according to Fujii, Matsumoto Excel-Fem (2021)
        lyi = jnt.Ryi / EIy # lambda_yi
        lzi = jnt.Rzi / EIz # lambda_zi
        lyj = jnt.Ryj / EIy # lambda_yj
        lzj = jnt.Rzj / EIz # lambda_zj
        lz1 = 1.0 + lzi + lzj
        ly1 = 1.0 + lyi + lyj

        cz = EIz / L ** 3
        cy = EIy / L ** 3

        # axial direction
        esm[ 0,  0] =  EA / L ###
        esm[ 0,  6] = -1.0 * esm[ 0,  0]
        esm[ 6,  0] = -1.0 * esm[ 0,  0]
        esm[ 6,  6] =  1.0 * esm[ 0,  0]

        # bending around z-axis
        esm[ 1,  1] = 6.0 *  cz * (lzi + lzj + 4.0 * lzi * lzj) / lz1 / (1.0 + PHIy)
        # = 12.0 * EIz / L ** 3 / (1.0 + PHIy)
        esm[ 1,  7] = -1.0 * esm[ 1,  1]
        esm[ 7,  1] = -1.0 * esm[ 1,  1]
        esm[ 7,  7] =  1.0 * esm[ 1,  1]

        esm[ 1,  5] =  6.0 * cz * lzi * (1.0 + 2.0 * lzj) * L / lz1 / (1.0 + PHIy)
        # =  6.0 * EIz / L ** 2 / (1.0 + PHIy)
        esm[ 5,  1] =  1.0 * esm[ 1,  5]
        esm[ 5,  7] = -1.0 * esm[ 1,  5]
        esm[ 7,  5] = -1.0 * esm[ 1,  5]

        esm[ 1, 11] =  6.0 * cz * (1.0 + 2.0 * lzi) * lzj * L / lz1 / (1.0 + PHIy)
        # =  6.0 * EIz / L ** 2 / (1.0 + PHIy)
        esm[11,  1] =  1.0 * esm[ 1, 11]
        esm[ 7, 11] = -1.0 * esm[ 1, 11] 
        esm[11,  7] = -1.0 * esm[ 1, 11]

        esm[ 5,  5] = (4.0 + PHIy) / (1.0 + PHIy) * cz * lzi * (1.0 + lzj) / lz1 * 3.0 / 2.0 * L ** 2
        # = (4.0 + PHIy) * EIz / L / (1.0 + PHIy) 
        esm[11, 11] = (4.0 + PHIy) / (1.0 + PHIy) * cz * (1.0 + lzi) * lzj / lz1 * 3.0 / 2.0 * L ** 2
        # =  1.0 * esm[ 5,  5] 
        esm[ 5, 11] = (2.0 - PHIy) / (1.0 + PHIy) * cz * lzi * lzj / lz1 * 3.0 * L ** 2 
        # = (2.0 - PHIy) * EIz / L / (1.0 + PHIy)
        esm[11,  5] =  1.0 * esm[ 5, 11] 

        # bending around y-axis
        esm[ 2,  2] =  6.0 * cy * (lyi + lyj + 4.0 * lyi * lyj) / ly1 / (1.0 + PHIz)
        # = 12.0 * EIy / L ** 3 / (1.0 + PHIz)
        esm[ 2,  8] = -1.0 * esm[ 2,  2]
        esm[ 8,  2] = -1.0 * esm[ 2,  2]
        esm[ 8,  8] =  1.0 * esm[ 2,  2]

        esm[ 2,  4] = -6.0 * cy * lyi * (1.0 + 2.0 * lyj) * L / ly1 / (1.0 + PHIz)
        # = -6.0 * EIy / L ** 2 / (1.0 + PHIz)
        esm[ 4,  2] =  1.0 * esm[ 2,  4]
        esm[ 4,  8] = -1.0 * esm[ 2,  4]
        esm[ 8,  4] = -1.0 * esm[ 2,  4]

        esm[ 2, 10] = -6.0 * cy * (1.0 + 2.0 * lyi) * lyj * L / ly1 / (1.0 + PHIz)
        # = -6.0 * EIy / L ** 2 / (1.0 + PHIz)
        esm[10,  2] =  1.0 * esm[ 2, 10]
        esm[ 8, 10] = -1.0 * esm[ 2, 10]
        esm[10,  8] = -1.0 * esm[ 2, 10]

        esm[ 4,  4] = (4.0 + PHIz) / (1.0 + PHIz) * cy * lyi * (1.0 + lyj) / ly1 * 3.0 / 2.0 * L ** 2 
        # = (4.0 + PHIz) * EIy / L / (1.0 + PHIz)
        esm[10, 10] = (4.0 + PHIz) / (1.0 + PHIz) * cy * (1.0 + lyi) * lyj / ly1 * 3.0 / 2.0 * L ** 2 
        # =  1.0 * esm[ 4,  4]
        esm[ 4, 10] = (2.0 - PHIz) / (1.0 + PHIz) * cy * lyi * lyj / ly1 * 3.0 * L ** 2 
        # = (2.0 - PHIz) * EIy / L / (1.0 + PHIz)
        esm[10,  4] =  1.0 * esm[ 4, 10]

        # torsion
        esm[ 3,  3] =  GJ / L
        esm[ 3,  9] = -1.0 * esm[ 3,  3]
        esm[ 9,  3] = -1.0 * esm[ 3,  3]
        esm[ 9,  9] =  1.0 * esm[ 3,  3]

        self.cy      =  cy
        self.cz      =  cz
        self.lyi     =  lyi
        self.lyj     =  lyj
        self.lzi     =  lzi
        self.lzj     =  lzj
        self.PHIy    =  PHIy
        self.PHIz    =  PHIz

        return esm

    @staticmethod
    def AssembleAll(elms):
        """Fill ek, tm and ekG for every element at once.

        Same formulas as ElmStiffMX / ElmTransMX, evaluated on stacked arrays
        so the 12x12 products are one BLAS call instead of one per member.
        """

        n = len(elms)
        if n == 0:
            return

        L   = np.empty(n, dtype=np.float64)
        EA  = np.empty(n, dtype=np.float64)
        EIy = np.empty(n, dtype=np.float64)
        EIz = np.empty(n, dtype=np.float64)
        GJ  = np.empty(n, dtype=np.float64)
        PHIy = np.empty(n, dtype=np.float64)
        PHIz = np.empty(n, dtype=np.float64)
        lyi = np.empty(n, dtype=np.float64)
        lzi = np.empty(n, dtype=np.float64)
        lyj = np.empty(n, dtype=np.float64)
        lzj = np.empty(n, dtype=np.float64)
        dx  = np.empty(n, dtype=np.float64)
        dy  = np.empty(n, dtype=np.float64)
        dz  = np.empty(n, dtype=np.float64)
        beta = np.empty(n, dtype=np.float64)

        for k, e in enumerate(elms):
            jnt = e.jnt
            if jnt is None:
                raise RuntimeError("Element {0} has no joint definition".format(e.id))
            mat = e.sec.mat
            L[k]   = e.len
            EA[k]  = mat.E * e.sec.A
            EIy[k] = mat.E * e.sec.Iy
            EIz[k] = mat.E * e.sec.Iz
            GJ[k]  = mat.G * e.sec.J
            PHIy[k] = 12.0 * mat.E * e.sec.Iz / (mat.G * e.sec.Asy * e.len ** 2)
            PHIz[k] = 12.0 * mat.E * e.sec.Iy / (mat.G * e.sec.Asz * e.len ** 2)
            lyi[k] = jnt.Ryi / (mat.E * e.sec.Iy)
            lzi[k] = jnt.Rzi / (mat.E * e.sec.Iz)
            lyj[k] = jnt.Ryj / (mat.E * e.sec.Iy)
            lzj[k] = jnt.Rzj / (mat.E * e.sec.Iz)
            dx[k] = e.n1.x - e.n0.x
            dy[k] = e.n1.y - e.n0.y
            dz[k] = e.n1.z - e.n0.z
            beta[k] = e.beta

        lz1 = 1.0 + lzi + lzj
        ly1 = 1.0 + lyi + lyj
        cz  = EIz / L ** 3
        cy  = EIy / L ** 3
        L2  = L ** 2

        ek = np.zeros((n, 12, 12), dtype=np.float64)
        k00 = EA / L
        ek[:, 0, 0] = k00
        ek[:, 0, 6] = -k00
        ek[:, 6, 0] = -k00
        ek[:, 6, 6] = k00

        k11 = 6.0 * cz * (lzi + lzj + 4.0 * lzi * lzj) / lz1 / (1.0 + PHIy)
        ek[:, 1, 1] = k11
        ek[:, 1, 7] = -k11
        ek[:, 7, 1] = -k11
        ek[:, 7, 7] = k11
        k15 = 6.0 * cz * lzi * (1.0 + 2.0 * lzj) * L / lz1 / (1.0 + PHIy)
        ek[:, 1, 5] = k15
        ek[:, 5, 1] = k15
        ek[:, 5, 7] = -k15
        ek[:, 7, 5] = -k15
        k1b = 6.0 * cz * (1.0 + 2.0 * lzi) * lzj * L / lz1 / (1.0 + PHIy)
        ek[:, 1, 11] = k1b
        ek[:, 11, 1] = k1b
        ek[:, 7, 11] = -k1b
        ek[:, 11, 7] = -k1b
        ek[:, 5, 5] = (4.0 + PHIy) / (1.0 + PHIy) * cz * lzi * (1.0 + lzj) / lz1 * 3.0 / 2.0 * L2
        ek[:, 11, 11] = (4.0 + PHIy) / (1.0 + PHIy) * cz * (1.0 + lzi) * lzj / lz1 * 3.0 / 2.0 * L2
        k5b = (2.0 - PHIy) / (1.0 + PHIy) * cz * lzi * lzj / lz1 * 3.0 * L2
        ek[:, 5, 11] = k5b
        ek[:, 11, 5] = k5b

        k22 = 6.0 * cy * (lyi + lyj + 4.0 * lyi * lyj) / ly1 / (1.0 + PHIz)
        ek[:, 2, 2] = k22
        ek[:, 2, 8] = -k22
        ek[:, 8, 2] = -k22
        ek[:, 8, 8] = k22
        k24 = -6.0 * cy * lyi * (1.0 + 2.0 * lyj) * L / ly1 / (1.0 + PHIz)
        ek[:, 2, 4] = k24
        ek[:, 4, 2] = k24
        ek[:, 4, 8] = -k24
        ek[:, 8, 4] = -k24
        k2a = -6.0 * cy * (1.0 + 2.0 * lyi) * lyj * L / ly1 / (1.0 + PHIz)
        ek[:, 2, 10] = k2a
        ek[:, 10, 2] = k2a
        ek[:, 8, 10] = -k2a
        ek[:, 10, 8] = -k2a
        ek[:, 4, 4] = (4.0 + PHIz) / (1.0 + PHIz) * cy * lyi * (1.0 + lyj) / ly1 * 3.0 / 2.0 * L2
        ek[:, 10, 10] = (4.0 + PHIz) / (1.0 + PHIz) * cy * (1.0 + lyi) * lyj / ly1 * 3.0 / 2.0 * L2
        k4a = (2.0 - PHIz) / (1.0 + PHIz) * cy * lyi * lyj / ly1 * 3.0 * L2
        ek[:, 4, 10] = k4a
        ek[:, 10, 4] = k4a

        # Members with EJNT end springs: the closed-form joint-factor terms
        # above are exact only without shear deformation (PHI -> 0), so
        # rebuild their bending blocks by exact static condensation of a
        # Timoshenko beam with series end springs.
        for k, e in enumerate(elms):
            kyi, kyj, kzi, kzj = element_end_springs(e)
            if kzi is not None or kzj is not None:
                Kz, _ = condense_end_springs(
                    timoshenko_plane_stiffness(EIz[k], L[k], PHIy[k]), kzi, kzj)
                ek[k][np.ix_(PLANE_ROWS_Z, PLANE_ROWS_Z)] = Kz
            if kyi is not None or kyj is not None:
                Ky, _ = condense_end_springs(
                    timoshenko_plane_stiffness(EIy[k], L[k], PHIz[k]), kyi, kyj)
                ek[k][np.ix_(PLANE_ROWS_Y, PLANE_ROWS_Y)] = Ky * np.outer(PLANE_Y_FLIP, PLANE_Y_FLIP)

        k33 = GJ / L
        ek[:, 3, 3] = k33
        ek[:, 3, 9] = -k33
        ek[:, 9, 3] = -k33
        ek[:, 9, 9] = k33

        lx = dx / L
        ly = dy / L
        lz = dz / L
        lm = np.sqrt(lx ** 2 + ly ** 2)
        vert = lm < common.PRES_ZERO
        c = np.cos(beta)
        s = np.sin(beta)

        sub1 = np.zeros((n, 3, 3), dtype=np.float64)
        sub1[:, 0, 0] = 1.0
        sub1[:, 1, 1] = c
        sub1[:, 1, 2] = s
        sub1[:, 2, 1] = -s
        sub1[:, 2, 2] = c

        lm_safe = np.where(vert, 1.0, lm)
        sub2 = np.zeros((n, 3, 3), dtype=np.float64)
        sub2[:, 0, 0] = lx
        sub2[:, 0, 1] = ly
        sub2[:, 0, 2] = lz
        sub2[:, 1, 0] = -ly / lm_safe
        sub2[:, 1, 1] = lx / lm_safe
        sub2[:, 2, 0] = -lx * lz / lm_safe
        sub2[:, 2, 1] = -ly * lz / lm_safe
        sub2[:, 2, 2] = lm
        if np.any(vert):
            sub2[vert] = 0.0
            sub2[vert, 0, 2] = lz[vert]
            sub2[vert, 1, 0] = lz[vert]
            sub2[vert, 2, 1] = 1.0

        sub = np.matmul(sub1, sub2)
        tm = np.zeros((n, 12, 12), dtype=np.float64)
        for i in range(4):
            tm[:, 3 * i:3 * i + 3, 3 * i:3 * i + 3] = sub

        ekG = np.matmul(np.matmul(tm.transpose(0, 2, 1), ek), tm)

        for k, e in enumerate(elms):
            e.ek  = ek[k]
            e.tm  = tm[k]
            e.ekG = ekG[k]
            e.sub_tm1 = sub1[k]
            e.sub_tm2 = sub2[k]
            e.cy   = cy[k]
            e.cz   = cz[k]
            e.lyi  = lyi[k]
            e.lyj  = lyj[k]
            e.lzi  = lzi[k]
            e.lzj  = lzj[k]
            e.PHIy = PHIy[k]
            e.PHIz = PHIz[k]
            if vert[k]:
                e.isVxZ = True

        return

    def SS_ElmStiffMX(self):

        # based on Aoyama and Takemura
        jnt = self.jnt
        if jnt is None:
            raise RuntimeError("Element {0} has no joint definition".format(self.id))

        E    = self.sec.mat.E
        G    = self.sec.mat.G
        A    = self.sec.A
        Iy   = self.sec.Iy
        Iz   = self.sec.Iz
        J    = self.sec.J
        L    = self.len 
        EA   = E * A 
        EIy  = E * Iy 
        EIz  = E * Iz 
        GJ   = G * J  

        # considering shear deformation
        # according to Aoyama
        gy = 6.0 * EIz / (G * self.sec.Asy * L ** 2) 
        gz = 6.0 * EIy / (G * self.sec.Asz * L ** 2) 

        # this considers rigid zone of beam, springs at beams ends
        # Takemura 2009 "Structural Mechanics for Biophysics and Architecture"
        
        K    = np.zeros((12, 12), dtype = np.float64) 
        Ci   = np.zeros(( 6,  6), dtype = np.float64) # coefficient of joint stiffness
        Cj   = np.zeros(( 6,  6), dtype = np.float64)
        H    = np.zeros(( 6,  6), dtype = np.float64) # equilibrium matrix
        Fm   = np.zeros(( 6,  6), dtype = np.float64) 

        Ci[0, 0] = jnt.Txi
        Ci[1, 1] = jnt.Tyi
        Ci[2, 2] = jnt.Tzi
        Ci[3, 3] = jnt.Rxi
        Ci[4, 4] = jnt.Ryi
        Ci[5, 5] = jnt.Rzi 

        Cj[0, 0] = jnt.Txj
        Cj[1, 1] = jnt.Tyj
        Cj[2, 2] = jnt.Tzj
        Cj[3, 3] = jnt.Rxj
        Cj[4, 4] = jnt.Ryj
        Cj[5, 5] = jnt.Rzj
        H[ 0, 0] =  1
        H[ 1, 1] =  1
        H[ 2, 2] =  1
        H[ 3, 3] =  1
        H[ 4, 4] =  1
        H[ 5, 5] =  1
        H[ 4, 2] = -1.0 * L
        H[ 5, 1] =  1.0 * L

        self.Fci = np.linalg.inv(Ci)
        self.Fcj = np.linalg.inv(Cj)

        Fm[0, 0] =   L / EA
        Fm[1, 1] =  (1.0 + 0.5 * gy) * L ** 3 / (3.0 * EIz) # shear term
        Fm[1, 5] =   1.0 * L ** 2 / (2.0 * EIz)
        Fm[2, 2] =  (1.0 + 0.5 * gz) * L ** 3 / (3.0 * EIy) # shear term
        Fm[2, 4] =  -1.0 * L ** 2 / (2.0 * EIy)
        Fm[3, 3] =   L / GJ
        Fm[4, 4] =   L / EIy
        Fm[5, 5] =   L / EIz 
        Fm[4, 2] =   Fm[2, 4]
        Fm[5, 1] =   Fm[1, 5]

        F    =  np.matmul(np.matmul(H.T, self.Fci), H) + Fm + self.Fcj 
        Finv =  np.linalg.inv(F)

        K11  =  np.matmul(np.matmul(H, Finv), H.T)
        K12  = -1.0 * np.matmul(H, Finv)
        K21  =  K12.T 
        K22  =  Finv

        K[0: 6, 0: 6] = K11
        K[0: 6, 6:12] = K12
        K[6:12, 0: 6] = K21
        K[6:12, 6:12] = K22

        return K
        
    def OutputElmInfo(self):

        props = ["ELEM",
            "{0: >6}".format(self.id),
            "{0: >6}".format(self.n0.id),
            "{0: >6}".format(self.n1.id),
            "{0: >6}".format(self.sec.id),
            "{0: >8}".format(self.theta)
            ]
        
        lns = ', '.join(props) + "\n"

        return lns
    
    #@staticmethod
    def DrawForceDiagram(self, _mdl, _lc, disp_fac, div_num):

        #for e in relevant_elms:
        e    = self
        clc  = _mdl.lcs.index(_lc)
        elds = _mdl.elds
        tm = e.tm
        pln = e.pln
        forces = e.forces
        if tm is None or pln is None or forces is None:
            return [[], []]

        els = list(filter(lambda el: (el.clc == clc) and (el.eid == e.id), elds))
        
        lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        for el in els: 

            el_lds = np.array(el.lds).reshape(6, 1)
            if el.isGlobal == True: el_lds = tm[0:6, 0:6] @ el_lds
            for i in range(6): lds[i] += el_lds[i, 0]
        
        if e.glds is not None: lds += e.glds[:, clc]

        if e.alds is not None: lds += e.alds[:, clc]

        vz = pln.vz.v # drawing direction of the element
        if e.isVxZ: vz = -1 * vz
        
        p0 = np.array([e.n0.x, e.n0.y, e.n0.z])
        p1 = np.array([e.n1.x, e.n1.y, e.n1.z])
        
        wzi = lds[2]
        wzj = lds[5]
        
        qzi = forces[2][clc]
        myi = forces[4][clc]
        myj = forces[10][clc]
        w_xc= wzi + (wzj - wzi) * 0.5
        m_xc= myi + qzi * 0.5 * e.len + 1.0 / 6.0 * (wzi + 2.0 * w_xc) * (0.5*e.len)**2 
        mp = 0.5 * p0 + 0.5 * p1 - (disp_fac * m_xc) * vz

        spline_pts = []
        vertical_ln_pts = []
        for i in range(div_num+1):
            t   = i / div_num
            x   = t * e.len
            pt  = (1-t) * p0 + t * p1
            w_x = wzi + (wzj - wzj) * t
            m_x = myi + qzi * x + 1.0 / 6.0 * (wzi + 2.0 * w_x) * x**2

            pt_f = pt - disp_fac * m_x * vz
            #frc_graphics.append(vedo.Line(pt, pt_f, lw=self.size["line-weight-thin"], c=self.colors["force-d"]))
            spline_pts.append(pt_f) 
            vertical_ln_pts.append((pt, pt_f))

        #frc_graphics.append(vedo.KSpline(spline_pts).color(self.colors["force-d"]).lw(self.size["line-weight-thin"]))
        
        return [spline_pts, vertical_ln_pts]