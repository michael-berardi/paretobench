import re
import unittest

from core.errors import ValidationError

CASES = ["ab-12", " x y z 9 ", "abcdefgh1234", "AB12CD34EF56GH78", "a-b-c-d-e-f-g-h-i-j", "ab", "",
         "!!!!", "abcdefgh1", "ABCDEFGHIJKLMNOPQ", 12345, None, "ab 12 cd"]


def reference(value):
    if not isinstance(value, str):
        raise ValidationError("sku must be text")
    cleaned = re.sub(r"[^A-Z0-9]+", "", value.upper())
    if not 4 <= len(cleaned) <= 16:
        raise ValidationError("sku must have 4 to 16 letters or digits")
    return cleaned[:8] + "-" + cleaned[8:] if len(cleaned) > 8 else cleaned


def outcome(fn, value):
    try:
        return ("ok", fn(value))
    except ValidationError as e:
        return ("err", str(e))


class TestSharedHelper(unittest.TestCase):
    def test_core_function_exists_and_matches(self):
        from core.skus import normalize_sku
        for c in CASES:
            self.assertEqual(outcome(normalize_sku, c), outcome(reference, c), repr(c))

    def test_four_public_names_keep_their_behaviour(self):
        from api.skus import clean_sku
        from cli.skus import sku_key
        from ingest.skus import canon_sku
        from store.skus import normalize_sku
        for fn in (clean_sku, sku_key, canon_sku, normalize_sku):
            for c in CASES:
                self.assertEqual(outcome(fn, c), outcome(reference, c), (fn.__module__, repr(c)))

    def test_wrappers_still_work(self):
        from api.skus import sku_label
        from cli.skus import sku_sort
        from ingest.skus import canon_rows, canon_slug
        from store.skus import sku_exists
        self.assertEqual(sku_label("ab 12"), "SKU AB12")
        self.assertEqual(sku_sort(["zz99", "aa11", "mm55"]), ["aa11", "mm55", "zz99"])
        self.assertEqual(canon_rows([{"sku": "abcdefgh12"}]), ["ABCDEFGH-12"])
        self.assertTrue(sku_exists({"AB12"}, "ab-12"))
        self.assertEqual(canon_slug("A B"), "a-b")  # a slug is not a SKU: untouched

    def test_slug_helpers_in_core_text_are_different_on_purpose(self):
        from core.text import normalize_slug, slugify
        self.assertEqual(normalize_slug("A_b c"), "a_b-c")
        self.assertEqual(slugify("A_b c"), "a-b-c")


if __name__ == "__main__":
    unittest.main()
