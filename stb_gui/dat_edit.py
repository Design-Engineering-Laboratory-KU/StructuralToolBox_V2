"""Line-based editors for Structural Toolbox .dat input files."""

from __future__ import annotations

from typing import Any


def _split_record(line: str) -> tuple[str, list[str]] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = [p.strip() for p in stripped.split(",")]
    if not parts or not parts[0]:
        return None
    return parts[0].upper(), parts


def _join_record(parts: list[str]) -> str:
    return ", ".join(parts)


def _parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as ex:
        raise ValueError("Invalid {0}: {1!r}".format(label, value)) from ex


def _section_ids(lines: list[str]) -> set[int]:
    out: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "SECT":
            out.add(_parse_int(rec[1][1], "section id"))
    return out


def _element_section_map(lines: list[str]) -> dict[int, int]:
    out: dict[int, int] = {}
    for line in lines:
        rec = _split_record(line)
        if not rec or rec[0] != "ELEM":
            continue
        parts = rec[1]
        if len(parts) < 5:
            continue
        out[_parse_int(parts[1], "element id")] = _parse_int(parts[4], "section id")
    return out


def _format_ejnt_line(elem_id: int, ryi, rzi, ryj, rzj) -> str:
    def field(val) -> str:
        if val is None:
            return ""
        if isinstance(val, (int, float)):
            if abs(val) < 1e-12:
                return "0.0"
            if abs(val) < 1e-3:
                return "{0:.6g}".format(val)
            return "{0:.6g}".format(val)
        return str(val)

    return _join_record(
        [
            "EJNT",
            str(elem_id),
            field(ryi),
            field(rzi),
            field(ryj),
            field(rzj),
        ]
    )


EJNT_PRESETS: dict[str, tuple[Any, Any, Any, Any] | None] = {
    "pin": (0.0, None, 0.0, None),
    "spring_soft": (1e-6, 1e-6, 1e-6, 1e-6),
    "rigid": None,
}


def _elements_touching_nodes(lines: list[str], node_ids: set[int]) -> set[int]:
    elem_ids: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if not rec or rec[0] != "ELEM":
            continue
        parts = rec[1]
        if len(parts) < 4:
            continue
        eid = _parse_int(parts[1], "element id")
        ni = _parse_int(parts[2], "node i")
        nj = _parse_int(parts[3], "node j")
        if ni in node_ids or nj in node_ids:
            elem_ids.add(eid)
    return elem_ids


def delete_nodes(text: str, node_ids: list[int]) -> tuple[str, list[str]]:
    targets = {int(n) for n in node_ids}
    if not targets:
        raise ValueError("node_ids is empty")

    lines = text.splitlines()
    elem_targets = _elements_touching_nodes(lines, targets)
    elem_remove_tags = {"ELEM", "EJNT", "ELOD", "EPLD"}

    out: list[str] = []
    removed_nodes = 0
    removed_elems = 0
    removed_other = 0

    for line in lines:
        rec = _split_record(line)
        if not rec:
            out.append(line)
            continue
        tag, parts = rec
        rec_id = _parse_int(parts[1], tag + " id")

        if tag == "NODE" and rec_id in targets:
            removed_nodes += 1
            continue
        if tag == "CONS" and rec_id in targets:
            removed_other += 1
            continue
        if tag == "PLOD" and rec_id in targets:
            removed_other += 1
            continue
        if tag in elem_remove_tags and rec_id in elem_targets:
            removed_elems += 1
            continue
        if tag == "DMEM" and len(parts) >= 6:
            nids = [
                _parse_int(parts[i], "node id")
                for i in range(3, 6)
            ]
            if any(nid in targets for nid in nids):
                removed_other += 1
                continue
        out.append(line)

    if removed_nodes == 0:
        raise ValueError("No matching nodes found to delete")

    warnings = [
        "Deleted {0} node(s) {1}, {2} connected element record(s), {3} related load/constraint record(s).".format(
            removed_nodes,
            sorted(targets),
            removed_elems,
            removed_other,
        )
    ]
    return _ensure_trailing_newline("\n".join(out)), warnings


def delete_elements(text: str, element_ids: list[int]) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    if not targets:
        raise ValueError("element_ids is empty")
    removed_tags = {"ELEM", "EJNT", "ELOD", "EPLD"}
    out: list[str] = []
    removed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] in removed_tags:
            parts = rec[1]
            rec_id = _parse_int(parts[1], rec[0] + " id")
            if rec_id in targets:
                removed += 1
                continue
        out.append(line)
    if removed == 0:
        raise ValueError("No matching elements found to delete")
    warnings = [
        "Deleted {0} record(s) for element id(s) {1}. Orphan nodes were kept.".format(
            removed, sorted(targets)
        )
    ]
    return _ensure_trailing_newline("\n".join(out)), warnings


