"""Pure statistics functions, unit-tested. Python 3 stdlib only.

Paired comparisons resample (task, rep) pairs: 5000 bootstrap resamples, seed 1.
Correctness differences use the exact paired sign test (McNemar exact, two-sided).
"""
import math
import random
import statistics as S

from . import config as C

BOOT_N = 5000
BOOT_SEED = 1
Z95 = 1.959963984540054


def ratio(n, d):
    if d > 0:
        return n / d
    if n == 0:
        return 1.0
    return float("inf")


def wilson(ok, n, z=Z95):
    """Wilson score 95% interval for a binomial proportion. Returns (lo, hi) in [0, 1]."""
    if n == 0:
        return (0.0, 1.0)
    if ok == 0:
        return (0.0, (z * z / n) / (1 + z * z / n))
    if ok == n:
        return (1.0 / (1 + z * z / n), 1.0)
    p = ok / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, mid - half), min(1.0, mid + half))


def p90(values):
    """90th percentile, nearest-rank on the sorted sample."""
    vs = sorted(values)
    if not vs:
        return None
    k = max(1, math.ceil(0.9 * len(vs)))
    return vs[k - 1]


def boot_ratio(pairs, f, g, rng, n_boot=BOOT_N):
    """Ratio of sums f(entry)/g(baseline) over paired rows, with a 95% bootstrap CI.
    pairs: dict key -> (entry_row, baseline_row). Resamples whole pairs."""
    keys = list(pairs)
    if not keys:
        return None, None, None
    point = ratio(sum(f(pairs[k][0]) for k in keys), sum(g(pairs[k][1]) for k in keys))
    samples = []
    for _ in range(n_boot):
        ks = [rng.choice(keys) for _ in keys]
        samples.append(ratio(sum(f(pairs[k][0]) for k in ks), sum(g(pairs[k][1]) for k in ks)))
    samples.sort()
    return point, samples[int(0.025 * n_boot)], samples[int(0.975 * n_boot) - 1]


