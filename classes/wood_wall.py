import math

import common
from dat_format import WWLL_FMTS, record_line
from ejnt import EJnt
from elm import Elm1D
from mat import Mat
from sec import Sec
from diaphragm import DiaphragmConnection


WOOD_WALL_MODEL_SHEAR_PANEL = "SHEAR_PANEL"
WOOD_WALL_MODEL_EQ_BRACE = "EQUIVALENT_BRACE"
WOOD_WALL_MODEL_MEMBRANE = "MEMBRANE_WALL"

WWLL_MODEL_BRACE = 0
WWLL_MODEL_PANEL = 1
WWLL_MODEL_MEMBRANE = 2
WWLL_DIR_X = 0
WWLL_DIR_Y = 1
WWLL_LAYO_SINGLE = 0
WWLL_LAYO_X = 1


def wwll_model_from_code(code):
    mapping = {
        WWLL_MODEL_BRACE: WOOD_WALL_MODEL_EQ_BRACE,
        WWLL_MODEL_PANEL: WOOD_WALL_MODEL_SHEAR_PANEL,
        WWLL_MODEL_MEMBRANE: WOOD_WALL_MODEL_MEMBRANE,
    }
    try:
        return mapping[int(code)]
    except (KeyError, ValueError, TypeError):
        raise ValueError("Unknown WWLL MODEL code: {0}".format(code))


def wwll_model_to_code(model):
    mapping = {
        WOOD_WALL_MODEL_EQ_BRACE: WWLL_MODEL_BRACE,
        WOOD_WALL_MODEL_SHEAR_PANEL: WWLL_MODEL_PANEL,
        WOOD_WALL_MODEL_MEMBRANE: WWLL_MODEL_MEMBRANE,
    }
    m = str(model).strip().upper()
    if m not in mapping:
        raise ValueError("Unknown WWLL MODEL: {0}".format(model))
    return mapping[m]


def wwll_dir_from_code(code):
    c = int(code)
    if c == WWLL_DIR_X:
        return "X"
    if c == WWLL_DIR_Y:
        return "Y"
    raise ValueError("Unknown WWLL DIR code: {0}".format(code))


def wwll_dir_to_code(direction):
    d = str(direction).strip().upper()
    if d == "X":
        return WWLL_DIR_X
    if d == "Y":
        return WWLL_DIR_Y
    raise ValueError("Unknown WWLL DIR: {0}".format(direction))


def wwll_layo_from_code(code):
    c = int(code)
    if c == WWLL_LAYO_SINGLE:
        return "SINGLE"
    if c == WWLL_LAYO_X:
        return "X"
    raise ValueError("Unknown WWLL LAYO code: {0}".format(code))


def wwll_layo_to_code(layout):
    return WWLL_LAYO_X if str(layout).strip().upper() == "X" else WWLL_LAYO_SINGLE


def _horizontal_distance(na, nb):
    return math.hypot(na.x - nb.x, na.y - nb.y)


def wwll_length_height_from_nodes(n1, n2, n3, n4):
    """Compute wall length and height from four corner nodes [m].

    Bottom/top corners are identified by Z level so N1..N4 ordering may follow
    either the documented bottom-line convention or the diagonal brace layout.
    """
    nodes = [n1, n2, n3, n4]
    z_min = min(n.z for n in nodes)
    z_max = max(n.z for n in nodes)
    tol = common.PRES_LEN

    if z_max - z_min < tol:
        raise ValueError("WOOD_RATED_WALL nodes must span a positive height")

    bottom = [n for n in nodes if n.z <= z_min + tol]
    top = [n for n in nodes if n.z >= z_max - tol]
    if len(bottom) != 2 or len(top) != 2:
        raise ValueError(
            "WOOD_RATED_WALL nodes must form a vertical rectangle "
            "(two bottom corners and two top corners)"
        )

    bottom_len = _horizontal_distance(bottom[0], bottom[1])
    top_len = _horizontal_distance(top[0], top[1])
    length = 0.5 * (bottom_len + top_len)
    height = z_max - z_min

    if length < tol:
        raise ValueError("WOOD_RATED_WALL computed length is not positive")
    if height < tol:
        raise ValueError("WOOD_RATED_WALL computed height is not positive")

    return length, height


