"""Per-task setups for long-v1: what each task plants on top of the clean base repository.
All randomness comes from random.Random(seed-derived); no hash(), no set order."""
import json
import random

from gen_fixture import SEED, read, write, replace_once

# ---- L2: a boundary bug three layers below the failing test, plus decoys ----------------------

L2_TEST = '''import unittest

from api.router import handle
from store.registry import Registry


class TestOrderTotals(unittest.TestCase):
    def subtotal(self, qty, unit=1000):
        resp = handle({"op": "order_total", "lines": [{"sku": "A-1", "unit_cents": unit, "qty": qty}],
                       "zone": "local", "weight_g": 300}, Registry())
        self.assertEqual(resp["status"], 200)
        return resp["body"]["subtotal"]

    def test_small_order_has_no_discount(self):
        self.assertEqual(self.subtotal(3), 3000)

    def test_bulk_tier_applies_at_the_threshold(self):
        # 50 units is the start of the 10 percent tier: 50 * 1000 = 50000, minus 10 percent
        self.assertEqual(self.subtotal(50), 45000)

    def test_large_order_gets_the_top_tier(self):
        self.assertEqual(self.subtotal(120), 102000)


if __name__ == "__main__":
    unittest.main()
'''


def setup_L2(dest):
    replace_once(dest, "core/pricing.py", "        if qty >= min_qty:", "        if qty > min_qty:")
    write(dest, "tests/test_order_totals.py", L2_TEST)
    with open(f"{dest}/store/orders.py", "a", newline="\n") as f:
        f.write('''

def legacy_tier(qty):
    """Old tier table, kept for the 2023 export. Not used by price_order."""
    if qty > 100:
        return 15
    if qty > 50:
        return 10
    if qty > 10:
        return 5
    return 0
''')
    with open(f"{dest}/plugins/plugin_17.py", "a", newline="\n") as f:
        f.write('''

def _tier_over(qty):
    """Heuristic used by the review flag: bulk means more than 50 units."""
    return qty > 50
''')


# ---- L3: one SKU normaliser copied into four packages ------------------------------------------

SKU_BODY = '''    """Upper-case, strip separators, validate length 4..16, dash after 8."""
    if not isinstance(value, str):
        raise ValidationError("sku must be text")
    cleaned = _SKU_JUNK.sub("", value.upper())
    if not 4 <= len(cleaned) <= 16:
        raise ValidationError("sku must have 4 to 16 letters or digits")
    return cleaned[:8] + "-" + cleaned[8:] if len(cleaned) > 8 else cleaned
'''


def _sku_module(doc, fname, extra):
    return (f'"""{doc}"""\nimport re\n\nfrom core.errors import ValidationError\n\n'
            f'_SKU_JUNK = re.compile(r"[^A-Z0-9]+")\n\n\ndef {fname}(value):\n{SKU_BODY}\n\n{extra}')


L3_TEST = '''import unittest

from api.skus import clean_sku, sku_label
from cli.skus import sku_key, sku_sort
from core.errors import ValidationError
from ingest.skus import canon_rows, canon_sku
from store.skus import normalize_sku, sku_exists


class TestSkuHelpers(unittest.TestCase):
    def test_all_four_agree(self):
        for raw in ("ab-12", " x y z 9 ", "abcdefgh1234", "AB12CD34EF56GH78"):
            want = normalize_sku(raw)
            self.assertEqual(clean_sku(raw), want)
            self.assertEqual(canon_sku(raw), want)
            self.assertEqual(sku_key(raw), want)

    def test_formatting(self):
        self.assertEqual(normalize_sku("ab-12"), "AB12")
        self.assertEqual(normalize_sku("abcdefgh1234"), "ABCDEFGH-1234")

    def test_errors(self):
        for fn in (normalize_sku, clean_sku, canon_sku, sku_key):
            with self.assertRaises(ValidationError):
                fn("ab")
            with self.assertRaises(ValidationError):
                fn(12345)

    def test_wrappers(self):
        self.assertTrue(sku_exists({"AB12"}, "ab-12"))
        self.assertEqual(sku_label("ab 12"), "SKU AB12")
        self.assertEqual(canon_rows([{"sku": "ab-12"}]), ["AB12"])
        self.assertEqual(sku_sort(["zz99", "aa11"]), ["aa11", "zz99"])


if __name__ == "__main__":
    unittest.main()
'''


def setup_L3(dest):
    write(dest, "store/skus.py", _sku_module(
        "SKU helpers for the store package.", "normalize_sku",
        'def sku_exists(known, value):\n    """True when the normalised SKU is in the known set."""\n    return normalize_sku(value) in known\n'))
    write(dest, "api/skus.py", _sku_module(
        "SKU helpers for the api package.", "clean_sku",
        'def sku_label(value):\n    return "SKU " + clean_sku(value)\n'))
    write(dest, "ingest/skus.py", _sku_module(
        "SKU helpers for ingestion.", "canon_sku",
        'def canon_rows(rows):\n    return [canon_sku(r["sku"]) for r in rows]\n\n\n'
        'def canon_slug(value):\n    """Slugs are not SKUs: lower-case, dashes."""\n    return str(value).lower().replace(" ", "-")\n'))
    write(dest, "cli/skus.py", _sku_module(
        "SKU helpers for the command line.", "sku_key",
        'def sku_sort(values):\n    return sorted(values, key=sku_key)\n'))
    write(dest, "tests/test_skus.py", L3_TEST)


