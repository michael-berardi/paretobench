import re
from _ref import *

grep(r"A-Z0-9", ".")
texts = {}
for rel in ("store/skus.py", "api/skus.py", "ingest/skus.py", "cli/skus.py"):
    texts[rel] = read(rel)
read("core/text.py")
read("tests/test_skus.py")
write("core/skus.py", '''"""One SKU normaliser for every package."""
import re

from core.errors import ValidationError

_SKU_JUNK = re.compile(r"[^A-Z0-9]+")


def normalize_sku(value):
    """Upper-case, strip separators, validate length 4..16, dash after 8."""
    if not isinstance(value, str):
        raise ValidationError("sku must be text")
    cleaned = _SKU_JUNK.sub("", value.upper())
    if not 4 <= len(cleaned) <= 16:
        raise ValidationError("sku must have 4 to 16 letters or digits")
    return cleaned[:8] + "-" + cleaned[8:] if len(cleaned) > 8 else cleaned
''')
for rel, text in texts.items():
    start = text.index("import re")
    end = text.index("cleaned\n\n\n") + len("cleaned\n")
    name = re.search(r"def (\w+)\(value\)", text).group(1)
    imp = "from core.skus import normalize_sku" + ("" if name == "normalize_sku" else f" as {name}") + "\n"
    edit(rel, text[start:end], imp)
sh("python3 -B -m unittest discover -s tests -t .")
grep(r"A-Z0-9", ".")