def _node_xyz(node):
    if hasattr(node, "x"):
        return float(node.x), float(node.y), float(node.z)
    return float(node[0]), float(node[1]), float(node[2])


def order_wwll_corner_node_ids(node_ids, nodes_by_id):
    """Reorder WRW corners to N1..N4 CCW rectangle convention.

    N1,N2: bottom edge left-to-right along wall length.
    N3: top corner above N2; N4: top corner above N1.
    This matches GUI quads and X-brace pairs (N1-N3, N2-N4).
    """
    if len(node_ids) != 4:
        raise ValueError("order_wwll_corner_node_ids requires exactly 4 node ids")
    if len(set(node_ids)) != 4:
        raise ValueError("WRW nodes must be distinct")

    entries = []
    for nid in node_ids:
        node = nodes_by_id.get(int(nid))
        if node is None:
            raise ValueError("WOOD_RATED_WALL node id not found: {0}".format(nid))
        x, y, z = _node_xyz(node)
        entries.append((int(nid), x, y, z))

    z_vals = [z for _, _, _, z in entries]
    z_min = min(z_vals)
    z_max = max(z_vals)
    tol = common.PRES_LEN
    if z_max - z_min < tol:
        raise ValueError("WOOD_RATED_WALL nodes must span a positive height")

    bottom = [item for item in entries if item[3] <= z_min + tol]
    top = [item for item in entries if item[3] >= z_max - tol]
    if len(bottom) != 2 or len(top) != 2:
        raise ValueError(
            "WOOD_RATED_WALL nodes must form a vertical rectangle "
            "(two bottom corners and two top corners)"
        )

    dx = abs(bottom[0][1] - bottom[1][1])
    dy = abs(bottom[0][2] - bottom[1][2])
    direction = 0 if dx >= dy else 1
    axis = 0 if direction == 0 else 1

    def along_coord(item):
        return item[1] if axis == 0 else item[2]

    bottom.sort(key=along_coord)
    top.sort(key=along_coord)

    n1 = bottom[0][0]
    n2 = bottom[1][0]

    def nearest_top(bottom_item, top_items):
        target = along_coord(bottom_item)
        return min(top_items, key=lambda item: abs(along_coord(item) - target))

    top_for_n1 = nearest_top(bottom[0], top)
    top_for_n2 = nearest_top(bottom[1], top)
    if top_for_n1[0] == top_for_n2[0]:
        top.sort(key=along_coord)
        top_for_n1, top_for_n2 = top[0], top[1]

    n4 = top_for_n1[0]
    n3 = top_for_n2[0]
    return n1, n2, n3, n4, direction


def _next_id(seq):
    ids = [x.id for x in seq] if seq else []
    return (max(ids) + 1) if ids else 1


