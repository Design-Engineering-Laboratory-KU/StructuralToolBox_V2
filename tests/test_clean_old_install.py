import os
import shutil
import subprocess
import tempfile
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PS1 = os.path.join(_STB_ROOT, "installer", "clean_old_install.ps1")
_SH = os.path.join(_STB_ROOT, "installer", "mac", "clean_old_install.sh")


def _put(base, rel, text="x"):
    path = os.path.join(base, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _read(base, rel):
    with open(os.path.join(base, *rel.split("/")), encoding="utf-8") as handle:
        return handle.read()


def _files(base):
    found = set()
    for folder, _, names in os.walk(base):
        for name in names:
            found.add(os.path.relpath(os.path.join(folder, name), base).replace(os.sep, "/"))
    return found


class _CleanerCases:
    """Shared expectations for the Windows and macOS cleaners."""

    launcher = None
    runtime = None

    def run_cleaner(self, target, manifest, old, home):
        raise NotImplementedError

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.new = os.path.join(self.tmp, "新しい インストール")
        self.old = os.path.join(self.tmp, "古い インストール")
        self.checkout = os.path.join(self.tmp, "checkout")
        for base in (self.new, self.old):
            _put(base, self.launcher)
            _put(base, "setup_runtime.py")
            _put(base, "README.md")
            _put(base, ".venv/Lib/site-packages/scipy/tests/data/test.dat")
            _put(base, self.runtime + "/lib.dat")
            _put(base, "examples/cantilever.dat", "shipped")
            _put(base, "stb_cli/__pycache__/cache.dat")
            _put(base, "unins000.dat")
            _put(base, "notes.txt")
        _put(self.old, "install_manifest.txt", "examples/removed_example.dat\n")
        _put(self.old, "examples/removed_example.dat", "old shipped")
        _put(self.new, "examples/my_model.dat", "user new")
        _put(self.new, "examples/my_model.project.json", "sidecar")
        _put(self.new, "data/Result.OUT", "result")
        _put(self.new, "work/frame.gh", "gh")
        _put(self.old, "examples/my_model.dat", "user old")
        _put(self.old, "work/frame.ghx", "ghx")
        _put(self.checkout, self.launcher)
        _put(self.checkout, "setup_runtime.py")
        _put(self.checkout, ".git/HEAD")
        _put(self.checkout, "notes.txt")
        self.manifest = os.path.join(self.tmp, "manifest.txt")
        with open(self.manifest, "w", encoding="utf-8") as handle:
            handle.write("\n".join([self.launcher, "setup_runtime.py", "README.md", "examples/cantilever.dat"]) + "\n")
        self.home = os.path.join(self.tmp, "home")

    def test_keeps_user_models_and_removes_the_rest(self):
        result = self.run_cleaner(self.new, self.manifest, self.old, self.checkout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            _files(self.new),
            {
                "examples/my_model.dat",
                "examples/my_model.project.json",
                "examples/my_model (old 1).dat",
                "data/Result.OUT",
                "work/frame.gh",
                "work/frame.ghx",
            },
        )
        self.assertEqual(_read(self.new, "examples/my_model.dat"), "user new")
        self.assertEqual(_read(self.new, "examples/my_model (old 1).dat"), "user old")
        self.assertFalse(os.path.exists(self.old))

    def test_never_touches_a_git_checkout(self):
        result = self.run_cleaner(self.checkout, self.manifest, None, None)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(_files(self.checkout), {self.launcher, "setup_runtime.py", ".git/HEAD", "notes.txt"})


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell"), "Windows PowerShell only")
class TestWindowsCleaner(_CleanerCases, unittest.TestCase):
    launcher = "Install_once.bat"
    runtime = "python-embed"

    def run_cleaner(self, target, manifest, old, location_target):
        args = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", _PS1,
            "-Dir", target, "-Manifest", manifest, "-Log", os.path.join(self.tmp, "clean.log"),
        ]
        if old:
            args += ["-OldDir", old]
        if location_target:
            location = os.path.join(self.tmp, "location.txt")
            with open(location, "w", encoding="utf-8") as handle:
                handle.write(location_target + "\n")
            args += ["-LocationFile", location]
        return subprocess.run(args, capture_output=True, text=True)


@unittest.skipUnless(shutil.which("bash"), "bash not available")
class TestMacCleaner(_CleanerCases, unittest.TestCase):
    launcher = "Install_once.command"
    runtime = "python-standalone-arm64"

    def run_cleaner(self, target, manifest, old, location_target):
        if location_target:
            _put(self.home, "Library/Application Support/Grasshopper/Libraries/StbGrasshopper.location.txt", location_target + "\n")
        env = dict(os.environ, STB_USER_HOME=self.home)
        args = ["bash", _SH, target, manifest] + ([old] if old else [])
        return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env)


if __name__ == "__main__":
    unittest.main()
