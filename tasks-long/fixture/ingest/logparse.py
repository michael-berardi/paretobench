"""Parse access-log lines: `<iso time> <METHOD> <path> <status> <bytes> <ms>ms`."""
import re

_LINE = re.compile(r"^(\S+) (GET|POST|PUT|DELETE) (\S+) (\d{3}) (\d+) (\d+)ms$")


def parse_line(line):
    m = _LINE.match(line.strip())
    if not m:
        return None
    ts, method, path, status, nbytes, ms = m.groups()
    return {"ts": ts, "method": method, "path": path, "status": int(status),
            "bytes": int(nbytes), "ms": int(ms)}


def read_log(path):
    """Yield parsed entries; malformed lines are skipped."""
    with open(path) as f:
        for line in f:
            entry = parse_line(line)
            if entry:
                yield entry
