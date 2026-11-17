"""Paginate a CalcDocument and draw it with ReportLab's canvas.

Rows have a known height, so pagination is plain arithmetic. Platypus tables
were measured at about 3 minutes for 860 pages; this layout avoids them.
"""

import math
import os
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from stb_reports.calc_book.document import (
    CENTER,
    LEFT,
    RIGHT,
    Cell,
    CalcDocument,
    Figure,
    Heading,
    PageBreak,
    Table,
    Text,
)

FONT = "StbGothic"
FONT_BOLD = "StbGothic-Bold"
_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_LEFT = 42.0
MARGIN_RIGHT = 36.0
FRAME_TOP = PAGE_HEIGHT - 62.0
FRAME_BOTTOM = 54.0
FRAME_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
FRAME_HEIGHT = FRAME_TOP - FRAME_BOTTOM

MIN_CELL_FONT = 4.0
CELL_PADDING = 2.0
GRID_LINE = 0.35
TOC_ROW_HEIGHT = 13.5
TOC_MAX_LEVEL = 3

_HEADING_STYLES = {
    1: (12.0, 8.0, 8.0),
    2: (10.5, 8.0, 6.0),
    3: (9.5, 6.0, 5.0),
}
_DEFAULT_HEADING_STYLE = (8.5, 5.0, 4.0)
_widths = {}


