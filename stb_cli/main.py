import argparse
import importlib.util
import os
import sys

# Exit codes for scripts and Grasshopper wrappers.
EXIT_OK = 0
EXIT_INPUT = 1
EXIT_SOLVE = 2
EXIT_GUI_ALREADY = 10


def _ensure_project_root_on_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)


def _stb_version():
    _ensure_project_root_on_path()
    from stb_engine.version import __version__

    return __version__


def _stderr(msg):
    sys.stderr.write(msg)
    if not msg.endswith("\n"):
        sys.stderr.write("\n")


def _read_lines(path):
    if not os.path.isfile(path):
        raise IOError("Input file not found: " + path)

    f = open(path, "r", encoding="utf-8")
    lines = f.read().splitlines()
    f.close()
    return lines


def _solve_with_stdout_control(mdl, quiet):
    from stb_engine import solve_model

    if quiet:
        old_stdout = sys.stdout
        devnull = open(os.devnull, "w")
        sys.stdout = devnull
        try:
            solve_model(mdl)
        finally:
            sys.stdout.close()
            sys.stdout = old_stdout
    else:
        solve_model(mdl)


def cmd_version(args):
    print("stb " + _stb_version())
    return EXIT_OK


def cmd_doctor(args):
    _ensure_project_root_on_path()
    from stb_engine import runtime

    print("stb " + _stb_version())
    for line in runtime.describe():
        print("  " + line)

    missing = []
    print("  libraries:")
    names = ("numpy", "scipy", "shapely", "fastapi", "uvicorn", "httpx")
    if importlib.util.find_spec("stb_reports") is not None:
        names += ("reportlab", "pypdf")
    for name in names:
        try:
            mod = __import__(name)
        except ImportError:
            missing.append(name)
            print("    {0:<10} (missing)".format(name))
            continue
        print("    {0:<10} {1}".format(name, getattr(mod, "__version__", "?")))

    if missing:
        _stderr("Missing libraries: " + ", ".join(missing))
        _stderr("Re-run the first-time setup (Install_once) to repair the install.")
        return EXIT_INPUT

    if not runtime.is_bundled() and getattr(args, "require_bundled", False):
        _stderr("This is not the bundled Python of an installer-based install.")
        return EXIT_INPUT

    return EXIT_OK


def cmd_validate(args):
    _ensure_project_root_on_path()
    from stb_engine import parse_input
    from stb_engine.errors import StbParseError

    try:
        lines = _read_lines(args.input)
        mdl = parse_input(lines)
    except IOError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except StbParseError as ex:
        _stderr("Parse error: " + str(ex))
        return EXIT_INPUT

    if args.verbose:
        print("Input OK: " + args.input)
        print("  nodes:      " + str(len(mdl.nds)))
        print("  elements:   " + str(len(mdl.elms)))
        print("  materials:  " + str(len(mdl.mats)))
        print("  sections:   " + str(len(mdl.secs)))
        print("  load cases: " + str(mdl.lcs))

    return EXIT_OK


def cmd_solve(args):
    _ensure_project_root_on_path()
    from stb_engine import parse_input, format_results
    from stb_engine.errors import StbParseError, StbSolveError
    from stb_project import apply_project_load_combinations_to_dat, load_project_file

    try:
        input_path = os.path.abspath(args.input)
        project = None
        if input_path.lower().endswith(".json"):
            project = load_project_file(input_path)
            dat_path = project.dat_path
            if not os.path.isabs(dat_path):
                dat_path = os.path.join(os.path.dirname(input_path), dat_path)
            apply_project_load_combinations_to_dat(dat_path, project)
        else:
            dat_path = input_path

        lines = _read_lines(dat_path)
        mdl = parse_input(lines)
        mdl.filepath = dat_path
    except IOError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except ValueError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except StbParseError as ex:
        _stderr("Parse error: " + str(ex))
        return EXIT_INPUT

    try:
        _solve_with_stdout_control(mdl, args.quiet)
        txt = format_results(mdl)
    except StbSolveError as ex:
        _stderr("Analysis error: " + str(ex))
        return EXIT_SOLVE

    if args.verbose:
        print("Solved: " + dat_path)
        if project is not None and project.load_conditions.load_combinations:
            print("  project:    " + (project.source_path or "(loaded)"))
            print("  LCMB->dat:  " + str(len(project.load_conditions.load_combinations)))
        print("  load cases: " + str(mdl.lcs))
        print("  analysis:   " + str(mdl.date_analysis))

    if args.output != None:
        out_path = args.output
        out_dir = os.path.dirname(os.path.abspath(out_path))
        if out_dir != "" and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        f = open(out_path, "w")
        f.write(txt)
        f.close()
        if args.verbose:
            print("  written:    " + out_path)
    else:
        sys.stdout.write(txt)

    return EXIT_OK


