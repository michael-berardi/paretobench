from _ref import *

ls(".")
read("store/memory.py")
read("plugins/registry.py")
read("cli/main.py")
read("ingest/logparse.py")
read("tests/test_registry.py")
write("ingest/windows.py", '''"""Count log entries in fixed time windows."""
import calendar
import time

from core.errors import ValidationError

_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _check(seconds):
    if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds < 1:
        raise ValidationError("seconds must be a positive integer")


def _epoch(ts):
    try:
        return calendar.timegm(time.strptime(ts, _FMT))
    except (ValueError, TypeError):
        raise ValidationError(f"bad timestamp: {ts!r}")


def window_start(ts, seconds):
    _check(seconds)
    return time.strftime(_FMT, time.gmtime(_epoch(ts) // seconds * seconds))


def window_counts(entries, seconds):
    """[(window start, count)] for windows aligned to the Unix epoch, oldest first; empty windows omitted."""
    _check(seconds)
    counts = {}
    for e in entries:
        start = _epoch(e["ts"]) // seconds * seconds
        counts[start] = counts.get(start, 0) + 1
    return [(time.strftime(_FMT, time.gmtime(s)), n) for s, n in sorted(counts.items())]
''')
edit("store/memory.py", "    def get(self, rid):", '''    def bulk_put(self, records, validate=True, atomic=True):
        """Store many records; with atomic=True one invalid record stores nothing. Returns the count."""
        records = list(records)
        if validate and atomic:
            for r in records:
                r.validate()
        stored = 0
        for r in records:
            self.put(r, validate=validate)
            stored += 1
        return stored

    def get(self, rid):''')
edit("plugins/registry.py", "import pkgutil\n", "import pkgutil\n\nfrom core.errors import NotFound\n")
edit("plugins/registry.py", "def run_chain(event):", '''def _get(name):
    if name not in PLUGINS:
        raise NotFound(f"unknown plugin: {name}")
    return PLUGINS[name]


def disable(name):
    _get(name).enabled = False


def enable(name):
    _get(name).enabled = True


def chain_report(event):
    """Names of the enabled plugins that would handle the event, in chain order (nothing is run)."""
    return [p.name for p in enabled() if p.handles(event)]


def run_chain(event):''')
edit("cli/main.py", "from cli.commands import COMMANDS\n", "from cli.commands import COMMANDS\nfrom core.errors import FreightError\nfrom ingest import logparse, windows\nfrom plugins import registry as plugin_registry\nfrom store.models import ENTITIES\n")
edit("cli/main.py", "    for add in COMMANDS.values():\n", '''    s = sub.add_parser("log-windows", help="count log entries per time window")
    s.add_argument("file")
    s.add_argument("--seconds", type=int, required=True)
    s = sub.add_parser("plugin-chain", help="the plugins that would handle an event kind")
    s.add_argument("--kind", required=True)
    s.add_argument("--disable", action="append", default=[])
    s = sub.add_parser("put-many", help="store a JSON array of records atomically")
    s.add_argument("entity")
    s.add_argument("records")
    for add in COMMANDS.values():
''')
edit("cli/main.py", "def main(argv=None, registry=None, out=None):", '''def _wave(args, registry, out):
    try:
        if args.cmd == "log-windows":
            entries = list(logparse.read_log(args.file))
            body = {"requests": len(entries),
                    "windows": [list(w) for w in windows.window_counts(entries, args.seconds)]}
        elif args.cmd == "plugin-chain":
            plugin_registry.load_all()
            disabled = []
            try:
                for name in args.disable:
                    plugin_registry.disable(name)
                    disabled.append(name)
                body = {"chain": plugin_registry.chain_report({"kind": args.kind})}
            finally:
                for name in disabled:
                    plugin_registry.enable(name)
        else:
            if args.entity not in ENTITIES:
                raise FreightError(f"unknown entity: {args.entity}")
            cls = ENTITIES[args.entity]
            records = [cls.from_dict(d) for d in json.loads(args.records)]
            body = {"stored": registry.repo(args.entity).bulk_put(records)}
            registry.save_all()
    except (FreightError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=out)
        return 1
    print(json.dumps(body, sort_keys=True), file=out)
    return 0


def main(argv=None, registry=None, out=None):''')
edit("cli/main.py", "    registry = registry or open_default()\n", '''    registry = registry or open_default()
    if args.cmd in ("log-windows", "plugin-chain", "put-many"):
        return _wave(args, registry, out)
''')
write("tests/test_wave.py", '''import io
import json
import unittest

from cli.main import main
from ingest.windows import window_counts
from plugins import registry
from store.memory import Repository
from store.models import ENTITIES
from store.registry import Registry


class TestWave(unittest.TestCase):
    def test_windows(self):
        out = window_counts([{"ts": "2025-03-04T10:00:01Z"}, {"ts": "2025-03-04T10:00:59Z"}], 60)
        self.assertEqual(out, [("2025-03-04T10:00:00Z", 2)])

    def test_bulk_put_atomic(self):
        cls = ENTITIES["customer"]
        repo = Repository(cls)
        bad = cls("zzz-1", **cls.sample(1))
        with self.assertRaises(Exception):
            repo.bulk_put([cls("cus-0001", **cls.sample(1)), bad])
        self.assertEqual(len(repo), 0)

    def test_toggle_and_report(self):
        registry.load_all()
        name = registry.enabled()[0].name
        registry.disable(name)
        self.addCleanup(registry.enable, name)
        self.assertNotIn(name, registry.chain_report({"kind": "shipment"}))

    def test_cli_plugin_chain(self):
        out = io.StringIO()
        self.assertEqual(main(["plugin-chain", "--kind", "invoice"], registry=Registry(), out=out), 0)
        self.assertIn("chain", json.loads(out.getvalue()))


if __name__ == "__main__":
    unittest.main()
''')
sh("python3 -B -m unittest tests.test_wave")
sh("python3 -B -m cli log-windows logs/access.log --seconds 3600")
sh("python3 -B -m cli plugin-chain --kind shipment")
edit("docs/api.md", "## Command line", "## Wave commands\n\n`log-windows <file> --seconds S`, `plugin-chain --kind K [--disable NAME]` and `put-many <entity> <json array>`.\n\n## Command line")
sh("python3 -B -m unittest discover -s tests -t .")
