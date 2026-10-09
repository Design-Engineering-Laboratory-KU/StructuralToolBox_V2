import os
import json

from stb_gui.input_format import NEW_MODEL_TEMPLATE, NEW_MODEL_TEMPLATE_SIMPLE

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def project_root():
    return _STB_ROOT


def normalize_model_relpath(path):
    """Normalize a project-relative model path (forward slashes)."""

    if path is None:
        return None
    path = str(path).strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path


def _format_load_value_text(val):
    """Format one load intensity for viewer labels (matches viewer.js)."""

    if abs(val) < 1e-6:
        return None
    return f"{val:.1f}"


def _dominant_signed_component(w):
    """Dominant force component (kN/m) from distributed-load w vector."""

    best = 0.0
    for i in range(3):
        for j in (i, i + 3):
            if abs(w[j]) > abs(best):
                best = w[j]
    return best


def _dominant_signed_component_profile(profile):
    best = 0.0
    if profile is None:
        return best
    for row in profile:
        for i in range(1, 4):
            if abs(row[i]) > abs(best):
                best = row[i]
    return best


def _element_load_display_value(w, is_gravity=False, is_area=False):
    text = _format_load_value_text(_dominant_signed_component(w))
    if text is None:
        return None
    if is_gravity:
        text += "G"
    elif is_area:
        text += "A"
    return text


def _elem_local_wloads(elem, mdl, lc_idx):
    """Sum element distributed loads in local ECS for one load-case index."""

    import numpy as np

    lds = np.zeros(6, dtype=float)
    elds = mdl.elds if mdl.elds != None else []

    for el in elds:
        if el.eid != elem.id or el.clc != lc_idx:
            continue
        el_lds = np.array(el.lds, dtype=float).reshape(6)
        if el.isGlobal:
            el_lds = (elem.tm[0:6, 0:6] @ el_lds.reshape(6, 1)).flatten()
        lds += el_lds

    if elem.glds is not None and lc_idx < elem.glds.shape[1]:
        lds += elem.glds[:, lc_idx]

    if elem.alds is not None and lc_idx < elem.alds.shape[1]:
        lds += elem.alds[:, lc_idx]

    if _is_connected_boundary_member(elem, mdl):
        lds[1] = 0.0
        lds[4] = 0.0

    return lds


def _is_connected_boundary_member(elem, mdl):
    for a in getattr(mdl, "dassocs", []):
        if a.member_id != elem.id:
            continue
        if a.connection_type != "CONNECTED_RIGID":
            continue
        if a.association_type != "boundary_member":
            continue
        return True
    return False


def _gravity_element_load_entries(mdl):
    """Per-element distributed loads from GLOD (local ECS, kN/m)."""

    import numpy as np
    from classes import common

    entries = []
    for g in mdl.glds or []:
        for elem in mdl.elms:
            if elem.tm is None or elem.sec is None or elem.sec.mat is None:
                continue
            mass_per_len = elem.sec.A * elem.sec.mat.gamma / common.GRAVITY
            lds = elem.tm[0:6, 0:6] @ np.array([
                mass_per_len * g.gx,
                mass_per_len * g.gy,
                mass_per_len * g.gz,
                mass_per_len * g.gx,
                mass_per_len * g.gy,
                mass_per_len * g.gz,
            ])
            w = [float(lds[i]) * 1e-3 for i in range(6)]
            if max(abs(x) for x in w) < 1e-12:
                continue
            entries.append({
                "elem": elem.id,
                "lc": g.lc,
                "global": False,
                "gravity": True,
                "w": w,
                "display_value": _element_load_display_value(w, is_gravity=True),
            })
    return entries


