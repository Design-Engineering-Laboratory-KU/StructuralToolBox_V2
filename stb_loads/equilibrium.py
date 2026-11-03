"""Equilibrium checks: applied horizontal loads vs support reactions for seismic LCs."""
from __future__ import annotations

import copy
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

from stb_loads.seismic import SeismicDistributionResult
from stb_loads.story import diaphragm_area_m2


def _ensure_classes_path() -> None:
    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)


def _lc_column(mdl, lc: int) -> Optional[int]:
    if mdl.lcs is None:
        return None
    try:
        return mdl.lcs.index(lc)
    except ValueError:
        return None


def _load_matrix_kN(mdl):
    _ensure_classes_path()
    from solve import Solve

    solver = Solve.__new__(Solve)
    solver.mdl = mdl
    solver.ndof = 6
    solver.num_row = solver.ndof * len(mdl.nds)
    lm = solver.CreateLoadMx(apply_constraints=False)
    return lm * 1e-3, solver.ndof


def _sum_translation_kN(mdl, lc: int, dof: int, lm=None, ndof: int = 6) -> float:
    col = _lc_column(mdl, lc)
    if col is None:
        return 0.0
    if lm is None:
        lm, ndof = _load_matrix_kN(mdl)
    total = 0.0
    for n in mdl.nds:
        total += float(lm[n.cid * ndof + dof, col])
    return total


_SOLVED_MODEL_CACHE: Dict[str, Tuple[float, Any]] = {}


def invalidate_solved_model_cache(full: str) -> None:
    _SOLVED_MODEL_CACHE.pop(full, None)


def get_cached_solved_model(full: str):
    """Return a cached solved model when the .dat mtime matches; otherwise None."""
    if not full or not os.path.isfile(full):
        return None
    mtime = os.path.getmtime(full)
    cached = _SOLVED_MODEL_CACHE.get(full)
    if not cached or cached[0] != mtime:
        return None
    return cached[1]


def seed_solved_model_cache(mdl) -> None:
    """Register an already-solved model (e.g. after /api/model?solve=1)."""
    cache_key = getattr(mdl, "filepath", None)
    if not cache_key or not os.path.isfile(cache_key):
        return
    mtime = os.path.getmtime(cache_key)
    _SOLVED_MODEL_CACHE[cache_key] = (mtime, mdl)


def prepare_solved_model(mdl, cache_key: Optional[str] = None):
    """Deep-copy the model and run a full static solve once (cached by filepath)."""
    from stb_engine import solve_model

    cache_key = cache_key or getattr(mdl, "filepath", None)
    mtime = None
    if cache_key:
        mtime = os.path.getmtime(cache_key)
        cached = _SOLVED_MODEL_CACHE.get(cache_key)
        if cached and cached[0] == mtime:
            return cached[1]

    mdl_solved = copy.deepcopy(mdl)
    solve_model(mdl_solved)
    if cache_key is not None and mtime is not None:
        _SOLVED_MODEL_CACHE[cache_key] = (mtime, mdl_solved)
    return mdl_solved


def _sum_reaction_translation_kN(mdl, lc: int, dof: int) -> float:
    col = _lc_column(mdl, lc)
    if col is None:
        return 0.0
    total = 0.0
    for c in mdl.cons:
        reacts = getattr(c.nd, "reacts", None)
        if reacts is None:
            continue
        total += float(reacts[col, dof]) * 1e-3
    return total