class WoodRatedWall:
    """High-level wood rated wall definition (multiplier-based input)."""

    def __init__(self, _id, _name, _multiplier, _length, _height, _direction,
                 _reference_drift=1.0 / 120.0,
                 _model=WOOD_WALL_MODEL_EQ_BRACE,
                 _n1=None, _n2=None, _n3=None, _n4=None,
                 _brace_layout="X", _diap_id=None, _dcon_tol=common.PRES_LEN):
        self.id = int(_id)
        self.name = str(_name).strip()
        self.multiplier = float(_multiplier)
        self.length_input = float(_length) if _length is not None else None  # [m]
        self.height_input = float(_height) if _height is not None else None  # [m]
        self.length = None
        self.height = None
        self.length_from_nodes = None
        self.height_from_nodes = None
        self.direction = str(_direction).strip().upper()
        self.reference_drift = float(_reference_drift)
        self.model_requested = str(_model).strip().upper()
        self.model_active = self.model_requested
        self.n1 = int(_n1) if _n1 is not None else None
        self.n2 = int(_n2) if _n2 is not None else None
        self.n3 = int(_n3) if _n3 is not None else None
        self.n4 = int(_n4) if _n4 is not None else None
        self.brace_layout = str(_brace_layout).strip().upper()
        self.diap_id = int(_diap_id) if _diap_id is not None else None
        self.dcon_tol = float(_dcon_tol)
        self.generated_elem_ids = []
        self.generated_shear_panel_ids = []
        self.generated_mat_id = None
        self.generated_sec_id = None

        if self.multiplier <= 0.0:
            raise ValueError("WOOD_RATED_WALL multiplier must be positive")
        if self.length_input is not None and self.length_input <= 0.0:
            raise ValueError("WOOD_RATED_WALL length must be positive")
        if self.height_input is not None and self.height_input <= 0.0:
            raise ValueError("WOOD_RATED_WALL height must be positive")
        if self.reference_drift <= 0.0:
            raise ValueError("WOOD_RATED_WALL RA must be positive")
        if self.direction not in ["X", "Y"]:
            raise ValueError("WOOD_RATED_WALL direction must be X or Y")

    def resolve_length_height(self, nds):
        """Resolve L/H from explicit input and/or corner nodes."""
        warnings = []
        needs_nodes = self.length_input is None or self.height_input is None

        if needs_nodes and not all(v is not None for v in [self.n1, self.n2, self.n3, self.n4]):
            raise ValueError(
                "WOOD_RATED_WALL {0} requires N1..N4 when L or H is omitted".format(self.id)
            )

        geom_l = None
        geom_h = None
        if all(v is not None for v in [self.n1, self.n2, self.n3, self.n4]):
            by_node = {n.id: n for n in nds}
            corner_nodes = [by_node.get(self.n1), by_node.get(self.n2),
                            by_node.get(self.n3), by_node.get(self.n4)]
            if any(n is None for n in corner_nodes):
                raise ValueError("WOOD_RATED_WALL {0} node id not found".format(self.id))
            geom_l, geom_h = wwll_length_height_from_nodes(*corner_nodes)
            self.length_from_nodes = geom_l
            self.height_from_nodes = geom_h

        if self.length_input is None:
            if geom_l is None:
                raise ValueError(
                    "WOOD_RATED_WALL {0} requires N1..N4 to derive omitted L".format(self.id)
                )
            self.length = geom_l
        else:
            self.length = self.length_input

        if self.height_input is None:
            if geom_h is None:
                raise ValueError(
                    "WOOD_RATED_WALL {0} requires N1..N4 to derive omitted H".format(self.id)
                )
            self.height = geom_h
        else:
            self.height = self.height_input

        tol = common.PRES_LEN
        if geom_l is not None and self.length_input is not None:
            if abs(self.length - geom_l) > tol:
                warnings.append(
                    "WOOD_RATED_WALL {0} ({1}): input L={2:.4f} m differs from "
                    "node geometry {3:.4f} m; using input value.".format(
                        self.id, self.name, self.length, geom_l
                    )
                )
        if geom_h is not None and self.height_input is not None:
            if abs(self.height - geom_h) > tol:
                warnings.append(
                    "WOOD_RATED_WALL {0} ({1}): input H={2:.4f} m differs from "
                    "node geometry {3:.4f} m; using input value.".format(
                        self.id, self.name, self.height, geom_h
                    )
                )

        if self.length <= 0.0 or self.height <= 0.0:
            raise ValueError("WOOD_RATED_WALL length/height must be positive")

        return warnings

    def _require_dims(self) -> tuple[float, float]:
        if self.length is None or self.height is None:
            raise ValueError(
                "WOOD_RATED_WALL {0} length/height not resolved; "
                "call resolve_length_height first".format(self.id)
            )
        return self.length, self.height

    @property
    def qa_kN(self):
        # Qa = 1.96 * m * L  [kN]
        length, _ = self._require_dims()
        return 1.96 * self.multiplier * length

    @property
    def delta(self):
        # Delta = RA * H [m]
        _, height = self._require_dims()
        return self.reference_drift * height

    @property
    def k_n_per_m(self):
        # K = Qa / Delta, Qa in N.
        return (self.qa_kN * 1e3) / self.delta

    @property
    def diagonal_length(self):
        length, height = self._require_dims()
        return math.sqrt(length ** 2 + height ** 2)

    def equivalent_brace_ea(self, brace_count=1):
        length, height = self._require_dims()
        d = math.sqrt(length ** 2 + height ** 2)
        ea_total = self.k_n_per_m * d ** 3 / max(length ** 2, common.PRES_ZERO)
        return ea_total / max(brace_count, 1)

    def output_info(self):
        values = [
            self.id,
            self.name,
            wwll_model_to_code(self.model_requested),
            self.multiplier,
            self.length,
            self.height,
            wwll_dir_to_code(self.direction),
            self.reference_drift,
            "" if self.n1 is None else self.n1,
            "" if self.n2 is None else self.n2,
            "" if self.n3 is None else self.n3,
            "" if self.n4 is None else self.n4,
            "" if self.diap_id is None else self.diap_id,
            wwll_layo_to_code(self.brace_layout),
        ]
        return record_line("WWLL", WWLL_FMTS, values) + "\n"

    def generate_mvp_equivalent_braces(self, nds, mats, secs, elms, ejnts, dcons):
        if self.model_requested == WOOD_WALL_MODEL_MEMBRANE:
            raise ValueError("MEMBRANE_WALL is reserved for future implementation")
        if self.model_requested == WOOD_WALL_MODEL_SHEAR_PANEL:
            raise ValueError("use generate_shear_panel() for SHEAR_PANEL model")

        if not all(v is not None for v in [self.n1, self.n2, self.n3, self.n4]):
            raise ValueError("WOOD_RATED_WALL requires N1,N2,N3,N4 in MVP")

        by_node = {n.id: n for n in nds}
        n1 = by_node.get(self.n1)
        n2 = by_node.get(self.n2)
        n3 = by_node.get(self.n3)
        n4 = by_node.get(self.n4)
        if any(n is None for n in [n1, n2, n3, n4]):
            raise ValueError("WOOD_RATED_WALL node id not found")

        brace_pairs = [(n1, n3), (n2, n4)] if self.brace_layout == "X" else [(n1, n3)]
        ea_each = self.equivalent_brace_ea(len(brace_pairs))

        if mats:
            e = mats[0].E
            g = mats[0].G
            gamma = mats[0].gamma
            alpha = mats[0].alpha
            fy = mats[0].fy
        else:
            e = 9.5e9
            g = e / 2.6
            gamma = 5.0e3
            alpha = 3.0e-6
            fy = 20.0e6

        a = max(ea_each / max(e, common.PRES_ZERO), 1e-8)
        side = math.sqrt(a)

        mid = _next_id(mats)
        sid = _next_id(secs)
        mat = Mat(mid, "WRW_MAT_{0}".format(self.id), e, g, gamma, alpha, fy)
        sec = Sec(sid, "WRW_SEC_{0}".format(self.id), mat, 0, [side, side])
        mat.auto_generated = True
        sec.auto_generated = True
        mats.append(mat)
        secs.append(sec)
        self.generated_mat_id = mid
        self.generated_sec_id = sid

        eid = _next_id(elms)
        for na, nb in brace_pairs:
            eobj = Elm1D(eid, na, nb, sec, 0.0)
            eobj.auto_generated = True
            eobj.generated_from = "WOOD_RATED_WALL"
            eobj.generated_from_id = self.id
            elms.append(eobj)
            self.generated_elem_ids.append(eid)
            # near-pin both ends to represent axial-only brace behavior.
            ej = EJnt(eid, [1e-6, 1e-6, 1e-6, 1e-6])
            ej.auto_generated = True
            ejnts.append(ej)
            if self.diap_id is not None:
                dc = DiaphragmConnection(
                    self.diap_id, "MEMBER", eid, "CONNECTED_RIGID", self.dcon_tol
                )
                dc.auto_generated = True
                dcons.append(dc)
            eid += 1

    def generate_shear_panel(self, nds, wshears, dcons):
        if self.model_requested == WOOD_WALL_MODEL_MEMBRANE:
            raise ValueError("MEMBRANE_WALL is reserved for future implementation")
        if not all(v is not None for v in [self.n1, self.n2, self.n3, self.n4]):
            raise ValueError("WOOD_RATED_WALL requires N1,N2,N3,N4 for SHEAR_PANEL")

        by_node = {n.id: n for n in nds}
        n1 = by_node.get(self.n1)
        n2 = by_node.get(self.n2)
        n3 = by_node.get(self.n3)
        n4 = by_node.get(self.n4)
        if any(n is None for n in [n1, n2, n3, n4]):
            raise ValueError("WOOD_RATED_WALL node id not found")

        self.model_active = WOOD_WALL_MODEL_SHEAR_PANEL
        pid = _next_id(wshears)
        panel = WoodShearPanel(pid, self.id, self.name, n1, n2, n3, n4, self.direction, self.k_n_per_m)
        panel.auto_generated = True
        wshears.append(panel)
        self.generated_shear_panel_ids.append(pid)

        if self.diap_id is not None:
            # Tie wall top nodes to diaphragm using existing MPC pipeline.
            for nid in [self.n3, self.n4]:
                dc = DiaphragmConnection(
                    self.diap_id, "NODE", nid, "CONNECTED_RIGID", self.dcon_tol
                )
                dc.auto_generated = True
                dcons.append(dc)