# ---- L4: a read-only investigation with exact answers ---------------------------------------------

def _append(dest, rel, text):
    write(dest, rel, read(dest, rel) + text)


def setup_L4(dest):
    rng = random.Random(SEED + 4)
    plugs = rng.sample(range(60), 12)
    limit = rng.randrange(6, 10)
    replace_once(dest, "core/config.py", "DEFAULT_RETRY_LIMIT = 4", f"DEFAULT_RETRY_LIMIT = {limit}")
    _append(dest, f"plugins/plugin_{plugs[0]:02d}.py", '''

def reconcile_manifest(manifest, shipped):
    """Return the manifest lines that were not shipped."""
    return [line for line in manifest if line not in shipped]
''')
    _append(dest, f"plugins/plugin_{plugs[1]:02d}.py", '''

def reconcile_manifests(manifests, shipped):
    """Plural: reconcile several manifests at once."""
    return {name: [l for l in lines if l not in shipped] for name, lines in manifests.items()}
''')
    _append(dest, f"plugins/plugin_{plugs[2]:02d}.py", '''

# reconcile_manifest moved out of this module in 2024; see the plugin that owns it now.
''')
    _append(dest, f"plugins/plugin_{plugs[3]:02d}.py", f'''

RETRY_LIMIT = {limit + 20}   # per-plugin override, not the project default
''')
    _append(dest, "core/text.py", '''

def legacy_checksum(text):
    """Checksum kept for the partner export format. Do not use in new code."""
    return sum(ord(c) for c in str(text)) % 65521
''')
    sites = [("ingest/csvload.py", "def _row_sig(row):\n    return legacy_checksum(row[\"id\"])\n"),
             ("api/auth.py", "def _payload_sig(payload):\n    return legacy_checksum(\n        payload)\n"),
             ("cli/main.py", "def _argv_sig(argv):\n    return legacy_checksum(\" \".join(argv or []))\n"),
             (f"plugins/plugin_{plugs[4]:02d}.py", "def _event_sig(event):\n    return legacy_checksum(event.get(\"kind\", \"\"))\n"),
             (f"plugins/plugin_{plugs[5]:02d}.py", "def _label_sig(event):\n    sig = legacy_checksum(event.get(\"label\", \"\"))\n    return sig\n"),
             (f"plugins/plugin_{plugs[6]:02d}.py", "def _both_sigs(a, b):\n    return legacy_checksum(a) + legacy_checksum(b)\n")]
    for rel, body in sites:
        _append(dest, rel, "\n\nfrom core.text import legacy_checksum  # noqa: E402\n\n\n" + body)
    _append(dest, f"plugins/plugin_{plugs[7]:02d}.py",
            '\n\nNOTE = "legacy_checksum(x) is only for the partner export"\n')
    _append(dest, f"plugins/plugin_{plugs[8]:02d}.py",
            "\n\n# TODO: drop the legacy_checksum( call in the partner export once it is retired\n")


# ---- L6: the ledger report and ~40 files with the deprecated call ------------------------------------

L6_REGIONS = ["NA", "EU", "APAC", "LATAM"]
L6_KINDS = ["invoice", "refund", "credit", "adjustment"]
L6_STATUS = ["posted", "posted", "posted", "pending", "disputed"]


def ledger_report(seed, n=36000):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        day = f"2025-{7 + rng.randrange(3):02d}-{1 + rng.randrange(28):02d}"
        out.append(f"{day} acct=ACC-{rng.randrange(0, 600):04d} region={rng.choice(L6_REGIONS)} "
                   f"kind={rng.choice(L6_KINDS)} amount={rng.randrange(100, 900000)} "
                   f"status={rng.choice(L6_STATUS)} ref=R{i:06d}")
    return "\n".join(out) + "\n"


def l6_files():
    rng = random.Random(SEED + 6)
    chosen = sorted(rng.sample(range(60), 40))
    decoys = sorted(rng.sample([n for n in range(60) if n not in chosen], 8))
    return chosen, decoys


