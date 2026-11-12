#!/usr/bin/env python3
"""Hidden checkers for long-v1. usage: check.py <task> <answer-file>, run with the agent's tree as cwd.

Prints "true" or "false" on stdout and the reason on stderr. Nothing here runs inside the agent's tree:
the tree is copied to a scratch folder, hidden tests and mutants run on the copy, and the expected state
is regenerated from the same seed (the full-tree SHA manifest comes from that pristine regeneration).
The checker lives outside the fixture, so an agent never sees it."""
import ast
import difflib
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.dirname(HERE)
sys.path.insert(0, TASKS)

import gen_fixture  # noqa: E402
import gen_setups  # noqa: E402

IGNORE_DIRS = {"__pycache__", ".pytest_cache"}
IGNORE_FILES = {"ans.txt"}       # the runner writes the final reply here
# dot-directories (harness state) are ignored by manifest(); the checker never looks inside them


# ---- tree helpers -------------------------------------------------------------------------------------

def manifest(root, ignore=()):
    out = {}
    for dp, dns, fns in os.walk(root):
        # harness state folders (dot-directories such as .steak-dsh) are not part of the repository
        dns[:] = sorted(d for d in dns if d not in IGNORE_DIRS and not d.startswith("."))
        for fn in sorted(fns):
            if fn in IGNORE_FILES or fn in ignore or fn.endswith(".pyc"):
                continue
            p = os.path.join(dp, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root).replace(os.sep, "/")] = hashlib.sha256(f.read()).hexdigest()
    return out


def pristine(task):
    d = tempfile.mkdtemp(prefix="pb-pristine-")
    gen_fixture.prepare(d, task)
    return d


def diff(agent, pris, ignore=()):
    a, p = manifest(agent, ignore), manifest(pris, ignore)
    return (sorted(set(a) - set(p)), sorted(set(p) - set(a)),
            sorted(k for k in a if k in p and a[k] != p[k]))


def snapshot(root):
    d = tempfile.mkdtemp(prefix="pb-snap-")
    shutil.copytree(root, d, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "ans.txt"))
    return d


def py(root, args, timeout=300):
    env = {k: v for k, v in os.environ.items() if k not in ("FREIGHT_DATA", "ACME_API_TOKEN")}
    env.update(PYTHONPATH=root, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-B"] + args, cwd=root, env=env, capture_output=True,
                          text=True, timeout=timeout)


def suite(root):
    r = py(root, ["-m", "unittest", "discover", "-s", "tests", "-t", "."])
    return r.returncode == 0, (r.stderr.strip()[-600:])


def hidden(root, *names):
    for name in names:
        shutil.copy(os.path.join(HERE, "hidden", name + ".py"), os.path.join(root, "_hidden_" + name + ".py"))
        r = py(root, ["-m", "unittest", "_hidden_" + name])
        if r.returncode != 0:
            return False, f"hidden tests {name} fail: " + r.stderr.strip()[-500:]
    return True, ""


def read(root, rel):
    with open(os.path.join(root, rel), newline="") as f:
        return f.read()


def pin(agent, pris, modified=(), added=(), added_globs=(), ignore=()):
    """Reason string if the tree differs from pristine anywhere outside the allowed paths, else ''."""
    add, rem, mod = diff(agent, pris, ignore)
    bad_add = [x for x in add if x not in added and not any(re.fullmatch(g, x) for g in added_globs)]
    bad_mod = [x for x in mod if x not in modified]
    if rem or bad_add or bad_mod:
        return f"unexpected changes: removed={rem[:5]} added={bad_add[:5]} modified={bad_mod[:5]}"
    return ""


def test_methods(path):
    try:
        tree = ast.parse(open(path).read())
    except (OSError, SyntaxError):
        return 0
    return sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"))


def all_py(root):
    for rel in sorted(manifest(root)):
        if rel.endswith(".py"):
            yield rel


# ---- L1 ----------------------------------------------------------------------------------------------

