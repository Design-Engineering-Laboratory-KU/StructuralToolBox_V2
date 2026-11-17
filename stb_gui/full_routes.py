"""GUI API routes that ship only in the Full edition.

The Simple installer omits this file, so these routes do not exist there.
"""

import os

from fastapi import Body, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse


def register(app, resolve_model_path, _raise_os_error, _invalidate_caches):
    @app.get("/api/report/pdf")
    def api_report_pdf(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        from urllib.parse import quote

        from fastapi.responses import Response
        from stb_gui.report_view import build_report_pdf_for_model

        try:
            data, name = build_report_pdf_for_model(path)
        except (ValueError, OSError) as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        return Response(
            data,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name)},
        )

    @app.post("/api/report/pdf/save")
    def api_report_pdf_save(body: dict = Body(...)):
        """Ask where to save (OS save-as dialog), then write the calculation book there."""

        import os

        from stb_gui import model_json
        from stb_gui.file_dialog import DialogBusy, DialogUnavailable, choose_save_path
        from stb_gui.report_view import build_report_pdf_for_model, report_pdf_name

        path = body.get("path")
        if not path:
            raise HTTPException(status_code=400, detail="path is required")
        if not model_json.ALLOW_EXTERNAL_MODELS:
            raise HTTPException(status_code=501, detail="Save dialog is available only on this computer")
        try:
            full = resolve_model_path(path)
            target = choose_save_path(
                os.path.dirname(full), report_pdf_name(full), title="Save the calculation book"
            )
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except DialogBusy as ex:
            raise HTTPException(status_code=409, detail=str(ex))
        except DialogUnavailable as ex:
            raise HTTPException(status_code=501, detail=str(ex))
        if not target:
            return JSONResponse({"ok": True, "saved": None})
        try:
            data, _name = build_report_pdf_for_model(path)
            with open(target, "wb") as fh:
                fh.write(data)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            # e.g. the PDF is open in a viewer that locks it
            raise HTTPException(status_code=500, detail="Could not write {0}: {1}".format(target, ex))
        return JSONResponse({"ok": True, "saved": os.path.abspath(target)})

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

    @app.get("/api/wall-quantity/report")
    def api_wall_quantity_report(
        path: str = Query(..., description="Relative path to .dat under project root"),
    ):
        from fastapi.responses import HTMLResponse
        from stb_gui.wall_quantity_view import error_page_html, render_wall_quantity_report_html

        headers = {"Cache-Control": "no-store"}
        try:
            body = render_wall_quantity_report_html(path)
        except (ValueError, OSError) as ex:
            return HTMLResponse(error_page_html(str(ex)), status_code=400, headers=headers)
        return HTMLResponse(body, headers=headers)

    def _require_local_origin(request: Request) -> None:
        # The report endpoint writes files at user-given paths, so refuse calls
        # from pages that are not served by this GUI (CORS is open for the API).
        origin = request.headers.get("origin")
        if not origin or origin == "null":
            return
        from urllib.parse import urlparse

        host = (urlparse(origin).hostname or "").lower()
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise HTTPException(status_code=403, detail="Report generation is only allowed from the local GUI")

    @app.get("/api/report/defaults")
    def api_report_defaults(
        path: str = Query("", description="Relative path to the open .dat (optional)"),
    ):
        from stb_gui.report_view import report_defaults_for_model

        try:
            data = report_defaults_for_model(path or None)
        except ValueError:
            data = report_defaults_for_model(None)
        return JSONResponse(data, headers={"Cache-Control": "no-store"})

    def _run_report_request(request, body, kind):
        _require_local_origin(request)
        from stb_engine.errors import StbParseError, StbSolveError
        from stb_gui.report_view import run_report
        from stb_reports.pdf import PdfExportError

        try:
            data = run_report(
                body.get("input"),
                body.get("output"),
                body.get("format") or None,
                kind=kind,
            )
        except StbParseError as ex:
            raise HTTPException(status_code=400, detail="Parse error: " + str(ex))
        except StbSolveError as ex:
            raise HTTPException(status_code=400, detail="Analysis error: " + str(ex))
        except PdfExportError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        except (ValueError, IOError) as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        return JSONResponse(data)

    @app.post("/api/report/confirmation")
    def api_report_confirmation(request: Request, body: dict = Body(...)):
        """Same as ``stb report <input> -o <output>``; returns where it was written."""

        return _run_report_request(request, body, "confirmation")

    @app.post("/api/report/wall-quantity")
    def api_report_wall_quantity(request: Request, body: dict = Body(...)):
        """Same as ``stb wallcalc <input> -o <output>`` (.html / .md / .pdf)."""

        return _run_report_request(request, body, "wall_quantity")

    @app.get("/api/report/view")
    def api_report_view(token: str = Query(...)):
        from fastapi.responses import HTMLResponse, PlainTextResponse
        from stb_gui.report_view import generated_report_file

        out = generated_report_file(token)
        if not out or not os.path.isfile(out):
            raise HTTPException(status_code=404, detail="Report not found (generate it again)")
        headers = {"Cache-Control": "no-store"}
        if out.lower().endswith(".pdf"):
            from urllib.parse import quote

            headers["Content-Disposition"] = "inline; filename*=UTF-8''" + quote(os.path.basename(out))
            return FileResponse(out, media_type="application/pdf", headers=headers)
        with open(out, "r", encoding="utf-8") as fh:
            text = fh.read()
        if out.lower().endswith(".md"):
            return PlainTextResponse(text, headers=headers)
        return HTMLResponse(text, headers=headers)

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