def _area_load_element_load_entries(mdl):
    """Per-edge ALOD loads with sampled tributary profile (ECS, kN/m)."""

    import numpy as np

    entries = []
    for al in mdl.alds or []:
        if al.elms is None:
            continue

        for idx, elem in enumerate(al.elms):
            if elem.tm is None:
                continue

            p_ecs = elem.tm[0:3, 0:3] @ np.array(al.lds, dtype=float)
            if np.max(np.abs(p_ecs)) < 1e-12:
                continue

            b0 = 0.0 if al.elms_b0 is None else float(al.elms_b0[idx])
            b1 = 0.0 if al.elms_b1 is None else float(al.elms_b1[idx])
            w = [
                b0 * p_ecs[0] * 1e-3,
                b0 * p_ecs[1] * 1e-3,
                b0 * p_ecs[2] * 1e-3,
                b1 * p_ecs[0] * 1e-3,
                b1 * p_ecs[1] * 1e-3,
                b1 * p_ecs[2] * 1e-3,
            ]

            profile = []
            if al.elms_t is not None and al.elms_b is not None:
                ts = al.elms_t[idx]
                bs = al.elms_b[idx]
                profile.append([0.0, 0.0, 0.0, 0.0])
                for j in range(len(ts)):
                    bj = float(bs[j])
                    profile.append([
                        float(ts[j]),
                        float(bj * p_ecs[0] * 1e-3),
                        float(bj * p_ecs[1] * 1e-3),
                        float(bj * p_ecs[2] * 1e-3),
                    ])
                profile.append([1.0, 0.0, 0.0, 0.0])

            entries.append({
                "elem": elem.id,
                "lc": al.lc,
                "global": False,
                "area_load": True,
                "w": w,
                "w_profile": profile if len(profile) > 1 else None,
                "display_value": _element_load_display_value(
                    [0.0, 0.0, _dominant_signed_component_profile(profile), 0.0, 0.0, 0.0],
                    is_area=True,
                ),
            })
    return entries


def resolve_model_path(path):
    """Resolve path under project root; reject paths outside the tree."""

    path = normalize_model_relpath(path)
    if path == None or path == "":
        raise ValueError("Model path is empty")

    root = os.path.realpath(project_root())
    if os.path.isabs(path):
        full = os.path.realpath(path)
    else:
        full = os.path.realpath(os.path.join(root, path))

    if not full.startswith(root + os.sep) and full != root:
        raise ValueError("Model path must be inside the project: " + path)

    if not os.path.isfile(full):
        raise ValueError("Model file not found: " + path)

    return full


def list_model_files():
    """Return relative paths of .dat files under data/ and examples/."""

    out = []
    for sub in ("data", "examples"):
        base = os.path.join(project_root(), sub)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if name.endswith(".dat"):
                out.append(os.path.join(sub, name).replace("\\", "/"))
    return out


def _model_dir_allowed(rel):
    rel = normalize_model_relpath(rel)
    if not rel or not rel.endswith(".dat"):
        return False
    return rel.startswith("data/") or rel.startswith("examples/")


def safe_model_basename(filename):
    """Return a safe .dat basename for files stored under data/."""

    name = os.path.basename(str(filename or "").replace("\\", "/")).strip()
    if not name:
        raise ValueError("Filename is required")
    if not name.lower().endswith(".dat"):
        name += ".dat"
    if name in (".dat", "..dat") or ".." in name or "/" in name or "\\" in name:
        raise ValueError("Invalid filename: " + filename)
    return name


def allocate_new_model_path():
    """Return an unused project-relative path under data/ for a new model."""

    data_dir = os.path.join(project_root(), "data")
    os.makedirs(data_dir, exist_ok=True)
    for i in range(1, 10000):
        name = "untitled.dat" if i == 1 else "untitled_{0:03d}.dat".format(i)
        rel = "data/" + name
        full = os.path.join(data_dir, name)
        if not os.path.isfile(full):
            return rel
    raise ValueError("Too many untitled model files in data/")


def create_new_model_file(mode: str = "advanced"):
    """Create a comment-only .dat file and return (relative path, text)."""

    text = NEW_MODEL_TEMPLATE_SIMPLE if mode == "simple" else NEW_MODEL_TEMPLATE
    rel = allocate_new_model_path()
    full = os.path.join(project_root(), rel.replace("/", os.sep))
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)
    return rel, text


