import os
import shutil
import sys
import tempfile
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_reports import default_report_output_path

_SAMPLE = "practice_wood_single_story"


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


class TestDefaultReportOutputPath(unittest.TestCase):

    def test_project_json_and_dat(self):
        folder = os.path.abspath(os.path.join(os.sep, "work"))
        self.assertEqual(
            default_report_output_path(os.path.join(folder, "a.project.json")),
            os.path.join(folder, "a_report.html"),
        )
        self.assertEqual(
            default_report_output_path(os.path.join(folder, "a.dat")),
            os.path.join(folder, "a_report.html"),
        )


class TestGuiReportApi(unittest.TestCase):
    """GUI 計算書出力: project.json outside the toolbox folder, written next to it."""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
            from stb_gui.server import create_app
        except (ImportError, RuntimeError) as ex:
            raise unittest.SkipTest("GUI deps not installed: " + str(ex))
        cls.client = TestClient(create_app())

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="stb_gui_report_")
        for ext in (".dat", ".project.json"):
            shutil.copy(_data_path(_SAMPLE + ext), os.path.join(self.tmp, _SAMPLE + ext))
        self.project = os.path.join(self.tmp, _SAMPLE + ".project.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_generate_default_output_and_view(self):
        res = self.client.post("/api/report/confirmation", json={"input": '"' + self.project + '"'})
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        expected = os.path.join(self.tmp, _SAMPLE + "_report.html")
        self.assertEqual(data["output"], expected)
        self.assertEqual(data["format"], "html")
        self.assertTrue(os.path.isfile(expected))
        self.assertIsInstance(data["warnings"], list)

        view = self.client.get("/api/report/view", params={"token": data["token"]})
        self.assertEqual(view.status_code, 200)
        self.assertIn("<html", view.text.lower())
        self.assertIn("木造梁・柱・筋かいの基本検定", view.text)

    def test_markdown_output(self):
        out = os.path.join(self.tmp, "out", "draft.md")
        res = self.client.post("/api/report/confirmation", json={"input": self.project, "output": out})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["format"], "markdown")
        with open(out, encoding="utf-8") as fh:
            self.assertIn("## 8. 木造梁・柱・筋かいの基本検定", fh.read())

    def test_rejects_bad_requests(self):
        cases = [
            {"input": ""},
            {"input": _SAMPLE + ".project.json"},  # relative
            {"input": os.path.join(self.tmp, "missing.project.json")},
            {"input": self.project, "output": os.path.join(self.tmp, "x.txt")},
            {"input": self.project, "output": os.path.join(self.tmp, "x.html"), "format": "markdown"},
        ]
        for body in cases:
            res = self.client.post("/api/report/confirmation", json=body)
            self.assertEqual(res.status_code, 400, body)
        self.assertEqual(sorted(os.listdir(self.tmp)), sorted([_SAMPLE + ".dat", _SAMPLE + ".project.json"]))

    def test_rejects_foreign_origin(self):
        res = self.client.post(
            "/api/report/confirmation",
            json={"input": self.project},
            headers={"Origin": "https://example.com"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, _SAMPLE + "_report.html")))

    def test_view_unknown_token(self):
        self.assertEqual(self.client.get("/api/report/view", params={"token": "nope"}).status_code, 404)

    def test_defaults_for_open_model(self):
        res = self.client.get("/api/report/defaults", params={"path": "data/" + _SAMPLE + ".dat"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["input_exists"])
        self.assertTrue(data["input"].endswith(_SAMPLE + ".project.json"))
        self.assertTrue(data["output"].endswith(_SAMPLE + "_report.html"))
        empty = self.client.get("/api/report/defaults").json()
        self.assertEqual(empty["input"], "")


if __name__ == "__main__":
    unittest.main()
