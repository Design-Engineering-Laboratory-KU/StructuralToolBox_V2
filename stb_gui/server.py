import os
import signal
import socket
import threading
import time

from stb_gui.browser import open_gui_browser


def _invalidate_caches(full):
    from stb_gui.model_session import invalidate_model_session
    from stb_loads.equilibrium import invalidate_solved_model_cache

    invalidate_model_session(full)
    invalidate_solved_model_cache(full)


def _open_browser_when_ready(host, port, url, timeout_s=20.0):
    """Open the GUI window after the HTTP port is accepting connections."""

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _port_is_open(host, port):
            try:
                open_gui_browser(url)
            except Exception:
                pass
            return
        time.sleep(0.05)

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

_GUI_WATCH_CLIENT = False
_GUI_LAST_HEARTBEAT = None
_GUI_WATCHDOG_STARTED = False
_GUI_HEARTBEAT_INTERVAL = 4.0
# Background browser tabs throttle timers; keep a generous margin when enabled.
_GUI_HEARTBEAT_TIMEOUT = 120.0


def _terminate_gui_server():
    print("\nStructural Toolbox: server stopped.")
    if os.name == "nt":
        os._exit(0)
    os.kill(os.getpid(), signal.SIGINT)


def _start_gui_client_watchdog():
    global _GUI_WATCHDOG_STARTED
    if _GUI_WATCHDOG_STARTED or not _GUI_WATCH_CLIENT:
        return
    _GUI_WATCHDOG_STARTED = True

    def _loop():
        while True:
            time.sleep(_GUI_HEARTBEAT_INTERVAL)
            if not _GUI_WATCH_CLIENT:
                continue
            last = _GUI_LAST_HEARTBEAT
            if last is None:
                continue
            if time.time() - last > _GUI_HEARTBEAT_TIMEOUT:
                _terminate_gui_server()

    threading.Thread(target=_loop, daemon=True, name="stb-gui-watchdog").start()


