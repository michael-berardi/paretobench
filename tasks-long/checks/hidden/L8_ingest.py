import calendar
import time
import unittest

from core.errors import ValidationError


def epoch(ts):
    return calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))


def iso(e):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(e))


class TestWindows(unittest.TestCase):
    def test_counts_match_independent_calculation(self):
        from ingest.windows import window_counts
        times = ["2025-03-04T10:00:00Z", "2025-03-04T10:00:59Z", "2025-03-04T10:01:00Z",
                 "2025-03-04T10:04:59Z", "2025-03-04T10:05:00Z", "2025-03-05T00:00:01Z"]
        entries = [{"ts": t, "path": "/x", "status": 200} for t in times]
        for seconds in (60, 300, 3600, 86400):
            want = {}
            for t in times:
                start = epoch(t) // seconds * seconds
                want[start] = want.get(start, 0) + 1
            got = window_counts(entries, seconds)
            self.assertEqual(got, [(iso(s), n) for s, n in sorted(want.items())], seconds)

    def test_windows_are_aligned_to_the_epoch_and_sorted(self):
        from ingest.windows import window_counts
        entries = [{"ts": "2025-03-04T10:07:30Z"}, {"ts": "2025-03-04T10:02:00Z"}]
        self.assertEqual(window_counts(entries, 300), [("2025-03-04T10:00:00Z", 1), ("2025-03-04T10:05:00Z", 1)])

    def test_empty_input(self):
        from ingest.windows import window_counts
        self.assertEqual(window_counts([], 60), [])

    def test_validation(self):
        from ingest.windows import window_counts
        for bad in (0, -5, 1.5, "60", True):
            with self.assertRaises(ValidationError):
                window_counts([{"ts": "2025-03-04T10:00:00Z"}], bad)
        with self.assertRaises(ValidationError):
            window_counts([{"ts": "yesterday"}], 60)

    def test_window_start(self):
        from ingest.windows import window_start
        self.assertEqual(window_start("2025-03-04T10:07:30Z", 300), "2025-03-04T10:05:00Z")


if __name__ == "__main__":
    unittest.main()
