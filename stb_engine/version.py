"""Structural Toolbox version, read from the VERSION file at the project root.

VERSION is the single source of the version number: pyproject.toml, the
installers and the Grasshopper plugin all read the same file.
"""

import os

_VERSION_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")


def _read_version():
    try:
        with open(_VERSION_FILE, encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        pass
    try:
        from importlib.metadata import version

        return version("structural-toolbox")
    except Exception:
        return "unknown"


__version__ = _read_version()