def _list_dlod_horizontal(mdl, lc: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for dl in getattr(mdl, "dloads", []):
        if dl.lc != lc or dl.load_type != "AREA":
            continue
        area = diaphragm_area_m2(mdl, dl.diap_id)
        px = dl.px * 1e-3
        py = dl.py * 1e-3
        fx = px * area
        fy = py * area
        if abs(fx) < 1e-9 and abs(fy) < 1e-9:
            continue
        rows.append({
            "kind": "DLOD",
            "diap_id": dl.diap_id,
            "px_kN_m2": px,
            "py_kN_m2": py,
            "area_m2": area,
            "fx_kN": fx,
            "fy_kN": fy,
        })
    return rows


def _list_other_horizontal(mdl, lc: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for pl in getattr(mdl, "lds", []):
        if pl.lc != lc:
            continue
        px, py = pl.lds[0] * 1e-3, pl.lds[1] * 1e-3
        if abs(px) < 1e-9 and abs(py) < 1e-9:
            continue
        rows.append({"kind": "PLOD", "node": pl.nid, "fx_kN": px, "fy_kN": py})

    for el in getattr(mdl, "elds", []):
        if el.lc != lc:
            continue
        kind = "EPLD" if getattr(el, "is_point", False) else "ELOD"
        rows.append({"kind": kind, "elem": el.eid, "note": "horizontal component may exist"})

    for gl in getattr(mdl, "glds", []):
        if gl.lc not in (0, lc):
            continue
        if abs(gl.gx) > 1e-9 or abs(gl.gy) > 1e-9:
            rows.append({"kind": "GLOD", "lc": gl.lc, "gx": gl.gx, "gy": gl.gy})

    for al in getattr(mdl, "alds", []):
        if al.lc != lc:
            continue
        rows.append({"kind": "ALOD", "id": al.id, "note": "area load — see solver matrix"})

    return rows


def _direction_label(axis: str, sign: int) -> str:
    if axis == "x":
        return "X+" if sign >= 0 else "X-"
    return "Y+" if sign >= 0 else "Y-"


def _expected_fi_dlod_kN(result: SeismicDistributionResult, axis: str, sign: int) -> float:
    total = 0.0
    for d in result.diaphragm_loads:
        if d.axis != axis or d.sign != sign:
            continue
        total += d.fi_kN
    return total


def _dat_dlod_pressure_mismatch(mdl, result: SeismicDistributionResult, tol: float = 1.0e-3):
    expected = {
        (d.diaphragm_id, d.load_case): d.pressure_kN_m2
        for d in result.diaphragm_loads
    }
    mismatches = []
    for dl in getattr(mdl, "dloads", []):
        if dl.load_type != "AREA":
            continue
        key = (dl.diap_id, dl.lc)
        if key not in expected:
            continue
        actual = abs(dl.px * 1e-3) if dl.px else abs(dl.py * 1e-3)
        exp = expected[key]
        if abs(actual - exp) > tol:
            mismatches.append({
                "diap_id": dl.diap_id,
                "lc": dl.lc,
                "dat_kN_m2": actual,
                "expected_kN_m2": exp,
            })
    return mismatches


def compute_seismic_equilibrium(
    mdl,
    result: SeismicDistributionResult,
    mdl_solved=None,
) -> List[Dict[str, Any]]:
    """Return per-direction equilibrium rows for seismic load cases in the model."""
    keys: List[Tuple[int, str, int]] = []
    seen = set()
    for d in result.diaphragm_loads:
        key = (d.load_case, d.axis, d.sign)
        if key not in seen:
            seen.add(key)
            keys.append(key)

    if not keys:
        return []

    if mdl_solved is None:
        mdl_solved = prepare_solved_model(mdl)

    lm, ndof = _load_matrix_kN(mdl)
    rows: List[Dict[str, Any]] = []
    for lc, axis, sign in sorted(keys):
        dof = 0 if axis == "x" else 1
        fx_applied = _sum_translation_kN(mdl, lc, dof, lm=lm, ndof=ndof)
        sum_tx = _sum_reaction_translation_kN(mdl_solved, lc, dof)
        fi_dlod = _expected_fi_dlod_kN(result, axis, sign)
        residual = abs(fx_applied + sum_tx)

        dlod_rows = _list_dlod_horizontal(mdl, lc)
        other_rows = _list_other_horizontal(mdl, lc)

        rows.append({
            "load_case": lc,
            "direction": _direction_label(axis, sign),
            "axis": axis,
            "sign": sign,
            "fi_dlod_output_kN": fi_dlod,
            "fx_applied_kN": fx_applied,
            "sum_reaction_kN": sum_tx,
            "abs_fx_applied_kN": abs(fx_applied),
            "abs_sum_reaction_kN": abs(sum_tx),
            "equilibrium_residual_kN": residual,
            "equilibrium_ok": residual <= max(1.0e-2, fi_dlod * 1.0e-3),
            "dlod_loads": dlod_rows,
            "other_loads": other_rows,
            "pressure_mismatches": _dat_dlod_pressure_mismatch(mdl, result),
        })
    return rows


def build_equilibrium_check_rows(
    mdl,
    result: SeismicDistributionResult,
    eq_rows: Optional[List[Dict[str, Any]]] = None,
    mdl_solved=None,
) -> List[Dict[str, Any]]:
    """Markdown/GUI check list for load–reaction equilibrium."""
    if eq_rows is None:
        eq_rows = compute_seismic_equilibrium(mdl, result, mdl_solved=mdl_solved)
    checks: List[Dict[str, Any]] = []
    for row in eq_rows:
        label_dir = "LC{0} {1}".format(row["load_case"], row["direction"])
        checks.append({
            "label": "{0} DLOD出力荷重合計 ΣFi_DLOD_output".format(label_dir),
            "ok": True,
            "detail": "{0} kN".format(_fmt(row["fi_dlod_output_kN"])),
        })
        checks.append({
            "label": "{0} 解析モデル水平荷重合計 ΣFx_applied".format(label_dir),
            "ok": abs(row["fx_applied_kN"] - row["fi_dlod_output_kN"]) <= max(
                1.0e-2, row["fi_dlod_output_kN"] * 1.0e-3
            ),
            "detail": "{0} kN（DLOD期待 {1} kN）".format(
                _fmt(row["fx_applied_kN"]), _fmt(row["fi_dlod_output_kN"])
            ),
        })
        checks.append({
            "label": "{0} 支点反力合計 ΣTx".format(label_dir),
            "ok": abs(row["sum_reaction_kN"] + row["fx_applied_kN"]) <= max(
                1.0e-2, row["fi_dlod_output_kN"] * 1.0e-3
            ),
            "detail": "{0} kN".format(_fmt(row["sum_reaction_kN"])),
        })
        checks.append({
            "label": "{0} 釣合 |ΣFx_applied + ΣTx|".format(label_dir),
            "ok": row["equilibrium_ok"],
            "detail": "{0} kN".format(_fmt(row["equilibrium_residual_kN"])),
        })
        if row["other_loads"]:
            checks.append({
                "label": "{0} PLOD/GLOD/ALOD 等の水平荷重なし".format(label_dir),
                "ok": False,
                "detail": ", ".join(r["kind"] for r in row["other_loads"]),
            })
        if row["pressure_mismatches"]:
            parts = [
                "DIAP{0} dat={1} 期待={2} kN/m²".format(
                    m["diap_id"], _fmt(m["dat_kN_m2"], 4), _fmt(m["expected_kN_m2"], 4)
                )
                for m in row["pressure_mismatches"]
            ]
            checks.append({
                "label": "{0} .dat DLOD 面圧が算定値と一致".format(label_dir),
                "ok": False,
                "detail": "; ".join(parts),
            })
    return checks


def _fmt(value, places=3):
    n = float(value)
    if abs(n - round(n)) < 1.0e-9:
        return str(int(round(n)))
    return ("{0:." + str(places) + "f}").format(n)