def L1(root, ans):
    pr = pristine("L1")
    try:
        why = pin(root, pr, modified={"store/query.py", "api/router.py", "cli/main.py", "docs/api.md"},
                  added={"tests/test_pagination.py"})
        if why:
            return False, why
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    if test_methods(os.path.join(root, "tests/test_pagination.py")) < 4:
        return False, "tests/test_pagination.py needs at least 4 test methods"
    doc = read(root, "docs/api.md")
    if not re.search(r"^##\s+Pagination\s*$", doc, re.M) or not all(k in doc for k in ("next_cursor", "--cursor", "--limit")):
        return False, "docs/api.md needs a '## Pagination' section naming next_cursor, --limit and --cursor"
    snap = snapshot(root)
    try:
        ok, why = suite(snap)
        if not ok:
            return False, "suite fails: " + why
        return hidden(snap, "L1_feature")
    finally:
        shutil.rmtree(snap, ignore_errors=True)


# ---- L2 ----------------------------------------------------------------------------------------------

def L2(root, ans):
    pr = pristine("L2")
    try:
        why = pin(root, pr, modified={"core/pricing.py"})
        if why:
            return False, why
        a = read(root, "core/pricing.py").splitlines()
        b = read(pr, "core/pricing.py").splitlines()
        n = sum(1 for l in difflib.unified_diff(b, a, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---"))
        if n > 4:
            return False, f"fix is not minimal: {n} changed lines (limit 4)"
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    snap = snapshot(root)
    try:
        ok, why = suite(snap)
        if not ok:
            return False, "suite fails: " + why
        return hidden(snap, "L2_boundaries")
    finally:
        shutil.rmtree(snap, ignore_errors=True)


# ---- L3 ----------------------------------------------------------------------------------------------

L3_FOUR = ["store/skus.py", "api/skus.py", "ingest/skus.py", "cli/skus.py"]


def L3(root, ans):
    pr = pristine("L3")
    try:
        why = pin(root, pr, modified=set(L3_FOUR), added={"core/skus.py"})
        if why:
            return False, why
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    holders = []
    for rel in all_py(root):
        try:
            tree = ast.parse(read(root, rel))
        except SyntaxError as e:
            return False, f"{rel} does not parse: {e}"
        if any(isinstance(n, ast.Constant) and n.value == "[^A-Z0-9]+" for n in ast.walk(tree)):
            holders.append(rel)
    if holders != ["core/skus.py"]:
        return False, f"the SKU pattern must live only in core/skus.py, found in {holders}"
    for rel in L3_FOUR:
        tree = ast.parse(read(root, rel))
        uses = False
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and (n.module == "core.skus" or (n.module == "core" and any(a.name == "skus" for a in n.names))):
                uses = True
            if isinstance(n, ast.Import) and any(a.name == "core.skus" for a in n.names):
                uses = True
        if not uses:
            return False, f"{rel} does not use core.skus"
    snap = snapshot(root)
    try:
        ok, why = suite(snap)
        if not ok:
            return False, "suite fails: " + why
        return hidden(snap, "L3_behaviour")
    finally:
        shutil.rmtree(snap, ignore_errors=True)


# ---- L4 (read-only, exact answers) ------------------------------------------------------------------------

def parse_answers(text, pattern):
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(pattern, line)
        if m:
            cur = m.group(1)
            out[cur] = m.group(2)
        elif cur:
            out[cur] += " " + line
    return out


def first_int(s):
    m = re.search(r"-?\d[\d,]*", s or "")
    return int(m.group(0).replace(",", "")) if m else None


def l4_expected(pr):
    exp = {}
    defs, calls = [], set()
    for rel in all_py(pr):
        tree = ast.parse(read(pr, rel))
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name == "reconcile_manifest":
                defs.append(rel)
            if isinstance(n, ast.Call):
                f = n.func
                if (isinstance(f, ast.Name) and f.id == "legacy_checksum") or \
                        (isinstance(f, ast.Attribute) and f.attr == "legacy_checksum"):
                    calls.add(f"{rel}:{n.lineno}")
    exp["Q1"] = defs
    cfg = ast.parse(read(pr, "core/config.py"))
    exp["Q2"] = next(n.value.value for n in cfg.body if isinstance(n, ast.Assign) and n.targets[0].id == "DEFAULT_RETRY_LIMIT")
    exp["Q3"] = calls
    q4 = q5 = 0
    for line in read(pr, "logs/access.log").splitlines():
        ts, method, path, status, nbytes, ms = line.split()
        if path == "/v2/orders" and status == "503" and ts.startswith("2025-03-02"):
            q4 += 1
        if path == "/v2/export" and status == "200":
            q5 += int(nbytes)
    exp["Q4"], exp["Q5"] = q4, q5
    return exp


def L4(root, ans):
    pr = pristine("L4")
    try:
        add, rem, mod = diff(root, pr)
        if add or rem or mod:
            return False, f"read-only task changed the tree: added={add[:5]} removed={rem[:5]} modified={mod[:5]}"
        exp = l4_expected(pr)
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    a = parse_answers(ans, r"\s*[*_`]*Q([1-5])[*_`]*\s*[:=]\s*(.*)$")
    miss = [k for k in ("Q1", "Q2", "Q3", "Q4", "Q5") if k[1] not in a]
    if miss:
        return False, f"answer lines missing: {miss}"
    paths = lambda s: {m.lstrip("./") if m.startswith("./") else m for m in re.findall(r"[\w./-]+\.py", s)}
    if paths(a["1"]) != set(exp["Q1"]):
        return False, f"Q1 expected {exp['Q1']}, got {a['1'][:80]!r}"
    if first_int(a["2"]) != exp["Q2"]:
        return False, f"Q2 expected {exp['Q2']}, got {a['2'][:40]!r}"
    got3 = {f"{p.lstrip('./') if p.startswith('./') else p}:{n}" for p, n in re.findall(r"([\w./-]+\.py):(\d+)", a["3"])}
    if got3 != exp["Q3"]:
        return False, f"Q3 expected {sorted(exp['Q3'])}, got {sorted(got3)}"
    for k in ("Q4", "Q5"):
        if first_int(a[k[1]]) != exp[k]:
            return False, f"{k} expected {exp[k]}, got {a[k[1]][:40]!r}"
    return True, ""


# ---- L5 (mutation-judged tests) ---------------------------------------------------------------------------

MUTANTS = [  # (old, new): each must occur exactly once in core/pricing.py
    ("        if qty >= min_qty:", "        if qty > min_qty:"),
    ("if twice > denominator or", "if twice >= denominator or"),
    ("(twice == denominator and q % 2 == 1)", "(twice == denominator and q % 2 == 0)"),
    ("or qty < 1:", "or qty < 0:"),
    ("discount = round_half_even(gross * pct, 100)", "discount = gross * pct // 100"),
    ("round_half_even(amount * 10000, 10000 + rate_bp)", "round_half_even(amount * 10000, 10000)"),
    ("started = -(-extra // 100)", "started = extra // 100"),
    ("extra = max(0, weight_g - 500)", "extra = max(0, weight_g - 400)"),
    ("    if weight_g <= 0:", "    if weight_g < 0:"),
    ("return min(coupon_cents, subtotal * max_pct // 100)", "return max(coupon_cents, subtotal * max_pct // 100)"),
    ("shipping = 0 if subtotal >= config.FREE_SHIPPING_CENTS", "shipping = 0 if subtotal > config.FREE_SHIPPING_CENTS"),
    ('"national": (900, 4)', '"national": (900, 5)'),
]
L5_NEEDED = 10
L5_TEST = "tests/test_pricing_suite.py"


def L5(root, ans):
    pr = pristine("L5")
    try:
        why = pin(root, pr, added={L5_TEST})
        if why:
            return False, why
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    src = read(root, L5_TEST)
    tree = ast.parse(src)
    for n in ast.walk(tree):
        names = [a.name.split(".")[0] for a in n.names] if isinstance(n, ast.Import) else \
            [(n.module or "").split(".")[0]] if isinstance(n, ast.ImportFrom) else []
        if {"inspect", "hashlib", "ast", "linecache", "importlib"} & set(names):
            return False, "the test module may not inspect source code"
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and ("pricing.py" in n.value or "core/" in n.value):
            return False, "the test module may not read the source file"
        if isinstance(n, ast.Name) and n.id == "__file__":
            return False, "the test module may not read files"
    if test_methods(os.path.join(root, L5_TEST)) < 8:
        return False, "at least 8 test methods are required"
    snap = snapshot(root)
    try:
        r = py(snap, ["-m", "unittest", "tests.test_pricing_suite"])
        if r.returncode != 0:
            return False, "the new tests fail on the unmodified code: " + r.stderr.strip()[-400:]
        original = read(snap, "core/pricing.py")
        killed = 0
        for old, new in MUTANTS:
            if original.count(old) != 1:
                return False, f"checker bug: mutant anchor not unique: {old!r}"
            with open(os.path.join(snap, "core/pricing.py"), "w", newline="") as f:
                f.write(original.replace(old, new))
            if py(snap, ["-m", "unittest", "tests.test_pricing_suite"]).returncode != 0:
                killed += 1
        with open(os.path.join(snap, "core/pricing.py"), "w", newline="") as f:
            f.write(original)
        if killed < L5_NEEDED:
            return False, f"only {killed} of {len(MUTANTS)} mutants killed, need {L5_NEEDED}"
        return True, ""
    finally:
        shutil.rmtree(snap, ignore_errors=True)


# ---- L6 (compaction stress) -------------------------------------------------------------------------------

class _Migrate(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "put_legacy":
            node.func.attr = "put"
            node.keywords.append(ast.keyword(arg="validate", value=ast.Constant(True)))
        return node


def l6_facts(pr):
    rows = [dict(kv.split("=", 1) for kv in line.split()[1:]) | {"date": line.split()[0]}
            for line in read(pr, "data/q3_ledger_report.txt").splitlines()]
    f1 = sum(int(r["amount"]) for r in rows if r["region"] == "EU" and r["kind"] == "invoice"
             and r["status"] == "posted" and r["date"].startswith("2025-08"))
    f2 = len({r["acct"] for r in rows if r["kind"] == "refund" and r["status"] == "posted"})
    f3 = max(int(r["amount"]) for r in rows if r["kind"] == "credit" and r["region"] == "APAC")
    f4 = sum(1 for r in rows if r["status"] == "disputed")
    tot = {}
    for r in rows:
        if r["region"] == "NA" and r["kind"] == "invoice" and r["status"] == "posted":
            tot[r["acct"]] = tot.get(r["acct"], 0) + int(r["amount"])
    f5 = sorted(tot.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return {"1": f1, "2": f2, "3": f3, "4": f4, "5": f5}


def L6(root, ans):
    pr = pristine("L6")
    try:
        facts = l6_facts(pr)
        add, rem, mod = diff(root, pr)
        if add or rem != ["data/q3_ledger_report.txt"]:
            return False, f"expected only the report removed: added={add[:5]} removed={rem[:5]}"
        pm = manifest(pr)
        for rel in mod:
            if not rel.endswith(".py"):
                return False, f"non-Python file changed: {rel}"
        migrated = 0
        for rel in sorted(pm):
            if not rel.endswith(".py"):
                continue
            expected = ast.dump(_Migrate().visit(ast.parse(read(pr, rel))))
            try:
                got = ast.dump(ast.parse(read(root, rel)))
            except SyntaxError as e:
                return False, f"{rel} does not parse: {e}"
            if got != expected:
                return False, f"{rel} is not the expected migration of put_legacy calls"
            migrated += rel in mod
        if migrated < 40:
            return False, f"only {migrated} files migrated"
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    got = parse_answers(ans, r"\s*[*_`]*F([1-5])[*_`]*\s*[:=]\s*(.*)$")
    for k in "1234":
        if first_int(got.get(k)) != facts[k]:
            return False, f"F{k} expected {facts[k]}, got {got.get(k, '')[:40]!r}"
    if facts["5"] not in got.get("5", ""):
        return False, f"F5 expected {facts['5']}, got {got.get('5', '')[:40]!r}"
    snap = snapshot(root)
    try:
        ok, why = suite(snap)
        return (ok, "suite fails: " + why if not ok else "")
    finally:
        shutil.rmtree(snap, ignore_errors=True)


# ---- L7 -------------------------------------------------------------------------------------------------

def L7(root, ans):
    pr = pristine("L7")
    try:
        why = pin(root, pr, modified={"cli/main.py", "docs/api.md"},
                  added={"core/retry.py", "core/ratelimit.py"}, added_globs=[r"tests/test_[\w]+\.py"])
        if why:
            return False, why
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    snap = snapshot(root)
    try:
        ok, why = suite(snap)
        if not ok:
            return False, "suite fails: " + why
        return hidden(snap, "L7_codegen")
    finally:
        shutil.rmtree(snap, ignore_errors=True)


# ---- L8 -------------------------------------------------------------------------------------------------

def L8(root, ans):
    pr = pristine("L8")
    try:
        why = pin(root, pr, modified={"store/memory.py", "plugins/registry.py", "cli/main.py", "docs/api.md"},
                  added={"ingest/windows.py"}, added_globs=[r"tests/test_[\w]+\.py"])
        if why:
            return False, why
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    snap = snapshot(root)
    try:
        ok, why = suite(snap)
        if not ok:
            return False, "suite fails: " + why
        return hidden(snap, "L8_ingest", "L8_store", "L8_plugins", "L8_cli")
    finally:
        shutil.rmtree(snap, ignore_errors=True)


# ---- L9 -------------------------------------------------------------------------------------------------

L9_EDITS = [
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


def L9(root, ans):
    pr = pristine("L9")
    try:
        files = {}
        for rel, old, new in L9_EDITS:
            files.setdefault(rel, read(pr, rel))
            if files[rel].count(old) != 1:
                return False, f"checker bug: anchor not unique in {rel}: {old!r}"
            files[rel] = files[rel].replace(old, new)
        why = pin(root, pr, modified=set(files))
        if why:
            return False, why
        for rel, text in files.items():
            if read(root, rel) != text:
                return False, f"{rel} is not exactly the requested edit"
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    snap = snapshot(root)
    try:
        ok, why = suite(snap)
        return (ok, "suite fails: " + why if not ok else "")
    finally:
        shutil.rmtree(snap, ignore_errors=True)


# ---- L10 ------------------------------------------------------------------------------------------------

def L10(root, ans):
    pr = pristine("L10")
    try:
        why = pin(root, pr, modified={"store/index.py"}, ignore={".verify_state"})
        if why:
            return False, why
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    import json
    try:
        st = json.loads(read(root, ".verify_state"))
    except (OSError, ValueError):
        return False, "scripts/verify.py was never run"
    if st.get("last") != 0 or st.get("runs", 0) < 3:
        return False, f"the check command did not end green: {st}"
    snap = snapshot(root)
    try:
        ok, why = suite(snap)
        if not ok:
            return False, "suite fails: " + why
        return hidden(snap, "L10_index")
    finally:
        shutil.rmtree(snap, ignore_errors=True)


# ---- L11 ------------------------------------------------------------------------------------------------

def L11(root, ans):
    import json
    pr = pristine("L11")
    try:
        why = pin(root, pr, modified={"ingest/reports.py", "cli/main.py", "docs/api.md", "tests/golden/summary.json"},
                  added={"tests/test_error_rate.py"})
        if why:
            return False, "part 1-5 scope: " + why
        log = [l.split() for l in read(pr, "logs/access.log").splitlines()]
    finally:
        shutil.rmtree(pr, ignore_errors=True)
    counts = {}
    paths = {}
    for ts, method, path, status, nbytes, ms in log:
        counts[status] = counts.get(status, 0) + 1
        paths[path] = paths.get(path, 0) + 1
    want = {"status_counts": counts,
            "top_paths": [list(p) for p in sorted(paths.items(), key=lambda kv: (-kv[1], kv[0]))[:5]],
            "error_rate": round(sum(1 for r in log if int(r[3]) >= 500) / len(log), 4)}
    try:
        got = json.loads(read(root, "tests/golden/summary.json"))
    except (OSError, ValueError):
        return False, "part 5: tests/golden/summary.json missing or invalid"
    if got != want:
        return False, "part 5: tests/golden/summary.json was not regenerated from the current code"
    doc = read(root, "docs/api.md")
    if not re.search(r"^##\s+Error rate\s*$", doc, re.M | re.I) or "error-rate" not in doc:
        return False, "part 3: docs/api.md needs a '## Error rate' section naming error-rate"
    if test_methods(os.path.join(root, "tests/test_error_rate.py")) < 3:
        return False, "part 4: tests/test_error_rate.py needs at least 3 test methods"
    snap = snapshot(root)
    try:
        ok, why = suite(snap)
        if not ok:
            return False, "suite fails: " + why
        return hidden(snap, "L11_parts")
    finally:
        shutil.rmtree(snap, ignore_errors=True)


CHECKS = {f"L{i}": globals()[f"L{i}"] for i in range(1, 12)}


def main():
    task = sys.argv[1]
    ans = ""
    if len(sys.argv) > 2 and os.path.isfile(sys.argv[2]):
        with open(sys.argv[2], errors="replace") as f:
            ans = f.read()
    root = os.getcwd()
    try:
        ok, why = CHECKS[task](root, ans)
    except Exception as e:  # a missing file or crash in an agent's tree is a failed check, with the reason
        ok, why = False, f"{type(e).__name__}: {e}"
    print("true" if ok else "false")
    if not ok:
        print(why, file=sys.stderr)


if __name__ == "__main__":
    main()