def set_element_section(text: str, element_ids: list[int], section_id: int) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    sec_id = int(section_id)
    if not targets:
        raise ValueError("element_ids is empty")

    section_ids = _section_ids(text.splitlines())
    if sec_id not in section_ids:
        raise ValueError("Unknown section id: {0}".format(sec_id))

    out: list[str] = []
    changed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "ELEM":
            parts = rec[1]
            eid = _parse_int(parts[1], "element id")
            if eid in targets:
                parts[4] = str(sec_id)
                line = _join_record(parts)
                changed += 1
        out.append(line)
    if changed == 0:
        raise ValueError("No matching elements found")
    return _ensure_trailing_newline("\n".join(out)), [
        "Changed section to {0} for {1} element(s).".format(sec_id, changed)
    ]


def set_material_for_elements(
    text: str, element_ids: list[int], material_id: int
) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    mat_id = int(material_id)
    if not targets:
        raise ValueError("element_ids is empty")

    lines = text.splitlines()
    elem_secs = _element_section_map(lines)
    sec_targets = {elem_secs[eid] for eid in targets if eid in elem_secs}
    if not sec_targets:
        raise ValueError("No matching elements found")

    mate_ids = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "MATE":
            mate_ids.add(_parse_int(rec[1][1], "material id"))
    if mat_id not in mate_ids:
        raise ValueError("Unknown material id: {0}".format(mat_id))

    out: list[str] = []
    changed_secs: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "SECT":
            parts = rec[1]
            sid = _parse_int(parts[1], "section id")
            if sid in sec_targets:
                parts[3] = str(mat_id)
                line = _join_record(parts)
                changed_secs.add(sid)
        out.append(line)

    warnings = [
        "Changed material to {0} on section id(s) {1}.".format(
            mat_id, sorted(changed_secs)
        ),
        "Note: all elements using the same section share the updated material.",
    ]
    return _ensure_trailing_newline("\n".join(out)), warnings


def set_ejnt_for_elements(
    text: str,
    element_ids: list[int],
    preset: str | None = None,
    values: list[Any] | None = None,
) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    if not targets:
        raise ValueError("element_ids is empty")

    if preset is not None:
        if preset not in EJNT_PRESETS:
            raise ValueError("Unknown EJNT preset: {0}".format(preset))
        preset_values = EJNT_PRESETS[preset]
        if preset_values is None:
            return remove_ejnt_for_elements(text, element_ids)
        ryi, rzi, ryj, rzj = preset_values
    elif values is not None and len(values) == 4:
        ryi, rzi, ryj, rzj = values
    else:
        raise ValueError("preset or values is required")

    lines = text.splitlines()
    existing: dict[int, int] = {}
    for idx, line in enumerate(lines):
        rec = _split_record(line)
        if rec and rec[0] == "EJNT":
            eid = _parse_int(rec[1][1], "element id")
            existing[eid] = idx

    out = list(lines)
    updated = 0
    inserted: list[str] = []
    for eid in sorted(targets):
        new_line = _format_ejnt_line(eid, ryi, rzi, ryj, rzj)
        if eid in existing:
            out[existing[eid]] = new_line
            updated += 1
        else:
            inserted.append(new_line)

    if inserted:
        insert_at = _ejnt_insert_index(out)
        out[insert_at:insert_at] = inserted

    if updated == 0 and not inserted:
        raise ValueError("No matching elements found")

    label = preset or "custom"
    return _ensure_trailing_newline("\n".join(out)), [
        "Set EJNT ({0}) for {1} element(s).".format(label, len(targets))
    ]


def remove_ejnt_for_elements(text: str, element_ids: list[int]) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    if not targets:
        raise ValueError("element_ids is empty")
    out: list[str] = []
    removed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "EJNT":
            eid = _parse_int(rec[1][1], "element id")
            if eid in targets:
                removed += 1
                continue
        out.append(line)
    return _ensure_trailing_newline("\n".join(out)), [
        "Removed EJNT for {0} element(s); default rigid joints apply.".format(removed)
    ]


def _ejnt_insert_index(lines: list[str]) -> int:
    last_ejnt = -1
    last_elem = -1
    for idx, line in enumerate(lines):
        rec = _split_record(line)
        if not rec:
            continue
        if rec[0] == "ELEM":
            last_elem = idx
        elif rec[0] == "EJNT":
            last_ejnt = idx
    if last_ejnt >= 0:
        return last_ejnt + 1
    if last_elem >= 0:
        return last_elem + 1
    return len(lines)


def ejnt_lines_for_elements(text: str, element_ids: list[int]) -> list[dict[str, Any]]:
    """Return EJNT input lines for the given element ids (template if missing)."""

    targets = sorted({int(e) for e in element_ids})
    if not targets:
        raise ValueError("element_ids is empty")

    existing: dict[int, str] = {}
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "EJNT":
            eid = _parse_int(rec[1][1], "element id")
            existing[eid] = line

    out: list[dict[str, Any]] = []
    for eid in targets:
        if eid in existing:
            out.append({
                "element_id": eid,
                "line": existing[eid],
                "exists": True,
            })
        else:
            out.append({
                "element_id": eid,
                "line": _format_ejnt_line(eid, None, None, None, None),
                "exists": False,
            })
    return out


