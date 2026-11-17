"""PDF calculation book: figures against closed-form results, layout and output."""

import dataclasses
import os
import sys
import tempfile
import unittest
from datetime import datetime

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from reportlab.pdfgen import canvas

from stb_engine import run_from_file
from stb_project import ProjectSchemaError, WoodMaterialStrength, load_project_file, validate_project_dict
from stb_reports import write_confirmation_draft
from stb_reports.calc_book import append_attachments, write_calc_book_pdf
from stb_reports.calc_book.common import fmt, markdown_blocks
from stb_reports.calc_book.context import Naming, build_context
from stb_reports.calc_book.document import Column, Figure, Heading, Table, Text
from stb_reports.calc_book.figures import bending_in_plane, elevation_views, plan_views
from stb_reports.calc_book.render_pdf import FRAME_BOTTOM, _layout

HEADER = """MATE, 1, Wood, 12000, 800, 5.0, 3e-06, 0
SECT, 1, S, 1, 0, 120.0, 240.0
"""
X_NORMAL = (1.0, 0.0, 0.0)
Y_NORMAL = (0.0, 1.0, 0.0)
Z_NORMAL = (0.0, 0.0, 1.0)


def _solve(body):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "model.dat")
        with open(path, "w", encoding="utf-8") as f:
            f.write(HEADER + body)
        mdl, _txt = run_from_file(path)
    return mdl


CANTILEVER = """NODE, 1, 0.0, 0.0, 3.0
NODE, 2, 2.0, 0.0, 3.0
ELEM, 1, 1, 2, 1, 0.0
CONS, 1, 1, 1, 1, 1, 1, 1
"""
COLUMN = """NODE, 1, 0.0, 0.0, 0.0
NODE, 2, 0.0, 0.0, 3.0
ELEM, 1, 1, 2, 1, 0.0
CONS, 1, 1, 1, 1, 1, 1, 1
"""
FIXED_BEAM = """NODE, 1, 0.0, 0.0, 3.0
NODE, 2, 4.0, 0.0, 3.0
ELEM, 1, 1, 2, 1, 0.0
CONS, 1, 1, 1, 1, 1, 1, 1
CONS, 2, 1, 1, 1, 1, 1, 1
ELOD, 1, 0, 1, 0.0, 0.0, -2.0, 0.0, 0.0, -2.0
"""


class TestBendingDirection(unittest.TestCase):
    """The diagram must lie on the tension side and carry the right magnitude."""

    def _tension(self, mdl, normal, axis):
        e = mdl.FindElemFromEid(1)
        values, direction = bending_in_plane(e, 0, normal)
        return values, [v * direction[axis] for v in values]

    def test_cantilever_tip_load_tensions_the_top_fibre(self):
        mdl = _solve(CANTILEVER + "PLOD, 2, 0, 0.0, 0.0, -5.0, 0.0, 0.0, 0.0\n")
        values, along_z = self._tension(mdl, Y_NORMAL, 2)
        self.assertAlmostEqual(abs(values[0]), 10000.0, places=3)
        self.assertAlmostEqual(abs(values[1]), 5000.0, places=3)
        self.assertAlmostEqual(values[2], 0.0, places=3)
        self.assertGreater(along_z[0], 0.0)

    def test_cantilever_lateral_load_in_plan(self):
        mdl = _solve(CANTILEVER + "PLOD, 2, 0, 0.0, 5.0, 0.0, 0.0, 0.0, 0.0\n")
        values, along_y = self._tension(mdl, Z_NORMAL, 1)
        self.assertAlmostEqual(abs(values[0]), 10000.0, places=3)
        self.assertLess(along_y[0], 0.0)

    def test_fixed_beam_hogs_at_ends_and_sags_at_midspan(self):
        mdl = _solve(FIXED_BEAM)
        values, along_z = self._tension(mdl, Y_NORMAL, 2)
        expected_end = 2000.0 * 4.0 ** 2 / 12.0
        expected_mid = 2000.0 * 4.0 ** 2 / 24.0
        self.assertAlmostEqual(abs(values[0]), expected_end, delta=1.0)
        self.assertAlmostEqual(abs(values[2]), expected_end, delta=1.0)
        self.assertAlmostEqual(abs(values[1]), expected_mid, delta=1.0)
        self.assertGreater(along_z[0], 0.0)
        self.assertGreater(along_z[2], 0.0)
        self.assertLess(along_z[1], 0.0)

    def test_column_pushed_in_x_tensions_the_far_face(self):
        mdl = _solve(COLUMN + "PLOD, 2, 0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0\n")
        values, along_x = self._tension(mdl, Y_NORMAL, 0)
        self.assertAlmostEqual(abs(values[0]), 15000.0, places=3)
        self.assertLess(along_x[0], 0.0)

    def test_column_pushed_in_y_tensions_the_far_face(self):
        mdl = _solve(COLUMN + "PLOD, 2, 0, 0.0, 5.0, 0.0, 0.0, 0.0, 0.0\n")
        values, along_y = self._tension(mdl, X_NORMAL, 1)
        self.assertAlmostEqual(abs(values[0]), 15000.0, places=3)
        self.assertLess(along_y[0], 0.0)


