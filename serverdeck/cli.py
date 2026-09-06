#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from serverdeck import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="serverdeck",
        description="Linux server monitoring dashboard and management tool."
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-b", "--banner", action="store_true", help="Print ServerDeck banner and metadata")
    parser.add_argument("-d", "--debug", "--diag", "--diagnostics", action="store_true", help="Run diagnostic self-test and benchmarks")
    parser.add_argument("-t", "--tab", type=int, choices=list(range(1, 10)), help="Render single static frame of a specific tab (1-9)")
    parser.add_argument("--theme", type=str, default="glacier_cyan", help="Select UI theme for static render")
    parser.add_argument("--bot", action="store_true", help="Launch Discord bot daemon")
    parser.add_argument("--config", type=str, default=None, help="Custom path to config.yaml")
    parser.add_argument("--bot-config", type=str, default=None, help="Custom path to bot.yaml")
    parser.add_argument("--env-file", type=str, default=None, help="Custom path to .env file")
    parser.add_argument("--service", type=str, choices=["status", "start", "stop", "restart", "enable", "disable", "logs", "install"], default=None, help="Manage systemd service instance")
    parser.add_argument("--unit", type=str, default="bot", help="Target service unit for --service (default: bot)")
    parser.add_argument("--snapshot", action="store_true", help="Dump telemetry JSON snapshot to stdout and exit")

    args, extra = parser.parse_known_args()

    if args.env_file:
        from serverdeck.core.state import load_secrets_config
        load_secrets_config(Path(args.env_file))

    if args.service:
        from serverdeck.managers.service import manage_service
        ok, msg = manage_service(args.service, target=args.unit)
        print(msg)
        sys.exit(0 if ok else 1)

    if args.banner:
        from serverdeck.app import print_banner
        print_banner()
    elif args.debug:
        from serverdeck.app import run_diagnostics
        run_diagnostics()
    elif args.tab is not None:
        from serverdeck.app import render_static_tab
        render_static_tab(args.tab, theme_name=args.theme)
    elif args.snapshot:
        import json
        from serverdeck.app import get_all_device_stats
        st = get_all_device_stats()
        print(json.dumps(st, indent=2, default=str))
    elif args.bot:
        from serverdeck.bot.main import main as bot_main
        bot_main()
    else:
        from serverdeck.app import run_monitor
        run_monitor()


if __name__ == "__main__":
    main()
