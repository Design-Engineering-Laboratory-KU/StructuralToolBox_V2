#!/usr/bin/env python3
"""Build the macOS student installer (tar.gz, and on Mac also dmg + pkg).

Windows or Linux produces StructuralToolbox_Mac_Setup_YYYYMMDD.tar.gz.
On macOS the same command also produces a .dmg and a per-user .pkg.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDENT = Path(__file__).resolve().parent
MAC = STUDENT / "mac"
DIST = STUDENT / "dist"
CACHE = DIST / "_cache"

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    ".venv-win",
    ".venv_win",
    ".venv_py314_broken",
    "python-embed",
    "python-standalone-arm64",
    "python-standalone-x64",
    "__pycache__",
    ".pytest_cache",
    "student",
    ".idea",
    ".vscode",
    ".bench",
    "structural_toolbox.egg-info",
    "bin",
    "obj",
}
SKIP_FILE_NAMES = {"Presentation1.pptx", ".DS_Store", "Thumbs.db"}
SCRIPT_NAMES = {
    "Install_once.command",
    "Start Structural Toolbox.command",
    "Start Structural Toolbox (debug).command",
    "Uninstall.command",
    "create_launchers.sh",
    "インストール.command",
    "postinstall",
}

ARCHIVES = {
    "python-standalone-arm64": "aarch64-apple-darwin",
    "python-standalone-x64": "x86_64-apple-darwin",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def lf_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 0:
        print(f"Using cached: {dest}")
        return
    print(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "StructuralToolbox-builder"})
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out)
        tmp.replace(dest)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def verify_sha256(archive: Path, sha_file: Path) -> None:
    expected = sha_file.read_text(encoding="utf-8").strip().split()[0].lower()
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected:
        raise SystemExit(f"SHA256 mismatch for {archive.name}: {digest} != {expected}")


def fetch_pythons(version: str, release: str) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    base = f"https://github.com/astral-sh/python-build-standalone/releases/download/{release}"
    for folder, triple in ARCHIVES.items():
        name = f"cpython-{version}+{release}-{triple}-install_only_stripped.tar.gz"
        archive = CACHE / name
        sha = CACHE / f"{name}.sha256"
        url = f"{base}/{name}"
        try:
            download(url, archive)
            download(f"{url}.sha256", sha)
        except Exception as exc:
            raise SystemExit(
                f"Failed to download macOS Python {version} ({release}).\n"
                f"  {url}\n"
                f"  {exc}\n"
                "Update student/PYTHON_EMBED_VERSION and student/PYTHON_MAC_RELEASE together."
            ) from exc
        verify_sha256(archive, sha)
        paths[folder] = archive
    return paths


def should_skip_dir(path: Path) -> bool:
    if path.name in SKIP_DIR_NAMES:
        return True
    if path.name == "_tmp_out" and path.parent.name == "tests":
        return True
    return False


def ignore_payload(directory: str, names: list[str]) -> list[str]:
    parent = Path(directory).name
    skipped = []
    for name in names:
        if name in SKIP_DIR_NAMES or name in SKIP_FILE_NAMES:
            skipped.append(name)
        elif name == "_tmp_out" and parent == "tests":
            skipped.append(name)
    return skipped


def copy_source(payload: Path) -> None:
    if payload.exists():
        shutil.rmtree(payload)
    payload.mkdir(parents=True)

    for item in ROOT.iterdir():
        if item.name in SKIP_DIR_NAMES or item.name in SKIP_FILE_NAMES:
            continue
        dest = payload / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=ignore_payload)
        elif item.is_file():
            shutil.copy2(item, dest)

    html = payload / "docs" / "element_stiffness_matrix.html"
    if html.exists():
        html.unlink()

    for cache_dir in payload.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir, ignore_errors=True)
    for pyc in payload.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)

    tmp_out = payload / "tests" / "_tmp_out"
    if tmp_out.exists():
        shutil.rmtree(tmp_out)


def install_scripts(payload: Path) -> None:
    for name in (
        "Install_once.command",
        "Start Structural Toolbox.command",
        "Start Structural Toolbox (debug).command",
        "Uninstall.command",
        "create_launchers.sh",
    ):
        target = payload / name
        target.write_bytes(lf_bytes(MAC / name))

    shutil.copyfile(STUDENT / "setup_runtime.py", payload / "setup_runtime.py")

    sys.path.insert(0, str(STUDENT))
    import stage_docs

    stage_docs.stage(payload, "macos", ROOT)


def include_wheels(payload: Path) -> None:
    sys.path.insert(0, str(STUDENT))
    import fetch_wheels

    source = fetch_wheels.build("macos", fetch_wheels.python_version(STUDENT / "PYTHON_EMBED_VERSION"))
    fetch_wheels.copy_into_payload(source, payload)
    count = len(list((payload / "wheels").glob("*.whl")))
    print("OK: bundled libraries ({0} wheels)".format(count))


def include_grasshopper(payload: Path) -> None:
    artifact = ROOT / "grasshopper" / "gha" / "bin" / "Release" / "StbGrasshopper.gha"
    project = ROOT / "grasshopper" / "gha" / "StbGrasshopper.csproj"
    if not artifact.is_file() and shutil.which("dotnet"):
        print("Building Grasshopper plugin...")
        libraries = DIST / "_gha_build_libraries"
        libraries.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "dotnet",
                "build",
                str(project),
                "-c",
                "Release",
                f"-p:GrasshopperLibrariesPath={libraries}",
            ],
            cwd=ROOT,
        )
        if result.returncode != 0:
            print("warning: Grasshopper plugin build failed; continuing without .gha")
    if artifact.is_file():
        dest = payload / "grasshopper"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(artifact, dest / "StbGrasshopper.gha")
        print(f"OK: Grasshopper plugin ({artifact})")
    else:
        print("warning: StbGrasshopper.gha not included")


def extract_python(archive: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tarfile.open(archive, "r:gz") as src:
        for member in src.getmembers():
            rel = strip_python_prefix(member.name)
            if not rel:
                continue
            target = dest.joinpath(*Path(rel).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.issym():
                if target.exists() or target.is_symlink():
                    target.unlink()
                os.symlink(member.linkname, target)
                continue
            if member.islnk():
                extracted = src.extractfile(member)
                if extracted is None:
                    continue
                target.write_bytes(extracted.read())
                continue
            if member.isfile():
                extracted = src.extractfile(member)
                if extracted is None:
                    continue
                target.write_bytes(extracted.read())
                try:
                    os.chmod(target, member.mode & 0o777)
                except OSError:
                    pass


def strip_python_prefix(name: str) -> str:
    parts = Path(name).parts
    if parts and parts[0] == "python":
        parts = parts[1:]
    return "/".join(parts)


def add_tree(tar: tarfile.TarFile, src: Path, arcname: str) -> None:
    import time

    if src.is_symlink():
        info = tarfile.TarInfo(arcname)
        info.type = tarfile.SYMTYPE
        info.linkname = os.readlink(src)
        info.mode = 0o777
        info.mtime = int(time.time())
        tar.addfile(info)
        return

    if src.is_dir():
        info = tarfile.TarInfo(arcname)
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        info.mtime = int(time.time())
        tar.addfile(info)
        for child in sorted(src.iterdir(), key=lambda p: p.name):
            add_tree(tar, child, f"{arcname}/{child.name}")
        return

    data = src.read_bytes()
    is_script = src.name in SCRIPT_NAMES or src.suffix in {".command", ".sh"} or data.startswith(b"#!")
    if is_script:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    mode = 0o755 if is_script else 0o644
    info = tarfile.TarInfo(arcname)
    info.size = len(data)
    info.mode = mode
    info.mtime = int(time.time())
    info.uid = 0
    info.gid = 0
    import io

    tar.addfile(info, fileobj=io.BytesIO(data))


def add_upstream_python(tar: tarfile.TarFile, archive: Path, folder: str, arc_root: str) -> None:
    import time

    prefix = f"{arc_root}/payload/{folder}"
    root_info = tarfile.TarInfo(prefix)
    root_info.type = tarfile.DIRTYPE
    root_info.mode = 0o755
    root_info.mtime = int(time.time())
    tar.addfile(root_info)

    with tarfile.open(archive, "r:gz") as src:
        for member in src.getmembers():
            rel = strip_python_prefix(member.name)
            if not rel:
                continue
            info = tarfile.TarInfo(f"{prefix}/{rel}")
            info.mode = member.mode & 0o777
            info.mtime = member.mtime
            info.uid = 0
            info.gid = 0
            if member.issym():
                info.type = tarfile.SYMTYPE
                info.linkname = member.linkname
                tar.addfile(info)
            elif member.islnk():
                extracted = src.extractfile(member)
                if extracted is None:
                    continue
                data = extracted.read()
                info.type = tarfile.REGTYPE
                info.size = len(data)
                import io

                tar.addfile(info, fileobj=io.BytesIO(data))
            elif member.isdir():
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            elif member.isfile():
                extracted = src.extractfile(member)
                if extracted is None:
                    continue
                info.type = tarfile.REGTYPE
                info.size = member.size
                tar.addfile(info, extracted)


def write_version_notes(tar: tarfile.TarFile, arc_root: str, version: str) -> None:
    import io
    import time

    notes = {
        "python-standalone-arm64": f"Python {version} (macOS standalone, Apple Silicon)\n",
        "python-standalone-x64": f"Python {version} (macOS standalone, Intel)\n",
    }
    for folder, text in notes.items():
        data = text.encode("utf-8")
        info = tarfile.TarInfo(f"{arc_root}/payload/{folder}/VERSION.txt")
        info.size = len(data)
        info.mode = 0o644
        info.mtime = int(time.time())
        tar.addfile(info, fileobj=io.BytesIO(data))


def verify_payload(payload: Path) -> None:
    required = [
        payload / "Install_once.command",
        payload / "Start Structural Toolbox.command",
        payload / "create_launchers.sh",
        payload / "setup_runtime.py",
        payload / "pyproject.toml",
        payload / "examples" / "cantilever.dat",
        payload / "grasshopper" / "StbGrasshopper.gha",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Payload is incomplete:\n  " + "\n  ".join(missing))

    for name in ("numpy", "scipy", "shapely", "fastapi", "uvicorn", "httpx"):
        if not list((payload / "wheels").glob(name + "-*.whl")):
            raise SystemExit("Bundled libraries are missing a wheel for " + name)


def build_dmg(stage: Path, dmg_path: Path) -> None:
    if dmg_path.exists():
        dmg_path.unlink()
    subprocess.check_call(
        [
            "hdiutil",
            "create",
            "-volname",
            "Structural Toolbox",
            "-srcfolder",
            str(stage),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )


def build_pkg(payload: Path, pkg_path: Path) -> None:
    work = payload.parent / "_pkg"
    if work.exists():
        shutil.rmtree(work)
    scripts = work / "scripts"
    resources = work / "resources"
    scripts.mkdir(parents=True)
    resources.mkdir(parents=True)
    postinstall = scripts / "postinstall"
    postinstall.write_bytes(lf_bytes(MAC / "postinstall"))
    postinstall.chmod(0o755)
    shutil.copyfile(MAC / "welcome.html", resources / "welcome.html")

    component = work / "StructuralToolbox-component.pkg"
    subprocess.check_call(
        [
            "pkgbuild",
            "--root",
            str(payload),
            "--install-location",
            "Library/Application Support/StructuralToolbox",
            "--scripts",
            str(scripts),
            "--identifier",
            "org.structuraltoolbox.mac",
            "--version",
            "0.1.0",
            str(component),
        ]
    )
    distribution = work / "distribution.xml"
    distribution.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>Structural Toolbox</title>
    <welcome file="welcome.html" mime-type="text/html"/>
    <options customize="never" require-scripts="false" hostArchitectures="arm64,x86_64"/>
    <domains enable_anywhere="false" enable_currentUserHome="true" enable_localSystem="false"/>
    <choices-outline>
        <line choice="main"/>
    </choices-outline>
    <choice id="main" title="Structural Toolbox" start_selected="true">
        <pkg-ref id="org.structuraltoolbox.mac"/>
    </choice>
    <pkg-ref id="org.structuraltoolbox.mac" version="0.1.0" auth="none">StructuralToolbox-component.pkg</pkg-ref>
</installer-gui-script>
""",
        encoding="utf-8",
    )
    if pkg_path.exists():
        pkg_path.unlink()
    subprocess.check_call(
        [
            "productbuild",
            "--distribution",
            str(distribution),
            "--package-path",
            str(work),
            "--resources",
            str(resources),
            str(pkg_path),
        ]
    )


