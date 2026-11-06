import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import parse_input
from stb_project import load_project_file
from stb_reports import build_wall_quantity_report, write_wall_quantity_report

SAMPLE_PROJECT = os.path.join(_STB_ROOT, "data", "sample_wall_quantity_2f.project.json")
SAMPLE_DAT = os.path.join(_STB_ROOT, "data", "sample_wall_quantity_2f.dat")


def _sample():
    project = load_project_file(SAMPLE_PROJECT)
    with open(SAMPLE_DAT, encoding="utf-8") as fh:
        mdl = parse_input(fh.read().splitlines())
    mdl.filepath = SAMPLE_DAT
    return mdl, project


class TestWallQuantitySample(unittest.TestCase):

    def test_sample_project_passes_all_checks(self):
        mdl, project = _sample()
        report = build_wall_quantity_report(mdl, project, generated_at=datetime(2026, 11, 6))
        s = report.summary
        self.assertEqual(report.status, "OK")
        self.assertEqual(report.warnings, ())
        self.assertEqual([d.lw_cm_m2 for d in s.seismic.stories], [31.0, 23.0])
        # The east 1F strip (Y direction) has no 2nd floor above -> 平屋 coefficient
        strip = [c for c in s.balance.checks if c.story == "1" and c.direction == "y"][0].strips[1]
        self.assertEqual(strip.lw_basis, "平屋")
        brace = [w for w in s.walls if w.ref == "7"][0]
        self.assertEqual((brace.kind, brace.brace_section, brace.brace_layout), ("brace", "45x90", "single"))
        self.assertTrue(len(s.n_values.columns) > 0)
        self.assertEqual({c.story for c in s.column_size.model_columns}, {"1", "2"})


class TestWallQuantityReport(unittest.TestCase):

    def setUp(self):
        mdl, project = _sample()
        self.report = build_wall_quantity_report(mdl, project, generated_at=datetime(2026, 11, 6),
                                                 program_version="9.9.9")

    def test_html_has_all_sections_and_figures(self):
        text = self.report.html
        self.assertTrue(text.startswith("<!doctype html>"))
        for heading in ("総合判定", "1. 準拠基準・適用範囲", "2. 地震力に対する必要壁量", "3. 風圧力に対する必要壁量",
                        "4. 存在壁量", "5. 壁量判定（表3-12）", "6. 壁配置のバランス（四分割法・表3-13）",
                        "7. 柱頭・柱脚の接合方法（N値計算法）", "8. 柱の小径", "注意事項・警告"):
            with self.subTest(heading=heading):
                self.assertIn(heading, text)
        self.assertEqual(text.count("<svg"), 4)   # 2 stories x (wall plan + N値 plan)
        self.assertIn("2026-11-06", text)
        self.assertIn("Structural Toolbox 9.9.9", text)
        self.assertIn("@media print", text)
        self.assertIn('class="ok"', text)
        self.assertNotIn('class="ng"', text)

    def test_markdown_has_tables_without_svg(self):
        md = self.report.markdown
        self.assertIn("## 5. 壁量判定（表3-12）", md)
        self.assertIn("| 階・方向 | 床面積 (m²) |", md)
        self.assertNotIn("<svg", md)
        self.assertIn("（HTML版に掲載）", md)

    def test_write_chooses_format_from_extension(self):
        mdl, project = _sample()
        with tempfile.TemporaryDirectory() as tmp:
            md_path = os.path.join(tmp, "out", "wall.md")
            write_wall_quantity_report(md_path, mdl, project)
            with open(md_path, encoding="utf-8") as fh:
                self.assertTrue(fh.read().startswith("# "))
            html_path = os.path.join(tmp, "wall.html")
            write_wall_quantity_report(html_path, mdl, project)
            with open(html_path, encoding="utf-8") as fh:
                self.assertIn("<svg", fh.read())


class TestWallCalcCli(unittest.TestCase):

    def test_wallcalc_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "wall.html")
            proc = subprocess.run(
                [sys.executable, "-m", "stb_cli", "wallcalc", SAMPLE_PROJECT, "-o", out, "-v"],
                cwd=_STB_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("overall:       OK", proc.stdout)
            self.assertTrue(os.path.isfile(out))

    def test_wallcalc_without_wall_quantity_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, "-m", "stb_cli", "wallcalc",
                 os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json"),
                 "-o", os.path.join(tmp, "x.html")],
                cwd=_STB_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("wall_quantity", proc.stderr)


class TestWallQuantityGuiEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
            from stb_gui.server import create_app
        except (ImportError, RuntimeError):
            cls.client = None
            return
        cls.client = TestClient(create_app())

    def test_report_endpoint(self):
        if self.client is None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/api/wall-quantity/report", params={"path": "data/sample_wall_quantity_2f.dat"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("壁量判定", r.text)

    def test_report_endpoint_without_settings(self):
        if self.client is None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/api/wall-quantity/report", params={"path": "data/practice_wood_single_story.dat"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("wall_quantity", r.text)


if __name__ == "__main__":
    unittest.main()
