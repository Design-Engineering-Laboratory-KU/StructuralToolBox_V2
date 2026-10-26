import datetime

from nd   import Nd
from elm  import Elm1D
from ejnt import EJnt
from mat  import Mat
from sec  import Sec
from cons import Cons
from ld   import PLd, ELd, ALd, GLd, Lcase, Lcmb, diagram_wsegs
from mdl  import Mdl
from axis import Axis
from plt  import Plt 
from diaphragm import (
    DiaphragmMaterial, DiaphragmRegion, DiaphragmPolygon, DiaphragmOpening,
    CSTMembrane3, DiaphragmConnection, DiaphragmLoad,
    TIMBER_FLOOR, TIMBER_ROOF, TIMBER_REFERENCE_DRIFT,
    DIAP_RIGID, DIAP_FLEXIBLE,
    DIAP_SRC_DMAT, DIAP_SRC_TIMBER_FLOOR, DIAP_SRC_TIMBER_ROOF,
    make_timber_diaphragm_material,
    diap_type_from_code, diap_src_from_code,
    dcon_trgt_from_code, dcon_conn_from_code,
    dlod_type_from_code,
    ensure_diaphragm_dregs, collect_diaphragm_input_warnings,
)
from wood_wall import (
    WoodRatedWall,
    WOOD_WALL_MODEL_SHEAR_PANEL,
    WWLL_LAYO_X,
    wwll_model_from_code, wwll_dir_from_code, wwll_layo_from_code,
)
import common


def _mdl_items(value):
    return value if value is not None else []


def _clean_items(line):
    return [item.strip() for item in line.split(',')]


def _opt_val(items, idx, default=None):
    if len(items) <= idx or items[idx] == "":
        return default
    return items[idx]


def _opt_int(items, idx, default=None):
    v = _opt_val(items, idx)
    if v is None:
        return default
    return int(v)


def _opt_float(items, idx, default=None):
    v = _opt_val(items, idx)
    if v is None:
        return default
    return float(v)


def _lookup_index_error(by_id, id_value, label):
    try:
        return by_id[id_value]
    except KeyError:
        raise IndexError("{0} id not found: {1}".format(label, id_value)) from None


def _find_by_id(by_id, id_value, label):
    if id_value not in by_id:
        raise ValueError("{0} id not found: {1}".format(label, id_value))
    return by_id[id_value]


def _register_unique_id(by_id, id_value, record_type, obj):
    if id_value in by_id:
        raise ValueError("duplicate {0} id: {1}".format(record_type, id_value))
    by_id[id_value] = obj


def _next_dmat_id(dmats_by_id, used_ids):
    ids = list(dmats_by_id.keys()) + list(used_ids)
    return (max(ids) + 1) if ids else 1