def _parse_ejnt_lines_text(lines_text: str, targets: set[int]) -> dict[int, str]:
    updates: dict[int, str] = {}
    for line in lines_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        rec = _split_record(stripped)
        if not rec or rec[0] != "EJNT":
            raise ValueError("Expected EJNT record: {0!r}".format(stripped[:80]))
        parts = rec[1]
        if len(parts) < 2:
            raise ValueError("Invalid EJNT record: {0!r}".format(stripped[:80]))
        eid = _parse_int(parts[1], "element id")
        if eid not in targets:
            raise ValueError(
                "EJNT element id {0} is not in the current selection".format(eid)
            )
        if eid in updates:
            raise ValueError("Duplicate EJNT for element id {0}".format(eid))
        updates[eid] = stripped
    return updates


def apply_ejnt_lines_text(
    text: str,
    element_ids: list[int],
    lines_text: str,
) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    if not targets:
        raise ValueError("element_ids is empty")

    updates = _parse_ejnt_lines_text(lines_text, targets)
    lines = text.splitlines()
    existing: dict[int, int] = {}
    for idx, line in enumerate(lines):
        rec = _split_record(line)
        if rec and rec[0] == "EJNT":
            eid = _parse_int(rec[1][1], "element id")
            existing[eid] = idx

    out: list[str] = []
    replaced: set[int] = set()
    updated = removed = 0
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "EJNT":
            eid = _parse_int(rec[1][1], "element id")
            if eid in targets:
                if eid in updates:
                    out.append(updates[eid])
                    replaced.add(eid)
                    updated += 1
                else:
                    removed += 1
                continue
        out.append(line)

    inserted = 0
    to_insert = [
        updates[eid] for eid in sorted(targets) if eid in updates and eid not in replaced
    ]
    if to_insert:
        insert_at = _ejnt_insert_index(out)
        out[insert_at:insert_at] = to_insert
        inserted = len(to_insert)

    if updated == 0 and inserted == 0 and removed == 0:
        raise ValueError("No EJNT changes to apply")

    parts: list[str] = []
    if updated:
        parts.append("updated {0}".format(updated))
    if inserted:
        parts.append("added {0}".format(inserted))
    if removed:
        parts.append("removed {0} (rigid default)".format(removed))
    return _ensure_trailing_newline("\n".join(out)), [
        "EJNT: " + ", ".join(parts) + " for selected element(s).",
    ]


def _node_ids_in_text(lines: list[str]) -> set[int]:
    out: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "NODE":
            out.add(_parse_int(rec[1][1], "node id"))
    return out


def _diap_ids_in_text(lines: list[str]) -> set[int]:
    out: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "DIAP":
            out.add(_parse_int(rec[1][1], "DIAP id"))
    return out


def _existing_dmem_ids(lines: list[str]) -> set[int]:
    out: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "DMEM":
            out.add(_parse_int(rec[1][1], "DMEM id"))
    return out


def _next_dmem_id(lines: list[str]) -> int:
    ids = _existing_dmem_ids(lines)
    if not ids:
        return 1001
    return max(ids) + 1


def _format_dmem_line(dmem_id: int, diap_id: int, n1: int, n2: int, n3: int) -> str:
    import os
    import sys

    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)
    from dat_format import DMEM_FMTS, record_line

    return record_line("DMEM", DMEM_FMTS, [dmem_id, diap_id, n1, n2, n3])


def _insert_dmem_lines(lines: list[str], new_data_lines: list[str]) -> list[str]:
    from stb_gui.dat_format_headers import SECTION_HEADERS

    out = list(lines)
    last_dmem = -1
    for idx, line in enumerate(out):
        rec = _split_record(line)
        if rec and rec[0] == "DMEM":
            last_dmem = idx
    if last_dmem >= 0:
        out[last_dmem + 1:last_dmem + 1] = new_data_lines
        return out

    insert_at = len(out)
    for idx, line in enumerate(out):
        rec = _split_record(line)
        if rec and rec[0] in ("DCON", "DLOD", "WWLL", "EJNT", "CONS"):
            insert_at = idx
            break

    block = list(SECTION_HEADERS["DMEM"])
    if insert_at < len(out) and insert_at > 0 and out[insert_at - 1].strip():
        block = [""] + block
    block.extend(new_data_lines)
    out[insert_at:insert_at] = block
    return out


def _existing_element_ids(lines: list[str]) -> set[int]:
    out: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "ELEM":
            out.add(_parse_int(rec[1][1], "element id"))
    return out


def _next_element_id(lines: list[str]) -> int:
    ids = _existing_element_ids(lines)
    if not ids:
        return 1
    return max(ids) + 1