def write_model_file(rel_path, text):
    """Write model text to data/ or examples/. Returns normalized relative path."""

    rel = normalize_model_relpath(rel_path)
    if rel is None:
        raise ValueError("Model path is required")
    if not _model_dir_allowed(rel):
        raise ValueError("Model path must be a .dat file under data/ or examples/")
    full = os.path.join(project_root(), rel.replace("/", os.sep))
    parent = os.path.dirname(full)
    if parent:
        os.makedirs(parent, exist_ok=True)
    from stb_gui.dat_format_headers import write_dat_text

    write_dat_text(full, text if text is not None else "")
    return rel


def open_uploaded_model(filename, text):
    """Save uploaded input under data/ and return its relative path."""

    name = safe_model_basename(filename)
    return write_model_file("data/" + name, text)


def mdl_to_dict(mdl, relpath=None, solved=False):
    """Build a JSON-serializable model description for the web viewer."""

    nodes = []
    for n in sorted(mdl.nds, key=lambda x: x.id):
        item = {
            "id": n.id,
            "x": n.x,
            "y": n.y,
            "z": n.z,
        }
        if solved and n.disps is not None and mdl.lcs != None:
            item["disps"] = {}
            for i in range(len(mdl.lcs)):
                lc = mdl.lcs[i]
                d = n.disps[:, i]
                item["disps"][str(lc)] = [
                    float(d[0]), float(d[1]), float(d[2]),
                    float(d[3]), float(d[4]), float(d[5]),
                ]
        nodes.append(item)

    explicit_ejnt_ids = set()
    if getattr(mdl, "ejnts", None) is not None:
        for j in mdl.ejnts:
            explicit_ejnt_ids.add(j.eid)

    elements = []
    for e in sorted(mdl.elms, key=lambda x: x.id):
        sec = e.sec
        sec_name = sec.name if sec != None else ""
        sec_id = sec.id if sec != None else None
        mat_name = sec.mat.name if sec != None and sec.mat != None else ""
        mat_id = sec.mat.id if sec != None and sec.mat != None else None
        item = {
            "id": e.id,
            "n0": e.n0.id,
            "n1": e.n1.id,
            "section": sec_name,
            "section_id": sec_id,
            "material_name": mat_name,
            "material_id": mat_id,
            "ejnt_defined": bool(e.id in explicit_ejnt_ids),
            "auto_generated": bool(getattr(e, "auto_generated", False)),
            "generated_from": getattr(e, "generated_from", None),
            "generated_from_id": getattr(e, "generated_from_id", None),
        }
        if e.pln != None:
            item["len"] = float(e.len)
            item["is_vxz"] = bool(e.isVxZ)
            item["lyi"] = float(e.lyi) if e.lyi is not None else None
            item["lyj"] = float(e.lyj) if e.lyj is not None else None
            item["lzi"] = float(e.lzi) if e.lzi is not None else None
            item["lzj"] = float(e.lzj) if e.lzj is not None else None
            item["PHIy"] = float(e.PHIy) if e.PHIy is not None else None
            item["PHIz"] = float(e.PHIz) if e.PHIz is not None else None
            if e.sec is not None and e.sec.mat is not None:
                item["EIy"] = float(e.sec.mat.E * e.sec.Iy)
                item["EIz"] = float(e.sec.mat.E * e.sec.Iz)
            item["vx"] = [
                float(e.pln.vx.v[0]), float(e.pln.vx.v[1]), float(e.pln.vx.v[2]),
            ]
            item["vy"] = [
                float(e.pln.vy.v[0]), float(e.pln.vy.v[1]), float(e.pln.vy.v[2]),
            ]
            item["vz"] = [
                float(e.pln.vz.v[0]), float(e.pln.vz.v[1]), float(e.pln.vz.v[2]),
            ]
        if solved and e.forces is not None and mdl.lcs != None:
            item["forces"] = {}
            item["local_wloads"] = {}
            item["end_rots"] = {}
            end_rots = None
            if getattr(e, "ndisps", None) is not None and e.pln is not None:
                from classes.solve import member_end_bending_rotations
                end_rots = member_end_bending_rotations(e)
            for i, lc in enumerate(mdl.lcs):
                if end_rots is not None and i < end_rots.shape[1]:
                    item["end_rots"][str(lc)] = [float(v) for v in end_rots[:, i]]
                f = e.forces[:, i]
                item["forces"][str(lc)] = [float(f[j]) for j in range(f.shape[0])]
                w = _elem_local_wloads(e, mdl, i)
                item["local_wloads"][str(lc)] = [float(w[j]) for j in range(6)]
        elements.append(item)

    supports = []
    for c in mdl.cons:
        item = {
            "node": c.nid,
            "fixed": [bool(x) for x in c.csts],
        }
        if solved and c.nd.reacts is not None and mdl.lcs != None:
            item["reacts"] = {}
            for i, lc in enumerate(mdl.lcs):
                rs = c.nd.reacts[i]
                item["reacts"][str(lc)] = [
                    float(rs[0]) * 1e-3, float(rs[1]) * 1e-3, float(rs[2]) * 1e-3,
                    float(rs[3]) * 1e-3, float(rs[4]) * 1e-3, float(rs[5]) * 1e-3,
                ]
        supports.append(item)

    reactions = []
    if solved and mdl.lcs != None:
        for i, lc in enumerate(mdl.lcs):
            for c in mdl.cons:
                if c.nd.reacts is None:
                    continue
                rs = c.nd.reacts[i]
                reactions.append({
                    "node": c.nid,
                    "lc": lc,
                    "tx": float(rs[0]) * 1e-3,
                    "ty": float(rs[1]) * 1e-3,
                    "tz": float(rs[2]) * 1e-3,
                    "rx": float(rs[3]) * 1e-3,
                    "ry": float(rs[4]) * 1e-3,
                    "rz": float(rs[5]) * 1e-3,
                })

    point_loads = []
    for l in mdl.lds:
        point_loads.append({
            "node": l.nid,
            "lc": l.lc,
            "px": float(l.lds[0]) * 1e-3,
            "py": float(l.lds[1]) * 1e-3,
            "pz": float(l.lds[2]) * 1e-3,
            "mx": float(l.lds[3]) * 1e-3,
            "my": float(l.lds[4]) * 1e-3,
            "mz": float(l.lds[5]) * 1e-3,
        })

    element_loads = []
    for el in mdl.elds:
        w = [
            float(el.lds[0]) * 1e-3, float(el.lds[1]) * 1e-3,
            float(el.lds[2]) * 1e-3, float(el.lds[3]) * 1e-3,
            float(el.lds[4]) * 1e-3, float(el.lds[5]) * 1e-3,
        ]
        if max(abs(x) for x in w) < 1e-12:
            continue
        element_loads.append({
            "elem": el.eid,
            "lc": el.lc,
            "global": bool(el.isGlobal),
            "w": w,
            "display_value": _element_load_display_value(w, is_gravity=False),
        })
    element_loads.extend(_gravity_element_load_entries(mdl))
    element_loads.extend(_area_load_element_load_entries(mdl))

    diaphragm_materials = []
    for dm in getattr(mdl, "dmats", []):
        diaphragm_materials.append({
            "id": dm.id,
            "name": dm.name,
            "Ex": float(dm.Ex) * 1e-6,
            "Ey": float(dm.Ey) * 1e-6,
            "Gxy": float(dm.Gxy) * 1e-6,
            "nuxy": float(dm.nuxy),
            "gamma": float(dm.gamma) * 1e-3,
            "alpha": float(dm.alpha),
            "source": getattr(dm, "source", "DMAT"),
            "multiplier": getattr(dm, "multiplier", None),
            "reference_drift": getattr(dm, "reference_drift", None),
            "equivalent_gt": getattr(dm, "equivalent_gt", None),
        })

    diaphragms = []
    for d in getattr(mdl, "diaps", []):
        diaphragms.append({
            "id": d.id,
            "name": d.name,
            "type": d.type,
            "material_id": d.mat.id if d.mat is not None else None,
            "thickness": float(d.t) if d.t is not None else None,
            "theta": float(d.theta),
            "source": getattr(d, "source", "DMAT"),
            "hmax": getattr(d, "hmax", None),
            "reference_drift": getattr(d, "reference_drift", None),
            "timber_multiplier": getattr(d, "timber_multiplier", None),
        })

    diaphragm_loads = []
    for dl in getattr(mdl, "dloads", []):
        diaphragm_loads.append({
            "diaphragm_id": dl.diap_id,
            "lc": dl.lc,
            "type": dl.load_type,
            "px": float(dl.px) * 1e-3,
            "py": float(dl.py) * 1e-3,
            "nodes": list(dl.node_ids),
            "member_id": dl.member_id,
            "mass": float(dl.mass),
            "weight": float(dl.weight) * 1e-3,
            "ax": float(dl.ax),
            "ay": float(dl.ay),
        })

    wood_rated_walls = []
    for w in getattr(mdl, "wwalls", []):
        item = {
            "id": w.id,
            "name": w.name,
            "model_requested": w.model_requested,
            "model_active": w.model_active,
            "multiplier": float(w.multiplier),
            "length": float(w.length),
            "height": float(w.height),
            "direction": w.direction,
            "reference_drift": float(w.reference_drift),
            "qa_kN": float(w.qa_kN),
            "delta": float(w.delta),
            "k_n_per_m": float(w.k_n_per_m),
            "diagonal_length": float(w.diagonal_length),
            "generated_elem_ids": list(w.generated_elem_ids),
            "diaphragm_id": w.diap_id,
        }
        if all(v is not None for v in [w.n1, w.n2, w.n3, w.n4]):
            item["nodes"] = [w.n1, w.n2, w.n3, w.n4]
        wood_rated_walls.append(item)

    wood_shear_panels = []
    for sp in getattr(mdl, "wshears", []):
        wood_shear_panels.append({
            "id": sp.id,
            "wall_id": sp.wall_id,
            "name": sp.name,
            "nodes": [sp.n1.id, sp.n2.id, sp.n3.id, sp.n4.id],
            "direction": sp.direction,
            "k_n_per_m": float(sp.k),
        })

    membrane_elements = []
    for m in getattr(mdl, "dmems", []):
        item = {
            "id": m.id,
            "diaphragm_id": m.diap.id,
            "nodes": [m.n0.id, m.n1.id, m.n2.id],
            "area": float(m.area),
        }
        if solved and m.strains is not None and mdl.lcs != None:
            item["strains"] = {}
            item["stresses"] = {}
            item["membrane_forces"] = {}
            for i, lc in enumerate(mdl.lcs):
                item["strains"][str(lc)] = [float(v) for v in m.strains[:, i]]
                item["stresses"][str(lc)] = [float(v) * 1e-6 for v in m.stresses[:, i]]
                item["membrane_forces"][str(lc)] = [float(v) * 1e-3 for v in m.mforces[:, i]]
        membrane_elements.append(item)

    bounds = None
    if mdl.bounds != None:
        bounds = [
            float(mdl.bounds[0]), float(mdl.bounds[1]),
            float(mdl.bounds[2]), float(mdl.bounds[3]),
            float(mdl.bounds[4]), float(mdl.bounds[5]),
        ]

    materials = []
    for m in sorted(mdl.mats, key=lambda x: x.id):
        materials.append({
            "id": m.id,
            "name": m.name,
        })

    sections = []
    for s in sorted(mdl.secs, key=lambda x: x.id):
        dims = [float(d) * 1e3 for d in s.dims] if s.dims is not None else []
        sections.append({
            "id": s.id,
            "name": s.name,
            "material_id": s.mat.id if s.mat is not None else None,
            "material_name": s.mat.name if s.mat is not None else "",
            "type": int(s.type),
            "dims": dims,
        })

    element_joints = []
    for j in sorted(getattr(mdl, "ejnts", []) or [], key=lambda x: x.eid):
        def _ejnt_out(val):
            if val is None:
                return None
            return float(val) * 1e-3

        element_joints.append({
            "elem_id": j.eid,
            "ryi": _ejnt_out(j.ryi),
            "rzi": _ejnt_out(j.rzi),
            "ryj": _ejnt_out(j.ryj),
            "rzj": _ejnt_out(j.rzj),
        })

    load_case_defs = []
    for lc in getattr(mdl, "lcases", []):
        load_case_defs.append({
            "lc": lc.lc,
            "type": getattr(lc, "load_type", 7),
            "label": getattr(lc, "label", ""),
            "name": getattr(lc, "lname", ""),
        })

    return {
        "path": relpath,
        "solved": solved,
        "schema": 2,
        "input_warnings": list(getattr(mdl, "input_warnings", []) or []),
        "date_analysis": mdl.date_analysis,
        "load_cases": mdl.lcs if mdl.lcs != None else [],
        "load_case_definitions": load_case_defs,
        "bounds": bounds,
        "nodes": nodes,
        "elements": elements,
        "materials": materials,
        "sections": sections,
        "element_joints": element_joints,
        "supports": supports,
        "reactions": reactions,
        "point_loads": point_loads,
        "element_loads": element_loads,
        "diaphragm_materials": diaphragm_materials,
        "diaphragms": diaphragms,
        "diaphragm_loads": diaphragm_loads,
        "wood_rated_walls": wood_rated_walls,
        "wood_shear_panels": wood_shear_panels,
        "membrane_elements": membrane_elements,
    }


