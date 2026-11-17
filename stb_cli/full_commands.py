"""CLI commands that ship only in the Full edition.

The Simple installer omits this file, so these commands do not exist there.
"""

import os
import sys

from stb_cli.main import (
    EXIT_INPUT,
    EXIT_OK,
    EXIT_SOLVE,
    _ensure_project_root_on_path,
    _read_lines,
    _solve_with_stdout_control,
    _stb_version,
    _stderr,
)


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
            program_version=_stb_version(),
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
        print("  warnings:    " + str(len(draft.warnings)))
        if hasattr(draft, "page_count"):
            print("  pages:       " + str(draft.page_count))

    return EXIT_OK


def cmd_wallcalc(args):
    """木造壁量計算書 (wall quantity / balance / N値 / 柱の小径). Parse only; no solve needed."""
    _ensure_project_root_on_path()
    from stb_engine import parse_input
    from stb_engine.errors import StbParseError
    from stb_project import load_project_file, load_project_for_dat
    from stb_reports import write_wall_quantity_report

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
        if not project.wall_quantity.enabled:
            raise ValueError("project.wall_quantity is not set (see docs/project_format.md)")

        mdl = parse_input(_read_lines(dat_path))
        mdl.filepath = dat_path
        report = write_wall_quantity_report(
            args.output, mdl, project, output_format=args.format, program_version=_stb_version(),
        )
    except IOError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except StbParseError as ex:
        _stderr("Parse error: " + str(ex))
        return EXIT_INPUT
    except ValueError as ex:
        _stderr(str(ex))
        return EXIT_INPUT

    if args.verbose:
        s = report.summary
        print("Wall quantity report written: " + args.output)
        print("  wall quantity: " + s.status)
        print("  balance (1/4): " + (s.balance.status if s.balance is not None else "-"))
        print("  N-value:       " + (s.n_values.status if s.n_values is not None else "-"))
        print("  column size:   " + (s.column_size.status if s.column_size is not None else "-"))
        print("  overall:       " + report.status)
        print("  warnings:    " + str(len(report.warnings)))
    return EXIT_OK


def register(sub, common):
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
        help="Output report file (.md, .html or .pdf)",
    )
    p_rep.add_argument(
        "--format",
        choices=["markdown", "html", "pdf"],
        default=None,
        help="Report format (default: from a .pdf output name, else project.report.format)",
    )
    p_rep.set_defaults(func=cmd_report)

    p_wall = sub.add_parser(
        "wallcalc",
        parents=[common],
        help="Generate the wood wall-quantity report (壁量計算書, 2025 standard)",
    )
    p_wall.add_argument(
        "input",
        help="Project JSON with wall_quantity, or input model file with a .project.json sidecar",
    )
    p_wall.add_argument(
        "-o", "--output",
        required=True,
        help="Output report file (.html or .md)",
    )
    p_wall.add_argument(
        "--format",
        choices=["markdown", "html"],
        default=None,
        help="Report format (default: from the output file extension)",
    )
    p_wall.set_defaults(func=cmd_wallcalc)

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