def _find_element_between_nodes(lines: list[str], n1: int, n2: int) -> int | None:
    pair = {int(n1), int(n2)}
    for line in lines:
        rec = _split_record(line)
        if not rec or rec[0] != "ELEM":
            continue
        parts = rec[1]
        if len(parts) < 4:
            continue
        ni = _parse_int(parts[2], "node i")
        nj = _parse_int(parts[3], "node j")
        if {ni, nj} == pair:
            return _parse_int(parts[1], "element id")
    return None


def _format_elem_line(elem_id: int, ni: int, nj: int, sect_id: int, beta: float = 0.0) -> str:
    import os
    import sys

    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)
    from dat_format import ELEM_FMTS, record_line

    return record_line("ELEM", ELEM_FMTS, [elem_id, ni, nj, sect_id, beta])


def _insert_elem_lines(lines: list[str], new_data_lines: list[str]) -> list[str]:
    from stb_gui.dat_format_headers import SECTION_HEADERS

    out = list(lines)
    last_elem = -1
    for idx, line in enumerate(out):
        rec = _split_record(line)
        if rec and rec[0] == "ELEM":
            last_elem = idx
    if last_elem >= 0:
        out[last_elem + 1:last_elem + 1] = new_data_lines
        return out

    insert_at = len(out)
    for idx, line in enumerate(out):
        rec = _split_record(line)
        if rec and rec[0] == "CONS":
            insert_at = idx
            break

    block = list(SECTION_HEADERS["ELEM"])
    if insert_at < len(out) and insert_at > 0 and out[insert_at - 1].strip():
        block = [""] + block
    block.extend(new_data_lines)
    out[insert_at:insert_at] = block
    return out


def create_element(
    text: str,
    node_ids: list[int],
    section_id: int,
    beta: float = 0.0,
    elem_id: int | None = None,
) -> tuple[str, list[str]]:
    if len(node_ids) != 2:
        raise ValueError("create_element requires exactly 2 node ids")
    n1, n2 = int(node_ids[0]), int(node_ids[1])
    if n1 == n2:
        raise ValueError("Element endpoints must be different nodes")

    lines = text.splitlines()
    valid_nodes = _node_ids_in_text(lines)
    for n in (n1, n2):
        if n not in valid_nodes:
            raise ValueError("Unknown node id: {0}".format(n))

    sect_id = int(section_id)
    if sect_id not in _section_ids(lines):
        raise ValueError("Unknown section id: {0}".format(sect_id))

    existing = _find_element_between_nodes(lines, n1, n2)
    if existing is not None:
        raise ValueError(
            "Element {0} already connects nodes {1} and {2}".format(existing, n1, n2)
        )

    new_id = int(elem_id) if elem_id is not None else _next_element_id(lines)
    if new_id in _existing_element_ids(lines):
        raise ValueError("Element id {0} already exists".format(new_id))

    new_line = _format_elem_line(new_id, n1, n2, sect_id, float(beta))
    out = _insert_elem_lines(lines, [new_line])
    return _ensure_trailing_newline("\n".join(out)), [
        "Created ELEM {0} (nodes {1}, {2}, SECT {3}).".format(new_id, n1, n2, sect_id)
    ]


def create_dmem(
    text: str,
    diap_id: int,
    node_ids: list[int],
    dmem_id: int | None = None,
) -> tuple[str, list[str]]:
    nodes = sorted({int(n) for n in node_ids})
    if len(nodes) < 3:
        raise ValueError("create_dmem requires at least 3 node ids")
    if len(set(nodes)) != len(nodes):
        raise ValueError("DMEM nodes must be distinct")

    lines = text.splitlines()
    known_nodes = _node_ids_in_text(lines)
    for nid in nodes:
        if nid not in known_nodes:
            raise ValueError("Unknown node id: {0}".format(nid))

    diap = int(diap_id)
    known_diaps = _diap_ids_in_text(lines)
    if diap not in known_diaps:
        raise ValueError("Unknown DIAP id: {0}".format(diap))

    if len(nodes) == 3:
        return _create_single_dmem(lines, diap, nodes, dmem_id)

    from stb_gui.dmem_triangulate import (
        elem_adjacency_for_nodes,
        triangulate_node_selection,
    )

    coords3d = _node_coords_map(lines)
    elem_adj = elem_adjacency_for_nodes(lines, set(nodes))
    triangles = triangulate_node_selection(coords3d, nodes, elem_adj=elem_adj)
    return _create_dmem_triangles(lines, diap, triangles, dmem_id)


def _create_single_dmem(
    lines: list[str],
    diap_id: int,
    nodes: list[int],
    dmem_id: int | None,
) -> tuple[str, list[str]]:
    new_id = int(dmem_id) if dmem_id is not None else _next_dmem_id(lines)
    if new_id in _existing_dmem_ids(lines):
        raise ValueError("DMEM id {0} already exists".format(new_id))
    n1, n2, n3 = nodes
    new_line = _format_dmem_line(new_id, diap_id, n1, n2, n3)
    out = _insert_dmem_lines(lines, [new_line])
    return _ensure_trailing_newline("\n".join(out)), [
        "Created DMEM {0} for DIAP {1} (nodes {2}, {3}, {4}).".format(
            new_id, diap_id, n1, n2, n3
        )
    ]