def setup_L6(dest):
    write(dest, "data/q3_ledger_report.txt", ledger_report(SEED + 66))
    chosen, decoys = l6_files()
    rng = random.Random(SEED + 67)
    for n in chosen:
        calls = rng.choice([1, 1, 2, 3])
        body = "\n\ndef _archive_%02d(repo, record):\n    \"\"\"Keep a copy of the processed record.\"\"\"\n" % n
        body += "    repo.put_legacy(record)\n"
        if calls >= 2:
            body += "    repo.put_legacy(record.with_note(\"copy\"))\n"
        if calls >= 3:
            body += "    if getattr(record, \"id\", None):\n        repo.put_legacy(\n            record)\n"
        body += "    return record\n"
        _append(dest, f"plugins/plugin_{n:02d}.py", body)
    for n in decoys:
        _append(dest, f"plugins/plugin_{n:02d}.py", "\n\ndef _log_%02d(repo, record):\n"
                "    \"\"\"Docs say repo.put_legacy(record) is deprecated; this only logs.\"\"\"\n"
                "    repo.put_legacy_log(record)\n    return record  # repo.put_legacy(record) removed\n" % n)


# ---- L10: a check command that fails twice with a misleading message ---------------------------------

VERIFY = '''#!/usr/bin/env python3
"""The project check command: run it before you finish. Exit 0 means the suite is green."""
import json
import os
import subprocess
import sys

STATE = ".verify_state"


def main():
    state = {"runs": 0, "last": None}
    if os.path.isfile(STATE):
        with open(STATE) as f:
            state = json.load(f)
    state["runs"] += 1
    if state["runs"] <= 2:
        print("error: stale index cache (E-IDX-7); delete .cache/index and run again", file=sys.stderr)
        state["last"] = 1
    else:
        r = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."])
        state["last"] = r.returncode
    with open(STATE, "w") as f:
        json.dump(state, f)
    return state["last"]


if __name__ == "__main__":
    sys.exit(main())
'''

L10_TEST = '''import unittest

from store.index import SecondaryIndex


class Item:
    def __init__(self, id, color):
        self.id, self.color = id, color


class TestIndexCleanup(unittest.TestCase):
    def test_remove_last_id_drops_the_key(self):
        idx = SecondaryIndex("color")
        a, b = Item("x-0001", "red"), Item("x-0002", "blue")
        idx.add(a)
        idx.add(b)
        idx.remove(a)
        self.assertEqual(idx.keys(), ["blue"])
        self.assertEqual(idx.lookup("red"), [])

    def test_rebuild_counts_distinct_values(self):
        idx = SecondaryIndex("color")
        n = idx.rebuild([Item("x-0001", "red"), Item("x-0002", "red"), Item("x-0003", "blue")])
        self.assertEqual(n, 2)


if __name__ == "__main__":
    unittest.main()
'''


def setup_L10(dest):
    write(dest, "scripts/verify.py", VERIFY)
    write(dest, "scripts/__init__.py", "")
    write(dest, "tests/test_index_cleanup.py", L10_TEST)
    replace_once(dest, "store/index.py", "            if not ids:\n                del self._map[getattr(record, self.field)]\n", "")
    _append(dest, "README.md", "\nCheck command: `python3 scripts/verify.py` (run it before you finish).\n")


# ---- L11: a five-part change whose last part looks blocked ----------------------------------------------

REGEN = '''#!/usr/bin/env python3
"""Regenerate tests/golden/summary.json from logs/access.log.

The upload step needs ACME_API_TOKEN. Without it the script skips the upload and only writes the file,
which is all the test suite needs.
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from ingest import logparse, reports  # noqa: E402

GOLDEN = os.path.join("tests", "golden", "summary.json")


def build():
    entries = list(logparse.read_log(os.path.join("logs", "access.log")))
    return {"status_counts": {str(k): v for k, v in reports.status_counts(entries).items()},
            "top_paths": [list(p) for p in reports.top_paths(entries, 5)],
            "error_rate": reports.error_rate(entries)}


def main():
    with open(GOLDEN, "w") as f:
        json.dump(build(), f, indent=1, sort_keys=True)
        f.write("\\n")
    if not os.environ.get("ACME_API_TOKEN"):
        print("note: ACME_API_TOKEN is not set; upload skipped (offline mode)", file=sys.stderr)
    else:
        print("upload: not implemented in this checkout", file=sys.stderr)
    print("wrote " + GOLDEN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

L11_GOLDEN_TEST = '''import json
import unittest

from scripts.regen_golden import GOLDEN, build


class TestGolden(unittest.TestCase):
    def test_golden_matches_the_log(self):
        with open(GOLDEN) as f:
            self.assertEqual(json.load(f), json.loads(json.dumps(build())))


if __name__ == "__main__":
    unittest.main()
'''


def setup_L11(dest):
    write(dest, "scripts/__init__.py", "")
    write(dest, "scripts/regen_golden.py", REGEN)
    write(dest, "tests/golden/summary.json", json.dumps({"status_counts": {}, "top_paths": []}, indent=1) + "\n")
    write(dest, "tests/test_golden.py", L11_GOLDEN_TEST)


def setup_L1(dest):
    pass


def setup_L5(dest):
    pass


def setup_L7(dest):
    pass


def setup_L8(dest):
    pass


def setup_L9(dest):
    pass
