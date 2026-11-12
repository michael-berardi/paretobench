"""Bulk generation for the long-v1 fixture: entity models, handlers, commands, tests, plugins,
parsers and the large data files. Everything is a pure function of the seed (random.Random only,
no hash(), no set iteration order), so two generations are byte-identical."""
import json
import os
import random

ENTITIES = [  # (name, id prefix)
    ("customer", "cus"), ("supplier", "sup"), ("warehouse", "war"), ("product", "pro"),
    ("shipment", "shi"), ("carrier", "car"), ("invoice", "inv"), ("payment", "pay"),
    ("refund", "ref"), ("ticket", "tic"), ("contract", "con"), ("route", "rou"),
    ("depot", "dep"), ("vehicle", "veh"), ("driver", "dri"), ("pallet", "pal"),
    ("container", "ctn"), ("manifest", "man"), ("claim", "cla"), ("quote", "quo"),
    ("surcharge", "sur"), ("tariff", "tar"), ("inspection", "ins"), ("rma", "rma"),
]
FIELD_POOL = {
    "str": ["name", "label", "notes", "contact", "address", "city", "reference"],
    "int": ["qty", "count", "weight_g", "capacity", "priority"],
    "cents": ["amount_cents", "fee_cents", "deposit_cents"],
    "bool": ["active", "insured", "fragile"],
    "enum": {"status": ["open", "closed", "hold"], "tier": ["gold", "silver", "bronze"],
             "mode": ["road", "rail", "air", "sea"]},
    "date": ["opened", "due", "issued"],
    "slug": ["code", "handle"],
}