def _existing_dmem_triangles_for_diap(lines: list[str], diap_id: int) -> set[tuple[int, int, int]]:
    out: set[tuple[int, int, int]] = set()
    for line in lines:
        rec = _split_record(line)
        if not rec or rec[0] != "DMEM":
            continue
        parts = rec[1]
        if int(parts[2]) != diap_id:
            continue
        tri = tuple(sorted(int(parts[i]) for i in (3, 4, 5)))
        out.add(tri)
    return out


def _create_dmem_triangles(
    lines: list[str],
    diap_id: int,
    triangles: list[tuple[int, int, int]],
    dmem_id: int | None,
) -> tuple[str, list[str]]:
    existing = _existing_dmem_triangles_for_diap(lines, diap_id)
    next_id = int(dmem_id) if dmem_id is not None else _next_dmem_id(lines)
    used_ids = _existing_dmem_ids(lines)
    new_lines: list[str] = []
    warnings: list[str] = []
    created = 0
    skipped = 0
    for n1, n2, n3 in triangles:
        key = tuple(sorted((n1, n2, n3)))
        if key in existing:
            skipped += 1
            continue
        while next_id in used_ids:
            next_id += 1
        new_lines.append(_format_dmem_line(next_id, diap_id, n1, n2, n3))
        used_ids.add(next_id)
        existing.add(key)
        warnings.append(
            "Created DMEM {0} for DIAP {1} (nodes {2}, {3}, {4}).".format(
                next_id, diap_id, n1, n2, n3
            )
        )
        next_id += 1
        created += 1
    if created == 0:
        raise ValueError("All candidate DMEM triangles already exist for DIAP {0}".format(diap_id))
    if skipped:
        warnings.append("Skipped {0} triangle(s) that already exist on DIAP {1}.".format(skipped, diap_id))
    warnings.insert(
        0,
        "Created {0} DMEM element(s) for DIAP {1} from {2} selected node(s).".format(
            created, diap_id, len({n for tri in triangles for n in tri})
        ),
    )
    out = _insert_dmem_lines(lines, new_lines)
    return _ensure_trailing_newline("\n".join(out)), warnings


def _node_coords_map(lines: list[str]) -> dict[int, tuple[float, float, float]]:
    out: dict[int, tuple[float, float, float]] = {}
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "NODE":
            parts = rec[1]
            nid = _parse_int(parts[1], "node id")
            out[nid] = (float(parts[2]), float(parts[3]), float(parts[4]))
    return out


def _order_wwll_corners(
    coords: dict[int, tuple[float, float, float]], node_ids: list[int]
) -> tuple[int, int, int, int, int]:
    import os
    import sys

    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)
    from wood_wall import order_wwll_corner_node_ids

    for nid in node_ids:
        if int(nid) not in coords:
            raise ValueError("Unknown node id: {0}".format(nid))
    return order_wwll_corner_node_ids(node_ids, coords)


def _existing_wwll_ids(lines: list[str]) -> set[int]:
    out: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "WWLL":
            out.add(_parse_int(rec[1][1], "WWLL id"))
    return out


def _next_wwll_id(lines: list[str]) -> int:
    ids = _existing_wwll_ids(lines)
    if not ids:
        return 1
    return max(ids) + 1


def _format_wwll_line(
    wwll_id: int,
    name: str,
    model: int,
    multiplier: float,
    direction: int,
    reference_drift: float,
    n1: int,
    n2: int,
    n3: int,
    n4: int,
    diap_id: int | None,
    layo: int,
) -> str:
    import os
    import sys

    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)
    from dat_format import WWLL_FMTS, record_line

    values = [
        wwll_id,
        name,
        int(model),
        float(multiplier),
        "",
        "",
        int(direction),
        float(reference_drift),
        n1,
        n2,
        n3,
        n4,
        "" if diap_id is None else int(diap_id),
        int(layo),
    ]
    return record_line("WWLL", WWLL_FMTS, values)


def _insert_wwll_lines(lines: list[str], new_data_lines: list[str]) -> list[str]:
    from stb_gui.dat_format_headers import SECTION_HEADERS

    out = list(lines)
    last_wwll = -1
    for idx, line in enumerate(out):
        rec = _split_record(line)
        if rec and rec[0] == "WWLL":
            last_wwll = idx
    if last_wwll >= 0:
        out[last_wwll + 1:last_wwll + 1] = new_data_lines
        return out

    insert_at = len(out)
    for idx, line in enumerate(out):
        rec = _split_record(line)
        if rec and rec[0] in ("EJNT", "CONS", "LNME", "LCMB", "PLOD"):
            insert_at = idx
            break

    block = list(SECTION_HEADERS["WWLL"])
    if insert_at < len(out) and insert_at > 0 and out[insert_at - 1].strip():
        block = [""] + block
    block.extend(new_data_lines)
    out[insert_at:insert_at] = block
    return out