def cmd_gui(args):
    _ensure_project_root_on_path()
    # Launched without a console (pythonw.exe): send output to a log file.
    from stb_gui.applog import ensure_log_streams, log_path, show_error_dialog

    ensure_log_streams()
    no_console = log_path() is not None
    try:
        from stb_gui.server import run_server
    except ImportError as ex:
        _stderr(str(ex))
        _stderr("Install GUI extras: pip install -e \".[gui]\"")
        if no_console:
            show_error_dialog("必要なライブラリが見つかりません。初回セットアップを再実行してください。\n\n" + str(ex))
        return EXIT_INPUT

    try:
        result = run_server(
            host=args.host,
            port=args.port,
            open_browser=(not args.no_browser),
            log_file=getattr(args, "log_file", None),
            exit_with_browser=not getattr(args, "no_exit_with_browser", False),
        )
    except KeyboardInterrupt:
        return EXIT_OK
    except SystemExit as ex:
        # uvicorn exits with 1 when it cannot bind the port.
        if ex.code not in (None, 0) and no_console:
            show_error_dialog("サーバーを起動できませんでした（ポート {0} が使用中の可能性があります）。".format(args.port))
        raise
    except Exception as ex:
        import traceback

        traceback.print_exc()
        if no_console:
            show_error_dialog("サーバーの起動中にエラーが発生しました。\n\n" + str(ex))
        return EXIT_INPUT
    if result == "already_running":
        return EXIT_GUI_ALREADY
    return EXIT_OK


def _build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress solver progress messages",
    )
    common.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print extra status messages",
    )

    parser = argparse.ArgumentParser(
        prog="stb",
        description="Structural Toolbox — static analysis and browser GUI",
    )

    sub = parser.add_subparsers(dest="command")

    p_ver = sub.add_parser("version", parents=[common], help="Show version")
    p_ver.set_defaults(func=cmd_version)

    p_doc = sub.add_parser(
        "doctor",
        parents=[common],
        help="Show which Python and libraries this install uses",
    )
    p_doc.add_argument(
        "--require-bundled",
        action="store_true",
        help="Fail unless running on the bundled Python of an installer-based install",
    )
    p_doc.set_defaults(func=cmd_doctor)

    p_val = sub.add_parser(
        "validate",
        parents=[common],
        help="Parse input only (no analysis)",
    )
    p_val.add_argument("input", help="Input model file (.dat, .stb, ...)")
    p_val.set_defaults(func=cmd_validate)

    p_sol = sub.add_parser(
        "solve",
        parents=[common],
        help="Run static analysis",
    )
    p_sol.add_argument("input", help="Input model file")
    p_sol.add_argument(
        "-o", "--output",
        help="Output results file (.out; default: stdout)",
    )
    p_sol.set_defaults(func=cmd_solve)

    if importlib.util.find_spec("stb_cli.full_commands") is not None:
        importlib.import_module("stb_cli.full_commands").register(sub, common)

    p_gui = sub.add_parser(
        "gui",
        parents=[common],
        help="Start Structural Toolbox in the browser",
    )
    p_gui.add_argument(
        "--host", default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    p_gui.add_argument(
        "--port", type=int, default=8765,
        help="Port (default: 8765)",
    )
    p_gui.add_argument(
        "--no-browser", action="store_true",
        help="Do not open a browser",
    )
    p_gui.add_argument(
        "--log-file",
        default=None,
        help="Also write server logs to this file (debug)",
    )
    p_gui.add_argument(
        "--no-exit-with-browser",
        action="store_true",
        help="Keep the server running after the browser tab closes (default: stop with browser)",
    )
    p_gui.set_defaults(func=cmd_gui)

    return parser


def main(argv=None):
    if argv == None:
        argv = sys.argv[1:]

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == None:
        parser.print_help()
        return EXIT_INPUT

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