class TestNaming(unittest.TestCase):

    def _project(self, grids=(), stories=()):
        return validate_project_dict({
            "schema": 1,
            "model": {"dat": "m.dat"},
            "building": {"name": "b", "location": "", "use": "", "structure": "wood", "calculation_route": "",
                         "designer": {"name": "", "qualification": "", "license_number": "", "contact": ""}},
            "grids": list(grids),
            "stories": list(stories),
            "member_classes": [],
            "report": {"title": "", "mode": "practice", "language": "ja", "format": "markdown",
                       "include_manual_items": True, "include_warnings": True},
        })

    FRAME = """NODE, 1, 0.0, 0.0, 0.0
NODE, 2, 0.0, 0.0, 3.0
NODE, 3, 4.0, 0.0, 0.0
NODE, 4, 4.0, 0.0, 3.0
ELEM, 1, 1, 2, 1, 0.0
ELEM, 2, 3, 4, 1, 0.0
ELEM, 3, 2, 4, 1, 0.0
CONS, 1, 1, 1, 1, 1, 1, 1
CONS, 3, 1, 1, 1, 1, 1, 1
PLOD, 2, 0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0
"""

    def test_infers_grids_from_columns(self):
        mdl = _solve(self.FRAME)
        naming = Naming(mdl, self._project())
        self.assertEqual(naming.member_location(mdl.FindElemFromEid(3)), ("Z2", "Y1", "X1-X2"))
        self.assertEqual(naming.member_location(mdl.FindElemFromEid(2)), ("Z1-Z2", "Y1", "X2"))

    def test_uses_project_grid_names(self):
        mdl = _solve(self.FRAME)
        project = self._project(
            grids=[
                {"name": "A", "direction": "x", "coordinate": 0.0},
                {"name": "B", "direction": "x", "coordinate": 4.0},
                {"name": "1", "direction": "y", "coordinate": 0.0},
            ],
            stories=[{"name": "1", "elevation": 0.0, "height": 3.0}],
        )
        naming = Naming(mdl, project)
        self.assertEqual(naming.member_location(mdl.FindElemFromEid(3)), ("Z2", "1", "A-B"))

    def test_views_cover_the_frame(self):
        mdl = _solve(self.FRAME)
        ctx = build_context(mdl, self._project())
        self.assertEqual([len(v.members) for v in elevation_views(ctx) if v.title == "Y1通り"], [3])
        self.assertEqual(len(plan_views(ctx)[-1].members), 1)


def _table(rows, **kwargs):
    return Table(columns=(Column("a"), Column("b")), rows=tuple((str(i), "x") for i in range(rows)), **kwargs)


class TestLayout(unittest.TestCase):

    def test_negative_zero_is_not_shown(self):
        self.assertEqual(fmt(-0.001, 2), "0.00")
        self.assertEqual(fmt(-0.5, 1), "-0.5")

    def test_long_table_flows_over_pages_and_stays_in_frame(self):
        layout = _layout((Heading(1, "§1"), _table(400)))
        self.assertGreater(len(layout.pages), 3)
        drawn = sum(len(op[3]) - 1 for page in layout.pages for op in page if op[0].__name__ == "_draw_table_segment")
        self.assertEqual(drawn, 400)
        self.assertGreaterEqual(layout.y, FRAME_BOTTOM)

    def test_chapter_starts_a_new_page(self):
        layout = _layout((Heading(1, "§1"), Text("a"), Heading(1, "§2"), Text("b")))
        self.assertEqual([h[2] for h in layout.headings], [1, 2])

    def test_heading_is_not_left_alone_at_page_bottom(self):
        filler = Figure(height=690.0, draw=lambda c, w, h: None)
        layout = _layout((filler, Heading(2, "sub"), _table(3)))
        self.assertEqual(layout.headings[0][2], 2)

    def test_keep_together_moves_to_next_page(self):
        filler = Figure(height=690.0, draw=lambda c, w, h: None)
        layout = _layout((filler, _table(6, keep_together=True)))
        self.assertEqual(len(layout.pages), 2)
        self.assertEqual(len(layout.pages[0]), 1)

    def test_markdown_tables_become_blocks(self):
        blocks = markdown_blocks("# Top\n\n## Sub\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- item\n")
        self.assertEqual([type(b).__name__ for b in blocks], ["Heading", "Table", "Text"])
        self.assertEqual(blocks[1].rows, (("1", "2"),))


