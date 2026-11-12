"""GUI API routes that ship only in the Full edition.

The Simple installer omits this file, so these routes do not exist there.
"""

from fastapi import Body, HTTPException, Query
from fastapi.responses import JSONResponse


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
