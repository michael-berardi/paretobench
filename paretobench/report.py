"""Report for both benches. Detects the bench from the rows, refuses to mix task sets,
reads legacy steak-dsh arm names, marks the Pareto frontiers and gives a plain verdict
per comparison. Writes summary.json and summary.md into the results dir."""
import glob
import json
import os
import random

from . import __version__
from . import config as C
from . import stats as ST
from .harnesses import ARM_MAP


def load_rows(dir_path):
    """Read rows from a results dir: rows.jsonl when present, else every *.jsonl."""
    dir_path = os.path.abspath(os.path.expanduser(dir_path))
    if os.path.isfile(dir_path):  # tolerate a direct file path
        files = [dir_path]
        dir_path = os.path.dirname(dir_path)
    else:
        rows_file = os.path.join(dir_path, "rows.jsonl")
        files = [rows_file] if os.path.isfile(rows_file) else sorted(glob.glob(os.path.join(dir_path, "*.jsonl")))
    if not files:
        raise C.PBError("no-rows", f"no .jsonl rows found in {dir_path}")
    rows = []
    for fp in files:
        with open(fp) as f:
            for n, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError as e:
                    raise C.PBError("bad-row", f"{fp} line {n}: {e}")
    if not rows:
        raise C.PBError("no-rows", f"row files in {dir_path} are empty")
    return rows, dir_path


def normalize(rows):
    """Map legacy arm names to harness names; fill bench and task_set defaults.
    Old rows have no task_set: they belong to the legacy set, one legacy set per dir."""
    out = []
    for r in rows:
        r = dict(r)
        r["harness"] = r.get("harness") or ARM_MAP.get(r.get("arm"), r.get("arm"))
        r["bench"] = r.get("bench") or "harness"
        r["task_set"] = r.get("task_set") or C.LEGACY_TASK_SET
        out.append(r)
    return out


