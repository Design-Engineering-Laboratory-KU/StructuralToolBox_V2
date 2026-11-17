"""``foundation`` settings in ``model.project.json`` (mat foundations)."""

from dataclasses import asdict, dataclass
import re
from typing import Tuple

from stb_project.schema import ProjectSchemaError

FOUNDATION_MAT = "mat"
ALLOWED_FOUNDATION_TYPES = (FOUNDATION_MAT,)
EDGES_AUTO = "auto"
DEFAULT_CONCRETE_UNIT_WEIGHT = 24.0

_SPACED_BARS = re.compile(r"^D\d+@\d+$")
_COUNTED_BARS = re.compile(r"^\d+-D\d+$")
_STIRRUPS = re.compile(r"^\d+-D\d+@\d+$")

FOUNDATION_JSON_SCHEMA = {"type": "object"}


@dataclass(frozen=True)
class SoilSettings:
    name: str = ""
    bearing_long: float = 0.0
    bearing_short: float = 0.0
    young: float = 0.0


@dataclass(frozen=True)
class ConcreteSettings:
    name: str = ""
    fc: float = 0.0
    unit_weight: float = DEFAULT_CONCRETE_UNIT_WEIGHT


@dataclass(frozen=True)
class SlabBars:
    end: str
    mid: str


@dataclass(frozen=True)
class SlabType:
    name: str
    thickness: float
    d_short: float
    d_long: float
    rebar: str
    short: SlabBars
    long: SlabBars


@dataclass(frozen=True)
class FoundationPanel:
    slab: str
    x: Tuple[str, str]
    y: Tuple[str, str]
    edges: str = EDGES_AUTO


@dataclass(frozen=True)
class FoundationBeamType:
    name: str
    b: float
    d: float
    top: str
    bottom: str
    dt: float
    stirrup: str
    main_rebar: str
    stirrup_rebar: str


@dataclass(frozen=True)
class FoundationBeamLine:
    beam: str
    frame: str
    span: Tuple[str, str]


@dataclass(frozen=True)
class FoundationSettings:
    type: str = ""
    level: str = ""
    soil: SoilSettings = SoilSettings()
    concrete: ConcreteSettings = ConcreteSettings()
    extra_load: float = 0.0
    first_floor_height: float = 0.0
    embedment_depth: float = 0.0
    slab_types: Tuple[SlabType, ...] = ()
    panels: Tuple[FoundationPanel, ...] = ()
    beam_types: Tuple[FoundationBeamType, ...] = ()
    beam_lines: Tuple[FoundationBeamLine, ...] = ()

    @property
    def is_default(self):
        return self.type == ""


def _object(raw, path, allowed):
    if not isinstance(raw, dict):
        raise ProjectSchemaError(path + " must be an object")
    unknown = sorted(set(raw) - set(allowed))
    if unknown:
        raise ProjectSchemaError(path + " has unknown field(s): " + ", ".join(unknown))
    return raw


def _list(raw, path):
    if not isinstance(raw, list):
        raise ProjectSchemaError(path + " must be an array")
    return raw


def _string(raw, key, path):
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProjectSchemaError(path + "." + key + " is required")
    return value.strip()


def _number(raw, key, path, default=None, minimum_exclusive=None, minimum=None):
    value = raw.get(key, default)
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProjectSchemaError(path + "." + key + " must be a number")
    value = float(value)
    if minimum_exclusive is not None and value <= minimum_exclusive:
        raise ProjectSchemaError(path + "." + key + " must be greater than " + str(minimum_exclusive))
    if minimum is not None and value < minimum:
        raise ProjectSchemaError(path + "." + key + " must be at least " + str(minimum))
    return value


def _pair(raw, key, path):
    value = raw.get(key)
    if not isinstance(value, list) or len(value) != 2 or not all(isinstance(v, str) and v.strip() for v in value):
        raise ProjectSchemaError(path + "." + key + " must list two grid names")
    return value[0].strip(), value[1].strip()


def _bars(raw, key, path, pattern, example):
    value = _string(raw, key, path)
    if not pattern.match(value):
        raise ProjectSchemaError(path + "." + key + " must look like " + example + ": " + value)
    return value


def _parse_slab_bars(raw, path):
    _object(raw, path, ["end", "mid"])
    return SlabBars(
        end=_bars(raw, "end", path, _SPACED_BARS, "D13@300"),
        mid=_bars(raw, "mid", path, _SPACED_BARS, "D13@300"),
    )


def _parse_slab_types(raw, path):
    out = []
    for idx, item in enumerate(_list(raw, path)):
        item_path = path + "[" + str(idx) + "]"
        _object(item, item_path, ["name", "thickness", "d_short", "d_long", "rebar", "short", "long"])
        out.append(SlabType(
            name=_string(item, "name", item_path),
            thickness=_number(item, "thickness", item_path, minimum_exclusive=0.0),
            d_short=_number(item, "d_short", item_path, minimum_exclusive=0.0),
            d_long=_number(item, "d_long", item_path, minimum_exclusive=0.0),
            rebar=_string(item, "rebar", item_path),
            short=_parse_slab_bars(item.get("short"), item_path + ".short"),
            long=_parse_slab_bars(item.get("long"), item_path + ".long"),
        ))
    _unique([s.name for s in out], path)
    return tuple(out)


