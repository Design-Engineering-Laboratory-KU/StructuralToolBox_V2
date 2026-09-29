"""Which Python interpreter is running Structural Toolbox.

Student installs bundle their own interpreter, so both the GUI and the
Grasshopper components must run inside the install's ``.venv`` and never fall
back to a Python the student installed for another course.
"""

import os
import sys

BUNDLED_PYTHON_DIRS = (
    "python-embed",
    "python-standalone-arm64",
    "python-standalone-x64",
)


def venv_root():
    """Root of the active virtual environment, or None outside a venv."""
    prefix = getattr(sys, "prefix", None)
    base = getattr(sys, "base_prefix", prefix)
    if not prefix or prefix == base:
        return None
    return os.path.abspath(prefix)


def install_root():
    """Folder holding the venv, i.e. the install or repository folder."""
    root = venv_root()
    if root:
        return os.path.dirname(root)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_bundled():
    """True when this interpreter is the one shipped with the install."""
    root = venv_root()
    if not root:
        return False
    parent = os.path.dirname(root)
    for name in BUNDLED_PYTHON_DIRS:
        if os.path.isdir(os.path.join(parent, name)):
            return True
    return False


def describe():
    """Lines describing the interpreter, for logs and the doctor command."""
    root = venv_root()
    lines = [
        "python:      {0}".format(sys.executable or "(unknown)"),
        "version:     {0}".format(sys.version.split()[0]),
        "venv:        {0}".format(root or "(none — system Python)"),
        "install:     {0}".format(install_root()),
        "bundled:     {0}".format("yes" if is_bundled() else "no"),
    ]
    return lines


def summary_line():
    """One line naming the interpreter, for the GUI startup banner."""
    kind = "bundled" if is_bundled() else ("venv" if venv_root() else "system")
    return "python: {0} ({1})".format(sys.executable or "(unknown)", kind)