def create_wwll(
    text: str,
    node_ids: list[int],
    multiplier: float = 2.0,
    model: int = 1,
    diap_id: int | None = None,
    layo: int = 1,
    reference_drift: float = 1.0 / 120.0,
    wwll_id: int | None = None,
    name: str | None = None,
) -> tuple[str, list[str]]:
    m = float(multiplier)
    if m <= 0.0:
        raise ValueError("Wall multiplier must be positive")
    if int(model) not in (0, 1):
        raise ValueError("WWLL MODEL must be 0 (brace) or 1 (panel)")
    if int(layo) not in (0, 1):
        raise ValueError("WWLL LAYO must be 0 (single) or 1 (X-brace)")

    lines = text.splitlines()
    coords = _node_coords_map(lines)
    n1, n2, n3, n4, direction = _order_wwll_corners(coords, node_ids)

    if diap_id is not None:
        diap = int(diap_id)
        if diap not in _diap_ids_in_text(lines):
            raise ValueError("Unknown DIAP id: {0}".format(diap))
    else:
        diap = None

    new_id = int(wwll_id) if wwll_id is not None else _next_wwll_id(lines)
    if new_id in _existing_wwll_ids(lines):
        raise ValueError("WWLL id {0} already exists".format(new_id))

    wall_name = name if name else "W{0}".format(new_id)
    new_line = _format_wwll_line(
        new_id,
        wall_name,
        int(model),
        m,
        direction,
        float(reference_drift),
        n1,
        n2,
        n3,
        n4,
        diap,
        int(layo),
    )
    out = _insert_wwll_lines(lines, [new_line])
    dir_label = "X" if direction == 0 else "Y"
    return _ensure_trailing_newline("\n".join(out)), [
        "Created WRW {0} ({1}) M={2} DIR={3} (nodes {4}, {5}, {6}, {7}).".format(
            new_id, wall_name, m, dir_label, n1, n2, n3, n4
        )
    ]


def delete_dmem(text: str, dmem_ids: list[int]) -> tuple[str, list[str]]:
    targets = {int(v) for v in dmem_ids}
    if not targets:
        raise ValueError("dmem_ids is empty")
    out: list[str] = []
    removed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "DMEM":
            rec_id = _parse_int(rec[1][1], "DMEM id")
            if rec_id in targets:
                removed += 1
                continue
        out.append(line)
    if removed == 0:
        raise ValueError("No matching DMEM records found to delete")
    warnings = [
        "Deleted {0} DMEM record(s) for id(s) {1}.".format(removed, sorted(targets))
    ]
    return _ensure_trailing_newline("\n".join(out)), warnings


def delete_wwll(text: str, wwll_ids: list[int]) -> tuple[str, list[str]]:
    targets = {int(v) for v in wwll_ids}
    if not targets:
        raise ValueError("wwll_ids is empty")
    out: list[str] = []
    removed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "WWLL":
            rec_id = _parse_int(rec[1][1], "WWLL id")
            if rec_id in targets:
                removed += 1
                continue
        out.append(line)
    if removed == 0:
        raise ValueError("No matching WWLL records found to delete")
    warnings = [
        "Deleted {0} WWLL record(s) for id(s) {1}.".format(removed, sorted(targets))
    ]
    return _ensure_trailing_newline("\n".join(out)), warnings


def delete_selection(
    text: str,
    *,
    node_ids: list[int] | None = None,
    element_ids: list[int] | None = None,
    dmem_ids: list[int] | None = None,
    wwll_ids: list[int] | None = None,
) -> tuple[str, list[str]]:
    nodes = [int(n) for n in (node_ids or [])]
    elems = [int(e) for e in (element_ids or [])]
    dmems = [int(v) for v in (dmem_ids or [])]
    wwlls = [int(v) for v in (wwll_ids or [])]
    if not nodes and not elems and not dmems and not wwlls:
        raise ValueError("Nothing selected to delete")

    warnings: list[str] = []
    if dmems:
        text, w = delete_dmem(text, dmems)
        warnings.extend(w)
    if wwlls:
        text, w = delete_wwll(text, wwlls)
        warnings.extend(w)
    if elems:
        text, w = delete_elements(text, elems)
        warnings.extend(w)
    if nodes:
        text, w = delete_nodes(text, nodes)
        warnings.extend(w)
    return text, warnings


def set_wwll_multiplier(text: str, wwll_ids: list[int], multiplier: float) -> tuple[str, list[str]]:
    targets = {int(v) for v in wwll_ids}
    m = float(multiplier)
    if not targets:
        raise ValueError("wwll_ids is empty")
    if m <= 0.0:
        raise ValueError("Wall multiplier must be positive")

    out: list[str] = []
    changed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "WWLL":
            parts = rec[1]
            rec_id = _parse_int(parts[1], "WWLL id")
            if rec_id in targets:
                parts[4] = "{0:.6g}".format(m)
                line = _join_record(parts)
                changed += 1
        out.append(line)
    if changed == 0:
        raise ValueError("No matching WWLL records found")
    return _ensure_trailing_newline("\n".join(out)), [
        "Changed wall multiplier to {0} for {1} WWLL record(s).".format(m, changed)
    ]