def summarize(rows, models, baseline=None):
    """Pure summary construction. Raises PBError on mixed task sets or unknown models."""
    rows = normalize(rows)
    tsets = sorted({r["task_set"] for r in rows})
    if len(tsets) > 1:
        raise C.PBError("mixed-task-sets",
                        f"rows carry {len(tsets)} task sets ({', '.join(tsets)}); "
                        "results from different task sets are never mixed")
    benches = sorted({r["bench"] for r in rows})
    if len(benches) > 1:
        raise C.PBError("mixed-benches", f"rows carry both benches ({', '.join(benches)}); report one bench at a time")
    bench = benches[0]
    entry_field = "harness" if bench == "harness" else "model"
    rng = random.Random(ST.BOOT_SEED)
    for r in rows:
        if r.get("model") not in models:
            raise C.PBError("unknown-model",
                            f"rows carry model '{r.get('model')}' which is not in the models config")
    if bench == "harness":
        groups = {}
        for r in rows:
            groups.setdefault(r["model"], []).append(r)
    else:
        groups = {}
        for r in rows:
            groups.setdefault(r["harness"], []).append(r)
        if len(groups) > 1:
            raise C.PBError("mixed-harnesses",
                            f"model bench rows carry {len(groups)} harnesses ({', '.join(sorted(groups))}); "
                            "the model bench compares models under one harness")
    summary = {"pb_version": __version__, "bench": bench, "task_set": tsets[0],
               "rows": len(rows), "bootstrap": {"resamples": ST.BOOT_N, "seed": ST.BOOT_SEED,
                                                "unit": "(task, rep) pairs"},
               "groups": {}}
    for gkey, rs in sorted(groups.items()):
        if bench == "harness":
            rates = models[gkey]["rates"]
            label = C.metric_label(rates)
            note = models[gkey].get("note", "")
            mfn = rates
        else:
            # one rate table per model, applied to every harness: each row keeps its own model's rates
            gmodels = sorted({r["model"] for r in rs})
            rates = {m: models[m]["rates"] for m in gmodels}
            any_free = any(C.all_zero(models[m]["rates"]) for m in gmodels)
            label = "weighted tokens" if any_free else "cost $"
            note = ("at least one model is on a flat plan with no per-token price, so every model is compared in "
                    "weighted tokens; dollars are shown beside each priced model") if any_free else ""

            if any_free:
                def mfn(r):
                    return C.weighted(r)
            else:
                def mfn(r):
                    return C.cost(r, models[r["model"]]["rates"])

        entries = sorted({r[entry_field] for r in rs})
        base = baseline or ("dsh" if bench == "harness" and "dsh" in entries else entries[0])
        if base not in entries:
            raise C.PBError("unknown-baseline", f"baseline '{base}' not in entries ({', '.join(entries)})")
        per_entry = {}
        rows_by_entry = {}
        for a in entries:
            ar = [r for r in rs if r[entry_field] == a]
            rows_by_entry[a] = ar
            per_entry[a] = ST.entry_summary(ar, mfn)
            # Dollars at list price, for entries that have one (None on a flat plan).
            if bench == "harness":
                priced = not C.all_zero(models[gkey]["rates"])
                per_entry[a]["dollars"] = sum(C.cost(r, models[gkey]["rates"]) for r in ar) if priced else None
            else:
                priced = not C.all_zero(models[a]["rates"])
                per_entry[a]["dollars"] = sum(C.cost(r, models[a]["rates"]) for r in ar) if priced else None
        cost_flags = ST.frontier([(per_entry[a]["correct_rate"], per_entry[a]["metric_per_correct"])
                                  for a in entries])
        time_flags = ST.frontier([(per_entry[a]["correct_rate"], per_entry[a]["median_sec"])
                                  for a in entries])
        for a, cf, tf in zip(entries, cost_flags, time_flags):
            per_entry[a]["frontier_cost"] = cf
            per_entry[a]["frontier_time"] = tf
        vs = {}
        for a in entries:
            if a == base:
                continue
            cmp_ = ST.compare(rows_by_entry[a], rows_by_entry[base], mfn, rng)
            if cmp_:
                vs[a] = cmp_
        tasks = sorted({r["task"] for r in rs})
        per_task = {t: {a: [sum(1 for r in rows_by_entry[a] if r["task"] == t and r["ok"]),
                          sum(1 for r in rows_by_entry[a] if r["task"] == t)] for a in entries}
                    for t in tasks}
        summary["groups"][gkey] = {
            "rates": rates, "metric": label, "note": note,
            "baseline": base, "entries": per_entry, "vs_baseline": vs, "per_task": per_task,
        }
    return summary


def _fmt(x, nd=2):
    if x is None:
        return "-"
    if isinstance(x, str):
        return x
    if x == float("inf"):
        return "inf"
    if x != x:
        return "n/a"
    return f"{x:.{nd}f}"