def ReadLines(_lns):

    nds   = []
    elms  = []
    ejnts = []
    mats  = []
    secs  = []
    cons  = []
    lds   = [] 
    elds  = []
    alds  = []
    glds  = []
    axes  = []
    plts  = []
    lcases= []
    lcmbs = []
    dmats = []
    diaps = []
    dregs = []
    dopns = []
    dcons = []
    dloads = []
    wwalls = []
    wshears = []
    dmem_specs = []
    nds_by_id = {}
    elms_by_id = {}
    mats_by_id = {}
    secs_by_id = {}
    dmats_by_id = {}
    diaps_by_id = {}
    dmem_by_id = {}
    auto_dmat_ids = set()
    input_warnings = []

    for i in range(len(_lns)):

        l = _lns[i]

        if l.startswith('#'): continue

        items = _clean_items(l)
        key = items[0].upper() if items and items[0] else ""

        if key == "MATE":

            id   =   int(items[1])
            name =   str(items[2]).strip()
            e    = float(items[3]) * 1e6  # [N/mm2] -> [N/m2] 
            g    = float(items[4]) * 1e6  # [N/mm2] -> [N/m2] 
            gm   = float(items[5]) * 1e3  # [kN/m3] -> [N/m3] 
            al   = float(items[6])
            fy   = float(items[7]) * 1e6  # [N/mm2] -> [N/m2] 

            mat_obj = Mat(id, name, e, g, gm, al, fy)
            _register_unique_id(mats_by_id, id, "MATE", mat_obj)
            mats.append(mat_obj)

        elif key == "DMAT":

            id    = int(items[1])
            name  = str(items[2]).strip()
            ex    = float(items[3]) * 1e6  # [N/mm2] -> [N/m2]
            ey    = float(items[4]) * 1e6  # [N/mm2] -> [N/m2]
            gxy   = float(items[5]) * 1e6  # [N/mm2] -> [N/m2]
            nuxy  = float(items[6])
            gamma = float(items[7]) * 1e3 if len(items) > 7 and items[7] != "" else 0.0
            alpha = float(items[8]) if len(items) > 8 and items[8] != "" else 0.0

            dmat_obj = DiaphragmMaterial(id, name, ex, ey, gxy, nuxy, gamma, alpha)
            _register_unique_id(dmats_by_id, id, "DMAT", dmat_obj)
            dmats.append(dmat_obj)

        elif key == "SECT":

            id   = int(items[1])
            name = str(items[2]).strip()
            mat  = _lookup_index_error(mats_by_id, int(items[3]), "MATE")
            type = int(items[4])
            dims = list(map(lambda d: float(d) * 1e-3, items[5:])) # [mm] -> [m]
            
            sec_obj = Sec(id, name, mat, type, dims)
            _register_unique_id(secs_by_id, id, "SECT", sec_obj)
            secs.append(sec_obj)

        elif key == "NODE":

            id =   int(items[1]) 
            x  = float(items[2]) # [m]
            y  = float(items[3]) # [m]
            z  = float(items[4]) # [m]

            nd_obj = Nd(id, x, y, z)
            _register_unique_id(nds_by_id, id, "NODE", nd_obj)
            nds.append(nd_obj)

        elif key == "ELEM":

            id  = int(items[1])
            n0  = _lookup_index_error(nds_by_id, int(items[2]), "NODE")
            n1  = _lookup_index_error(nds_by_id, int(items[3]), "NODE")
            sec = _lookup_index_error(secs_by_id, int(items[4]), "SECT")
            if len(items) > 5:
                theta = float(items[5])
            else:
                theta = 0.0

            elm_obj = Elm1D(id, n0, n1, sec, theta)
            _register_unique_id(elms_by_id, id, "ELEM", elm_obj)
            elms.append(elm_obj) 

        elif key == "EJNT":

            eid  = int(items[1])
            jnts: list[float | None] = [0.0] * 4

            #for i in range(12):
            for i in range(4):
                try:
                    jnts[i] = float(items[i+2]) * 1e3 # [kNm/rad] -> [kNm2/rad] or [kNm] -> [Nm]
                except ValueError:
                    jnts[i] = None  

            ejnts.append(EJnt(eid, jnts))

        elif key == "DIAP":

            id   = int(items[1])
            name = str(items[2]).strip()
            dtype = diap_type_from_code(items[3])
            src = int(items[4])
            mag_raw = _opt_val(items, 5)
            thick_mm = _opt_float(items, 6)
            theta = _opt_float(items, 7, 0.0)
            reference_drift = _opt_float(items, 8, TIMBER_REFERENCE_DRIFT)
            hmax_mm = _opt_float(items, 9)
            hmax = hmax_mm * 1e-3 if hmax_mm is not None else None

            if src in [DIAP_SRC_TIMBER_FLOOR, DIAP_SRC_TIMBER_ROOF]:
                if mag_raw is None:
                    raise ValueError("DIAP timber source requires MAG/ID multiplier")
                source = diap_src_from_code(src)
                timber_multiplier = float(mag_raw)
                thick = thick_mm * 1e-3 if thick_mm is not None else 1.0
                mat_id = _next_dmat_id(dmats_by_id, auto_dmat_ids)
                auto_dmat_ids.add(mat_id)
                mat = make_timber_diaphragm_material(
                    mat_id, "{0}_{1}".format(name, source), source,
                    timber_multiplier, reference_drift, 0.0, thick
                )
                dmats_by_id[mat_id] = mat
                dmats.append(mat)
                diap_obj = DiaphragmRegion(
                    id, name, dtype, mat, thick, theta,
                    source, hmax, reference_drift, timber_multiplier
                )
                _register_unique_id(diaps_by_id, id, "DIAP", diap_obj)
                diaps.append(diap_obj)
                continue

            if src != DIAP_SRC_DMAT:
                raise ValueError("Unknown DIAP SRC code: {0}".format(src))

            if dtype in [DIAP_RIGID, DIAP_FLEXIBLE]:
                thick = thick_mm * 1e-3 if thick_mm is not None else None
                diap_obj = DiaphragmRegion(
                    id, name, dtype, None, thick, theta, "DMAT", hmax, None, None
                )
                _register_unique_id(diaps_by_id, id, "DIAP", diap_obj)
                diaps.append(diap_obj)
                continue

            if mag_raw is None:
                raise ValueError("DIAP DMAT source requires MAG/ID (DMAT id)")
            if thick_mm is None:
                raise ValueError("DIAP thickness is required")

            mat_id = int(mag_raw)
            thick = thick_mm * 1e-3
            mat = _find_by_id(dmats_by_id, mat_id, "DMAT")
            diap_obj = DiaphragmRegion(id, name, dtype, mat, thick, theta)
            _register_unique_id(diaps_by_id, id, "DIAP", diap_obj)
            diaps.append(diap_obj)

        elif key == "DREG":

            diap_id = int(items[1])
            node_ids = [int(v) for v in items[2:] if v != ""]
            dregs.append(DiaphragmPolygon(diap_id, node_ids))

        elif key == "DOPN":

            diap_id = int(items[1])
            node_ids = [int(v) for v in items[2:] if v != ""]
            dopns.append(DiaphragmOpening(diap_id, node_ids))

        elif key == "DMEM":

            id = int(items[1])
            diap_id = int(items[2])
            nids = [int(items[3]), int(items[4]), int(items[5])]
            _register_unique_id(dmem_by_id, id, "DMEM", nids)
            dmem_specs.append((id, diap_id, nids))

        elif key == "DCON":

            diap_id = int(items[1])
            target_type = dcon_trgt_from_code(items[2])
            target_id = _opt_int(items, 3)
            conn_code = _opt_int(items, 4, 0)
            connection_type = dcon_conn_from_code(conn_code)
            tolerance = _opt_float(items, 5, common.PRES_LEN)
            spacing = _opt_float(items, 6)

            dcons.append(DiaphragmConnection(
                diap_id, target_type, target_id, connection_type,
                tolerance, spacing
            ))

        elif key == "DLOD":

            diap_id = int(items[1])
            lc = int(items[2])
            load_type = dlod_type_from_code(items[3])

            if load_type == DiaphragmLoad.AREA:
                px = float(items[4])
                py = float(items[5])
                dloads.append(DiaphragmLoad(diap_id, lc, load_type, px * 1e3, py * 1e3))
            elif load_type == DiaphragmLoad.LINE:
                node_ids = [int(items[4]), int(items[5])]
                px = float(items[6])
                py = float(items[7])
                dloads.append(DiaphragmLoad(diap_id, lc, load_type, px * 1e3, py * 1e3, node_ids))
            elif load_type == DiaphragmLoad.MEMBER_TRANSFER:
                member_id = int(items[4])
                px = float(items[5])
                py = float(items[6])
                dloads.append(DiaphragmLoad(diap_id, lc, load_type, px * 1e3, py * 1e3, None, member_id))
            elif load_type == DiaphragmLoad.MASS:
                mass = float(items[4])
                ax = float(items[5])
                ay = float(items[6])
                dloads.append(DiaphragmLoad(
                    diap_id, lc, load_type, 0.0, 0.0, None, None, mass, 0.0, ax, ay
                ))
            elif load_type == DiaphragmLoad.WEIGHT:
                weight = float(items[4])
                ax = float(items[5])
                ay = float(items[6])
                dloads.append(DiaphragmLoad(
                    diap_id, lc, load_type, 0.0, 0.0, None, None, 0.0, weight * 1e3, ax, ay
                ))

        elif key == "WWLL":

            wid = int(items[1])
            name = str(items[2]).strip()
            model = wwll_model_from_code(items[3])
            multiplier = float(items[4])
            length = _opt_float(items, 5)
            height = _opt_float(items, 6)
            direction = wwll_dir_from_code(items[7])
            ra = _opt_float(items, 8, 1.0 / 120.0)
            n1 = _opt_int(items, 9)
            n2 = _opt_int(items, 10)
            n3 = _opt_int(items, 11)
            n4 = _opt_int(items, 12)
            diap_id = _opt_int(items, 13)
            layo = _opt_int(items, 14, WWLL_LAYO_X)
            brace_layout = wwll_layo_from_code(layo)

            wwalls.append(WoodRatedWall(
                wid, name, multiplier, length, height, direction, ra, model,
                n1, n2, n3, n4, brace_layout, diap_id, common.PRES_LEN
            ))

        elif key == "CONS":

            nid =      int(items[1])
            tx  = bool(int(items[2]))
            ty  = bool(int(items[3]))
            tz  = bool(int(items[4]))
            rx  = bool(int(items[5]))
            ry  = bool(int(items[6]))
            rz  = bool(int(items[7]))

            cons.append(Cons(nid, tx, ty, tz, rx, ry, rz))

        elif key == "PLOD":

            nid =   int(items[1])
            lc  =   int(items[2])
            px  = float(items[3]) * 1e3 # [kN]  --> [N]
            py  = float(items[4]) * 1e3 # [kN]  --> [N]
            pz  = float(items[5]) * 1e3 # [kN]  --> [N]
            mx  = float(items[6]) * 1e3 # [kNm] --> [Nm]
            my  = float(items[7]) * 1e3 # [kNm] --> [Nm]
            mz  = float(items[8]) * 1e3 # [kNm] --> [Nm]

            lds.append(PLd(nid, lc, px, py, pz, mx, my, mz)) 

        elif key == "ELOD":

            eid =   int(items[1])
            lc  =   int(items[2])
            isGlobal = int(items[3])
            wxi  = float(items[4]) * 1e3 # [kN/m] --> [N/m]
            wyi  = float(items[5]) * 1e3 # [kN/m] --> [N/m]
            wzi  = float(items[6]) * 1e3 # [kN/m] --> [N/m]
            wxj  = float(items[7]) * 1e3 # [kN/m] --> [N/m]
            wyj  = float(items[8]) * 1e3 # [kN/m] --> [N/m]
            wzj  = float(items[9]) * 1e3 # [kN/m] --> [N/m]

            # optional load range T0, T1 (both or neither; empty = missing)
            try:
                t0 = _opt_float(items, 10)
                t1 = _opt_float(items, 11)
            except ValueError:
                raise ValueError(
                    "ELOD on ELEM {0}: T0, T1 must be numbers".format(eid)) from None
            if (t0 is None) != (t1 is None):
                raise ValueError(
                    "ELOD on ELEM {0}: T0 and T1 must be given together".format(eid))
            if t0 is None:
                t0, t1 = 0.0, 1.0

            elds.append(ELd(eid, lc, isGlobal, wxi, wyi, wzi, wxj, wyj, wzj, False, t0, t1)) 

        elif key == "ALOD":

            lc = int(items[1])
            px = float(items[2]) * 1e3 # [kN/m2] --> [N/m2]
            py = float(items[3]) * 1e3 # [kN/m2] --> [N/m2]
            pz = float(items[4]) * 1e3 # [kN/m2] --> [N/m2]
            e1 = int(items[5])
            e2 = int(items[6])
            e3 = int(items[7])

            if len(items) > 8:
                e4 = int(items[8])
            else:
                e4 = None

            alds.append(ALd(lc, px, py, pz, e1, e2, e3, e4))
        
        elif key == "GLOD":

            lc =   int(items[1])
            gx = float(items[2])
            gy = float(items[3])
            gz = float(items[4])

            glds.append(GLd(lc, gx, gy, gz))

        elif key == "LNME":
            from load_case_types import parse_lnme_fields

            lid = int(items[1])
            label = str(items[3]).strip() if len(items) > 3 else ""
            load_type, label = parse_lnme_fields(items[2], label)
            lcases.append(Lcase(lid, load_type, label))

        elif key == "LCMB":

            fcs = []
            lcs = []

            lc  = int(items[1])
            name = str(items[2]).strip()

            datalen = len(items)-3

            for i in range(datalen):
                if i % 2 == 0:
                    fcs.append(float(items[i+3]))
                else:
                    lcs.append(int(items[i+3]))

            lcmbs.append(Lcmb(lc, name, fcs, lcs))

        elif key == "AXIS":

            id   = int(items[1])
            name = str(items[2]).strip()
            isHorizontal = bool(int(items[3]))
            nid  = int(items[4])

            if len(items) > 5:
                try: 
                    xdir = int(items[5])
                except ValueError:
                    xdir = None
            else:
                xdir = None

            axes.append(Axis(id, name, isHorizontal, nid, xdir))

        elif key == "PLOT":

            id   = int(items[1])
            name = str(items[2]).strip()
            axis = int(items[3])
            type = int(items[4])
            
            try:
                lc = int(items[5])
            except ValueError:
                lc = None

            scale = int(items[6]) 

            if len(items) > 7:
                deffac = float(items[7])
            else:
                deffac = 0

            plts.append(Plt(id, name, axis, type, lc, scale, deffac))
      
    dmems = []
    for id, diap_id, nids in dmem_specs:
        diap = _find_by_id(diaps_by_id, diap_id, "DIAP")
        ns = [_find_by_id(nds_by_id, nid, "NODE") for nid in nids]
        dmems.append(CSTMembrane3(id, diap, ns[0], ns[1], ns[2]))

    input_warnings.extend(collect_diaphragm_input_warnings(diaps, dopns, dcons))
    dregs, dreg_warnings = ensure_diaphragm_dregs(diaps, dregs, dmems)
    input_warnings.extend(dreg_warnings)

    by_node = nds_by_id
    for w in wwalls:
        if all(v is not None for v in [w.n1, w.n2, w.n3, w.n4]):
            from wood_wall import order_wwll_corner_node_ids
            n1, n2, n3, n4, _ = order_wwll_corner_node_ids(
                [w.n1, w.n2, w.n3, w.n4], by_node
            )
            w.n1, w.n2, w.n3, w.n4 = n1, n2, n3, n4

    for w in wwalls:
        input_warnings.extend(w.resolve_length_height(nds))

    for w in wwalls:
        if w.model_requested == WOOD_WALL_MODEL_SHEAR_PANEL:
            w.generate_shear_panel(nds, wshears, dcons)
        else:
            w.generate_mvp_equivalent_braces(nds, mats, secs, elms, ejnts, dcons)

    date_input = str(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
                     
    mdl = Mdl(
        nds, elms, ejnts, mats, secs, cons, lds, elds, alds, glds,
        lcases, lcmbs, axes, plts, date_input,
        dmats, diaps, dregs, dopns, dmems, dcons, dloads, wwalls, wshears,
        input_warnings
    )

    return mdl

def RegisterInputData(_mdl: Mdl):
    
    nds  = sorted(_mdl_items(_mdl.nds),   key=lambda n: n.id)
    elms = sorted([e for e in _mdl_items(_mdl.elms) if not getattr(e, "auto_generated", False)], key=lambda e: e.id)
    ejnts= sorted([e for e in _mdl_items(_mdl.ejnts) if not getattr(e, "auto_generated", False)], key=lambda e: e.eid)
    mats = sorted([m for m in _mdl_items(_mdl.mats) if not getattr(m, "auto_generated", False)], key=lambda m: m.id)
    secs = sorted([s for s in _mdl_items(_mdl.secs) if not getattr(s, "auto_generated", False)], key=lambda s: s.id)
    dmats= sorted(_mdl_items(_mdl.dmats), key=lambda m: m.id)
    diaps= sorted(_mdl_items(_mdl.diaps), key=lambda d: d.id)
    dregs= list(_mdl_items(_mdl.dregs))
    dopns= list(_mdl_items(_mdl.dopns))
    dmems= sorted(_mdl_items(_mdl.dmems), key=lambda m: m.id)
    dcons= [dc for dc in _mdl_items(_mdl.dcons) if not getattr(dc, "auto_generated", False)]
    dloads = sorted(_mdl_items(_mdl.dloads), key=lambda dl: (dl.diap_id, dl.lc, dl.load_type))
    wwalls = sorted(_mdl_items(_mdl.wwalls), key=lambda w: w.id)
    cons = sorted(_mdl_items(_mdl.cons),  key=lambda c: c.nid)

    lds_w_o_combi = [l for l in _mdl_items(_mdl.lds) if not l.combi]
    lds  = sorted(lds_w_o_combi,   key=lambda l: l.nid)

    elds_w_o_combi = [l for l in _mdl_items(_mdl.elds) if not l.combi]
    elds = sorted(elds_w_o_combi,  key=lambda l: l.eid)

    alds = sorted(_mdl_items(_mdl.alds),  key=lambda l: l.lc)

    glds_w_o_combi = [l for l in _mdl_items(_mdl.glds) if not l.combi]
    glds = sorted(glds_w_o_combi,  key=lambda g: g.lc)

    lcases = sorted(_mdl_items(_mdl.lcases), key=lambda l: l.lc)
    lcmbs = sorted(_mdl_items(_mdl.lcmbs), key=lambda l: l.lc)
    axes = sorted(_mdl_items(_mdl.axes),  key=lambda a: a.id)
    plts = sorted(_mdl_items(_mdl.plts),  key=lambda p: p.id)
    
    lns  = ""

    ## header
    lns += "# --- HEADER INPUT ---\n"
    lns += "\n"
    lns += "# DATE OF INPUT DATA: " + str(_mdl.date_input or "")
    lns += "\n"
    lns += "# NUM. OF MATERIALS: " + str(len(mats)) + "\n"
    lns += "# NUM. OF DIAPHRAGM MATERIALS: " + str(len(dmats)) + "\n"
    lns += "# NUM. OF CROSS-SECTIONS " + str(len(secs)) + "\n" 
    lns += "# NUM. OF NODES: " + str(len(nds)) + "\n"
    lns += "# NUM. OF ELEMENTS: " + str(len(elms)) + "\n"
    lns += "# NUM. OF CONSTRAINED NODES: " + str(len(cons)) + "\n"
    lns += "# NUM. OF LOADS: " + str(len(lds)) + "\n"
    lns += "# NUM. OF ELEMENT LOADS: " + str(len(elds)) + "\n"
    lns += "\n"

    lns += "### <INPUT DATA> ### \n\n"

    ## analysis type
    lns += "# TYPE OF ANALYSIS: 3D LINEAR STATIC\n"
    lns += "\n"

    ## material
    lns += "# --- MATERIAL(MATE) ---\n"
    lns += "#         ID,       NAME,        E,        G,    Gamma,    Alpha,       Fy\n"
    lns += "#                           (N/mm2)   (N/mm2)   (kN/m3)       (-)   (N/mm2)\n"
    for m in mats:
        lns += m.OutputMatInfo()
    lns += "\n"

    ## diaphragm material
    lns += "# --- DIAPHRAGM MATERIAL(DMAT) ---\n"
    lns += "#         ID,       NAME,        Ex,        Ey,       Gxy,      Nuxy,    Gamma,    Alpha\n"
    lns += "#                           (N/mm2)   (N/mm2)   (N/mm2)       (-)  (kN/m3)       (-)\n"
    for m in dmats:
        lns += m.OutputDMatInfo()
    lns += "\n"

    ## cross section
    lns += "# --- SECTION(SECT) ---\n"
    lns += "#         ID,       NAME,    MAT,   TYPE,  DIM 1,  DIM 2,  DIM 3,  DIM 4\n"
    lns += "#                                            (mm)    (mm)    (mm)    (mm)\n"
    lns += "#       (TYPE 0: RECT., 1: CIRC., 2: I, 3: CHS, 4: RHS) \n"
    for s in secs:
        lns += s.OutputSecInfo()
    lns += "\n"

    ## node 
    lns += "# --- NODE ---\n"
    lns += "#         ID,         X,         Y,         Z,  CONST.\n"
    lns += "#                    (m)        (m)        (m)\n"
    for n in nds:
        lns += n.OutputNdInfo()
    lns += "\n"

    ## element
    lns += "# --- ELEMENT(ELEM) ---\n"
    lns += "#         ID,     Ni,     Nj,    SEC,     Beta\n"
    lns += "#                                         (deg)\n"
    for e in elms:
        lns += e.OutputElmInfo()
    lns += "\n"

    ## diaphragms and membrane elements
    lns += "# --- DIAPHRAGM REGION(DIAP) ---\n"
    lns += "#         ID,       NAME,  TYPE,  SRC, MAG/ID,      T, THETA,      RA, HMAX\n"
    lns += "#   TYPE: 0=RIGID  1=SEMI  2=FLEX\n"
    lns += "#   SRC:  0=DMAT  1=TIMBER_FLOOR  2=TIMBER_ROOF\n"
    lns += "#   MAG/ID: SRC=0 -> DMAT ID, SRC=1/2 -> multiplier\n"
    lns += "#   T, HMAX: (mm)   RA: (rad)\n"
    lns += "#   HMAX is optional metadata only (not used by the current solver).\n"
    for d in diaps:
        lns += d.OutputDiapInfo()
    lns += "\n"

    lns += "# --- DIAPHRAGM OUTER POLYGON(DREG) ---\n"
    lns += "#    DIAP ID,  NODE1,  NODE2,  NODE3, ...\n"
    lns += "#   Optional when DMEM is supplied; outer boundary is derived from DMEM if omitted.\n"
    for r in dregs:
        if getattr(r, "auto_generated", False):
            continue
        lns += "DREG, {0: >6}".format(r.diap_id)
        for nid in r.node_ids:
            lns += ", {0: >6}".format(nid)
        lns += "\n"
    lns += "\n"

    lns += "# --- DIAPHRAGM OPENING(DOPN) ---\n"
    lns += "#    DIAP ID,  NODE1,  NODE2,  NODE3, ...\n"
    lns += "#   Parsed only; opening cut-outs are not applied in the current solver.\n"
    for o in dopns:
        lns += "DOPN, {0: >6}".format(o.diap_id)
        for nid in o.node_ids:
            lns += ", {0: >6}".format(nid)
        lns += "\n"
    lns += "\n"

    lns += "# --- DIAPHRAGM MEMBRANE ELEMENT(DMEM) ---\n"
    lns += "#         ID,    DIAP,     N1,     N2,     N3\n"
    for m in dmems:
        lns += m.OutputDMemInfo()
    lns += "\n"

    lns += "# --- DIAPHRAGM CONNECTION(DCON) ---\n"
    lns += "#    DIAP, TRGT,    ID, CONN,   TOL, SPACING\n"
    lns += "#   SPACING is optional metadata only (not used by the current MPC generator).\n"
    lns += "#   TRGT: 0=AUTO  1=ELEM  2=NODE\n"
    lns += "#   CONN: 0=RIGID  1=OPEN\n"
    for dc in dcons:
        lns += dc.OutputDConInfo()
    lns += "\n"

    lns += "# --- DIAPHRAGM LOAD(DLOD) ---\n"
    lns += "#    DIAP,  LC, TYPE,  (TYPE-dependent columns)\n"
    lns += "#   TYPE: 0=AREA(PX,PY kN/m2)  1=LINE(N1,N2,PX,PY)  2=MBTR(ELEM,PX,PY)\n"
    lns += "#         3=MASS(MASS,AX,AY kg/m2)  4=WGHT(WGHT,AX,AY kN/m2)\n"
    for dl in dloads:
        lns += dl.OutputDLoadInfo()
    lns += "\n"

    lns += "# --- WOOD RATED WALL(WWLL) ---\n"
    lns += "#         ID,     NAME, MODEL,    M,      L,      H, DIR,       RA, N1, N2, N3, N4, DIAP, LAYO\n"
    lns += "#   MODEL: 0=BRACE  1=PANEL  2=MEMBRANE(reserved)\n"
    lns += "#   DIR: 0=X  1=Y    LAYO: 0=SINGLE  1=X-BRACE\n"
    lns += "#   M: multiplier   L,H: (m, optional; derived from N1..N4 when blank)   RA: (rad)\n"
    for w in wwalls:
        lns += w.output_info()
    lns += "\n"

    ## element joints

    lns += "# --- ELEMENT JOINT(EJNT) ---\n"
    # lns += "#    ELEM ID,      Txi,      Tyi,      Tzi,      Rxi,      Ryi,      Rzi,      Txj,      Tyj,      Tzj,      Rxj,      Ryj,      Rzj\n"
    # lns += "#                (kN/m)    (kN/m)    (kN/m) (kNm/rad) (kNm/rad) (kNm/rad)    (kN/m)    (kN/m)    (kN/m) (kNm/rad) (kNm/rad) (kNm/rad)\n"
    lns += "#    ELEM ID,      Ryi,      Rzi,      Ryj,      Rzj\n"
    lns += "#             (kNm/rad) (kNm/rad) (kNm/rad) (kNm/rad)\n"
    for j in ejnts:
        lns += j.OutputElmJntInfo()
    lns += "\n"

    ## constraint
    lns += "# --- CONSTRAINT(CONS) ---\n"
    lns += "#    NODE ID,   TX,   TY,   TZ,   RX,   RY,   RZ\n"
    lns += "#   (0:FREE, 1:FIXED)\n"
    for c in cons:
        lns += c.OutputConstInfo()
    lns += "\n"

    ## load name
    lns += "# --- LOAD NAME(LNME) ---\n"
    lns += "#       LC,   TYPE,     LABEL\n"
    lns += "#   TYPE: 1=DL  2=LL  3=LL(E)  4=S  5=W  6=E  7=CUSTOM(label required)\n"
    for l in lcases:
        lns += l.OutputLnameInfo()
    lns += "\n"

    ## load combination
    lns += "# --- LOAD COMBINATION(LCMB) ---\n"
    lns += "#       LC,     NAME,   FC1,   LC1,   FC2,   LC2,   FC3,   LC3,...\n"
    for l in lcmbs:
        lns += l.OutputLcmbInfo()
    lns += "\n"

    ## load
    lns += "# --- POINT LOAD(PLOD) ---\n"
    lns += "#    NODE ID,   LC,     PX,     PY,     PZ,     MX,     MY,     MZ\n"
    lns += "#                      (kN)    (kN)    (kN)   (kNm)   (kNm)   (kNm)\n"
    for l in lds:
        lns += l.OutputLdInfo()
    lns += "\n"

    ## element load
    lns += "# --- ELEMENT LOAD(ELOD) ---\n"
    lns += "#    ELEM ID,   LC,  E/G,    WXi,    WYi,    WZi,    WXj,    WYj,    WZj\n"
    lns += "#                          (kN/m)  (kN/m)  (kN/m)  (kN/m)  (kN/m)  (kN/m)\n"
    lns += "#   (E/G: Element(=0) or Global(=1) Coordinate System)\n"
    if any(el.is_partial for el in elds):
        lns += "#   (optional T0, T1: load range along the member, 0 at node i, 1 at node j)\n"
    for el in elds:
        lns += el.OutputELdInfo()
    
    lns += "\n"

    ## area load
    lns += "# --- AREA LOAD(ALOD) ---\n"
    lns += "#         LC,     PX,     PY,     PZ,   E1,   E2,   E3,   E4\n"
    lns += "#             (kN/m2) (kN/m2) (kN/m2)\n"
    for al in alds:
        lns += al.OutputALdInfo()
    lns += "\n"

    ## gravity load
    lns += "# --- GRAVITY LOAD(GLOD) ---\n"
    lns += "#         LC,     Vec X,     Vec Y,     Vec Z\n"
    lns += "#                 (m/s2)     (m/s2)     (m/s2)\n"
    for gl in glds:
        lns += gl.OutputGLdInfo()

    lns += "\n" 

    ## axis 
    lns += "# --- AXIS (AXIS) ---\n"
    lns += "#         ID,       NAME,    V/H,    NID,  x-DIR(if V)\n"
    lns += "#                  (V/H 0:V, 1:H)     (x-DIR 0:X, 1:Y)\n"
    for a in axes:
        lns += a.OutputAxisInfo()

    lns += "\n"

    ## plot
    lns += "# --- PLOT (PLOT) ---\n"
    lns += "#         ID,       NAME,   AXIS,   TYPE,     LC,  SCALE, DEFFAC\n"
    lns += "#             (TYPE 0: MODEL, 1: LOAD, 2: FORCE, 3: UTIL)\n"

    for p in plts:
        lns += p.OutputPltInfo()
    
    lns += "\n\n"

    # lns += "### <END OF INPUT DATA> ### \n\n"

    return lns

def RegisterResultData(_mdl: Mdl):

    nds  = sorted(_mdl_items(_mdl.nds),  key=lambda n: n.id)
    elms = sorted(_mdl_items(_mdl.elms), key=lambda e: e.id)
    #mats = sorted(_mdl.mats, key=lambda m: m.id)
    secs = sorted(_mdl_items(_mdl.secs), key=lambda s: s.id)
    #cons = sorted(_mdl.cons, key=lambda c: c.nid)
    #lds  = sorted(_mdl.lds,  key=lambda l: l.nid)
    #elds = sorted(_mdl.elds, key=lambda l: l.eid)
    #glds = sorted(_mdl.glds, key=lambda g: g.lc)

    model_lcs = _mdl_items(_mdl.lcs)
    lcs  = sorted(model_lcs)
    model_cons = _mdl_items(_mdl.cons)
    model_dmems = _mdl_items(_mdl.dmems)

    lns  = ""

    ## header
    # lns += "# --- HEADER ---\n"
    # lns += "\n"
    # lns += "# DATE OF ANALYSIS: " + _mdl.date_analysis 
    # lns += "\n"
    # lns += "# NUM. OF MATERIALS: " + str(len(mats)) + "\n"
    # lns += "# NUM. OF CROSS-SECTIONS " + str(len(secs)) + "\n" 
    # lns += "# NUM. OF NODES: " + str(len(nds)) + "\n"
    # lns += "# NUM. OF ELEMENTS: " + str(len(elms)) + "\n"
    # lns += "# NUM. OF CONSTRAINED NODES: " + str(len(cons)) + "\n"
    # lns += "# NUM. OF LOADS: " + str(len(lds)) + "\n"
    # lns += "# NUM. OF ELEMENT LOADS: " + str(len(elds)) + "\n"
    # lns += "\n"

    lns += "# --- HEADER OUTPUT --- \n" 
    lns += "# DATE OF ANALYSIS: " + str(_mdl.date_analysis or "") + "\n\n"

    ## section properties
    lns += "# --- SECTION PROPS ---\n"
    lns += "#      SEC,          A,       Asy,       Asz,         J,        Iy,        Iz,        Wy,        Wz,        iy,        iz\n"
    lns += "#                 (mm2)      (mm2)      (mm2)      (mm4)      (mm4)      (mm4)      (mm3)      (mm3)       (mm)       (mm)\n"

    for s in secs:
        props = ["SPRP",
                 "{: >6}".format(s.id), 
                 "{:10.3e}".format(s.A * 1e6), 
                 "{:10.3e}".format(s.Asy * 1e6), 
                 "{:10.3e}".format(s.Asz * 1e6),
                 "{:10.3e}".format(s.J * 1e12),  
                 "{:10.3e}".format(s.Iy * 1e12), 
                 "{:10.3e}".format(s.Iz * 1e12), 
                 "{:10.3e}".format(s.Wy * 1e9), 
                 "{:10.3e}".format(s.Wz * 1e9), 
                 "{:10.3e}".format(s.iy * 1e3), 
                 "{:10.3e}".format(s.iz * 1e3), 
                 ]
        lns += ','.join(props) + "\n"
    
    lns += "\n"

    ## nodal displacements
    lns += "# --- NODAL DISPLACEMENT ---\n"
    lns += "#        LC,  NODE,         X,         Y,         Z,   Theta X,   Theta Y,   Theta Z\n"
    lns += "#                          (m)        (m)        (m)      (rad)      (rad)      (rad)\n"
    
    for lc in lcs:
        # lc : loadcase
        # clc: computational loadcase id 

        clc = model_lcs.index(lc) 
        for n in nds: 
            ds = n.disps[:, clc]
            props = ["NDSP", 
                     "{: >6}".format(lc), 
                     "{: >6}".format(n.id), 
                     "{:10.3e}".format(ds[0]), 
                     "{:10.3e}".format(ds[1]), 
                     "{:10.3e}".format(ds[2]), 
                     "{:10.3e}".format(ds[3]), 
                     "{:10.3e}".format(ds[4]), 
                     "{:10.3e}".format(ds[5])]
            lns += ','.join(props) + "\n"

    lns += "\n"

    ## reaction forces
    lns += "# --- REACTION FORCE ---\n"
    lns += "#        LC,  NODE,           TX,           TY,           TZ,           RX,           RY,           RZ\n"
    lns += "#                            (kN)         (kN)         (kN)        (kNm)        (kNm)        (kNm)\n"

    for i in range(len(model_lcs)):
        lc   = model_lcs[i]
        #csts = list(filter(lambda l: l.lc == lc, _))

        for c in model_cons:
            nid   = c.nd.id
            rs    = c.nd.reacts[i] # [lc][vals]
            # 7 significant digits (other records use 4) so that reactions
            # summed from the .out file balance the applied loads.
            props = ["REAC",
                     "{: >6}".format(lc),
                     "{: >6}".format(nid),
                     "{:13.6e}".format(rs[0] * 1e-3),
                     "{:13.6e}".format(rs[1] * 1e-3),
                     "{:13.6e}".format(rs[2] * 1e-3),
                     "{:13.6e}".format(rs[3] * 1e-3),
                     "{:13.6e}".format(rs[4] * 1e-3),
                     "{:13.6e}".format(rs[5] * 1e-3)
                    ]

            lns += ','.join(props) + "\n"
    lns += "\n"            

    ## element forces
    lns += "# --- ELEMENT FORCE ---\n"
    # lns += "#        LC,  ELEM,        Pi,       Vyi,       Vzi,       Mxi,       Myi,       Mzi         Pj,       Vyj,       Vzj,       Mxj,       Myj,       Mzj,       Myc,       Mzc\n"
    lns += "#        LC,  ELEM,        Ni,       Qyi,       Qzi,       Mxi,       Myi,       Mzi         Nj,       Qyj,       Qzj,       Mxj,       Myj,       Mzj,       Myc,       Mzc\n"
    lns += "#                         (kN)       (kN)       (kN)      (kNm)      (kNm)      (kNm)       (kN)       (kN)       (kN)      (kNm)      (kNm)      (kNm)      (kNm)      (kNm)\n"
    
    for lc in lcs:
        # lc : loadcase
        # clc: computational loadcase id 

        clc = model_lcs.index(lc) 
        for e in elms: 
            ef = e.forces[:, clc]

            fs = [] # forces
            for i in range(14):
                if abs(ef[i]) < common.PRES_ZERO:
                    fs.append(0)
                else:
                    fs.append(ef[i])
                    
            props = ["EFRC", 
                     "{: >6}".format(lc), 
                     "{: >6}".format(e.id), 
                     "{:10.3e}".format(fs[0] * 1e-3), 
                     "{:10.3e}".format(fs[1] * 1e-3), 
                     "{:10.3e}".format(fs[2] * 1e-3), 
                     "{:10.3e}".format(fs[3] * 1e-3), 
                     "{:10.3e}".format(fs[4] * 1e-3), 
                     "{:10.3e}".format(fs[5] * 1e-3), 
                     "{:10.3e}".format(fs[6] * 1e-3), 
                     "{:10.3e}".format(fs[7] * 1e-3), 
                     "{:10.3e}".format(fs[8] * 1e-3), 
                     "{:10.3e}".format(fs[9] * 1e-3), 
                     "{:10.3e}".format(fs[10]* 1e-3), 
                     "{:10.3e}".format(fs[11]* 1e-3), 
                     "{:10.3e}".format(fs[12]* 1e-3), 
                     "{:10.3e}".format(fs[13]* 1e-3)    ]

            lns += ','.join(props) + "\n"

    lns += "\n"

    ## element load segments (local axes, diagram convention)
    # The block is written only when at least one member carries a line load,
    # so outputs of models without member loads stay unchanged.
    ewld_rows = ""
    for lc in lcs:
        clc = model_lcs.index(lc)
        for e in elms:
            for seg in diagram_wsegs(e, clc):
                props = ["EWLD",
                         "{: >6}".format(lc),
                         "{: >6}".format(e.id)]
                props += ["{:10.3e}".format(v) for v in seg]
                ewld_rows += ','.join(props) + "\n"

    if ewld_rows:
        lns += "# --- ELEMENT LOAD SEGMENT (local axes, diagram convention) ---\n"
        lns += "#        LC,  ELEM,        T0,        T1,       WXi,       WYi,       WZi,       WXj,       WYj,       WZj\n"
        lns += "#                          (-)        (-)    (kN/m)    (kN/m)    (kN/m)    (kN/m)    (kN/m)    (kN/m)\n"
        lns += ewld_rows
        lns += "\n"

    ## membrane element strains, stresses and membrane forces
    if model_dmems:
        lns += "# --- MEMBRANE ELEMENT STRESS ---\n"
        lns += "#        LC,  DMEM,       EXX,       EYY,      GXY,        SX,        SY,       TXY,        NX,        NY,       NXY\n"
        lns += "#                           (-)       (-)       (-)   (N/mm2)   (N/mm2)   (N/mm2)    (kN/m)    (kN/m)    (kN/m)\n"
        for lc in lcs:
            clc = model_lcs.index(lc)
            for m in model_dmems:
                if m.strains is None or m.stresses is None or m.mforces is None:
                    continue
                strain = m.strains[:, clc]
                stress = m.stresses[:, clc]
                mforce = m.mforces[:, clc]
                props = [
                    "MSTR",
                    "{: >6}".format(lc),
                    "{: >6}".format(m.id),
                    "{:10.3e}".format(strain[0]),
                    "{:10.3e}".format(strain[1]),
                    "{:10.3e}".format(strain[2]),
                    "{:10.3e}".format(stress[0] * 1e-6),
                    "{:10.3e}".format(stress[1] * 1e-6),
                    "{:10.3e}".format(stress[2] * 1e-6),
                    "{:10.3e}".format(mforce[0] * 1e-3),
                    "{:10.3e}".format(mforce[1] * 1e-3),
                    "{:10.3e}".format(mforce[2] * 1e-3),
                ]
                lns += ','.join(props) + "\n"
        lns += "\n"

    return lns
