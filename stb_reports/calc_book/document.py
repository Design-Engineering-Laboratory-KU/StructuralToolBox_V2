"""Output-independent building blocks of a structural calculation book."""

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence, Tuple, Union

CENTER = "center"
LEFT = "left"
RIGHT = "right"


@dataclass(frozen=True)
class Heading:
    """Level 1 is a chapter (§) and starts a new page."""

    level: int
    text: str


@dataclass(frozen=True)
class Text:
    text: str
    size: float = 8.0
    indent: float = 0.0
    bold: bool = False


@dataclass(frozen=True)
class Column:
    label: str
    width: float = 1.0
    align: str = CENTER


@dataclass(frozen=True)
class Cell:
    text: str
    span: int = 1
    align: Optional[str] = None
    bold: bool = False


Row = Sequence[Union[str, Cell]]


@dataclass(frozen=True)
class Table:
    columns: Tuple[Column, ...]
    rows: Tuple[Row, ...]
    title: str = ""
    unit: str = ""
    note: str = ""
    show_header: bool = True
    font_size: float = 7.0
    width_ratio: float = 1.0
    keep_together: bool = False


@dataclass(frozen=True)
class Figure:
    """draw(canvas, width, height) paints in points, with the origin at bottom left."""

    height: float
    draw: Callable
    title: str = ""
    unit: str = ""


@dataclass(frozen=True)
class PageBreak:
    pass


Block = Union[Heading, Text, Table, Figure, PageBreak]


@dataclass(frozen=True)
class CoverField:
    label: str
    value: str


@dataclass(frozen=True)
class CalcDocument:
    title: str
    project_name: str
    program: str
    generated_at: str
    input_id: str
    designer: str = ""
    cover_fields: Tuple[CoverField, ...] = ()
    blocks: Tuple[Block, ...] = field(default_factory=tuple)


def key_value_table(rows, title="", label_width=1.0, value_width=2.4, width_ratio=0.8, unit=""):
    """A two-column table without a header; values are left aligned."""

    return Table(
        columns=(Column("", label_width), Column("", value_width, LEFT)),
        rows=tuple((str(k), _text(v)) for k, v in rows),
        title=title,
        unit=unit,
        show_header=False,
        width_ratio=width_ratio,
        font_size=7.5,
    )


def _text(value):
    return "-" if value is None or value == "" else str(value)