def sign_test(b, c):
    """Exact two-sided paired sign test (McNemar exact) on discordant counts b, c.
    b: entry correct / baseline wrong; c: baseline correct / entry wrong."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return min(1.0, 2 * tail)


def _mfn(rates):
    """rates is a dict (one rate table) or a row->metric callable (model bench,
    where each model keeps its own rate table)."""
    if callable(rates):
        return rates
    return lambda r: C.metric(r, rates)


def pass_at_k(rows):
    """Share of tasks with at least one correct repeat (pass@k) and with every repeat correct (pass^k)."""
    by = {}
    for r in rows:
        by.setdefault(r["task"], []).append(bool(r.get("ok")))
    n = len(by) or 1
    return {"k": max((len(v) for v in by.values()), default=0),
            "pass_any": sum(any(v) for v in by.values()) / n,
            "pass_all": sum(all(v) for v in by.values()) / n}


def timeouts(rows):
    """Runs that ended at the hard timeout. They stay in the sample as incorrect; this only names them."""
    # the runner stores repr(error), so the marker can sit inside RunFail('timeout after 600s')
    return sum(1 for r in rows if "timeout after" in str(r.get("err") or ""))


def per_rep_correct(rows):
    """Correct rate per repeat, to show drift between repeats (provider or cache changes during a run)."""
    by = {}
    for r in rows:
        by.setdefault(r["rep"], []).append(bool(r.get("ok")))
    return {rep: sum(v) / len(v) for rep, v in sorted(by.items())}


def entry_summary(rows, rates):
    """Per-entry aggregates. Cost from the one rate table (weighted tokens if all zero)."""
    mf = _mfn(rates)
    ok = sum(1 for r in rows if r["ok"])
    n = len(rows)
    m = sum(mf(r) for r in rows)
    lo, hi = wilson(ok, n)
    secs = [r["sec"] for r in rows]
    return {
        "correct": ok, "total": n, "correct_rate": (ok / n if n else 0.0),
        "wilson95": [lo, hi],
        "i": sum(r.get("i", 0) for r in rows),
        "cr": sum(r.get("cr", 0) for r in rows),
        "cw": sum(r.get("cw", 0) for r in rows),
        "o": sum(r.get("o", 0) for r in rows),
        "metric": m,
        "metric_per_correct": (m / ok if ok else None),
        "median_sec": (S.median(secs) if secs else None),
        "p90_sec": p90(secs),
        "median_turns": (S.median([r.get("turns") or 0 for r in rows]) if rows else None),
        "pass_at_k": pass_at_k(rows),
        "timeouts": timeouts(rows),
        "per_rep_correct": per_rep_correct(rows),
    }


def frontier(points):
    """Pareto frontier flags. points: list of (rate, cost) with rate maximized and
    cost minimized; cost None means infinite (no correct run). An entry is on the
    frontier when no other entry is at least as correct AND at least as cheap with
    one strictly better. Returns a list of bools aligned with points."""
    vals = [(r, (c if c is not None else float("inf"))) for r, c in points]
    flags = []
    for i, (r, c) in enumerate(vals):
        dominated = False
        for j, (r2, c2) in enumerate(vals):
            if i != j and r2 >= r and c2 <= c and (r2 > r or c2 < c):
                dominated = True
                break
        # An entry with no correct run solved nothing: it is never on a frontier, however cheap or fast.
        flags.append(not dominated and r > 0)
    return flags


def verdict(correct_a, correct_b, cost_lo, cost_hi, p):
    """Plain verdict for entry a vs baseline b.
    'better' only when correct is not lower and the cost interval is wholly below 1.00;
    'worse' when the interval is wholly above 1.00, or correct is lower with p < 0.05;
    otherwise 'no clear difference'."""
    if cost_lo is None or cost_hi is None:
        return "no clear difference"
    if correct_a >= correct_b and cost_hi < 1.00:
        return "better"
    if cost_lo > 1.00 or (correct_a < correct_b and p is not None and p < 0.05):
        return "worse"
    return "no clear difference"


def compare(rows_a, rows_b, rates, rng=None):
    """Paired comparison of entry rows vs baseline rows on (task, rep)."""
    rng = rng if rng is not None else random.Random(BOOT_SEED)
    mf = _mfn(rates)
    ia = {(r["task"], r["rep"]): r for r in rows_a}
    ib = {(r["task"], r["rep"]): r for r in rows_b}
    pairs = {k: (ia[k], ib[k]) for k in ia if k in ib}
    if not pairs:
        return None
    entry = {"pairs": len(pairs)}
    for name, f in (("cost", mf), ("total_input", C.total_input),
                    ("output", lambda r: r.get("o", 0)), ("wall_time", lambda r: r["sec"])):
        p, lo, hi = boot_ratio(pairs, f, f, rng)
        entry[name] = {"ratio": p, "ci95": [lo, hi]}
    entry["cost_wins"] = sum(mf(p[0]) < mf(p[1]) for p in pairs.values())
    b = sum(1 for a, bb in pairs.values() if a["ok"] and not bb["ok"])
    c = sum(1 for a, bb in pairs.values() if not a["ok"] and bb["ok"])
    ok_a = sum(1 for a, _ in pairs.values() if a["ok"])
    ok_b = sum(1 for _, bb in pairs.values() if bb["ok"])
    entry["correct"] = [ok_a, ok_b]
    entry["discordant"] = [b, c]
    entry["sign_test_p"] = sign_test(b, c) if (b or c) else None
    entry["verdict"] = verdict(ok_a, ok_b, entry["cost"]["ci95"][0], entry["cost"]["ci95"][1],
                               entry["sign_test_p"])
    return entry


def clean(x):
    """JSON-safe: non-finite floats become strings, recursively."""
    if isinstance(x, float) and (x != x or x in (float("inf"), float("-inf"))):
        return "nan" if x != x else ("inf" if x > 0 else "-inf")
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return x
