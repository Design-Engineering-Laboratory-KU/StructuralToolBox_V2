import os
import re
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine.version import __version__


def _read(*parts):
    with open(os.path.join(_STB_ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestVersion(unittest.TestCase):
    """VERSION is the only place the version number is written."""

    def test_version_file_is_semver(self):
        self.assertRegex(_read("VERSION").strip(), r"^\d+\.\d+\.\d+$")

    def test_engine_reads_version_file(self):
        self.assertEqual(__version__, _read("VERSION").strip())

    def test_pyproject_reads_version_file(self):
        text = _read("pyproject.toml")
        self.assertIn('dynamic = ["version"]', text)
        self.assertIn('version = {file = "VERSION"}', text)

    def test_no_hard_coded_versions(self):
        # Each entry: file and a pattern that would mean a literal version crept back in.
        checks = [
            (("installer", "StructuralToolbox.iss"), r'#define\s+MyAppVersion\s+"\d'),
            (("installer", "build_mac.py"), r'PKG_VERSION\s*=\s*"\d'),
            (("installer", "mac", "create_launchers.sh"), r"<string>\d+\.\d+\.\d+</string>"),
            (("stb_gui", "server.py"), r'version="\d'),
            (("stb_cli", "main.py"), r'_STB_VERSION\s*=\s*"\d'),
            (("grasshopper", "gha", "StbGrasshopper.csproj"), r"<Version>\d"),
        ]
        for parts, pattern in checks:
            with self.subTest(file="/".join(parts)):
                self.assertIsNone(re.search(pattern, _read(*parts)))

    def test_consumers_reference_version_file(self):
        consumers = [
            ("installer", "StructuralToolbox.iss"),
            ("installer", "build_windows_installer.ps1"),
            ("installer", "build_windows_zip.ps1"),
            ("installer", "build_mac.py"),
            ("installer", "mac", "create_launchers.sh"),
            ("grasshopper", "gha", "StbGrasshopper.csproj"),
        ]
        for parts in consumers:
            with self.subTest(file="/".join(parts)):
                self.assertIn("VERSION", _read(*parts))


if __name__ == "__main__":
    unittest.main()
