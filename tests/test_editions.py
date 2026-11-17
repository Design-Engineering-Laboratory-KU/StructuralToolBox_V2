"""The Simple edition really omits the Full features and still runs."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "installer"))

import editions  # noqa: E402

_COPY_IGNORED = shutil.ignore_patterns(
    ".git", ".venv", ".venv-win", "installer", "grasshopper", "__pycache__", "_tmp_out", "dist", "*.pyc"
)

# The development .venv installs this repository in editable mode, which would
# otherwise let the payload import the modules it is supposed to lack.
_ISOLATE = textwrap.dedent(
    """\
    import os, sys
    repo = os.path.normcase({repo!r})
    payload = {payload!r}
    sys.meta_path[:] = [f for f in sys.meta_path if "editable" not in repr(f).lower()]
    sys.path[:] = [payload] + [
        p for p in sys.path if p and os.path.normcase(os.path.abspath(p)) != repo
    ]
    os.chdir(payload)
    """
)


class TestSimplePayload(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.payload = Path(cls._tmp.name) / "payload"
        shutil.copytree(ROOT, cls.payload, ignore=_COPY_IGNORED)
        editions.apply(cls.payload, editions.SIMPLE)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _python(self, body):
        code = _ISOLATE.format(repo=str(ROOT), payload=str(self.payload)) + textwrap.dedent(body)
        env = dict(os.environ, PYTHONUTF8="1")
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=self.payload,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )

    def _cli(self, *argv):
        return self._python(
            "from stb_cli.main import main\n"
            "sys.exit(main({0!r}))\n".format(list(argv))
        )

    def test_full_only_files_are_gone(self):
        for rel in editions.FULL_ONLY_PATHS:
            self.assertFalse((self.payload / rel).exists(), rel)
        self.assertEqual(list(self.payload.glob("data/*.project.json")), [])

    def test_analysis_files_remain(self):
        for rel in ("stb_engine", "stb_project", "stb_loads", "stb_cli/main.py", "stb_gui/server.py", "classes"):
            self.assertTrue((self.payload / rel).exists(), rel)

    def test_isolation_hides_the_repository(self):
        result = self._python("import stb_reports\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ModuleNotFoundError", result.stderr)

    def test_full_commands_do_not_exist(self):
        for command in ("report", "wallcalc", "loads"):
            result = self._cli(command, "x")
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("invalid choice", result.stderr)
            self.assertNotIn("Full", result.stderr.replace(",", " ").split("usage")[0])

    def test_help_lists_only_simple_commands(self):
        result = self._cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("solve", "validate", "gui"):
            self.assertIn(command, result.stdout)
        for command in ("report", "wallcalc", "loads"):
            self.assertNotIn(command + " ", result.stdout.replace(",", " "))

    def test_solve_runs(self):
        result = self._cli("solve", "examples/cantilever.dat", "-q")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NDSP", result.stdout)

    def test_gui_serves_analysis_without_full_routes(self):
        result = self._python(
            """\
            import json
            from fastapi.testclient import TestClient
            from stb_gui.server import create_app
            client = TestClient(create_app())
            q = "?path=examples/cantilever.dat"
            out = {
                "model": client.get("/api/model" + q + "&solve=1").status_code,
                "index": client.get("/").text,
            }
            for name in ("project", "loads/dead", "loads/wind", "practice/summary", "wall-quantity/report", "report/pdf"):
                out[name] = client.get("/api/" + name + q).status_code
            out["seismic_apply"] = client.post("/api/loads/seismic/apply" + q).status_code
            print("RESULT" + json.dumps(out))
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout.split("RESULT", 1)[1])
        self.assertEqual(out.pop("model"), 200)
        index = out.pop("index")
        for button_id in editions.FULL_ONLY_BUTTONS:
            self.assertNotIn('id="' + button_id + '"', index)
        self.assertIn('id="btnSolve"', index)
        self.assertEqual(set(out.values()), {404}, out)

    def test_readme_exists_for_the_package_build(self):
        text = (self.payload / editions.README).read_text(encoding="utf-8")
        self.assertNotIn("wallcalc", text)


class TestVerify(unittest.TestCase):

    def test_repository_is_a_full_payload(self):
        editions.verify(ROOT, editions.FULL)

    def test_repository_is_not_a_simple_payload(self):
        with self.assertRaises(editions.EditionError):
            editions.verify(ROOT, editions.SIMPLE)

    def _minimal_simple(self, base):
        html = base / editions.INDEX_HTML
        html.parent.mkdir(parents=True)
        html.write_text("<html></html>", encoding="utf-8")

    def test_leftover_import_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._minimal_simple(base)
            editions.verify(base, editions.SIMPLE)
            (base / "module.py").write_text("def f():\n    from stb_reports import x\n", encoding="utf-8")
            with self.assertRaises(editions.EditionError):
                editions.verify(base, editions.SIMPLE)

    def test_leftover_file_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._minimal_simple(base)
            (base / "stb_checks").mkdir()
            with self.assertRaises(editions.EditionError):
                editions.verify(base, editions.SIMPLE)

    def test_missing_button_fails_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._minimal_simple(base)
            with self.assertRaises(editions.EditionError):
                editions.apply(base, editions.SIMPLE)


class TestFullCommands(unittest.TestCase):

    def test_development_tree_has_full_commands(self):
        from stb_cli.main import _build_parser

        subparsers = next(a for a in _build_parser()._actions if hasattr(a, "choices") and a.choices)
        self.assertLessEqual({"report", "wallcalc", "loads", "solve", "gui"}, set(subparsers.choices))

    def test_development_tree_has_full_routes(self):
        from stb_gui.server import create_app

        paths = {route.path for route in create_app().routes}
        self.assertLessEqual({"/api/project", "/api/loads/wind", "/api/wall-quantity/report"}, paths)


if __name__ == "__main__":
    unittest.main()