def register_fonts():
    if FONT in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont(FONT, os.path.join(_FONT_DIR, "BIZUDGothic-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(_FONT_DIR, "BIZUDGothic-Bold.ttf")))


def text_width(text, font, size):
    key = (text, font)
    width = _widths.get(key)
    if width is None:
        width = pdfmetrics.stringWidth(text, font, 1.0)
        _widths[key] = width
    return width * size


def wrap_text(text, font, size, max_width):
    lines = []
    for paragraph in str(text).split("\n"):
        current = ""
        for ch in paragraph:
            if current and text_width(current + ch, font, size) > max_width:
                lines.append(current)
                current = ch
            else:
                current += ch
        lines.append(current)
    return lines


class _Row:
    __slots__ = ("cells", "height")

    def __init__(self, cells, height):
        self.cells = cells
        self.height = height


class _Layout:
    def __init__(self):
        self.pages: List[list] = [[]]
        self.y = FRAME_TOP
        self.headings = []

    def new_page(self):
        if self.pages[-1]:
            self.pages.append([])
        self.y = FRAME_TOP

    def ensure(self, height):
        if self.y - height < FRAME_BOTTOM:
            self.new_page()

    def add(self, op):
        self.pages[-1].append(op)


def _heading_style(level):
    return _HEADING_STYLES.get(level, _DEFAULT_HEADING_STYLE)


def _heading_height(block):
    size, before, after = _heading_style(block.level)
    return before + size + after


def _text_lines(block):
    font = FONT_BOLD if block.bold else FONT
    return wrap_text(block.text, font, block.size, FRAME_WIDTH - block.indent)


def _table_width(table):
    return FRAME_WIDTH * table.width_ratio


def _column_widths(table):
    total = sum(c.width for c in table.columns)
    return [c.width / total * _table_width(table) for c in table.columns]


def _normalize_cells(row, table):
    cells = []
    index = 0
    for item in row:
        if isinstance(item, Cell):
            cells.append((item.text, index, item.span, item.align, item.bold))
            index += item.span
        else:
            cells.append((str(item), index, 1, None, False))
            index += 1
    return cells


def _make_row(cells, table, widths, bold=False):
    size = table.font_size
    lines = 1
    for text, _start, _span, _align, _bold in cells:
        lines = max(lines, text.count("\n") + 1)
    height = lines * size * 1.22 + 3.4
    return _Row(tuple((t, s, n, a, b or bold) for t, s, n, a, b in cells), height)


def _header_row(table, widths):
    cells = [(c.label, i, 1, CENTER, True) for i, c in enumerate(table.columns)]
    return _make_row(cells, table, widths, bold=True)


def _block_lead_height(blocks, index):
    """Space the block needs on a page so a heading is not left alone."""

    block = blocks[index]
    if isinstance(block, Heading):
        following = _block_lead_height(blocks, index + 1) if index + 1 < len(blocks) else 0.0
        return _heading_height(block) + following
    if isinstance(block, Text):
        return block.size * 1.3
    if isinstance(block, Figure):
        return block.height + (12.0 if block.title else 0.0)
    if isinstance(block, Table):
        title = 11.0 if (block.title or block.unit) else 0.0
        widths = _column_widths(block)
        header = _header_row(block, widths).height if block.show_header else 0.0
        if block.keep_together:
            return title + header + sum(_make_row(_normalize_cells(r, block), block, widths).height for r in block.rows)
        first = _make_row(_normalize_cells(block.rows[0], block), block, widths).height if block.rows else 0.0
        return title + header + first
    return 0.0


def _layout(blocks) -> _Layout:
    out = _Layout()
    for index, block in enumerate(blocks):
        if isinstance(block, PageBreak):
            out.new_page()
        elif isinstance(block, Heading):
            _place_heading(out, blocks, index, block)
        elif isinstance(block, Text):
            _place_text(out, block)
        elif isinstance(block, Table):
            _place_table(out, block)
        elif isinstance(block, Figure):
            _place_figure(out, block)
    if not out.pages[-1] and len(out.pages) > 1:
        out.pages.pop()
    return out


def _place_heading(out, blocks, index, block):
    if block.level == 1:
        out.new_page()
    else:
        needed = _block_lead_height(blocks, index)
        if needed <= FRAME_HEIGHT:
            out.ensure(needed)
    size, before, after = _heading_style(block.level)
    baseline = out.y - before - size
    key = "h{0}".format(len(out.headings))
    out.headings.append((block.level, block.text, len(out.pages), key, out.y))
    out.add((_draw_heading, block, baseline, key))
    out.y = baseline - after


def _place_text(out, block):
    font = FONT_BOLD if block.bold else FONT
    leading = block.size * 1.3
    for line in _text_lines(block):
        out.ensure(leading)
        out.y -= leading
        out.add((_draw_text_line, line, MARGIN_LEFT + block.indent, out.y + leading * 0.2, font, block.size))
    out.y -= 3.0


def _place_figure(out, block):
    title = 12.0 if (block.title or block.unit) else 0.0
    out.ensure(block.height + title)
    if title:
        out.add((_draw_caption, block.title, block.unit, MARGIN_LEFT, FRAME_WIDTH, out.y - 9.0))
        out.y -= title
    out.add((_draw_figure, block, out.y - block.height))
    out.y -= block.height + 6.0


def _place_table(out, table):
    widths = _column_widths(table)
    header = _header_row(table, widths) if table.show_header else None
    rows = [_make_row(_normalize_cells(r, table), table, widths) for r in table.rows]
    title_height = 11.0 if (table.title or table.unit) else 0.0
    header_height = header.height if header else 0.0

    if table.keep_together:
        total = title_height + header_height + sum(r.height for r in rows)
        if total <= FRAME_HEIGHT:
            out.ensure(total)

    index = 0
    first = True
    while first or index < len(rows):
        lead = (title_height if first else 0.0) + header_height
        next_row = rows[index].height if index < len(rows) else 0.0
        if out.y - lead - next_row < FRAME_BOTTOM:
            out.new_page()
        if first and title_height:
            out.add((_draw_caption, table.title, table.unit, MARGIN_LEFT, _table_width(table), out.y - 8.0))
            out.y -= title_height
        top = out.y
        segment = [header] if header else []
        out.y -= header_height
        while index < len(rows) and out.y - rows[index].height >= FRAME_BOTTOM:
            segment.append(rows[index])
            out.y -= rows[index].height
            index += 1
        if segment:
            out.add((_draw_table_segment, table, widths, segment, top))
        first = False

    if table.note:
        for line in wrap_text(table.note, FONT, 6.0, _table_width(table)):
            out.ensure(8.0)
            out.y -= 8.0
            out.add((_draw_text_line, line, MARGIN_LEFT, out.y + 1.5, FONT, 6.0))
    out.y -= 7.0


# --- drawing -----------------------------------------------------------------


def _draw_heading(c, block, baseline, key):
    size, _before, _after = _heading_style(block.level)
    c.bookmarkPage(key, fit="XYZ", top=baseline + size + 8.0, left=0)
    c.setFont(FONT_BOLD, size)
    x = MARGIN_LEFT - (4.0 if block.level == 1 else 0.0)
    c.drawString(x, baseline, block.text)
    if block.level == 1:
        c.setLineWidth(0.8)
        c.line(MARGIN_LEFT - 8.0, baseline - 3.0, PAGE_WIDTH - MARGIN_RIGHT, baseline - 3.0)


def _draw_text_line(c, line, x, y, font, size):
    if line:
        c.setFont(font, size)
        c.drawString(x, y, line)


def _draw_caption(c, title, unit, x, width, y):
    c.setFont(FONT_BOLD, 7.5)
    if title:
        c.drawString(x, y, title)
    if unit:
        c.setFont(FONT, 6.5)
        c.drawRightString(x + width, y, unit)


def _draw_figure(c, block, bottom):
    c.saveState()
    c.translate(MARGIN_LEFT, bottom)
    block.draw(c, FRAME_WIDTH, block.height)
    c.restoreState()


def _draw_cell_text(c, text, x, width, top, height, size, align, font):
    if not text:
        return
    lines = text.split("\n")
    leading = size * 1.22
    baseline = top - (height - len(lines) * leading) / 2.0 - size * 0.98
    available = width - 2.0 * CELL_PADDING
    for line in lines:
        fitted = size
        measured = text_width(line, font, size)
        if measured > available > 0.0:
            fitted = max(MIN_CELL_FONT, size * available / measured)
            while text_width(line, font, fitted) > available and len(line) > 1:
                line = line[:-1]
        c.setFont(font, fitted)
        if align == LEFT:
            c.drawString(x + CELL_PADDING, baseline, line)
        elif align == RIGHT:
            c.drawRightString(x + width - CELL_PADDING, baseline, line)
        else:
            c.drawCentredString(x + width / 2.0, baseline, line)
        baseline -= leading


def _draw_table_segment(c, table, widths, rows, top):
    left = MARGIN_LEFT
    offsets = [0.0]
    for width in widths:
        offsets.append(offsets[-1] + width)
    right = left + offsets[-1]
    columns = table.columns

    path = c.beginPath()
    y = top
    path.moveTo(left, y)
    path.lineTo(right, y)
    for row in rows:
        bottom = y - row.height
        path.moveTo(left, bottom)
        path.lineTo(right, bottom)
        for _text, start, span, _align, _bold in row.cells:
            x = left + offsets[start]
            path.moveTo(x, y)
            path.lineTo(x, bottom)
        path.moveTo(right, y)
        path.lineTo(right, bottom)
        y = bottom
    c.setLineWidth(GRID_LINE)
    c.drawPath(path, stroke=1, fill=0)

    y = top
    for row in rows:
        for text, start, span, align, bold in row.cells:
            cell_align = align or columns[start].align
            width = offsets[start + span] - offsets[start]
            _draw_cell_text(
                c, text, left + offsets[start], width, y, row.height, table.font_size, cell_align,
                FONT_BOLD if bold else FONT,
            )
        y -= row.height


def _draw_chrome(c, doc: CalcDocument, footer_page):
    c.setFont(FONT, 7.5)
    c.drawString(MARGIN_LEFT, PAGE_HEIGHT - 26.0, doc.program)
    c.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, PAGE_HEIGHT - 36.0, doc.project_name)
    c.drawString(MARGIN_LEFT + 12.0, 26.0, doc.generated_at)
    if footer_page:
        c.drawCentredString(PAGE_WIDTH / 2.0, 26.0, footer_page)
    c.drawRightString(PAGE_WIDTH - MARGIN_RIGHT - 12.0, 26.0, "入力データID = " + doc.input_id)


def _draw_cover(c, doc: CalcDocument):
    c.setFont(FONT_BOLD, 26.0)
    c.drawCentredString(PAGE_WIDTH / 2.0, PAGE_HEIGHT - 190.0, doc.title)
    c.setFont(FONT, 12.0)
    c.drawCentredString(PAGE_WIDTH / 2.0, PAGE_HEIGHT - 240.0, "建築物名称：  " + doc.project_name)
    y = PAGE_HEIGHT - 320.0
    label_x = 110.0
    value_x = 260.0
    for field in doc.cover_fields:
        c.setFont(FONT, 10.0)
        c.drawString(label_x, y, field.label)
        c.drawString(value_x, y, field.value)
        c.setLineWidth(0.3)
        c.line(value_x, y - 4.0, PAGE_WIDTH - 90.0, y - 4.0)
        y -= 25.0


def _toc_entries(headings):
    return [h for h in headings if h[0] <= TOC_MAX_LEVEL]


def _toc_rows_per_page():
    return int(math.floor(FRAME_HEIGHT / TOC_ROW_HEIGHT)) - 3


def _draw_toc_page(c, entries):
    c.setFont(FONT_BOLD, 13.0)
    c.drawCentredString(PAGE_WIDTH / 2.0, FRAME_TOP - 8.0, "目    次")
    y = FRAME_TOP - 40.0
    right = PAGE_WIDTH - MARGIN_RIGHT
    for level, text, body_page, key, _top in entries:
        x = MARGIN_LEFT + (level - 1) * 12.0
        font = FONT_BOLD if level == 1 else FONT
        c.setFont(font, 9.0)
        c.drawString(x, y, text)
        number = str(body_page)
        c.setFont(FONT, 9.0)
        c.drawRightString(right, y, number)
        start = x + text_width(text, font, 9.0) + 6.0
        end = right - text_width(number, FONT, 9.0) - 6.0
        if end > start:
            c.setDash(1, 2.5)
            c.setLineWidth(0.4)
            c.line(start, y + 1.5, end, y + 1.5)
            c.setDash()
        c.linkAbsolute("", key, (x, y - 2.0, right, y + 9.0), Border="[0 0 0]")
        y -= TOC_ROW_HEIGHT


def _toc_page_count(entries):
    return int(math.ceil(len(entries) / float(_toc_rows_per_page()))) if entries else 1


def _add_outline(c, headings):
    previous = -1
    for level, text, _page, key, _top in headings:
        depth = min(level - 1, previous + 1)
        c.addOutlineEntry(text, key, level=depth, closed=depth > 0)
        previous = depth


def render_pdf(doc: CalcDocument, output_path) -> int:
    """Write the PDF and return the number of body pages."""

    register_fonts()
    layout = _layout(doc.blocks)
    total = len(layout.pages)
    entries = _toc_entries(layout.headings)

    c = canvas.Canvas(str(output_path), pagesize=A4, pageCompression=1, initialFontName=FONT)
    c.setTitle(doc.title + " " + doc.project_name)
    c.setAuthor(doc.designer or doc.program)
    c.setSubject("構造計算書")
    c.setCreator(doc.program)

    _draw_chrome(c, doc, "")
    _draw_cover(c, doc)
    c.showPage()

    per_page = _toc_rows_per_page()
    for page in range(_toc_page_count(entries)):
        _draw_chrome(c, doc, "")
        _draw_toc_page(c, entries[page * per_page:(page + 1) * per_page])
        c.showPage()

    for index, page in enumerate(layout.pages):
        _draw_chrome(c, doc, "{0} / {1}".format(index + 1, total))
        for op in page:
            op[0](c, *op[1:])
        c.showPage()

    _add_outline(c, layout.headings)
    c.save()
    return total
