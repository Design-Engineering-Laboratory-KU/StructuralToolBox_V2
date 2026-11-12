"""Small helpers shared by the chapter builders."""

import re

from stb_reports.calc_book.document import Column, Heading, Table, Text


def fmt(value, places=2):
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "はい" if value else "いいえ"
    if isinstance(value, int):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value) if value != "" else "-"
    text = "{0:.{1}f}".format(number, places)
    if text.startswith("-") and float(text) == 0.0:
        text = text[1:]
    return text


def dict_table(keys, rows, labels, title="", unit="", places=None, font_size=7.0):
    """A table from row dicts; places maps a key to its decimal places (default 3)."""

    places = places or {}
    columns = tuple(Column(labels.get(k, k)) for k in keys)
    body = tuple(tuple(_cell(row.get(k), places.get(k, 3)) for k in keys) for row in rows)
    return Table(columns=columns, rows=body, title=title, unit=unit, font_size=font_size)


def _cell(value, places):
    if isinstance(value, float):
        return fmt(value, places)
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) if value else "-"
    return "-" if value is None or value == "" else str(value)


_SEPARATOR = re.compile(r"^[\s:|-]+$")


def _split_row(line):
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip().replace("\\|", "|") for cell in text.split("|")]


def markdown_blocks(text, base_level=3):
    """Turn the Markdown written by the load reports into blocks.

    The top heading of each report is dropped because the chapter has its own.
    """

    blocks = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("|"):
            table = []
            while i < len(lines) and lines[i].startswith("|"):
                table.append(lines[i])
                i += 1
            rows = [_split_row(r) for r in table if not _SEPARATOR.match(r)]
            if rows:
                count = max(len(r) for r in rows)
                body = tuple(tuple(r + [""] * (count - len(r))) for r in rows[1:])
                columns = tuple(Column(c) for c in rows[0] + [""] * (count - len(rows[0])))
                blocks.append(Table(columns=columns, rows=body, font_size=6.5))
            continue
        heading = re.match(r"^(#+)\s+(.*)$", line)
        if heading:
            depth = len(heading.group(1))
            if depth > 1:
                blocks.append(Heading(base_level + depth - 1, heading.group(2)))
        elif line.startswith("- "):
            blocks.append(Text("・" + line[2:], size=7.5, indent=8.0))
        elif line.strip():
            blocks.append(Text(line.strip(), size=7.5))
        i += 1
    return blocks
