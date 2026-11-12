import sys


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="stb-gui",
        description="Structural Toolbox browser application",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="Port (default: 8765)",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Do not open a browser window",
    )
    parser.add_argument(
        "--no-exit-with-browser", action="store_true",
        help="Keep the server running after the browser tab closes",
    )
    args = parser.parse_args()

    from stb_gui.applog import ensure_log_streams

    ensure_log_streams()
    try:
        from stb_gui.server import run_server
    except ImportError as ex:
        sys.stderr.write(str(ex) + "\n")
        sys.exit(1)

    run_server(
        host=args.host,
        port=args.port,
        open_browser=(not args.no_browser),
        exit_with_browser=(not args.no_exit_with_browser),
    )


if __name__ == "__main__":
    main()