def w(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        f.write(text)


def sample_value(kind, name, i, choices=None):
    if kind == "str":
        return f"{name.title()} {i}"
    if kind == "int":
        return i % 50 + 1
    if kind == "cents":
        return 100 * (i % 90 + 1)
    if kind == "bool":
        return i % 2 == 0
    if kind == "enum":
        return choices[i % len(choices)]
    if kind == "date":
        return f"2025-{i % 12 + 1:02d}-{i % 28 + 1:02d}"
    if kind == "slug":
        return f"{name}-{i}"
    raise ValueError(kind)


def pick_fields(rng):
    """4 to 7 distinct fields: (name, kind, choices)."""
    kinds = ["str", "str", "int", "cents", "bool", "enum", "date", "slug", "int"]
    n = rng.randrange(4, 8)
    out, used = [], set()
    tries = 0
    while len(out) < n and tries < 100:
        tries += 1
        kind = rng.choice(kinds)
        if kind == "enum":
            name = rng.choice(sorted(FIELD_POOL["enum"]))
            choices = FIELD_POOL["enum"][name]
        else:
            name = rng.choice(FIELD_POOL[kind])
            choices = None
        if name in used:
            continue
        used.add(name)
        out.append((name, kind, choices))
    if not any(k == "str" for _, k, _ in out):
        out[0] = ("name", "str", None)
    return out


def check_lines(name, kind, choices):
    if kind in ("str", "slug"):
        lines = [f"        if self.{name} is not None and not isinstance(self.{name}, str):",
                 f"            raise ValidationError(\"{{kind}}: {name} must be text\".format(kind=self.kind))"]
        if kind == "str":
            lines += [f"        if self.{name} is not None and len(self.{name}) > 80:",
                      f"            raise ValidationError(\"{{kind}}: {name} is longer than 80 characters\".format(kind=self.kind))"]
        else:
            lines += [f"        if self.{name} is not None and not re.match(r\"^[a-z0-9-]+$\", self.{name}):",
                      f"            raise ValidationError(\"{{kind}}: {name} must be a slug\".format(kind=self.kind))"]
        return lines
    if kind in ("int", "cents"):
        return [f"        if self.{name} is not None and (not isinstance(self.{name}, int) or self.{name} < 0):",
                f"            raise ValidationError(\"{{kind}}: {name} must be a non-negative integer\".format(kind=self.kind))"]
    if kind == "bool":
        return [f"        if self.{name} is not None and not isinstance(self.{name}, bool):",
                f"            raise ValidationError(\"{{kind}}: {name} must be true or false\".format(kind=self.kind))"]
    if kind == "enum":
        return [f"        if self.{name} is not None and self.{name} not in {name.upper()}_CHOICES:",
                f"            raise ValidationError(self.kind + \": {name} must be one of \" + \", \".join({name.upper()}_CHOICES))"]
    if kind == "date":
        return [f"        if self.{name} is not None and not re.match(r\"^\\d{{4}}-\\d{{2}}-\\d{{2}}$\", self.{name}):",
                f"            raise ValidationError(self.kind + \": {name} must be a date like 2025-03-04\")"]
    raise ValueError(kind)


def model_source(ename, prefix, fields, rng):
    cls = ename.title()
    names = [f[0] for f in fields]
    req = names[:2]
    enums = [(n, c) for n, k, c in fields if k == "enum"]
    out = [f'"""{cls} records: {rng.choice(["tracked", "billed", "scheduled", "audited", "reconciled"])} '
           f'{rng.choice(["by the desk", "per site", "per account", "per lane"])}."""', "import re", "",
           "from core.errors import ValidationError", "from store.records import Record", ""]
    for n, c in enums:
        out.append(f"{n.upper()}_CHOICES = {tuple(c)!r}")
    if enums:
        out.append("")
    out += ["", f"class {cls}(Record):", f'    kind = "{ename}"', f'    prefix = "{prefix}"',
            "    fields = (" + ", ".join(f'("{n}", "{k}")' for n, k, _ in fields) + ",)",
            f"    required = {tuple(req)!r}", "", "    @classmethod", "    def sample(cls, i):",
            "        \"\"\"A valid field dict for the i-th record (used by tests and seed data).\"\"\"", "        return {"]
    for n, k, c in fields:
        if k == "str":
            e = f'"{n.title()} {{}}".format(i)'
        elif k == "int":
            e = "i % 50 + 1"
        elif k == "cents":
            e = "100 * (i % 90 + 1)"
        elif k == "bool":
            e = "i % 2 == 0"
        elif k == "enum":
            e = f"{n.upper()}_CHOICES[i % len(" + f"{n.upper()}_CHOICES)]"
        elif k == "date":
            e = 'f"2025-{i % 12 + 1:02d}-{i % 28 + 1:02d}"'
        else:
            e = f'"{n}-{{}}".format(i)'
        out.append(f'            "{n}": {e},')
    out += ["        }", "", "    def validate(self):", "        super().validate()"]
    for n, k, c in fields:
        out += check_lines(n, k, c)
    out += ["        return self", "", "    def summary(self):"]
    show = names[:3]
    out.append('        return f"{self.id} ' + " ".join("{self." + n + "}" for n in show) + '"')
    out.append("")
    ints = [n for n, k, _ in fields if k in ("int", "cents")]
    bools = [n for n, k, _ in fields if k == "bool"]
    if ints:
        out += [f"    def is_empty_{ints[0]}(self):", f"        return not self.{ints[0]}", ""]
    if bools:
        out += [f"    def is_{bools[0]}(self):", f"        return bool(self.{bools[0]})", ""]
    if enums:
        n = enums[0][0]
        out += [f"    def with_{n}(self, value):",
                f"        data = self.to_dict()", f"        data[\"{n}\"] = value",
                f"        return type(self).from_dict(data).validate()", ""]
    out += ["", f"def new_{ename}(n, **overrides):",
            f'    """Build the n-th {ename} from sample data, with overrides."""',
            f"    values = {cls}.sample(n)", "    values.update(overrides)",
            f'    return {cls}(f"{prefix}-{{n:04d}}", **values)', "",
            "", f"def describe(record):", f'    """One line for lists and logs."""',
            "    return record.summary()", ""]
    return "\n".join(out)


def handler_source(ename, rng):
    cls = ename.title()
    return f'''"""Handler for {ename} requests."""
from store.models.{ename} import {cls}


def create(registry, record):
    """Validate and store one {ename}; returns the stored dict."""
    rec = {cls}.from_dict(record)
    rec.validate()
    registry.repo("{ename}").put(rec)
    return rec.to_dict()


def fetch(registry, rid):
    return registry.repo("{ename}").get(rid).to_dict()


def remove(registry, rid):
    registry.repo("{ename}").delete(rid)
    return {{"deleted": rid}}


def list_all(registry):
    return [r.to_dict() for r in registry.repo("{ename}").all()]


def search(registry, **filters):
    """Records whose fields equal every filter value, as dicts."""
    out = []
    for rec in registry.repo("{ename}").all():
        if all(getattr(rec, k, None) == v for k, v in filters.items()):
            out.append(rec.to_dict())
    return out


def count(registry):
    return len(registry.repo("{ename}"))
'''


def command_source(ename):
    return f'''"""`{ename}-show`: print one {ename}."""
from core.errors import NotFound


def add_parser(sub):
    s = sub.add_parser("{ename}-show", help="show one {ename}")
    s.add_argument("id")
    return s


def run(registry, args):
    try:
        return {{"status": 200, "body": registry.repo("{ename}").get(args.id).to_dict()}}
    except NotFound as e:
        return {{"status": 404, "body": {{"error": str(e)}}}}
'''


def test_source(ename, prefix, fields):
    cls = ename.title()
    names = [f[0] for f in fields]
    bad = None
    for n, k, c in fields:
        if k in ("int", "cents"):
            bad = (n, "-5", "negative number")
            break
        if k == "enum":
            bad = (n, '"zzz"', "bad choice")
            break
        if k == "bool":
            bad = (n, '"yes"', "non boolean")
            break
    bad_test = ""
    if bad:
        bad_test = f'''
    def test_rejects_{bad[2].replace(" ", "_")}(self):
        rec = new_{ename}(2, {bad[0]}={bad[1]})
        with self.assertRaises(ValidationError):
            rec.validate()
'''
    return f'''import unittest

from api.handlers import {ename} as handler
from core.errors import NotFound, ValidationError
from store.models.{ename} import {cls}, new_{ename}
from store.registry import Registry


class Test{cls}(unittest.TestCase):
    def test_sample_is_valid(self):
        for i in range(8):
            new_{ename}(i).validate()

    def test_required_fields(self):
        rec = new_{ename}(1, {names[0]}=None)
        with self.assertRaises(ValidationError):
            rec.validate()

    def test_roundtrip_dict(self):
        rec = new_{ename}(3)
        self.assertEqual({cls}.from_dict(rec.to_dict()), rec)

    def test_bad_id_prefix(self):
        with self.assertRaises(ValidationError):
            {cls}("zzz-0001", **{cls}.sample(1)).validate()
{bad_test}
    def test_handler_create_fetch_remove(self):
        reg = Registry()
        stored = handler.create(reg, new_{ename}(4).to_dict())
        self.assertEqual(handler.fetch(reg, stored["id"]), stored)
        self.assertEqual(handler.count(reg), 1)
        handler.remove(reg, stored["id"])
        with self.assertRaises(NotFound):
            handler.fetch(reg, stored["id"])

    def test_handler_search(self):
        reg = Registry()
        for i in range(3):
            handler.create(reg, new_{ename}(i).to_dict())
        found = handler.search(reg, {names[0]}=new_{ename}(1).{names[0]})
        self.assertEqual([r["id"] for r in found], ["{prefix}-0001"])

    def test_summary_mentions_id(self):
        self.assertIn("{prefix}-0005", new_{ename}(5).summary())


if __name__ == "__main__":
    unittest.main()
'''


def export_source(ename, fields):
    cls = ename.title()
    kinds = {n: k for n, k, _ in fields}
    names = ["id"] + [n for n, _, _ in fields]
    nums = [n for n, k, _ in fields if k in ("int", "cents")]
    return f'''"""CSV export and import for {ename} records."""
import csv
import io

from store.models.{ename} import {cls}

FIELDS = {tuple(names)!r}
KINDS = {kinds!r}


def header():
    return list(FIELDS)


def row(record):
    data = record.to_dict()
    return [data[f] for f in FIELDS]


def rows(records):
    return [row(r) for r in records]


def to_csv(records):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\\n")
    writer.writerow(header())
    writer.writerows(rows(records))
    return buf.getvalue()


def _convert(name, text):
    if text == "":
        return None
    kind = KINDS.get(name, "str")
    if kind in ("int", "cents"):
        return int(text)
    if kind == "bool":
        return text == "True"
    return text


def from_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for raw in reader:
        data = {{k: _convert(k, v) for k, v in raw.items()}}
        out.append({cls}.from_dict(data))
    return out


def totals(records):
    """Sum of every numeric field."""
    out = {{}}
    for name in {tuple(nums)!r}:
        out[name] = sum(getattr(r, name) or 0 for r in records)
    return out


def filter_rows(records, **equals):
    return [r for r in records if all(getattr(r, k, None) == v for k, v in equals.items())]
'''


PLUGIN_WORDS_A = ["audit", "route", "tariff", "label", "dedupe", "round", "stamp", "geo", "weight", "fraud",
                  "retry", "notify", "tax", "split", "merge", "hold", "priority", "currency", "carrier", "batch"]
PLUGIN_WORDS_B = ["guard", "tagger", "scaler", "filter", "mapper", "checker", "enricher", "limiter", "marker"]
KINDS = ["shipment", "invoice", "payment", "claim", "ticket", "refund", "quote"]


def plugin_source(n, rng):
    a, b = rng.choice(PLUGIN_WORDS_A), rng.choice(PLUGIN_WORDS_B)
    cls = f"Plugin{n:02d}"
    kinds = tuple(sorted(rng.sample(KINDS, rng.randrange(1, 4))))
    pri = 100 + n * 10 + rng.randrange(0, 9)
    bp = rng.choice([250, 500, 750, 1250, 1500])
    limit = rng.randrange(200, 9000)
    cap = rng.randrange(2, 40)
    tags = tuple(rng.sample(["fast", "slow", "bulk", "fragile", "cold", "vip", "manual", "auto", "intl"], 3))
    variant = rng.randrange(4)
    helper = {
        0: f'''def _scale(amount):
    """Scale an amount by {bp} basis points, rounding half up."""
    return (amount * {bp} + 5000) // 10000
''',
        1: f'''def _bucket(value):
    """Group a value into steps of {cap}."""
    return (int(value) // {cap}) * {cap}
''',
        2: f'''def _clip(text, width={cap + 8}):
    text = str(text)
    return text if len(text) <= width else text[:width]
''',
        3: f'''def _over(value):
    return int(value) > {limit}
''',
    }[variant]
    body = {
        0: f'''        amount = event.get("amount_cents", 0)
        event["fee_cents"] = event.get("fee_cents", 0) + _scale(amount)
        return event''',
        1: f'''        event["bucket"] = _bucket(event.get("weight_g", 0))
        event["tags"] = list(event.get("tags", [])) + ["{tags[0]}"]
        return event''',
        2: f'''        event["label"] = _clip(event.get("label", event.get("kind", "")))
        event["tags"] = list(event.get("tags", [])) + ["{tags[1]}"]
        return event''',
        3: f'''        if _over(event.get("amount_cents", 0)):
            event["tags"] = list(event.get("tags", [])) + ["{tags[2]}"]
            event["review"] = True
        return event''',
    }[variant]
    return f'''"""{a.title()} {b}: {rng.choice(["adjusts", "annotates", "checks", "normalises"])} \
{", ".join(kinds)} events (plugin {n:02d})."""
from plugins.registry import Plugin, register

SETTINGS = {{"limit": {limit}, "cap": {cap}, "rate_bp": {bp}, "tags": {tags!r}}}


{helper}

def describe():
    """Human-readable summary of the settings (used by the docs generator)."""
    return ", ".join(f"{{k}}={{v}}" for k, v in sorted(SETTINGS.items()))


@register
class {cls}(Plugin):
    name = "{a}-{b}-{n:02d}"
    priority = {pri}
    kinds = {kinds!r}

    def process(self, event):
{body}

    def settings(self):
        return dict(SETTINGS)

    def explain(self, event):
        """What this plugin would do to an event, without doing it."""
        before = dict(event)
        after = self.process(dict(event))
        return {{k: (before.get(k), after.get(k)) for k in sorted(set(before) | set(after))
                if before.get(k) != after.get(k)}}
'''


def parser_source(n, rng):
    sep = rng.choice([",", ";", "|", "\\t"])
    cols = rng.sample(["id", "ts", "kind", "amount", "site", "ref", "user", "status"], rng.randrange(4, 7))
    return f'''"""Parser {n:02d}: lines of {len(cols)} fields separated by {sep!r}."""
COLUMNS = {tuple(cols)!r}
SEP = "{sep}"


def parse(line):
    """Return a dict for one line, or None when the field count is wrong."""
    parts = line.rstrip("\\n").split(SEP)
    if len(parts) != len(COLUMNS):
        return None
    row = dict(zip(COLUMNS, (p.strip() for p in parts)))
    if "amount" in row:
        try:
            row["amount"] = int(row["amount"])
        except ValueError:
            return None
    return row


def parse_many(lines):
    return [r for r in (parse(l) for l in lines) if r is not None]


def header():
    return SEP.join(COLUMNS)


def format_row(row):
    return SEP.join(str(row.get(c, "")) for c in COLUMNS)
'''


def access_log(rng, n=40000):
    paths = ["/v1/customers", "/v1/shipments", "/v1/invoices", "/v2/orders", "/v2/export", "/v2/quotes",
             "/v1/health", "/v2/tracking", "/v1/carriers", "/v2/claims"]
    weights = [6, 9, 5, 8, 3, 4, 7, 6, 2, 2]
    status = [200] * 40 + [201] * 4 + [204] * 3 + [301] * 2 + [400] * 5 + [404] * 6 + [500] * 2 + [503] * 4
    methods = ["GET"] * 6 + ["POST"] * 3 + ["PUT"] + ["DELETE"]
    pool = [p for p, wt in zip(paths, weights) for _ in range(wt)]
    out = []
    t = 0
    for _ in range(n):
        t += rng.randrange(1, 28)
        day, rest = divmod(t, 86400)
        day = 1 + day % 7
        ts = f"2025-03-{day:02d}T{rest // 3600:02d}:{rest % 3600 // 60:02d}:{rest % 60:02d}Z"
        out.append((t, ts, rng.choice(methods), rng.choice(pool), rng.choice(status),
                    rng.randrange(120, 90000), rng.randrange(2, 1400)))
    out.sort(key=lambda r: r[0])
    # timestamps wrap by day; keep them in the order generated by t so each day appears in order
    lines = [f"{ts} {m} {p} {s} {b} {ms}ms" for _, ts, m, p, s, b, ms in out]
    return "\n".join(lines) + "\n"


def shipments_csv(rng, n=12000):
    carriers = ["northwind", "bluefin", "ardent", "kestrel", "marlow", "oakline"]
    zones = ["local", "national", "intl"]
    statuses = ["created", "in_transit", "delivered", "returned", "lost"]
    out = ["id,customer,carrier,weight_g,zone,status,cost_cents"]
    for i in range(n):
        out.append(f"shi-{i:05d},cus-{rng.randrange(0, 400):04d},{rng.choice(carriers)},"
                   f"{rng.randrange(50, 30000)},{rng.choice(zones)},{rng.choice(statuses)},{rng.randrange(300, 90000)}")
    return "\n".join(out) + "\n"


def audit_jsonl(rng, n=6000):
    actors = ["ana", "ben", "cy", "di", "ed", "fay", "gus", "hal"]
    actions = ["login", "export", "edit", "delete", "approve", "reject", "view"]
    out = []
    for i in range(n):
        out.append(json.dumps({"seq": i, "actor": rng.choice(actors), "action": rng.choice(actions),
                               "target": f"{rng.choice(['cus', 'inv', 'shi', 'pay'])}-{rng.randrange(0, 900):04d}",
                               "ms": rng.randrange(1, 900)}, sort_keys=True))
    return "\n".join(out) + "\n"


def generate(root, seed):
    """Write every generated file below root and return the entity specs."""
    specs = []
    erng = random.Random(seed * 7 + 1)
    for ename, prefix in ENTITIES:
        fields = pick_fields(random.Random(erng.randrange(1 << 30)))
        specs.append((ename, prefix, fields))
        r = random.Random(erng.randrange(1 << 30))
        w(root, f"store/models/{ename}.py", model_source(ename, prefix, fields, r))
        w(root, f"api/handlers/{ename}.py", handler_source(ename, r))
        w(root, f"cli/commands/{ename}.py", command_source(ename))
        w(root, f"tests/test_{ename}.py", test_source(ename, prefix, fields))
        w(root, f"ingest/exports/{ename}.py", export_source(ename, fields))
        # seed data for the command line
        items = []
        for i in range(1, 13 + erng.randrange(0, 30)):
            vals = {n: sample_value(k, n, i, c) for n, k, c in fields}
            items.append(dict(id=f"{prefix}-{i:04d}", **vals))
        w(root, f"data/store/{ename}.json",
          json.dumps({"version": 3, "items": items}, indent=1, sort_keys=True) + "\n")
    names = [s[0] for s in specs]
    w(root, "store/models/__init__.py",
      '"""One model per entity. ENTITIES maps an entity name to its record class."""\n'
      + "".join(f"from store.models.{n} import {n.title()}\n" for n in names)
      + "\nENTITIES = {\n" + "".join(f'    "{n}": {n.title()},\n' for n in names) + "}\n")
    w(root, "api/handlers/__init__.py",
      '"""Entity handlers by name (the order handler is separate: api.handlers.orders)."""\n'
      + "".join(f"from api.handlers import {n}\n" for n in names)
      + "\nHANDLERS = {\n" + "".join(f'    "{n}": {n},\n' for n in names) + "}\n")
    w(root, "cli/commands/__init__.py",
      '"""Per-entity commands: `<entity>-show`."""\n'
      + "".join(f"from cli.commands import {n}\n" for n in names)
      + "\nCOMMANDS = {\n" + "".join(f'    "{n}": {n},\n' for n in names) + "}\n")
    w(root, "ingest/exports/__init__.py", '"""CSV export and import per entity."""\n')
    w(root, "tests/test_exports.py", '''import importlib
import unittest

from store.models import ENTITIES


class TestExports(unittest.TestCase):
    def test_csv_roundtrip_every_entity(self):
        for name, cls in sorted(ENTITIES.items()):
            mod = importlib.import_module("ingest.exports." + name)
            recs = [cls(f"{cls.prefix}-{i:04d}", **cls.sample(i)) for i in range(1, 6)]
            again = mod.from_csv(mod.to_csv(recs))
            self.assertEqual(again, recs, name)
            self.assertEqual(mod.header()[0], "id")

    def test_totals_are_integers(self):
        for name, cls in sorted(ENTITIES.items()):
            mod = importlib.import_module("ingest.exports." + name)
            recs = [cls(f"{cls.prefix}-{i:04d}", **cls.sample(i)) for i in range(1, 4)]
            for value in mod.totals(recs).values():
                self.assertIsInstance(value, int)

    def test_filter_rows(self):
        for name, cls in sorted(ENTITIES.items()):
            mod = importlib.import_module("ingest.exports." + name)
            recs = [cls(f"{cls.prefix}-{i:04d}", **cls.sample(i)) for i in range(1, 4)]
            self.assertEqual(mod.filter_rows(recs, id=recs[0].id), recs[:1])


if __name__ == "__main__":
    unittest.main()
''')
    prng = random.Random(seed * 11 + 3)
    for n in range(60):
        w(root, f"plugins/plugin_{n:02d}.py", plugin_source(n, random.Random(prng.randrange(1 << 30))))
    w(root, "tests/test_plugins.py", '''import unittest

from plugins import registry


class TestEveryPlugin(unittest.TestCase):
    def setUp(self):
        registry.load_all()

    def test_sixty_plugins_registered(self):
        self.assertEqual(len(registry.PLUGINS), 60)

    def test_each_plugin_keeps_the_kind(self):
        for p in registry.enabled():
            for kind in p.kinds:
                out = p.process({"kind": kind, "amount_cents": 1000, "weight_g": 700, "label": "x" * 90})
                self.assertEqual(out["kind"], kind)

    def test_settings_are_complete(self):
        import importlib
        for p in registry.enabled():
            mod = importlib.import_module(type(p).__module__)
            self.assertEqual(set(p.settings()), {"limit", "cap", "rate_bp", "tags"})
            self.assertTrue(mod.describe())

    def test_priorities_are_unique_enough(self):
        pri = [p.priority for p in registry.enabled()]
        self.assertEqual(len(pri), len(set(pri)))

    def test_chain_runs_for_every_kind(self):
        for kind in ("shipment", "invoice", "payment", "claim", "ticket", "refund", "quote"):
            out = registry.run_chain({"kind": kind, "amount_cents": 5000, "weight_g": 900})
            self.assertEqual(out["kind"], kind)


if __name__ == "__main__":
    unittest.main()
''')
    for n in range(16):
        w(root, f"ingest/parsers/p_{n:02d}.py", parser_source(n, random.Random(seed * 13 + n)))
    w(root, "ingest/parsers/__init__.py", '"""Line parsers for the partner formats."""\n')
    w(root, "tests/test_parsers.py", '''import importlib
import unittest


class TestParsers(unittest.TestCase):
    def test_roundtrip_every_parser(self):
        for n in range(16):
            mod = importlib.import_module(f"ingest.parsers.p_{n:02d}")
            row = {c: ("5" if c == "amount" else f"{c}1") for c in mod.COLUMNS}
            line = mod.format_row(row)
            parsed = mod.parse(line)
            first = mod.COLUMNS[0]
            if first != "amount":
                self.assertEqual(parsed[first], row[first])
            if "amount" in parsed:
                self.assertEqual(parsed["amount"], 5)
            self.assertIsNone(mod.parse("a" + mod.SEP + "b"))

    def test_parse_many_skips_bad_lines(self):
        mod = importlib.import_module("ingest.parsers.p_00")
        good = mod.format_row({c: ("7" if c == "amount" else "v") for c in mod.COLUMNS})
        self.assertEqual(len(mod.parse_many([good, "bad", good])), 2)


if __name__ == "__main__":
    unittest.main()
''')
    drng = random.Random(seed * 17 + 5)
    w(root, "logs/access.log", access_log(drng))
    w(root, "data/shipments.csv", shipments_csv(drng))
    w(root, "data/audit.jsonl", audit_jsonl(drng))
    w(root, "tests/test_seed_data.py", '''import os
import unittest

from store.models import ENTITIES
from store.registry import Registry


class TestSeedData(unittest.TestCase):
    def test_every_seeded_record_is_valid(self):
        reg = Registry(os.path.join("data", "store"))
        for name in reg.entities():
            repo = reg.repo(name)
            self.assertGreater(len(repo), 5, name)
            for rec in repo.all():
                rec.validate()

    def test_entity_count(self):
        self.assertEqual(len(ENTITIES), 24)


if __name__ == "__main__":
    unittest.main()
''')
    return specs