def _load_mdl(path, solve=False, quiet=True):
    """Parse model file; optionally run analysis. Returns Mdl instance."""

    import copy
    import sys
    root = project_root()
    if root not in sys.path:
        sys.path.insert(0, root)

    from stb_engine import solve_model
    from stb_engine.errors import StbParseError, StbSolveError
    from stb_gui.model_session import get_parsed_model
    from stb_loads.equilibrium import seed_solved_model_cache

    full = resolve_model_path(path)
    try:
        mdl = get_parsed_model(full)
    except StbParseError as ex:
        raise ValueError(str(ex))

    if solve:
        mdl = copy.deepcopy(mdl)
        if quiet:
            old_stdout = sys.stdout
            devnull = open(os.devnull, "w")
            sys.stdout = devnull
            try:
                solve_model(mdl)
            except StbSolveError as ex:
                raise ValueError(str(ex))
            finally:
                devnull.close()
                sys.stdout = old_stdout
        else:
            try:
                solve_model(mdl)
            except StbSolveError as ex:
                raise ValueError(str(ex))
        seed_solved_model_cache(mdl)

    return mdl, full


def load_model_dict(path, solve=False, quiet=True, use_cached=True):
    """Parse (and optionally solve) a model file; return dict for JSON."""

    mdl, full = _load_mdl(path, solve=solve, quiet=quiet)
    relpath = os.path.relpath(full, project_root()).replace("\\", "/")
    solved = bool(solve)
    if not solve and use_cached:
        from stb_loads.equilibrium import get_cached_solved_model

        cached = get_cached_solved_model(full)
        if cached is not None:
            mdl = cached
            solved = True
    data = mdl_to_dict(mdl, relpath=relpath, solved=solved)

    if solved:
        from stb_engine import format_results
        data["results_text"] = format_results(mdl)

    return data


def load_results_text(path, quiet=True):
    """Return result text from cache when available; otherwise run analysis."""

    from stb_loads.equilibrium import get_cached_solved_model

    full = resolve_model_path(path)
    mdl = get_cached_solved_model(full)
    if mdl is None:
        mdl, full = _load_mdl(path, solve=True, quiet=quiet)
    from stb_engine import format_results
    return format_results(mdl)


def load_input_text(path):
    """Return raw .dat input file contents."""

    full = resolve_model_path(path)
    with open(full, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def model_to_json(path, solve=False, quiet=True):
    data = load_model_dict(path, solve=solve, quiet=quiet)
    return json.dumps(data, indent=2)
