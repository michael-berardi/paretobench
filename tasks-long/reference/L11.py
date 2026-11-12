from _ref import *

ls(".")
read("README.md")
read("ingest/reports.py")
read("cli/main.py")
read("docs/api.md")
read("scripts/regen_golden.py")
read("tests/test_golden.py")
edit("ingest/reports.py", "def top_paths(entries, n=5):", '''def error_rate(entries):
    """Share of entries with status 500 or higher, rounded to 4 decimals; 0.0 for no entries."""
    entries = list(entries)
    if not entries:
        return 0.0
    return round(sum(1 for e in entries if e["status"] >= 500) / len(entries), 4)


def top_paths(entries, n=5):''')
edit("cli/main.py", "    for add in COMMANDS.values():\n", '''    s = sub.add_parser("error-rate", help="share of 5xx responses in an access log")
    s.add_argument("file")
    for add in COMMANDS.values():
''')
edit("cli/main.py", "    registry = registry or open_default()\n", '''    registry = registry or open_default()
    if args.cmd == "error-rate":
        from ingest import logparse, reports
        print(json.dumps({"error_rate": reports.error_rate(list(logparse.read_log(args.file)))}), file=out)
        return 0
''')
edit("docs/api.md", "## Command line", "## Error rate\n\n`python -m cli error-rate <logfile>` prints `{\"error_rate\": x}`, the share of responses with status 500 or higher.\n\n## Command line")
write("tests/test_error_rate.py", '''import unittest

from ingest import reports


def e(status):
    return {"status": status}


class TestErrorRate(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(reports.error_rate([]), 0.0)

    def test_only_5xx_count(self):
        self.assertEqual(reports.error_rate([e(200), e(404), e(499)]), 0.0)
        self.assertEqual(reports.error_rate([e(500), e(200)]), 0.5)

    def test_rounding(self):
        self.assertEqual(reports.error_rate([e(503), e(200), e(200)]), 0.3333)


if __name__ == "__main__":
    unittest.main()
''')
sh("python3 -B -m unittest discover -s tests -t .", ok=(1,))
sh("python3 -B scripts/regen_golden.py")
sh("python3 -B -m unittest discover -s tests -t .")
