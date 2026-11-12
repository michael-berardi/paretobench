"""Command line entry point."""
import argparse
import json
import sys

from api.router import handle
from cli.commands import COMMANDS
from store.registry import open_default


def build_parser():
    p = argparse.ArgumentParser(prog="cli", description="freightdesk command line")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list", help="list the records of an entity")
    s.add_argument("entity")
    s = sub.add_parser("get", help="show one record")
    s.add_argument("entity")
    s.add_argument("id")
    s = sub.add_parser("put", help="store a record given as JSON")
    s.add_argument("entity")
    s.add_argument("record")
    s = sub.add_parser("delete", help="delete a record")
    s.add_argument("entity")
    s.add_argument("id")
    for add in COMMANDS.values():
        add.add_parser(sub)
    return p


def main(argv=None, registry=None, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    registry = registry or open_default()
    if args.cmd in ("list", "get", "put", "delete"):
        req = {"op": args.cmd, "entity": args.entity}
        if args.cmd in ("get", "delete"):
            req["id"] = args.id
        if args.cmd == "put":
            req["record"] = json.loads(args.record)
        resp = handle(req, registry)
        if resp["status"] == 200 and args.cmd in ("put", "delete"):
            registry.save_all()
    else:
        resp = COMMANDS[args.cmd.split("-")[0]].run(registry, args)
    print(json.dumps(resp["body"], indent=1, sort_keys=True), file=out)
    return 0 if resp["status"] == 200 else 1