def render(summary, md=False):
    """Text or GitHub markdown rendering of a summary."""
    out = []
    bench = summary["bench"]
    entry_word = "harness" if bench == "harness" else "model"
    out.append(f"ParetoBench {bench} bench, task set {summary['task_set']}, {summary['rows']} rows"
               + (f", pb {summary['pb_version']}" if not md else ""))
    if md:
        out.append("")
        out.append(f"ParetoBench **{bench}** bench. Task set `{summary['task_set']}`, "
                   f"{summary['rows']} rows, pb {summary['pb_version']}. "
                   f"Bootstrap: {summary['bootstrap']['resamples']} resamples of "
                   f"(task, rep) pairs, seed {summary['bootstrap']['seed']}.")
    for gkey, ms in summary["groups"].items():
        label = ms["metric"]
        entries = list(ms["entries"])
        base = ms["baseline"]
        out.append("")
        group_word = "model" if bench == "harness" else "harness"
        out.append(f"{group_word} {gkey}" + (f" ({ms['note']})" if ms.get("note") else ""))
        if label == "weighted tokens":
            out.append("weighted tokens = input 1, cacheRead 0.1, cacheWrite 1.25, output 4 (a proxy, not a price)")
        if md:
            out.append("")
            out.append(f"| {entry_word} | correct | Wilson 95% | uncached input | cached input (read/write) | "
                       f"output | {label} | {label}/correct | list price $ | median s | p90 s | median turns | "
                       f"cost frontier | time frontier |")
            out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
            for a in entries:
                s = ms["entries"][a]
                out.append(
                    f"| {a} | {s['correct']}/{s['total']} | "
                    f"{_fmt(s['wilson95'][0])}-{_fmt(s['wilson95'][1])} | {s['i']:,} | "
                    f"{s['cr']:,}/{s['cw']:,} | {s['o']:,} | {_fmt(s['metric'], 4)} | "
                    f"{_fmt(s['metric_per_correct'], 4)} | {_fmt(s.get('dollars'), 4)} | {_fmt(s['median_sec'], 1)} | "
                    f"{_fmt(s['p90_sec'], 1)} | {_fmt(s['median_turns'], 1)} | "
                    f"{'yes' if s['frontier_cost'] else 'no'} | {'yes' if s['frontier_time'] else 'no'} |")
        else:
            for a in entries:
                s = ms["entries"][a]
                flags = (" [cost frontier]" if s["frontier_cost"] else "") + \
                        (" [time frontier]" if s["frontier_time"] else "")
                out.append(f"  {a:12} correct {s['correct']}/{s['total']} "
                           f"(Wilson 95% {_fmt(s['wilson95'][0])}-{_fmt(s['wilson95'][1])})  "
                           f"uncached in {s['i']:,}  cache r/w {s['cr']:,}/{s['cw']:,}  out {s['o']:,}  "
                           f"{label} {_fmt(s['metric'], 4 if label == 'cost $' else 0)}  "
                           f"per correct {_fmt(s['metric_per_correct'], 4 if label == 'cost $' else 0)}  "
                           + (f"list price ${_fmt(s.get('dollars'), 4)}  " if label != 'cost $' else "") +
                           f"median {_fmt(s['median_sec'], 1)}s  p90 {_fmt(s['p90_sec'], 1)}s  "
                           f"median turns {_fmt(s['median_turns'], 1)}{flags}")
        for a, e in ms["vs_baseline"].items():
            ca, cb = e["correct"]
            p = e["sign_test_p"]
            out.append("")
            head = (f"{a} vs {base}, paired on {e['pairs']} (task, rep) pairs; "
                    f"{a} cheaper in {e['cost_wins']}/{e['pairs']} pairs; "
                    f"correct {ca} vs {cb}" + (f", exact sign test p={_fmt(p, 4)}" if p is not None else ""))
            out.append(head)
            if md:
                out.append("")
                out.append(f"| measure | {a}/{base} | 95% CI |")
                out.append("|---|---|---|")
                for name in ("cost", "total_input", "output", "wall_time"):
                    r = e[name]
                    nm = label if name == "cost" else name
                    out.append(f"| {nm} | {_fmt(r['ratio'])} | {_fmt(r['ci95'][0])}-{_fmt(r['ci95'][1])} |")
                out.append("")
                out.append(f"Verdict: **{e['verdict']}**.")
            else:
                for name in ("cost", "total_input", "output", "wall_time"):
                    r = e[name]
                    nm = label if name == "cost" else name
                    out.append(f"    {nm:15} {_fmt(r['ratio'])}  (95% CI {_fmt(r['ci95'][0])}-{_fmt(r['ci95'][1])})")
                out.append(f"    verdict: {e['verdict']}")
        if md:
            out.append("")
            out.append("| task | " + " | ".join(entries) + " |")
            out.append("|---|" + "---|" * len(entries))
            for t, d in ms["per_task"].items():
                out.append("| " + t + " | " + " | ".join(f"{d[a][0]}/{d[a][1]}" for a in entries) + " |")
        else:
            out.append("")
            out.append("  per-task correct: " + "; ".join(
                t + " " + " ".join(f"{a}={d[a][0]}/{d[a][1]}" for a in entries)
                for t, d in ms["per_task"].items()))
    out.append("")
    return "\n".join(out)


def write_reports(summary, dir_path):
    jp = os.path.join(dir_path, "summary.json")
    mp = os.path.join(dir_path, "summary.md")
    with open(jp, "w") as f:
        json.dump(ST.clean(summary), f, indent=2)
        f.write("\n")
    with open(mp, "w") as f:
        f.write(render(summary, md=True) + "\n")
    return jp, mp
