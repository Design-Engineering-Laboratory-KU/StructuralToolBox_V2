"""Opening a .dat outside the install folder: the file is used where it is, not copied to data/."""

import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_gui import model_json
from stb_gui.model_json import model_display_path, project_root, resolve_model_path

SAMPLE = os.path.join(_STB_ROOT, "examples", "cantilever.dat")


class _ExternalFolder(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="stb_external_")
        # A non-ASCII folder name, as on a Japanese Dropbox path.
        self.folder = os.path.join(self.folder, "構造 計算")
        os.makedirs(self.folder)
        self.dat = os.path.join(self.folder, "model.dat")
        shutil.copyfile(SAMPLE, self.dat)
        self.data_before = set(os.listdir(os.path.join(project_root(), "data")))
        model_json.set_external_models_allowed(True)

    def tearDown(self):
        model_json.set_external_models_allowed(True)
        shutil.rmtree(os.path.dirname(self.folder), ignore_errors=True)
        self.assertEqual(set(os.listdir(os.path.join(project_root(), "data"))), self.data_before)

    def gui_path(self):
        return self.dat.replace("\\", "/")


class TestResolve(_ExternalFolder):

    def test_absolute_dat_outside_the_project_is_used_in_place(self):
        self.assertEqual(os.path.normcase(resolve_model_path(self.gui_path())), os.path.normcase(os.path.realpath(self.dat)))

    def test_other_files_outside_the_project_are_refused(self):
        other = os.path.join(self.folder, "notes.txt")
        with open(other, "w", encoding="utf-8") as fh:
            fh.write("x")
        with self.assertRaises(ValueError):
            resolve_model_path(other)

    def test_relative_paths_still_cannot_leave_the_project(self):
        with self.assertRaises(ValueError):
            resolve_model_path("../" + os.path.basename(self.dat))

    def test_external_files_can_be_turned_off(self):
        model_json.set_external_models_allowed(False)
        with self.assertRaises(ValueError):
            resolve_model_path(self.gui_path())

    def test_display_path(self):
        self.assertEqual(model_display_path(os.path.join(project_root(), "examples", "cantilever.dat")), "examples/cantilever.dat")
        shown = model_display_path(self.dat)
        self.assertTrue(os.path.isabs(shown))
        self.assertNotIn("\\", shown)


class TestApi(_ExternalFolder):

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            raise unittest.SkipTest("fastapi not installed")
        from stb_gui.server import create_app

        cls.client = TestClient(create_app())

    def test_model_loads_and_saves_in_place(self):
        r = self.client.get("/api/model", params={"path": self.gui_path(), "solve": 0})
        self.assertEqual(r.status_code, 200, r.text)
        text = self.client.get("/api/input", params={"path": self.gui_path()}).text
        edited = text + "\n# edited in place\n"
        r = self.client.put("/api/input", params={"path": self.gui_path()}, json={"text": edited})
        self.assertEqual(r.status_code, 200, r.text)
        with open(self.dat, encoding="utf-8") as fh:
            self.assertIn("# edited in place", fh.read())

    def test_browse_returns_the_chosen_file(self):
        with unittest.mock.patch("stb_gui.file_dialog.choose_dat_file", return_value=self.dat) as dialog:
            r = self.client.post("/api/model/browse", json={"start": "examples/cantilever.dat"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(os.path.normcase(r.json()["path"]), os.path.normcase(os.path.realpath(self.dat).replace("\\", "/")))
        start_dir = dialog.call_args[0][0]
        self.assertEqual(os.path.normcase(start_dir), os.path.normcase(os.path.join(os.path.realpath(project_root()), "examples")))

    def test_browse_cancel(self):
        with unittest.mock.patch("stb_gui.file_dialog.choose_dat_file", return_value=None):
            r = self.client.post("/api/model/browse", json={})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["path"])

    def test_browse_without_a_dialog_falls_back(self):
        from stb_gui.file_dialog import DialogUnavailable

        with unittest.mock.patch("stb_gui.file_dialog.choose_dat_file", side_effect=DialogUnavailable("none")):
            r = self.client.post("/api/model/browse", json={})
        self.assertEqual(r.status_code, 501)

    def test_browse_is_off_for_a_remote_server(self):
        model_json.set_external_models_allowed(False)
        r = self.client.post("/api/model/browse", json={})
        self.assertEqual(r.status_code, 501)


class TestCalcBookSave(_ExternalFolder):

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            raise unittest.SkipTest("fastapi not installed")
        import importlib.util

        if importlib.util.find_spec("stb_gui.full_routes") is None:
            raise unittest.SkipTest("Full edition routes are not installed")
        from stb_gui.server import create_app

        cls.client = TestClient(create_app())

    PDF = b"%PDF-1.4 test"

    def _save(self, target, **kwargs):
        with unittest.mock.patch("stb_gui.file_dialog.choose_save_path", return_value=target, **kwargs) as dialog, \
                unittest.mock.patch("stb_gui.report_view.build_report_pdf_for_model", return_value=(self.PDF, "x.pdf")):
            r = self.client.post("/api/report/pdf/save", json={"path": self.gui_path()})
        return r, dialog

    def test_writes_the_book_where_the_user_chose(self):
        target = os.path.join(self.folder, "出力", "book.pdf")
        os.makedirs(os.path.dirname(target))
        r, dialog = self._save(target)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(os.path.normcase(r.json()["saved"]), os.path.normcase(os.path.abspath(target)))
        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), self.PDF)
        start_dir, name = dialog.call_args[0][:2]
        self.assertEqual(os.path.normcase(start_dir), os.path.normcase(os.path.realpath(self.folder)))
        self.assertEqual(name, "model_計算書.pdf")

    def test_cancel_writes_nothing(self):
        r, _dialog = self._save(None)
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["saved"])
        self.assertEqual(os.listdir(self.folder), ["model.dat"])

    def test_write_failure_is_reported(self):
        r, _dialog = self._save(os.path.join(self.folder, "missing", "book.pdf"))
        self.assertEqual(r.status_code, 500)
        self.assertIn("book.pdf", r.json()["detail"])

    def test_remote_server_falls_back_to_download(self):
        model_json.set_external_models_allowed(False)
        r = self.client.post("/api/report/pdf/save", json={"path": "examples/cantilever.dat"})
        self.assertEqual(r.status_code, 501)


class TestSaveDialog(unittest.TestCase):

    def test_extension_is_added(self):
        from stb_gui import file_dialog

        with unittest.mock.patch.object(file_dialog, "_run", return_value="C:/out/book"):
            self.assertEqual(file_dialog.choose_save_path("C:/out", "book.pdf"), "C:/out/book.pdf")
        with unittest.mock.patch.object(file_dialog, "_run", return_value="C:/out/book.PDF"):
            self.assertEqual(file_dialog.choose_save_path("C:/out", "book.pdf"), "C:/out/book.PDF")
        with unittest.mock.patch.object(file_dialog, "_run", return_value=None):
            self.assertIsNone(file_dialog.choose_save_path("C:/out", "book.pdf"))


class TestLoopback(unittest.TestCase):

    def test_loopback_hosts(self):
        from stb_gui.server import _is_loopback_host

        for host in ("127.0.0.1", "localhost", "::1", "127.0.0.2"):
            self.assertTrue(_is_loopback_host(host))
        for host in ("0.0.0.0", "192.168.1.5", ""):
            self.assertFalse(_is_loopback_host(host))


if __name__ == "__main__":
    unittest.main()
