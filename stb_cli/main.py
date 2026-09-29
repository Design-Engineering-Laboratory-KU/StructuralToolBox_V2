import argparse
import os
import sys

_STB_VERSION = "0.1.0"

# Exit codes for scripts and Grasshopper wrappers.
EXIT_OK = 0
EXIT_INPUT = 1
EXIT_SOLVE = 2
EXIT_GUI_ALREADY = 10


def _ensure_project_root_on_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)


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
    print("stb " + _STB_VERSION)
    return EXIT_OK


def cmd_doctor(args):
    _ensure_project_root_on_path()
    from stb_engine import runtime

    print("stb " + _STB_VERSION)
    for line in runtime.describe():
        print("  " + line)

    missing = []
    print("  libraries:")
    for name in ("numpy", "scipy", "shapely", "fastapi", "uvicorn", "httpx"):
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
        _stderr("This is not the bundled Python of a student install.")
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


def cmd_loads_seismic(args):
    _ensure_project_root_on_path()
    from stb_engine import parse_input
    from stb_engine.errors import StbParseError
    from stb_project import load_project_file, load_project_for_dat
    from stb_loads import (
        apply_seismic_to_dat,
        compute_seismic_distribution,
        generate_dlod_records,
        render_seismic_markdown,
    )

    try:
        input_path = os.path.abspath(args.project)
        if input_path.lower().endswith(".json"):
            project = load_project_file(input_path)
            project_dir = os.path.dirname(input_path)
            dat_path = project.dat_path
            if not os.path.isabs(dat_path):
                dat_path = os.path.join(project_dir, dat_path)
        else:
            dat_path = input_path
            project = load_project_for_dat(dat_path, required=True)

        lines = _read_lines(dat_path)
        mdl = parse_input(lines)
        mdl.filepath = dat_path
        result = compute_seismic_distribution(mdl, project)
        dloads = generate_dlod_records(result)
        markdown = render_seismic_markdown(result, project, mdl=mdl)

        if args.dry_run or not args.write_dat:
            sys.stdout.write(markdown)
            if not markdown.endswith("\n"):
                sys.stdout.write("\n")
        if args.write_dat:
            apply_seismic_to_dat(dat_path, dloads)
            if args.verbose:
                print("Updated: " + dat_path)
                print("  seismic DLOD records: " + str(len(dloads)))
    except IOError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except StbParseError as ex:
        _stderr("Parse error: " + str(ex))
        return EXIT_INPUT
    except ValueError as ex:
        _stderr(str(ex))
        return EXIT_INPUT

    return EXIT_OK


def cmd_loads_wind(args):
    _ensure_project_root_on_path()
    from stb_engine import parse_input
    from stb_engine.errors import StbParseError
    from stb_project import apply_load_combinations_to_model, load_project_file, load_project_for_dat
    from stb_loads import (
        apply_wind_to_dat,
        compute_wind_distribution,
        generate_wind_dlod_records,
        render_wind_markdown,
    )

    try:
        input_path = os.path.abspath(args.project)
        if input_path.lower().endswith(".json"):
            project = load_project_file(input_path)
            project_dir = os.path.dirname(input_path)
            dat_path = project.dat_path
            if not os.path.isabs(dat_path):
                dat_path = os.path.join(project_dir, dat_path)
        else:
            dat_path = input_path
            project = load_project_for_dat(dat_path, required=True)

        lines = _read_lines(dat_path)
        mdl = parse_input(lines)
        mdl.filepath = dat_path
        result = compute_wind_distribution(mdl, project)
        dloads = generate_wind_dlod_records(result)
        markdown = render_wind_markdown(result, project, mdl=mdl)

        if args.dry_run or not args.write_dat:
            sys.stdout.write(markdown)
            if not markdown.endswith("\n"):
                sys.stdout.write("\n")
        if args.write_dat:
            apply_wind_to_dat(dat_path, dloads)
            if args.verbose:
                print("Updated: " + dat_path)
                print("  wind DLOD records: " + str(len(dloads)))
    except IOError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except StbParseError as ex:
        _stderr("Parse error: " + str(ex))
        return EXIT_INPUT
    except ValueError as ex:
        _stderr(str(ex))
        return EXIT_INPUT

    return EXIT_OK


def cmd_loads_combinations(args):
    _ensure_project_root_on_path()
    from stb_project import (
        apply_project_load_combinations_to_dat,
        build_lcmb_block,
        load_project_file,
        load_project_for_dat,
    )

    try:
        input_path = os.path.abspath(args.project)
        if input_path.lower().endswith(".json"):
            project = load_project_file(input_path)
            dat_path = project.dat_path
            if not os.path.isabs(dat_path):
                dat_path = os.path.join(os.path.dirname(input_path), dat_path)
        else:
            dat_path = input_path
            project = load_project_for_dat(dat_path, required=True)

        combinations = project.load_conditions.load_combinations
        if args.dry_run or not args.write_dat:
            sys.stdout.write(build_lcmb_block(combinations))
        if args.write_dat:
            count = apply_project_load_combinations_to_dat(dat_path, project)
            if args.verbose:
                print("Updated: " + dat_path)
                print("  LCMB records: " + str(count))
    except IOError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except ValueError as ex:
        _stderr(str(ex))
        return EXIT_INPUT

    return EXIT_OK