class TestPdfOutput(unittest.TestCase):

    def _sample(self, standard=True):
        project = load_project_file(os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json"))
        mdl, _txt = run_from_file(os.path.join(_STB_ROOT, "data", project.dat_path))
        mdl.filepath = os.path.join(_STB_ROOT, "data", project.dat_path)
        if standard:
            wood = dataclasses.replace(
                project.design_checks.wood,
                materials=(WoodMaterialStrength("Sugi", 17.7, 13.5, 22.2, 1.8),),
            )
            project = dataclasses.replace(project, design_checks=dataclasses.replace(project.design_checks, wood=wood))
        return mdl, project

    def _write(self, mdl, project, tmp):
        path = os.path.join(tmp, "book.pdf")
        book = write_calc_book_pdf(path, mdl, project, generated_at=datetime(2026, 11, 9), program_version="9.9")
        return path, book

    def test_writes_a_book_with_embedded_fonts_only(self):
        mdl, project = self._sample()
        with tempfile.TemporaryDirectory() as tmp:
            path, book = self._write(mdl, project, tmp)
            with open(path, "rb") as fh:
                data = fh.read()
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertGreater(book.page_count, 10)
        self.assertIn(b"BIZUDGothic", data)
        self.assertNotIn(b"Helvetica", data)
        self.assertIn(b"/Outlines", data)

    def test_every_chapter_is_built(self):
        from stb_reports.calc_book import build_document

        mdl, project = self._sample()
        doc = build_document(build_context(mdl, project, program_version="9.9"))
        chapters = [b.text for b in doc.blocks if isinstance(b, Heading) and b.level == 1]
        self.assertEqual(len(chapters), 15)
        titles = [b.text for b in doc.blocks if isinstance(b, Heading)]
        self.assertIn("7.5 柱の断面検定表", titles)
        self.assertIn("7.6 はりの断面検定表", titles)

    def test_check_card_shows_the_values_of_the_check(self):
        from stb_reports.calc_book.chapters_results import _check_card

        mdl, project = self._sample()
        ctx = build_context(mdl, project, program_version="9.9")
        check = next(c for c in ctx.wood.element_checks if c.kind == "column")
        table = _check_card(ctx, check)
        cells = [c.text if hasattr(c, "text") else c for row in table.rows for c in row]
        governing = check.standard.governing
        self.assertIn(fmt(governing.combined_stress_ratio, 3), cells)
        self.assertIn(fmt(governing.axial * 1.0e-3), cells)
        self.assertIn("長期", cells)
        self.assertTrue(table.keep_together)

    def test_simplified_method_is_stated_in_the_book(self):
        from stb_reports.calc_book import build_document

        mdl, project = self._sample(standard=False)
        doc = build_document(build_context(mdl, project, program_version="9.9"))
        texts = [b.text for b in doc.blocks if isinstance(b, Text)]
        self.assertTrue(any("簡易法" in t for t in texts))

    def test_draft_writer_infers_pdf_from_the_extension(self):
        mdl, project = self._sample()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.pdf")
            write_confirmation_draft(path, mdl, project, program_version="9.9")
            with open(path, "rb") as fh:
                self.assertTrue(fh.read(4) == b"%PDF")

    def _one_page_pdf(self, path):
        c = canvas.Canvas(path)
        c.drawString(100, 100, "x")
        c.showPage()
        c.drawString(100, 100, "y")
        c.showPage()
        c.save()

    def test_attachments_are_appended(self):
        from pypdf import PdfReader

        mdl, project = self._sample()
        with tempfile.TemporaryDirectory() as tmp:
            path, book = self._write(mdl, project, tmp)
            before = len(PdfReader(path).pages)
            extra = os.path.join(tmp, "ground.pdf")
            self._one_page_pdf(extra)
            self.assertEqual(append_attachments(path, [extra]), 2)
            reader = PdfReader(path)
            self.assertEqual(len(reader.pages), before + 2)
            titles = [item.title for item in reader.outline if not isinstance(item, list)]
            self.assertIn("添付資料", titles)

    def test_missing_attachment_is_an_error(self):
        mdl, project = self._sample()
        with tempfile.TemporaryDirectory() as tmp:
            path, _book = self._write(mdl, project, tmp)
            with self.assertRaises(ValueError):
                append_attachments(path, [os.path.join(tmp, "none.pdf")])

    def test_attachment_setting_round_trips_only_when_used(self):
        project = load_project_file(os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json"))
        self.assertNotIn("attachments", project.to_dict()["report"])
        raw = project.to_dict()
        raw["report"]["attachments"] = ["ground.pdf"]
        again = validate_project_dict(raw)
        self.assertEqual(again.report.attachments, ("ground.pdf",))
        self.assertEqual(validate_project_dict(again.to_dict()).to_dict(), again.to_dict())
        raw["report"]["attachments"] = [""]
        with self.assertRaises(ProjectSchemaError):
            validate_project_dict(raw)


class TestGuiRoute(unittest.TestCase):

    def test_pdf_route_returns_a_book(self):
        from fastapi.testclient import TestClient
        from stb_gui.server import create_app

        client = TestClient(create_app())
        response = client.get("/api/report/pdf?path=data/practice_wood_single_story.dat")
        self.assertEqual(response.status_code, 200, response.text[:300])
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_pdf_route_needs_a_project_file(self):
        from fastapi.testclient import TestClient
        from stb_gui.server import create_app

        client = TestClient(create_app())
        response = client.get("/api/report/pdf?path=examples/cantilever.dat")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
