from _ref import *

EDITS = [
    ("core/config.py", 'DEFAULT_ZONE = "national"', 'DEFAULT_ZONE = "local"'),
    ("core/config.py", "LOG_SLOW_MS = 800", "LOG_SLOW_MS = 600"),
    ("core/config.py", "SESSION_TTL_SECONDS = 1800", "SESSION_TTL_SECONDS = 3600"),
    ("core/config.py", 'CURRENCY = "EUR"', 'CURRENCY = "USD"'),
    ("core/config.py", "STORE_FORMAT_VERSION = 3", "STORE_FORMAT_VERSION = 4"),
    ("core/text.py", 'text[: max(0, width - 3)] + "..."', 'text[: max(0, width - 1)] + "~"'),
    ("ingest/reports.py", "def top_paths(entries, n=5):", "def top_paths(entries, n=10):"),
    ("ingest/logparse.py", "(GET|POST|PUT|DELETE)", "(GET|POST|PUT|PATCH|DELETE)"),
    ("core/pricing.py", "MAX_COUPON_PCT = 30", "MAX_COUPON_PCT = 25"),
    ("core/ids.py", r"\d{4,}", r"\d{3,}"),
    ("plugins/registry.py", "    priority = 500", "    priority = 400"),
    ("cli/main.py", 'description="freightdesk command line"', 'description="freightdesk back office command line"'),
]
ls(".")
seen = set()
for rel, old, new in EDITS:
    if rel not in seen:
        seen.add(rel)
        read(rel)
    edit(rel, old, new)
sh("python3 -B -m unittest discover -s tests -t .")