def main() -> None:
    version = read_text(STUDENT / "PYTHON_EMBED_VERSION")
    release = read_text(STUDENT / "PYTHON_MAC_RELEASE")
    stamp = date.today().strftime("%Y%m%d")
    name = f"StructuralToolbox_Mac_Setup_{stamp}"
    stage = DIST / "_build" / name
    payload = stage / "payload"
    archive_path = DIST / f"{name}.tar.gz"

    print(f"Building macOS installer -> {archive_path}")
    print(f"  Python {version} (standalone release {release})")
    pythons = fetch_pythons(version, release)

    if stage.exists():
        shutil.rmtree(stage)
    copy_source(payload)
    install_scripts(payload)
    include_wheels(payload)
    include_grasshopper(payload)
    verify_payload(payload)
    (stage / "はじめに.txt").write_bytes(lf_bytes(MAC / "はじめに.txt"))
    (stage / "インストール.command").write_bytes(lf_bytes(MAC / "インストール.command"))

    DIST.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    with tarfile.open(archive_path, "w:gz", format=tarfile.PAX_FORMAT, encoding="utf-8") as tar:
        add_tree(tar, stage, name)
        for folder, archive in pythons.items():
            add_upstream_python(tar, archive, folder, name)
        write_version_notes(tar, name, version)

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"Done: {archive_path} ({size_mb:.1f} MB)")

    if sys.platform == "darwin":
        print("Extracting standalone Python for the disk image and package...")
        for folder, archive in pythons.items():
            extract_python(archive, payload / folder)
            (payload / folder / "VERSION.txt").write_text(
                f"Python {version} (macOS standalone, {folder})\n",
                encoding="utf-8",
            )
        dmg_path = DIST / f"StructuralToolbox_Mac_{stamp}.dmg"
        pkg_path = DIST / f"StructuralToolbox_Setup_Mac_{stamp}.pkg"
        print("Creating disk image...")
        build_dmg(stage, dmg_path)
        print(f"Done: {dmg_path}")
        print("Creating installer package...")
        build_pkg(payload, pkg_path)
        print(f"Done: {pkg_path}")
    else:
        print("")
        print("This PC produced the tar.gz installer.")
        print("Students: extract it, then right-click インストール.command and choose Open.")
        print("On a Mac, run the same script to also build .dmg and .pkg:")
        print("  ./student/build_student_installer_mac.sh")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(1)