def create_app(default_model=None, watch_client=False, exit_with_browser=None):
    global _GUI_WATCH_CLIENT
    if exit_with_browser is None:
        exit_with_browser = watch_client
    _GUI_WATCH_CLIENT = bool(exit_with_browser)
    from stb_gui.model_json import (
        create_new_model_file,
        list_model_files,
        load_input_text,
        load_model_dict,
        load_results_text,
        normalize_model_relpath,
        open_uploaded_model,
        resolve_model_path,
    )
    default_model = normalize_model_relpath(default_model)
    try:
        from fastapi import FastAPI, HTTPException, Query, Body
        from fastapi.responses import FileResponse, JSONResponse
    except ImportError:
        raise ImportError(
            "Structural Toolbox GUI requires fastapi and uvicorn. "
            "Install with: pip install -e \".[gui]\""
        )

    app = FastAPI(title="Structural Toolbox", version="0.1.0")

    def _raise_os_error(ex: OSError) -> None:
        msg = str(ex)
        status = 404 if "Project file not found" in msg else 500
        raise HTTPException(status_code=status, detail=msg)

    @app.on_event("startup")
    def _on_startup():
        _start_gui_client_watchdog()

    try:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    except ImportError:
        pass

    @app.get("/")
    def index():
        return FileResponse(
            os.path.join(_STATIC_DIR, "index.html"),
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )

    @app.get("/static/{asset_path:path}")
    def static_asset(asset_path: str):
        full = os.path.normpath(os.path.join(_STATIC_DIR, asset_path))
        static_root = os.path.realpath(_STATIC_DIR)
        if not os.path.realpath(full).startswith(static_root + os.sep):
            raise HTTPException(status_code=404, detail="Not found")
        if not os.path.isfile(full):
            raise HTTPException(status_code=404, detail="Not found")
        cache = (
            "public, max-age=31536000, immutable"
            if asset_path.replace("\\", "/").startswith("vendor/")
            else "no-cache, must-revalidate"
        )
        return FileResponse(full, headers={"Cache-Control": cache})

    @app.get("/api/models")
    def api_models():
        models = list_model_files()
        return JSONResponse({"models": models, "default": default_model})

    @app.get("/api/model")
    def api_model(
        path: str = Query(..., description="Relative path under project root"),
        solve: int = Query(0, description="1 to run analysis and include displacements"),
    ):
        try:
            resolve_model_path(path)
            data = load_model_dict(path, solve=(solve == 1), quiet=True)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        return JSONResponse(data)

    @app.get("/api/results")
    def api_results(
        path: str = Query(..., description="Relative path under project root"),
    ):
        try:
            resolve_model_path(path)
            txt = load_results_text(path, quiet=True)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(txt, media_type="text/plain; charset=utf-8")

    @app.get("/api/input")
    def api_input(
        path: str = Query(..., description="Relative path under project root"),
    ):
        try:
            resolve_model_path(path)
            txt = load_input_text(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(txt, media_type="text/plain; charset=utf-8")

    @app.put("/api/input")
    def api_input_save(
        path: str = Query(..., description="Relative path under project root"),
        text: str = Body(..., embed=True, description="Input file content"),
    ):
        try:
            from stb_gui.dat_format_headers import prepare_dat_text_for_write, write_dat_text

            full = resolve_model_path(path)
            current = load_input_text(path)
            normalized = prepare_dat_text_for_write(text)
            if prepare_dat_text_for_write(current) == normalized:
                return JSONResponse({
                    "ok": True,
                    "path": normalize_model_relpath(path),
                    "changed": False,
                })
            write_dat_text(full, text)
            _invalidate_caches(full)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        return JSONResponse({
            "ok": True,
            "path": normalize_model_relpath(path),
            "changed": True,
        })

    @app.post("/api/model/edit")
    def api_model_edit(
        path: str = Query(..., description="Relative path under project root"),
        body: dict = Body(..., description="Edit action payload"),
    ):
        try:
            from stb_gui.dat_edit import apply_edit_action, validate_dat_text
            from stb_gui.dat_format_headers import write_dat_text

            full = resolve_model_path(path)
            text = load_input_text(path)
            new_text, warnings = apply_edit_action(text, body)
            validate_dat_text(new_text)
            write_dat_text(full, new_text)
            _invalidate_caches(full)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        return JSONResponse({
            "ok": True,
            "path": normalize_model_relpath(path),
            "warnings": warnings,
            "element_ids": body.get("element_ids") or [],
            "action": body.get("action"),
        })

    @app.get("/api/model/ejnt-lines")
    def api_model_ejnt_lines(
        path: str = Query(..., description="Relative path under project root"),
        element_ids: str = Query(..., description="Comma-separated element ids"),
    ):
        try:
            from stb_gui.dat_edit import ejnt_lines_for_elements
            from stb_gui.input_format import EJNT_EDITOR_HEADER

            resolve_model_path(path)
            ids = [int(x.strip()) for x in element_ids.split(",") if x.strip()]
            text = load_input_text(path)
            rows = ejnt_lines_for_elements(text, ids)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        return JSONResponse({
            "path": normalize_model_relpath(path),
            "header": EJNT_EDITOR_HEADER,
            "lines": rows,
        })

    @app.get("/api/project")
    def api_project(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        try:
            from stb_gui.project_view import load_project_view_for_model

            resolve_model_path(path)
            data = load_project_view_for_model(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            _raise_os_error(ex)
        return JSONResponse(data)

    @app.get("/api/project/template")
    def api_project_template(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        try:
            from stb_gui.project_view import build_new_project_template_view

            resolve_model_path(path)
            data = build_new_project_template_view(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            _raise_os_error(ex)
        return JSONResponse(data)

    @app.put("/api/project")
    def api_project_save(
        path: str = Query(..., description="Relative path to .dat under project root"),
        body: dict = Body(..., description="Project JSON payload"),
    ):
        project = body.get("project")
        if project is None:
            raise HTTPException(status_code=400, detail="project is required")
        try:
            from stb_gui.project_view import save_project_json_for_model

            full = resolve_model_path(path)
            data = save_project_json_for_model(path, project)
            _invalidate_caches(full)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        return JSONResponse({"ok": True, "view": data})

    @app.get("/api/loads/dead")
    def api_loads_dead(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        try:
            from stb_gui.loads_view import load_dead_view_for_model

            resolve_model_path(path)
            data = load_dead_view_for_model(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            _raise_os_error(ex)
        return JSONResponse(data)

    @app.get("/api/loads/live")
    def api_loads_live(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        try:
            from stb_gui.loads_view import load_live_view_for_model

            resolve_model_path(path)
            data = load_live_view_for_model(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            _raise_os_error(ex)
        return JSONResponse(data)

    @app.get("/api/loads/seismic")
    def api_loads_seismic(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        try:
            from stb_gui.loads_view import load_seismic_view_for_model

            resolve_model_path(path)
            data = load_seismic_view_for_model(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            _raise_os_error(ex)
        return JSONResponse(data)

    @app.get("/api/loads/wind")
    def api_loads_wind(
        path: str = Query(..., description="Relative path to .dat under project root"),
        include_visual: bool = Query(
            True,
            description="Include 3D overlay metadata (omit in loads-verify window)",
        ),
    ):
        try:
            from stb_gui.loads_view import load_wind_view_for_model

            resolve_model_path(path)
            data = load_wind_view_for_model(path, include_visual=include_visual)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            _raise_os_error(ex)
        return JSONResponse(data)

    @app.get("/api/practice/summary")
    def api_practice_summary(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        try:
            from stb_gui.practice_view import load_practice_summary_view_for_model

            resolve_model_path(path)
            data = load_practice_summary_view_for_model(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            _raise_os_error(ex)
        return JSONResponse(data)

    @app.post("/api/loads/seismic/apply")
    def api_loads_seismic_apply(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        try:
            from stb_gui.loads_view import apply_seismic_dlod_for_model

            resolve_model_path(path)
            data = apply_seismic_dlod_for_model(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            _raise_os_error(ex)
        return JSONResponse({"ok": True, "view": data})

    @app.post("/api/loads/wind/apply")
    def api_loads_wind_apply(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        try:
            from stb_gui.loads_view import apply_wind_dlod_for_model

            resolve_model_path(path)
            data = apply_wind_dlod_for_model(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            _raise_os_error(ex)
        return JSONResponse({"ok": True, "view": data})

    @app.post("/api/model/new")
    def api_model_new():
        try:
            rel, text = create_new_model_file()
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        return JSONResponse({"ok": True, "path": rel, "text": text})

    @app.post("/api/model/open")
    def api_model_open(body: dict = Body(...)):
        text = body.get("text")
        if text is None:
            raise HTTPException(status_code=400, detail="text is required")
        filename = body.get("filename") or body.get("path") or "model.dat"
        try:
            rel = open_uploaded_model(filename, text)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        return JSONResponse({"ok": True, "path": rel})

    @app.get("/api/gui-config")
    def api_gui_config():
        return JSONResponse({"exit_with_browser": _GUI_WATCH_CLIENT})

    @app.post("/api/heartbeat")
    def api_heartbeat():
        global _GUI_LAST_HEARTBEAT
        _GUI_LAST_HEARTBEAT = time.time()
        return JSONResponse({"ok": True})

    @app.post("/api/shutdown")
    def api_shutdown():
        def _stop_server():
            _terminate_gui_server()

        threading.Timer(0.3, _stop_server).start()
        return JSONResponse({"ok": True})

    return app


def gui_open_url(host, port):
    return "http://{0}:{1}/".format(host, port)


def _port_is_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def run_server(
    host="127.0.0.1",
    port=8765,
    default_model=None,
    open_browser=True,
    log_file=None,
    exit_with_browser=True,
):
    from stb_gui.model_json import project_root

    url = gui_open_url(host, port)

    if _port_is_open(host, port):
        print("Structural Toolbox: already running at {0}".format(url))
        print("  project root: {0}".format(project_root()))
        print("  Logs are in the other console window (do not close it while debugging).")
        print("  Or end the old server: close that window, or stop python.exe in Task Manager.")
        if open_browser:
            try:
                open_gui_browser(url)
            except Exception:
                pass
        return "already_running"

    if open_browser:
        threading.Thread(
            target=_open_browser_when_ready,
            args=(host, port, url),
            daemon=True,
            name="stb-gui-browser",
        ).start()

    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "Structural Toolbox GUI requires uvicorn. "
            "Install with: pip install -e \".[gui]\""
        )

    app = create_app(default_model=default_model, exit_with_browser=exit_with_browser)

    print("Structural Toolbox: {0}".format(url))
    print("  project root: {0}".format(project_root()))
    try:
        from stb_engine import runtime

        print("  {0}".format(runtime.summary_line()))
    except ImportError:
        pass
    print("  Close the GUI window or press Ctrl+C here to stop the server.")
    if not exit_with_browser:
        print("  (--no-exit-with-browser: server keeps running after the browser tab closes.)")
    if log_file:
        print("  Log file: {0}".format(os.path.abspath(log_file)))

    log_config = None
    if log_file:
        log_path = os.path.abspath(log_file)
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s %(message)s",
                },
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": log_path,
                    "encoding": "utf-8",
                    "formatter": "default",
                },
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["file", "console"], "level": "INFO"},
                "uvicorn.error": {"handlers": ["file", "console"], "level": "INFO"},
                "uvicorn.access": {"handlers": ["file", "console"], "level": "INFO"},
            },
        }

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        log_config=log_config,
    )
    return "stopped"