def set_wwll_model(text: str, wwll_ids: list[int], model: int) -> tuple[str, list[str]]:
    targets = {int(v) for v in wwll_ids}
    mdl = int(model)
    if not targets:
        raise ValueError("wwll_ids is empty")
    if mdl not in (0, 1):
        raise ValueError("WWLL MODEL must be 0 (brace) or 1 (panel)")

    out: list[str] = []
    changed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "WWLL":
            parts = rec[1]
            rec_id = _parse_int(parts[1], "WWLL id")
            if rec_id in targets:
                parts[3] = str(mdl)
                if mdl == 0 and (len(parts) < 15 or not parts[14].strip()):
                    while len(parts) < 15:
                        parts.append("")
                    parts[14] = "1"
                line = _join_record(parts)
                changed += 1
        out.append(line)
    if changed == 0:
        raise ValueError("No matching WWLL records found")
    label = "brace" if mdl == 0 else "panel"
    return _ensure_trailing_newline("\n".join(out)), [
        "Changed wall model to {0} for {1} WWLL record(s).".format(label, changed)
    ]


def _diap_src_is_timber(src_code: int) -> bool:
    return src_code in (1, 2)


def set_diap_timber_multiplier(
    text: str, diap_ids: list[int], multiplier: float
) -> tuple[str, list[str]]:
    targets = {int(v) for v in diap_ids}
    m = float(multiplier)
    if not targets:
        raise ValueError("diap_ids is empty")
    if m <= 0.0:
        raise ValueError("Floor/roof multiplier must be positive")

    out: list[str] = []
    changed = 0
    skipped: list[int] = []
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "DIAP":
            parts = rec[1]
            if len(parts) < 6:
                out.append(line)
                continue
            rec_id = _parse_int(parts[1], "DIAP id")
            if rec_id in targets:
                src = _parse_int(parts[4], "DIAP SRC")
                if not _diap_src_is_timber(src):
                    skipped.append(rec_id)
                    out.append(line)
                    continue
                parts[5] = "{0:.6g}".format(m)
                line = _join_record(parts)
                changed += 1
        out.append(line)
    if changed == 0:
        if skipped:
            raise ValueError(
                "DIAP id(s) {0} are not timber floor/roof (SRC=1/2)".format(sorted(skipped))
            )
        raise ValueError("No matching DIAP records found")
    warnings = [
        "Changed floor/roof multiplier to {0} for {1} DIAP record(s).".format(m, changed)
    ]
    if skipped:
        warnings.append(
            "Skipped DIAP id(s) {0}: not timber floor/roof (SRC=1/2).".format(sorted(skipped))
        )
    return _ensure_trailing_newline("\n".join(out)), warnings


CONS_DOF_LABELS = ("TX", "TY", "TZ", "RX", "RY", "RZ")


def _format_cons_line(node_id: int, fixed: list[bool]) -> str:
    import os
    import sys

    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)
    from dat_format import CONS_FMTS, record_line

    values = [int(node_id)] + [int(bool(v)) for v in fixed]
    return record_line("CONS", CONS_FMTS, values)


def _cons_insert_index(lines: list[str]) -> int:
    last_cons = -1
    last_node = -1
    for idx, line in enumerate(lines):
        rec = _split_record(line)
        if not rec:
            continue
        if rec[0] == "NODE":
            last_node = idx
        elif rec[0] == "CONS":
            last_cons = idx
    if last_cons >= 0:
        return last_cons + 1
    if last_node >= 0:
        return last_node + 1
    return len(lines)


def _parse_cons_fixed(values: list[Any]) -> list[bool]:
    if not isinstance(values, list) or len(values) != 6:
        raise ValueError("fixed must be a list of 6 booleans (TX..RZ)")
    out: list[bool] = []
    for i, raw in enumerate(values):
        if isinstance(raw, bool):
            out.append(raw)
            continue
        if isinstance(raw, (int, float)) and raw in (0, 1):
            out.append(bool(int(raw)))
            continue
        raise ValueError("Invalid CONS {0} value: {1!r}".format(CONS_DOF_LABELS[i], raw))
    return out