def cmd_report(args):
    _ensure_project_root_on_path()
    from stb_engine import parse_input, format_results
    from stb_engine.errors import StbParseError, StbSolveError
    from stb_project import apply_load_combinations_to_model, load_project_file, load_project_for_dat
    from stb_reports import write_confirmation_draft

    try:
        input_path = os.path.abspath(args.input)
        if input_path.lower().endswith(".json"):
            project = load_project_file(input_path)
            dat_path = project.dat_path
            if not os.path.isabs(dat_path):
                dat_path = os.path.join(os.path.dirname(input_path), dat_path)
        else:
            dat_path = input_path
            project = load_project_for_dat(dat_path, required=True)

        lines = _read_lines(dat_path)
        mdl = parse_input(lines)
        mdl.filepath = dat_path
        apply_load_combinations_to_model(mdl, project)
        _solve_with_stdout_control(mdl, args.quiet)
        txt = format_results(mdl)
        draft = write_confirmation_draft(
            args.output,
            mdl,
            project,
            output_format=args.format,
            analysis_text=txt,
            program_version=_STB_VERSION,
        )
    except IOError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except StbParseError as ex:
        _stderr("Parse error: " + str(ex))
        return EXIT_INPUT
    except StbSolveError as ex:
        _stderr("Analysis error: " + str(ex))
        return EXIT_SOLVE
    except ValueError as ex:
        _stderr(str(ex))
        return EXIT_INPUT

    if args.verbose:
        print("Report written: " + args.output)
        print("  format:      " + (args.format or project.report.format))
        print("  warnings:    " + str(len(draft.warnings)))

    return EXIT_OK


def cmd_gui(args):
    _ensure_project_root_on_path()
    try:
        from stb_gui.server import run_server
    except ImportError as ex:
        _stderr(str(ex))
        _stderr("Install GUI extras: pip install -e \".[gui]\"")
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
        help="Fail unless running on the bundled Python of a student install",
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

    p_rep = sub.add_parser(
        "report",
        parents=[common],
        help="Generate a confirmation application draft report",
    )
    p_rep.add_argument(
        "input",
        help="Project JSON or input model file with a .project.json sidecar",
    )
    p_rep.add_argument(
        "-o", "--output",
        required=True,
        help="Output report file (.md or .html)",
    )
    p_rep.add_argument(
        "--format",
        choices=["markdown", "html"],
        default=None,
        help="Report format (default: project.report.format)",
    )
    p_rep.set_defaults(func=cmd_report)

    p_loads = sub.add_parser(
        "loads",
        parents=[common],
        help="Load generation utilities",
    )
    p_loads_sub = p_loads.add_subparsers(dest="loads_command")
    p_loads_sub.required = True

    p_seismic = p_loads_sub.add_parser(
        "seismic",
        parents=[common],
        help="Generate seismic DLOD records from Ai distribution",
    )
    p_seismic.add_argument(
        "--project",
        required=True,
        help="Project JSON sidecar path",
    )
    p_seismic.add_argument(
        "--dry-run",
        action="store_true",
        help="Print Wi/Ai/Qi table without modifying .dat",
    )
    p_seismic.add_argument(
        "--write-dat",
        action="store_true",
        help="Write generated DLOD block into the linked .dat file",
    )
    p_seismic.set_defaults(func=cmd_loads_seismic)

    p_wind = p_loads_sub.add_parser(
        "wind",
        parents=[common],
        help="Generate wind DLOD records from wall surfaces",
    )
    p_wind.add_argument(
        "--project",
        required=True,
        help="Project JSON sidecar path",
    )
    p_wind.add_argument(
        "--dry-run",
        action="store_true",
        help="Print wind load report without modifying .dat",
    )
    p_wind.add_argument(
        "--write-dat",
        action="store_true",
        help="Write generated DLOD block into the linked .dat file",
    )
    p_wind.set_defaults(func=cmd_loads_wind)

    p_lcmb = p_loads_sub.add_parser(
        "combinations",
        parents=[common],
        help="Write project load combinations into the linked .dat file",
    )
    p_lcmb.add_argument(
        "--project",
        required=True,
        help="Project JSON sidecar path or linked .dat path",
    )
    p_lcmb.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated LCMB block without modifying .dat",
    )
    p_lcmb.add_argument(
        "--write-dat",
        action="store_true",
        help="Write generated LCMB block into the linked .dat file",
    )
    p_lcmb.set_defaults(func=cmd_loads_combinations)

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
