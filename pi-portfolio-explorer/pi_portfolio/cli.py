"""Command-line interface and program entry point."""
import sys
import argparse

from .setup_ui import launch_setup_ui
from .sync import cmd_sync
from .server import cmd_serve


def main():
    if len(sys.argv) == 1:
        launch_setup_ui()
        return
    ap = argparse.ArgumentParser(description="PI Portfolio Explorer (all teams)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("setup", help="open the setup window")
    u.set_defaults(func=lambda a: launch_setup_ui())
    s = sub.add_parser("sync", help="Jira -> Excel (all teams)")
    s.add_argument("--pi", default=None, help="target PI, e.g. 26.3 (default: from settings)")
    s.add_argument("--num-sprints", type=int, default=None)
    s.set_defaults(func=cmd_sync)
    v = sub.add_parser("serve", help="local dashboard app")
    v.add_argument("--port", type=int, default=8010)
    v.set_defaults(func=cmd_serve)
    args = ap.parse_args()
    args.func(args)