def _unique(names, path):
    if len(set(names)) != len(names):
        raise ProjectSchemaError(path + " has duplicate names")


def _parse_panels(raw, path, slab_names):
    out = []
    for idx, item in enumerate(_list(raw, path)):
        item_path = path + "[" + str(idx) + "]"
        _object(item, item_path, ["slab", "x", "y", "edges"])
        slab = _string(item, "slab", item_path)
        if slab not in slab_names:
            raise ProjectSchemaError(item_path + ".slab refers to an unknown slab type: " + slab)
        edges = item.get("edges", EDGES_AUTO)
        if edges != EDGES_AUTO:
            raise ProjectSchemaError(item_path + ".edges supports only auto")
        out.append(FoundationPanel(slab=slab, x=_pair(item, "x", item_path), y=_pair(item, "y", item_path), edges=edges))
    return tuple(out)


def _parse_beam_types(raw, path):
    out = []
    for idx, item in enumerate(_list(raw, path)):
        item_path = path + "[" + str(idx) + "]"
        _object(item, item_path, ["name", "b", "d", "top", "bottom", "dt", "stirrup", "main_rebar", "stirrup_rebar"])
        out.append(FoundationBeamType(
            name=_string(item, "name", item_path),
            b=_number(item, "b", item_path, minimum_exclusive=0.0),
            d=_number(item, "d", item_path, minimum_exclusive=0.0),
            top=_bars(item, "top", item_path, _COUNTED_BARS, "2-D19"),
            bottom=_bars(item, "bottom", item_path, _COUNTED_BARS, "2-D19"),
            dt=_number(item, "dt", item_path, minimum_exclusive=0.0),
            stirrup=_bars(item, "stirrup", item_path, _STIRRUPS, "1-D10@200"),
            main_rebar=_string(item, "main_rebar", item_path),
            stirrup_rebar=_string(item, "stirrup_rebar", item_path),
        ))
    _unique([b.name for b in out], path)
    return tuple(out)


def _parse_beam_lines(raw, path, beam_names):
    out = []
    for idx, item in enumerate(_list(raw, path)):
        item_path = path + "[" + str(idx) + "]"
        _object(item, item_path, ["beam", "frame", "span"])
        beam = _string(item, "beam", item_path)
        if beam not in beam_names:
            raise ProjectSchemaError(item_path + ".beam refers to an unknown beam type: " + beam)
        out.append(FoundationBeamLine(beam=beam, frame=_string(item, "frame", item_path), span=_pair(item, "span", item_path)))
    return tuple(out)


def parse_foundation_settings(raw, path="project.foundation"):
    if raw is None:
        return FoundationSettings()
    _object(
        raw,
        path,
        [
            "type", "level", "soil", "concrete", "extra_load", "first_floor_height", "embedment_depth",
            "slab_types", "panels", "beam_types", "beam_lines",
        ],
    )
    kind = _string(raw, "type", path)
    if kind not in ALLOWED_FOUNDATION_TYPES:
        raise ProjectSchemaError(path + ".type is not supported: " + kind)

    soil_raw = _object(raw.get("soil"), path + ".soil", ["name", "bearing_long", "bearing_short", "young"])
    soil = SoilSettings(
        name=str(soil_raw.get("name", "") or ""),
        bearing_long=_number(soil_raw, "bearing_long", path + ".soil", minimum_exclusive=0.0),
        bearing_short=_number(soil_raw, "bearing_short", path + ".soil", minimum_exclusive=0.0),
        young=_number(soil_raw, "young", path + ".soil", default=0.0, minimum=0.0),
    )
    concrete_raw = _object(raw.get("concrete"), path + ".concrete", ["name", "fc", "unit_weight"])
    concrete = ConcreteSettings(
        name=_string(concrete_raw, "name", path + ".concrete"),
        fc=_number(concrete_raw, "fc", path + ".concrete", minimum_exclusive=0.0),
        unit_weight=_number(
            concrete_raw, "unit_weight", path + ".concrete", default=DEFAULT_CONCRETE_UNIT_WEIGHT, minimum_exclusive=0.0
        ),
    )
    slab_types = _parse_slab_types(raw.get("slab_types", []), path + ".slab_types")
    if not slab_types:
        raise ProjectSchemaError(path + ".slab_types is required")
    panels = _parse_panels(raw.get("panels", []), path + ".panels", {s.name for s in slab_types})
    if not panels:
        raise ProjectSchemaError(path + ".panels is required")
    beam_types = _parse_beam_types(raw.get("beam_types", []), path + ".beam_types")
    return FoundationSettings(
        type=kind,
        level=str(raw.get("level", "") or "").strip(),
        soil=soil,
        concrete=concrete,
        extra_load=_number(raw, "extra_load", path, default=0.0, minimum=0.0),
        first_floor_height=_number(raw, "first_floor_height", path, default=0.0, minimum=0.0),
        embedment_depth=_number(raw, "embedment_depth", path, default=0.0, minimum=0.0),
        slab_types=slab_types,
        panels=panels,
        beam_types=beam_types,
        beam_lines=_parse_beam_lines(raw.get("beam_lines", []), path + ".beam_lines", {b.name for b in beam_types}),
    )


def _plain(value):
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def foundation_settings_to_dict(settings: FoundationSettings):
    return _plain(asdict(settings))
