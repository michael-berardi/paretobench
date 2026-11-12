"""Summaries over parsed log entries and shipment rows."""


def status_counts(entries):
    out = {}
    for e in entries:
        out[e["status"]] = out.get(e["status"], 0) + 1
    return dict(sorted(out.items()))


def bytes_by_path(entries):
    out = {}
    for e in entries:
        out[e["path"]] = out.get(e["path"], 0) + e["bytes"]
    return out


def slow_requests(entries, threshold_ms):
    return [e for e in entries if e["ms"] > threshold_ms]


def cost_by_carrier(rows):
    out = {}
    for r in rows:
        out[r["carrier"]] = out.get(r["carrier"], 0) + r["cost_cents"]
    return dict(sorted(out.items()))


def top_paths(entries, n=5):
    counts = {}
    for e in entries:
        counts[e["path"]] = counts.get(e["path"], 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