def set_cons_for_nodes(
    text: str,
    node_ids: list[int],
    fixed: list[Any],
) -> tuple[str, list[str]]:
    targets = {int(n) for n in node_ids}
    if not targets:
        raise ValueError("node_ids is empty")

    flags = _parse_cons_fixed(fixed)
    lines = text.splitlines()
    known_nodes = _node_ids_in_text(lines)
    for nid in targets:
        if nid not in known_nodes:
            raise ValueError("Unknown node id: {0}".format(nid))

    existing: dict[int, int] = {}
    for idx, line in enumerate(lines):
        rec = _split_record(line)
        if rec and rec[0] == "CONS":
            nid = _parse_int(rec[1][1], "node id")
            existing[nid] = idx

    out = list(lines)
    removed = 0
    updated = 0
    inserted: list[str] = []

    if not any(flags):
        kept: list[str] = []
        for line in out:
            rec = _split_record(line)
            if rec and rec[0] == "CONS":
                nid = _parse_int(rec[1][1], "node id")
                if nid in targets:
                    removed += 1
                    continue
            kept.append(line)
        out = kept
    else:
        new_line = None
        for nid in sorted(targets):
            line = _format_cons_line(nid, flags)
            if nid in existing:
                out[existing[nid]] = line
                updated += 1
            else:
                inserted.append(line)

        if inserted:
            insert_at = _cons_insert_index(out)
            out[insert_at:insert_at] = inserted

    if removed == 0 and updated == 0 and not inserted:
        raise ValueError("No CONS changes to apply")

    active = [CONS_DOF_LABELS[i] for i, v in enumerate(flags) if v]
    if not any(flags):
        summary = "Removed CONS for {0} node(s).".format(removed)
    else:
        dof_text = ", ".join(active) if active else "none"
        parts: list[str] = []
        if updated:
            parts.append("updated {0}".format(updated))
        if inserted:
            parts.append("added {0}".format(len(inserted)))
        summary = "Set CONS ({0}) for {1} node(s): {2}.".format(
            dof_text, len(targets), ", ".join(parts)
        )
    return _ensure_trailing_newline("\n".join(out)), [summary]


def apply_edit_action(text: str, action: dict[str, Any]) -> tuple[str, list[str]]:
    op = action.get("action")
    element_ids = action.get("element_ids") or []
    node_ids = action.get("node_ids") or []
    dmem_ids = action.get("dmem_ids") or []
    wwll_ids = action.get("wwll_ids") or []
    diap_ids = action.get("diap_ids") or []
    if not isinstance(element_ids, list):
        raise ValueError("element_ids must be a list")
    if not isinstance(node_ids, list):
        raise ValueError("node_ids must be a list")
    if not isinstance(dmem_ids, list):
        raise ValueError("dmem_ids must be a list")
    if not isinstance(wwll_ids, list):
        raise ValueError("wwll_ids must be a list")
    if not isinstance(diap_ids, list):
        raise ValueError("diap_ids must be a list")

    if op == "delete":
        return delete_elements(text, element_ids)
    if op == "delete_nodes":
        return delete_nodes(text, node_ids)
    if op == "create_element":
        return create_element(
            text,
            node_ids,
            action["section_id"],
            beta=action.get("beta", 0.0),
            elem_id=action.get("elem_id"),
        )
    if op == "create_dmem":
        return create_dmem(text, action["diap_id"], node_ids, action.get("dmem_id"))
    if op == "create_wwll":
        diap_raw = action.get("diap_id")
        return create_wwll(
            text,
            node_ids,
            multiplier=action["multiplier"],
            model=action.get("model", 1),
            diap_id=None if diap_raw in (None, "") else int(diap_raw),
            layo=action.get("layo", 1),
        )
    if op == "delete_dmem":
        return delete_dmem(text, dmem_ids)
    if op == "delete_wwll":
        return delete_wwll(text, wwll_ids)
    if op == "delete_selection":
        return delete_selection(
            text,
            node_ids=node_ids,
            element_ids=element_ids,
            dmem_ids=dmem_ids,
            wwll_ids=wwll_ids,
        )
    if op == "set_wwll_multiplier":
        return set_wwll_multiplier(text, wwll_ids, action["multiplier"])
    if op == "set_wwll_model":
        return set_wwll_model(text, wwll_ids, action["model"])
    if op == "set_diap_timber_multiplier":
        return set_diap_timber_multiplier(text, diap_ids, action["multiplier"])
    if op == "set_section":
        return set_element_section(text, element_ids, action["section_id"])
    if op == "set_material":
        return set_material_for_elements(text, element_ids, action["material_id"])
    if op == "set_ejnt":
        return set_ejnt_for_elements(
            text,
            element_ids,
            preset=action.get("preset"),
            values=action.get("values"),
        )
    if op == "remove_ejnt":
        return remove_ejnt_for_elements(text, element_ids)
    if op == "set_ejnt_lines":
        lines_text = action.get("lines_text")
        if lines_text is None:
            raise ValueError("lines_text is required")
        return apply_ejnt_lines_text(text, element_ids, str(lines_text))
    if op == "set_cons":
        return set_cons_for_nodes(text, node_ids, action.get("fixed") or [])
    raise ValueError("Unknown action: {0!r}".format(op))


def validate_dat_text(text: str) -> None:
    import sys

    root = __import__("os").path.dirname(__import__("os").path.dirname(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)
    from stb_engine import parse_input
    from stb_engine.errors import StbParseError

    try:
        parse_input(text.splitlines())
    except StbParseError as ex:
        raise ValueError(str(ex)) from ex


def _ensure_trailing_newline(text: str) -> str:
    if not text.endswith("\n"):
        return text + "\n"
    return text