class WoodShearPanel:
    """Equivalent shear panel on a wall rectangle."""

    def __init__(self, _id, _wall_id, _name, _n1, _n2, _n3, _n4, _direction, _k_n_per_m):
        self.id = int(_id)
        self.wall_id = int(_wall_id)
        self.name = str(_name)
        self.n1 = _n1
        self.n2 = _n2
        self.n3 = _n3
        self.n4 = _n4
        self.direction = str(_direction).upper()
        self.k = float(_k_n_per_m)  # [N/m]
        self.auto_generated = False

    def nodes(self):
        return [self.n1, self.n2, self.n3, self.n4]

    def _plane(self):
        """In-plane unit vectors a (along the bottom edge) and b (up the panel), top nodes, L, H."""

        nodes = sorted(self.nodes(), key=lambda n: n.z)
        bottom, top = nodes[:2], nodes[2:]
        edge = (bottom[1].x - bottom[0].x, bottom[1].y - bottom[0].y, bottom[1].z - bottom[0].z)
        edge_length = math.sqrt(sum(v * v for v in edge))
        if edge_length <= 0.0:
            raise ValueError("WoodShearPanel {0} has no width at the bottom".format(self.wall_id))
        a = tuple(v / edge_length for v in edge)

        rise = tuple(
            (getattr(top[0], c) + getattr(top[1], c) - getattr(bottom[0], c) - getattr(bottom[1], c)) / 2.0
            for c in "xyz"
        )
        along = sum(r * v for r, v in zip(rise, a))
        offset = tuple(r - along * v for r, v in zip(rise, a))
        height = math.sqrt(sum(v * v for v in offset))
        if height <= 0.0:
            raise ValueError("WoodShearPanel {0} corners do not form a wall".format(self.wall_id))
        b = tuple(v / height for v in offset)

        span = abs(sum((getattr(top[1], c) - getattr(top[0], c)) * v for c, v in zip("xyz", a)))
        if span <= 0.0:
            raise ValueError("WoodShearPanel {0} has no width at the top".format(self.wall_id))
        return a, b, top, span, height

    def stiffness_weights(self):
        """Weights of (ux, uy, uz) at each node in the panel's shear deformation.

        delta = (avg top - avg bottom along a) + (H/L)(right top - left top along b)
        with a along the bottom edge and b in the panel plane, which is vertical for
        a wall. Rigid motions give zero, so the panel stays in moment equilibrium.
        The couple enters at the top corners, so each end column carries the full
        Q*H/L over its height, as with an equivalent brace.
        """

        a, b, top, span, height = self._plane()
        ratio = height / span
        right = max(top, key=lambda n: n.x * a[0] + n.y * a[1] + n.z * a[2])
        weights = []
        for node in self.nodes():
            is_top = any(node is n for n in top)
            horizontal = 0.5 if is_top else -0.5
            across = 0.0
            if is_top:
                across = ratio if node is right else -ratio
            weights.extend(horizontal * a[i] + across * b[i] for i in range(3))
        return weights

    def shear_force(self, clc):
        """Panel shear force [N] for a computational load case."""

        weights = self.stiffness_weights()
        delta = 0.0
        for i, node in enumerate(self.nodes()):
            for d in range(3):
                delta += weights[3 * i + d] * float(node.disps[d, clc])
        return self.k * delta

    def direction_matches_wall(self):
        a = self._plane()[0]
        return abs(a[0] if self.direction == "X" else a[1]) >= math.sqrt(0.5) * math.hypot(a[0], a[1])
